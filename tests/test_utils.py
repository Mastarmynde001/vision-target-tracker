"""Draw overlay verification tests (pytest)."""

import pytest
import numpy as np
from tracking_engine.core import TrackedTarget
from tracking_engine.utils import draw_target_annotations, draw_fps_overlay, create_side_by_side


def test_draw_target_annotations_modifies_frame():
    frame = np.zeros((400, 600, 3), dtype=np.uint8)
    target = TrackedTarget(
        centroid=(240, 190),
        bbox=(200, 150, 80, 80),
        area=6400.0,
        velocity=(10.0, -5.0),
        contour=np.array([[[200, 150]], [[280, 150]], [[280, 230]], [[200, 230]]])
    )

    annotated = draw_target_annotations(frame, target, color=(0, 255, 0), draw_velocity=True)
    assert annotated.shape == frame.shape
    assert not np.array_equal(annotated, frame)


def test_draw_fps_overlay():
    frame = np.zeros((400, 600, 3), dtype=np.uint8)
    annotated = draw_fps_overlay(frame, fps=30.5, latency_ms=12.4)
    assert annotated.shape == frame.shape
    assert not np.array_equal(annotated, frame)


def test_create_side_by_side():
    frame = np.zeros((400, 600, 3), dtype=np.uint8)
    mask = np.zeros((400, 600), dtype=np.uint8)

    composite = create_side_by_side(frame, mask)
    assert composite.shape == (400, 1200, 3)
