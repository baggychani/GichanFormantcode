"""Debounced main-preview orchestration around the preview renderer service."""

from __future__ import annotations


class MainPreviewWorkflowService:
    def __init__(self, host) -> None:
        self.host = host

    def render_now(self) -> None:
        host = self.host
        if not host.view.supports_preview() or not host.plot_data_list:
            host._set_preview_empty()
            return
        current_data, _index = host.get_current_file_data()
        if current_data is None:
            host._set_preview_empty()
            return
        params = host._get_main_ui_plot_params()
        ranges = (
            host._norm_ranges_for_widgets(params["normalization"])
            if params.get("normalization")
            else host._get_smart_ranges(
                params["type"], params["use_bark_units"], params["f1_scale"], params["f2_scale"]
            )
        )
        try:
            host._render_live_preview_content(current_data, params, ranges, host._get_preview_design(params))
        except Exception as error:
            host.live_preview_service.show_error(error)
