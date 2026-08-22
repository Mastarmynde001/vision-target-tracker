"""Unit tests for tracking_engine core using synthetic frames (pytest)."""

import pytest
import numpy as np
import cv2
from tracking_engine.core import ObjectTracker, TrackedTarget
from tracking_engine.benchmark import FPSBenchmark
from tracking_engine.utils import draw_target_annotations, draw_fps_overlay, create_side_by_side


def create_synthetic_circle_frame(
    width: int = 300,
    height: int = 300,
    center: tuple = (100, 100),
    radius: int = 25,
    bgr_color: tuple = (255, 255, 255),
) -> np.ndarray:
    """Generate a synthetic black NumPy array containing a circle."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.circle(frame, center, radius, bgr_color, -1)
    return frame


def test_tracker_initialization():
    tracker = ObjectTracker(hsv_lower=(0, 0, 200), hsv_upper=(180, 30, 255))
    assert tracker.min_area == 500.0
    assert tracker.hsv_lower.shape == (3,)
    assert tracker.hsv_upper.shape == (3,)


def test_white_circle_centroid_detection_accuracy():
    """Verify centroid detection accuracy on a synthetic white circle centered at (100, 100)."""
    target_center = (100, 100)
    radius = 30
    frame = create_synthetic_circle_frame(center=target_center, radius=radius, bgr_color=(255, 255, 255))

    # White in HSV space has low saturation and high value
    tracker = ObjectTracker(hsv_lower=(0, 0, 200), hsv_upper=(180, 30, 255), min_area=100.0)
    target = tracker.track_primary(frame)

    assert target is not None
    assert isinstance(target, TrackedTarget)

    cx, cy = target.centroid
    # Verify output centroid falls within 2 pixels of target (100, 100)
    assert abs(cx - target_center[0]) <= 2, f"Centroid X {cx} deviated by more than 2px from {target_center[0]}"
    assert abs(cy - target_center[1]) <= 2, f"Centroid Y {cy} deviated by more than 2px from {target_center[1]}"


def test_bounding_box_extraction():
    """Test bounding box utility and dimensions for target circle centered at (100, 100)."""
    target_center = (100, 100)
    radius = 30
    frame = create_synthetic_circle_frame(center=target_center, radius=radius, bgr_color=(255, 255, 255))

    tracker = ObjectTracker(hsv_lower=(0, 0, 200), hsv_upper=(180, 30, 255), min_area=100.0)
    target = tracker.track_primary(frame)

    assert target is not None
    x, y, w, h = target.bbox
    # Expected bounding box around (100, 100) with radius 30 is roughly x=70, y=70, w=60, h=60
    assert abs((x + w / 2) - target_center[0]) <= 2
    assert abs((y + h / 2) - target_center[1]) <= 2
    assert abs(w - (2 * radius)) <= 4
    assert abs(h - (2 * radius)) <= 4


def test_velocity_vector_tracking():
    """Verify 2D velocity vector tracking across consecutive frames."""
    tracker = ObjectTracker(hsv_lower=(0, 0, 200), hsv_upper=(180, 30, 255), min_area=100.0)

    # Frame 1: circle centered at (100, 100), t = 1.0s
    frame1 = create_synthetic_circle_frame(center=(100, 100))
    target1 = tracker.track_primary(frame1, timestamp=1.0)
    assert target1 is not None
    assert target1.velocity == (0.0, 0.0)

    # Frame 2: circle moved to (140, 120), t = 2.0s
    frame2 = create_synthetic_circle_frame(center=(140, 120))
    target2 = tracker.track_primary(frame2, timestamp=2.0)
    assert target2 is not None

    vx, vy = target2.velocity
    assert abs(vx - 40.0) <= 2.0
    assert abs(vy - 20.0) <= 2.0


def test_fps_benchmark_profiler():
    """Test FPSBenchmark profiler timing, properties, decorator, and summary generation."""
    benchmark = FPSBenchmark(window_size=10)
    assert benchmark.fps == 0.0
    assert benchmark.latency_ms == 0.0

    # Test context manager interface
    with benchmark:
        _ = np.zeros((100, 100), dtype=np.uint8)

    assert benchmark.total_frames == 1
    assert benchmark.fps > 0.0
    assert benchmark.latency_ms > 0.0

    # Test decorator interface
    @benchmark
    def dummy_func():
        return True

    res = dummy_func()
    assert res is True
    assert benchmark.total_frames == 2

    summary = benchmark.get_summary()
    assert summary["total_frames"] == 2
    assert "avg_fps" in summary
    assert "avg_latency_ms" in summary
