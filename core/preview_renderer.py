"""Framework-neutral LIVE preview rendering."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from core.normalization_service import normalize_dataframe


class PreviewRenderer:
    def __init__(self, plot_engine, figure):
        self.plot_engine = plot_engine
        self.figure = figure

    def render_png(
        self,
        current_data: dict[str, Any],
        params: dict[str, Any],
        ranges: dict[str, str],
        design_settings: dict[str, Any],
    ) -> bytes:
        self.figure.clear()
        normalization = params.get("normalization")
        if normalization:
            dataframe = normalize_dataframe(
                current_data["df"],
                normalization,
                data_item=current_data,
            )
            self.plot_engine.draw_single_normalized(
                self.figure,
                dataframe,
                normalization,
                manual_ranges=ranges,
                design_settings=design_settings,
                plot_params=params,
            )
        else:
            self.plot_engine.draw_plot(
                self.figure,
                current_data["df"],
                params,
                manual_ranges=ranges,
                design_settings=design_settings,
            )

        buffer = BytesIO()
        self.figure.savefig(buffer, format="png", facecolor="white")
        return buffer.getvalue()
