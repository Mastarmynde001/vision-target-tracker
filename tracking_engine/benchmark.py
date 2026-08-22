"""FPS & processing latency profiler module."""

import functools
import time
from collections import deque
from typing import Any, Callable, Dict, Optional


class FPSBenchmark:
    """Frame rate and processing latency profiler with rolling window statistics.

    Supports context manager pattern, decorator syntax, and manual timing calls.

    Attributes:
        window_size (int): Size of rolling sample window for averaging.
        latencies (deque[float]): Double-ended queue holding latencies in seconds.
        total_frames (int): Cumulative count of processed frames.
    """

    def __init__(self, window_size: int = 30) -> None:
        """Initialize FPSBenchmark profiler with specified sample window size."""
        self.window_size = window_size
        self.latencies: deque[float] = deque(maxlen=window_size)
        self.total_frames = 0
        self.start_time = time.perf_counter()
        self._frame_start_time: Optional[float] = None

    def start_frame(self) -> None:
        """Mark start timestamp for processing current frame."""
        self._frame_start_time = time.perf_counter()

    def end_frame(self) -> float:
        """Mark end timestamp for frame processing, append latency, and return latency in seconds."""
        if self._frame_start_time is None:
            raise RuntimeError("start_frame() must be called before end_frame()")
        latency = time.perf_counter() - self._frame_start_time
        self.latencies.append(latency)
        self.total_frames += 1
        self._frame_start_time = None
        return latency

    def __enter__(self) -> "FPSBenchmark":
        """Context manager entry point."""
        self.start_frame()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit point."""
        self.end_frame()

    def __call__(self, func: Callable) -> Callable:
        """Decorator interface to profile execution time of target function."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper

    @property
    def fps(self) -> float:
        """Compute rolling average Frames Per Second (FPS)."""
        if not self.latencies:
            return 0.0
        avg_latency = sum(self.latencies) / len(self.latencies)
        return 1.0 / avg_latency if avg_latency > 0 else 0.0

    @property
    def latency_ms(self) -> float:
        """Compute rolling average latency per frame in milliseconds."""
        if not self.latencies:
            return 0.0
        avg_latency = sum(self.latencies) / len(self.latencies)
        return avg_latency * 1000.0

    def get_summary(self) -> Dict[str, Any]:
        """Generate performance summary dictionary."""
        elapsed = time.perf_counter() - self.start_time
        return {
            "total_frames": self.total_frames,
            "elapsed_sec": round(elapsed, 2),
            "avg_fps": round(self.fps, 2),
            "avg_latency_ms": round(self.latency_ms, 2),
        }
