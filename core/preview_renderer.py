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
        *,
        filter_state: dict[str, str] | None = None,
        layer_overrides: dict[str, dict[str, Any]] | None = None,
        layer_order: list[str] | None = None,
        custom_label_offsets: dict[str, tuple[float, float]] | None = None,
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
                filter_state=filter_state,
                design_settings=design_settings,
                sigma=float(params.get("sigma", 2.0)),
                custom_label_offsets=custom_label_offsets,
                layer_overrides=layer_overrides,
                plot_params=params,
                layer_order=layer_order,
            )
        else:
            self.plot_engine.draw_plot(
                self.figure,
                current_data["df"],
                params,
                manual_ranges=ranges,
                filter_state=filter_state,
                design_settings=design_settings,
            layer_overrides=layer_overrides,
            layer_order=layer_order,
            custom_label_offsets=custom_label_offsets,
            )

        buffer = BytesIO()
        self.figure.savefig(buffer, format="png", facecolor="white")
        return buffer.getvalue()
