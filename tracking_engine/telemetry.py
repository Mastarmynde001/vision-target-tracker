"""Telemetry streaming module for UDP network datagrams and UART serial communication."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import json
import queue
import socket
import sys
import threading
import time

try:
    import serial
except ImportError:
    serial = None


class BaseTelemetryBroadcaster(ABC):
    """Abstract base class for non-blocking asynchronous telemetry dispatch."""

    def __init__(self, queue_size: int = 100) -> None:
        self.queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start background worker thread for asynchronous packet dispatch."""
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def send(self, payload: Dict[str, Any]) -> None:
        """Enqueue telemetry payload without blocking video processing thread.

        Drops oldest packet if queue is full to prevent backpressure.
        """
        if not self._running:
            return
        try:
            self.queue.put_nowait(payload)
        except queue.Full:
            try:
                self.queue.get_nowait()  # Drop stale packet
                self.queue.put_nowait(payload)
            except (queue.Empty, queue.Full):
                pass

    def stop(self) -> None:
        """Stop background worker thread gracefully."""
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)

    def _worker_loop(self) -> None:
        """Internal background queue consumer loop."""
        while self._running:
            try:
                payload = self.queue.get(timeout=0.05)
                self._dispatch(payload)
                self.queue.task_done()
            except queue.Empty:
                continue

    @abstractmethod
    def _dispatch(self, payload: Dict[str, Any]) -> None:
        """Dispatch packet over network socket or serial transport."""
        pass


class UDPTelemetryBroadcaster(BaseTelemetryBroadcaster):
    """UDP network datagram telemetry broadcaster."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5005, queue_size: int = 100) -> None:
        super().__init__(queue_size=queue_size)
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None

    def start(self) -> None:
        """Initialize socket and start background thread."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except OSError as e:
            print(f"Warning: UDP socket initialization failed: {e}", file=sys.stderr)
            self.socket = None
        super().start()

    def _dispatch(self, payload: Dict[str, Any]) -> None:
        if self.socket is None:
            return
        raw_bytes = json.dumps(payload).encode("utf-8")
        try:
            self.socket.sendto(raw_bytes, (self.host, self.port))
        except OSError:
            pass

    def stop(self) -> None:
        super().stop()
        if self.socket:
            self.socket.close()
            self.socket = None


class SerialTelemetryBroadcaster(BaseTelemetryBroadcaster):
    """UART Serial telemetry broadcaster for microcontrollers with fallback support."""

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 115200,
        queue_size: int = 100,
    ) -> None:
        super().__init__(queue_size=queue_size)
        self.port_name = port
        self.baudrate = baudrate
        self.serial_conn: Any = None

    def start(self) -> None:
        """Open serial port connection if pyserial is available."""
        if serial is None:
            print("Warning: pyserial is not installed. Serial telemetry disabled.", file=sys.stderr)
            self.serial_conn = None
        else:
            try:
                self.serial_conn = serial.Serial(self.port_name, self.baudrate, timeout=0.1)
            except Exception as e:
                print(f"Warning: Serial port '{self.port_name}' open failed: {e}", file=sys.stderr)
                self.serial_conn = None

        super().start()

    def _dispatch(self, payload: Dict[str, Any]) -> None:
        if self.serial_conn is not None:
            try:
                if getattr(self.serial_conn, "is_open", False):
                    line = json.dumps(payload) + "\n"
                    self.serial_conn.write(line.encode("utf-8"))
            except Exception:
                pass

    def stop(self) -> None:
        super().stop()
        if self.serial_conn is not None:
            try:
                if getattr(self.serial_conn, "is_open", False):
                    self.serial_conn.close()
            except Exception:
                pass
            self.serial_conn = None
