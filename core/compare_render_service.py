"""Compare-plot rendering orchestration, isolated from popup creation."""

from __future__ import annotations

from typing import Any

from core.compare_runtime import (
    apply_compare_render_to_popup,
    build_compare_series_inputs,
    make_compare_plot_key,
)
from core.compare_series import CompareSession


class CompareRenderService:
    """Render a compare session through a deliberately narrow host adapter.

    The host currently supplies legacy range/design/tool callbacks. Keeping
    those callbacks at the edge lets popup creation evolve separately from the
    deterministic input-build → PlotEngine → popup-result pipeline.
    """

    def __init__(self, host: Any) -> None:
        self.host = host

    def refresh(
        self,
        figure: Any,
        canvas: Any,
        range_widgets: Any,
        popup: Any,
        session: CompareSession,
    ) -> None:
        manual_ranges = self.host._read_manual_ranges(range_widgets)
        popup.fixed_plot_params = self.host._get_current_plot_params(popup)
        sigma_picker = getattr(popup, "cb_sigma", None)
        if sigma_picker is not None:
            try:
                popup.fixed_plot_params = dict(
                    popup.fixed_plot_params or {},
                    sigma=float(sigma_picker.currentText()),
                )
            except (ValueError, TypeError):
                pass

        normalization = popup.normalization
        design = popup.get_design_settings() or self.host._get_default_design()
        sigma = (popup.fixed_plot_params or {}).get("sigma", 2.0)
        if normalization and hasattr(self.host.plot_engine, "draw_compare_plot_normalized"):
            popup.fixed_plot_params = dict(
                popup.fixed_plot_params or {}, normalization=normalization
            )
            plot_key = make_compare_plot_key(session, "f1_f2", normalization)
            series_inputs = build_compare_series_inputs(
                self.host,
                session,
                popup,
                design_settings=design,
                plot_type="f1_f2",
                norm=normalization,
                plot_key=plot_key,
            )
            result = self.host.plot_engine.draw_compare_plot_normalized(
                figure,
                series_inputs,
                normalization,
                design_settings=design,
                sigma=sigma,
                manual_ranges=manual_ranges,
            )
        elif hasattr(self.host.plot_engine, "draw_compare_plot"):
            plot_type = popup.fixed_plot_params.get("type", "f1_f2")
            plot_key = make_compare_plot_key(session, plot_type, None)
            series_inputs = build_compare_series_inputs(
                self.host,
                session,
                popup,
                design_settings=design,
                plot_type=plot_type,
                norm=None,
                plot_key=plot_key,
            )
            result = self.host.plot_engine.draw_compare_plot(
                figure,
                series_inputs,
                popup.fixed_plot_params,
                manual_ranges=manual_ranges,
                design_settings=design,
            )
        else:
            raise RuntimeError("compare plot engine is unavailable")

        apply_compare_render_to_popup(popup, result, session, plot_key)
        self.host._present_popup_canvas(popup, canvas)
        self.host._sync_popup_tool_contexts(popup, figure, canvas)
