# Real-Time Object & Target Tracker Engine

## Project Specs
- **Engine**: OpenCV, NumPy, Pytest
- **Environment**: Python managed via `uv`
- **Target Logic**: Track a color range (HSV space) or moving object, derive its bounding box, calculate centroid coordinates `(x, y)`, track movement velocity vectors, and render performance statistics (FPS) on frames.
- **Components**:
  1. `tracking_engine/core.py`: ObjectTracker class taking `(hsv_lower, hsv_upper)` boundaries, processing raw NumPy image matrices, returning bounding box and centroid.
  2. `tracking_engine/benchmark.py`: Decorator/Context manager to log rolling average processing time per frame.
  3. `tests/`: Mock synthetic frames using NumPy shapes (e.g., solid circles on black background) to verify centroid localization accuracy deterministically using pytest.
  4. Packaging: Standard `pyproject.toml` environment configuration.