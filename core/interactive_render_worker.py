"""Dedicated renderer for React's interactive preview.

The scheduler owns one render thread, so this renderer can keep one private
Matplotlib figure in the sidecar process.  Keeping the figure here avoids the
startup and DataFrame serialization cost of spawning a Python process for the
first preview.
"""

from __future__ import annotations

import threading
from typing import Any, Mapping


class InteractiveRenderer:
    """Single-owner Matplotlib renderer, called by the render scheduler."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._renderer = None

    def render(self, prepared: Mapping[str, Any]) -> dict[str, Any]:
        if prepared.get("empty"):
            return dict(prepared)
        with self._lock:
            renderer = self._ensure_started()
            try:
                png_data = renderer.render_png(
                    prepared["current_data"],
                    prepared["params"],
                    prepared["ranges"],
                    prepared["design"],
                    filter_state=prepared.get("filter_state"),
                    layer_overrides=prepared.get("layer_overrides"),
                    layer_order=prepared.get("layer_order"),
                    custom_label_offsets=prepared.get("custom_label_offsets"),
                )
            except Exception as exc:  # noqa: BLE001 - render boundary
                raise RuntimeError(f"interactive render failed: {exc}") from exc
            return {
                "empty": False,
                "png_data": png_data,
                "filename": prepared["filename"],
                "request_id": prepared.get("request_id"),
                "revision": prepared.get("revision"),
            }

    def close(self) -> None:
        with self._lock:
            self._renderer = None

    def _ensure_started(self):
        if self._renderer is None:
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            from matplotlib.figure import Figure

            from core.preview_renderer import PreviewRenderer
            from engine.plot_engine import PlotEngine

            figure = Figure(figsize=(6.5, 6.5), dpi=150)
            FigureCanvasAgg(figure)
            self._renderer = PreviewRenderer(PlotEngine(), figure)
        return self._renderer


# Compatibility name for code that imported the old implementation directly.
IsolatedInteractiveRenderer = InteractiveRenderer
