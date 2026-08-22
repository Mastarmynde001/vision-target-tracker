"""Visualization and overlay annotation utilities for vision target tracking."""

from typing import Tuple
import cv2
import numpy as np
from .core import TrackedTarget


def draw_target_annotations(
    frame: np.ndarray,
    target: TrackedTarget,
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
    draw_velocity: bool = True,
) -> np.ndarray:
    """Render bounding box rectangle, centroid marker crosshair, text labels, and velocity vector on frame.

    Args:
        frame: Original BGR image matrix (shape: (H, W, 3), uint8).
        target: Tracked object containing centroid, bbox, area, velocity.
        color: BGR color tuple for drawing annotations. Default green (0, 255, 0).
        thickness: Line thickness in pixels for shapes. Default 2.
        draw_velocity: Whether to draw velocity directional vector arrow. Default True.

    Returns:
        Annotated copy of input frame (shape: (H, W, 3), uint8).
    """
    annotated = frame.copy()
    x, y, w, h = target.bbox
    cx, cy = target.centroid

    # 1. Bounding Box
    cv2.rectangle(annotated, (x, y), (x + w, y + h), color, thickness)

    # 2. Target Centroid Crosshair
    cv2.drawMarker(
        annotated,
        (cx, cy),
        color,
        markerType=cv2.MARKER_CROSS,
        markerSize=15,
        thickness=thickness,
    )

    # 3. Label Text
    vx, vy = target.velocity
    label = f"Pos: ({cx},{cy}) | Area: {int(target.area)}"
    cv2.putText(
        annotated,
        label,
        (x, max(y - 10, 20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1 if thickness == 1 else thickness - 1,
        cv2.LINE_AA,
    )

    # 4. Velocity Vector Arrow
    if draw_velocity and (abs(vx) > 0.1 or abs(vy) > 0.1):
        # Scale velocity vector for visual clarity
        scale = 0.5
        end_point = (int(cx + vx * scale), int(cy + vy * scale))
        cv2.arrowedLine(
            annotated,
            (cx, cy),
            end_point,
            (0, 0, 255),  # Red velocity arrow
            thickness,
            tipLength=0.3,
        )

    return annotated


def draw_fps_overlay(
    frame: np.ndarray,
    fps: float,
    latency_ms: float,
    position: Tuple[int, int] = (10, 30),
    color: Tuple[int, int, int] = (0, 255, 255),
) -> np.ndarray:
    """Draw performance statistics (FPS & Latency in ms) on frame top-left or designated position.

    Args:
        frame: Image matrix (shape: (H, W, 3), uint8).
        fps: Calculated frames per second value.
        latency_ms: Frame processing latency in milliseconds.
        position: (x, y) baseline pixel coordinates for text placement. Default (10, 30).
        color: BGR color tuple for text overlay. Default cyan (0, 255, 255).

    Returns:
        Copy of input frame with performance overlay.
    """
    annotated = frame.copy()
    text = f"FPS: {fps:.1f} | Latency: {latency_ms:.1f}ms"
    cv2.putText(
        annotated,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2,
        cv2.LINE_AA,
    )
    return annotated


def create_side_by_side(frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Construct a horizontal side-by-side composite of annotated BGR frame and 3-channel colorized binary mask.

    Args:
        frame: Color BGR image (shape: (H, W, 3), uint8).
        mask: Single-channel binary mask image (shape: (H, W), uint8).

    Returns:
        Horizontal concatenation matrix (shape: (H, W*2, 3), uint8).
    """
    if len(mask.shape) == 2:
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    else:
        mask_bgr = mask
    return np.hstack((frame, mask_bgr))
