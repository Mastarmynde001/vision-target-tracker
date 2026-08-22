"""Core vision target tracking module with HSV color thresholding, contour analysis, and velocity tracking."""

import time
from dataclasses import dataclass
from typing import List, Optional, Tuple
import cv2
import numpy as np


@dataclass
class TrackedTarget:
    """Dataclass encapsulating extracted target metrics.

    Attributes:
        centroid: (cx, cy) pixel coordinates.
        bbox: (x, y, width, height) bounding rectangle.
        area: Contour area in square pixels.
        velocity: (vx, vy) pixel velocity vector.
        contour: Raw OpenCV contour array.
    """
    centroid: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    area: float
    velocity: Tuple[float, float]
    contour: np.ndarray


class ObjectTracker:
    """HSV color mask target tracker with contour analysis, centroid calculation, and velocity estimation.

    Attributes:
        hsv_lower (np.ndarray): Lower bound HSV threshold matrix (shape: (3,)).
        hsv_upper (np.ndarray): Upper bound HSV threshold matrix (shape: (3,)).
        min_area (float): Minimum contour area threshold in pixels to filter noise.
        blur_kernel (Tuple[int, int]): Kernel size for Gaussian blur noise suppression.
        last_centroid (Optional[Tuple[int, int]]): Centroid position from previous frame.
        last_timestamp (Optional[float]): Timestamp of previous frame.
    """

    def __init__(
        self,
        hsv_lower: Tuple[int, int, int] = (35, 50, 50),
        hsv_upper: Tuple[int, int, int] = (85, 255, 255),
        min_area: float = 500.0,
        blur_kernel: Tuple[int, int] = (11, 11),
    ) -> None:
        """Initialize ObjectTracker with color thresholds and noise filtering parameters."""
        self.hsv_lower = np.array(hsv_lower, dtype=np.uint8)
        self.hsv_upper = np.array(hsv_upper, dtype=np.uint8)
        self.min_area = min_area
        self.blur_kernel = blur_kernel
        self.last_centroid: Optional[Tuple[int, int]] = None
        self.last_timestamp: Optional[float] = None

    def set_hsv_bounds(
        self,
        hsv_lower: Tuple[int, int, int],
        hsv_upper: Tuple[int, int, int]
    ) -> None:
        """Update lower and upper HSV color space threshold boundaries."""
        self.hsv_lower = np.array(hsv_lower, dtype=np.uint8)
        self.hsv_upper = np.array(hsv_upper, dtype=np.uint8)

    def create_mask(self, frame: np.ndarray) -> np.ndarray:
        """Generate binary mask by applying Gaussian blur, HSV transformation, inRange masking,
        and morphological opening/closing operations.

        Args:
            frame: Input image matrix in BGR format (shape: (H, W, 3), uint8).

        Returns:
            Binary mask matrix (shape: (H, W), uint8).
        """
        blurred = cv2.GaussianBlur(frame, self.blur_kernel, 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def compute_velocity(
        self,
        current_centroid: Tuple[int, int],
        current_time: Optional[float] = None
    ) -> Tuple[float, float]:
        """Compute pixel velocity vector (vx, vy) based on displacement from previous frame.

        Args:
            current_centroid: Current (cx, cy) pixel coordinates.
            current_time: Current frame timestamp in seconds.

        Returns:
            Velocity displacement vector (vx, vy).
        """
        if current_time is None:
            current_time = time.perf_counter()

        if self.last_centroid is None or self.last_timestamp is None:
            velocity = (0.0, 0.0)
        else:
            dt = current_time - self.last_timestamp
            if dt > 0:
                vx = (current_centroid[0] - self.last_centroid[0]) / dt
                vy = (current_centroid[1] - self.last_centroid[1]) / dt
            else:
                vx = float(current_centroid[0] - self.last_centroid[0])
                vy = float(current_centroid[1] - self.last_centroid[1])
            velocity = (vx, vy)

        self.last_centroid = current_centroid
        self.last_timestamp = current_time
        return velocity

    def track(
        self,
        frame: np.ndarray,
        timestamp: Optional[float] = None
    ) -> List[TrackedTarget]:
        """Process BGR image frame, extract matching targets sorted by area descending.

        Args:
            frame: Input raw frame matrix (BGR, shape (H, W, 3), uint8).
            timestamp: Timestamp in seconds associated with frame.

        Returns:
            List of detected target objects matching criteria.
        """
        mask = self.create_mask(frame)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        raw_targets = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area:
                continue

            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue

            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            bbox = cv2.boundingRect(cnt)
            raw_targets.append((cnt, area, (cx, cy), bbox))

        raw_targets.sort(key=lambda t: t[1], reverse=True)

        tracked_targets: List[TrackedTarget] = []
        for i, (cnt, area, centroid, bbox) in enumerate(raw_targets):
            # Velocity is tracked for the primary (largest) target
            if i == 0:
                vel = self.compute_velocity(centroid, timestamp)
            else:
                vel = (0.0, 0.0)

            tracked_targets.append(
                TrackedTarget(
                    centroid=centroid,
                    bbox=bbox,
                    area=area,
                    velocity=vel,
                    contour=cnt,
                )
            )

        if not tracked_targets:
            self.reset_tracker()

        return tracked_targets

    def track_primary(
        self,
        frame: np.ndarray,
        timestamp: Optional[float] = None
    ) -> Optional[TrackedTarget]:
        """Convenience method returning the largest detected target in frame or None."""
        targets = self.track(frame, timestamp)
        return targets[0] if targets else None

    def reset_tracker(self) -> None:
        """Reset internal temporal tracking state (previous centroid and timestamp)."""
        self.last_centroid = None
        self.last_timestamp = None
