"""Tracking Engine package initialization."""

from .core import ObjectTracker, TrackedTarget
from .benchmark import FPSBenchmark
from .utils import draw_target_annotations, draw_fps_overlay, create_side_by_side
from .telemetry import (
    BaseTelemetryBroadcaster,
    UDPTelemetryBroadcaster,
    SerialTelemetryBroadcaster,
)

__all__ = [
    "ObjectTracker",
    "TrackedTarget",
    "FPSBenchmark",
    "draw_target_annotations",
    "draw_fps_overlay",
    "create_side_by_side",
    "BaseTelemetryBroadcaster",
    "UDPTelemetryBroadcaster",
    "SerialTelemetryBroadcaster",
]
