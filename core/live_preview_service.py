"""Rendering and presentation of the main-window live preview."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import config
from core.display_utils import strip_gichan_prefix
from engine.plot_engine import kor_font


class LivePreviewService:
    """Keep preview bytes, view presentation, and IPC publication together."""

    def __init__(
        self,
        *,
        renderer: Any,
        figure: Any,
        view: Any,
        publish_ready: Callable[..., None],
        publish_empty: Callable[[], None],
        publish_error: Callable[[str], None],
    ) -> None:
        self.renderer = renderer
        self.figure = figure
        self.view = view
        self._publish_ready = publish_ready
        self._publish_empty = publish_empty
        self._publish_error = publish_error

    def show_empty(self) -> None:
        self.view.show_empty_preview()
        self._publish_empty()

    def render(
        self,
        current_data: dict[str, Any],
        params: dict[str, Any],
        ranges: dict[str, str],
        design: dict[str, Any],
        *,
        outlier_mode: str | None,
        request_id: int | None,
    ) -> None:
        png_data = self.renderer.render_png(current_data, params, ranges, design)
        info = self._info(current_data, params, outlier_mode)
        self.view.show_preview(png_data, info)
        self._publish_ready(png_data, info, request_id=request_id)

    def show_error(self, error: Exception) -> None:
        try:
            self.figure.clear()
            axes = self.figure.add_subplot(111)
            axes.text(
                0.5,
                0.5,
                "LIVE preview rendering failed",
                ha="center",
                va="center",
                fontfamily=kor_font,
                fontsize=11,
            )
            axes.set_axis_off()
        except Exception:
            # The primary error is more useful than a fallback rendering error.
            pass
        message = str(error)
        self.view.show_preview_error(message)
        self._publish_error(message)

    def _info(
        self,
        current_data: dict[str, Any],
        params: dict[str, Any],
        outlier_mode: str | None,
    ) -> str:
        filename = strip_gichan_prefix(os.path.splitext(current_data["name"])[0])
        normalization = params.get("normalization")
        if normalization:
            detail = f"nF1 / nF2 / {normalization}"
        else:
            f1_scale = params.get("f1_scale", "linear")
            f2_scale = params.get("f2_scale", "linear")
            use_bark = params.get("use_bark_units", False)
            f1_unit = "Bark" if f1_scale == "bark" and use_bark else "Hz"
            f2_unit = "Bark" if f2_scale == "bark" and use_bark else "Hz"
            x_name = config.PLOT_X_AXIS_LABEL.get(params["type"], "F2")
            f1_display, f2_display = self.view.get_display_scales()
            detail = (
                f"F1({f1_display.capitalize()}, {f1_unit}) / "
                f"{x_name}({f2_display.capitalize()}, {f2_unit})"
            )
        if outlier_mode == "mahalanobis_2sigma":
            detail += " / outlier removal: 2σ (Mahalanobis)"
        elif outlier_mode == "tukey_iqr":
            detail += " / outlier removal: Tukey IQR"
        return f"{filename}\n{detail}"
