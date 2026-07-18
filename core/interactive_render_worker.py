"""Dedicated renderer for React's interactive preview.

The scheduler owns one render thread, so this renderer can keep one private
Matplotlib figure in the sidecar process.  Keeping the figure here avoids the
startup and DataFrame serialization cost of spawning a Python process for the
first preview.
"""

from __future__ import annotations

import threading
from io import BytesIO
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
            return self._render_locked(prepared)

    def render_export(self, prepared: Mapping[str, Any], image_format: str) -> bytes:
        """Render one export while keeping the Matplotlib figure locked."""
        if prepared.get("empty"):
            raise ValueError("cannot export an empty preview")
        fmt = str(image_format).lower().lstrip(".")
        if fmt not in {"png", "jpg", "jpeg", "svg"}:
            raise ValueError("unsupported export format")
        with self._lock:
            renderer = self._ensure_started()
            renderer.render_png(
                prepared["current_data"], prepared["params"], prepared["ranges"], prepared["design"],
                filter_state=prepared.get("filter_state"),
                layer_overrides=prepared.get("layer_overrides"),
                layer_order=prepared.get("layer_order"),
                custom_label_offsets=prepared.get("custom_label_offsets"),
                draw_objects=prepared.get("draw_objects"),
            )
            buffer = BytesIO()
            if fmt == "svg":
                renderer.figure.savefig(buffer, format="svg", facecolor="white")
            elif fmt in {"jpg", "jpeg"}:
                renderer.figure.savefig(buffer, format="jpg", facecolor="white")
            else:
                renderer.figure.savefig(buffer, format="png", facecolor="white")
            return buffer.getvalue()

    def _render_locked(self, prepared: Mapping[str, Any]) -> dict[str, Any]:
        renderer = self._ensure_started()
        try:
            png_data, ruler_context = renderer.render_png(
                prepared["current_data"], prepared["params"], prepared["ranges"], prepared["design"],
                filter_state=prepared.get("filter_state"),
                layer_overrides=prepared.get("layer_overrides"),
                layer_order=prepared.get("layer_order"),
                custom_label_offsets=prepared.get("custom_label_offsets"),
                draw_objects=prepared.get("draw_objects"),
                include_context=True,
            )
        except Exception as exc:  # noqa: BLE001 - render boundary
            raise RuntimeError(f"interactive render failed: {exc}") from exc
        return {
            "empty": False, "png_data": png_data, "filename": prepared["filename"],
            "request_id": prepared.get("request_id"), "revision": prepared.get("revision"),
            "ruler_context": ruler_context,
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
