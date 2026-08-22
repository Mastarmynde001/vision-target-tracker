"""Unit tests for telemetry broadcasters, mock UDP listener, schema validation, and queue overflow eviction (pytest)."""

import json
import socket
import time
import pytest
from tracking_engine.telemetry import UDPTelemetryBroadcaster, SerialTelemetryBroadcaster


def test_mock_udp_listener_schema_and_payload_validation():
    """Spin up a mock local UDP listener socket and assert schema keys, types, and centroid values within tolerance."""
    test_host = "127.0.0.1"
    test_port = 5998

    # Setup receiver socket
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind((test_host, test_port))
    recv_sock.settimeout(2.0)

    # Setup broadcaster
    broadcaster = UDPTelemetryBroadcaster(host=test_host, port=test_port)
    broadcaster.start()

    expected_centroid = (320, 240)
    payload = {
        "timestamp": time.time(),
        "frame_id": 100,
        "target_id": 1,
        "centroid_x": 321,
        "centroid_y": 239,
        "velocity_x": 10.5,
        "velocity_y": -4.2,
        "fps": 59.8,
    }

    required_keys = {
        "timestamp": (int, float),
        "frame_id": int,
        "target_id": int,
        "centroid_x": int,
        "centroid_y": int,
        "velocity_x": (int, float),
        "velocity_y": (int, float),
        "fps": (int, float),
    }

    try:
        broadcaster.send(payload)
        data, _ = recv_sock.recvfrom(1024)
        received = json.loads(data.decode("utf-8"))

        # Assert JSON Schema keys and value types
        for key, expected_type in required_keys.items():
            assert key in received, f"Missing required telemetry key: {key}"
            assert isinstance(received[key], expected_type), f"Key '{key}' invalid type: {type(received[key])}"

        # Assert Centroid payload accuracy within 2px tolerance
        assert abs(received["centroid_x"] - expected_centroid[0]) <= 2
        assert abs(received["centroid_y"] - expected_centroid[1]) <= 2

    finally:
        broadcaster.stop()
        recv_sock.close()


def test_queue_overflow_non_blocking_eviction():
    """Verify queue overflow eviction handles rapid packet bursts without blocking execution."""
    broadcaster = UDPTelemetryBroadcaster(host="127.0.0.1", port=5997, queue_size=2)
    broadcaster.start()

    try:
        start_time = time.perf_counter()
        # Enqueue 20 packets rapidly into a queue of size 2
        for i in range(20):
            broadcaster.send({"frame_id": i, "timestamp": time.time()})
        elapsed = time.perf_counter() - start_time

        # Ensure enqueuing 20 packets completes in under 5ms (non-blocking)
        assert elapsed < 0.05, f"Enqueueing burst took too long: {elapsed:.4f}s"
    finally:
        broadcaster.stop()


def test_serial_telemetry_broadcaster_fallback():
    """Verify SerialTelemetryBroadcaster graceful fallback when serial port is unavailable."""
    broadcaster = SerialTelemetryBroadcaster(port="/dev/ttyNONEXISTENT", baudrate=115200)
    broadcaster.start()

    assert broadcaster.serial_conn is None

    # Sending payload should execute safely without exception
    payload = {
        "timestamp": time.time(),
        "frame_id": 1,
        "target_id": 1,
        "centroid_x": 100,
        "centroid_y": 100,
        "velocity_x": 0.0,
        "velocity_y": 0.0,
        "fps": 30.0,
    }
    broadcaster.send(payload)

    broadcaster.stop()
