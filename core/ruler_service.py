"""Framework-free measurement helpers for the React/Tauri ruler tool."""

from __future__ import annotations

import math


def measure_distance(x1: float, y1: float, x2: float, y2: float) -> dict[str, float]:
    values = (x1, y1, x2, y2)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("ruler coordinates must be finite numbers")
    dx = x2 - x1
    dy = y2 - y1
    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "dx": dx,
        "dy": dy,
        "distance": math.hypot(dx, dy),
        "angle_degrees": math.degrees(math.atan2(dy, dx)),
    }
