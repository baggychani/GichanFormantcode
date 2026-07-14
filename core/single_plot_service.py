"""Legacy single-plot popup creation, rendering, and file navigation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import config
from matplotlib.figure import Figure

from core.plot_session_service import PlotSessionService
from core.display_utils import apply_file_indicator_style, format_file_label


class SinglePlotService:
    """Move deterministic single-popup work out of ``MainController``.

    The host remains a temporary compatibility adapter for legacy widget
    helpers; this service owns the operation sequence and rendering contract.
    """

    def __init__(self, host: Any) -> None:
        self.host = host

    def open(self) -> Any | None:
        self.host.sync_analysis_settings_from_view()
        self.host._cleanup_popups()
        if not self.host.plot_data_list:
            self.host.view.show_warning("데이터 없음", "분석할 데이터를 먼저 불러와 주세요.")
            return None
        figure = Figure(figsize=(6.5, 6.5), dpi=100)
        plot_type = self.host.get_analysis_settings().plot_type
        params = self.host._get_main_ui_plot_params()
        normalization = params.get("normalization")
        popup = self.host.window_coordinator.create_single_plot(
            parent=self.host.ui,
            controller=self.host,
            figure=figure,
            x_axis_label=self.host._get_x_axis_label(plot_type),
            normalization=normalization,
        )
        popup.set_initial_plot_state(
            params, deepcopy(self.host.plot_data_list), self.host.current_idx
        )
        session = self.host.plot_session_state
        PlotSessionService.apply_to_popup(session, popup, index=self.host.current_idx)
        popup._last_synced_normalization = normalization
        self._apply_initial_axis_state(popup, plot_type, normalization, session)
        current_data = popup.plot_data_snapshot[popup.current_idx]
        popup.update_file_nav_indicator(popup.current_idx, current_data)
        self.refresh(figure, popup.canvas, popup.range_widgets, popup.lbl_info, popup)
        popup.show()
        self.host.legacy_windows.register(popup)
        refresh_layers = getattr(popup, "_refresh_layer_dock_vowels", None)
        if callable(refresh_layers):
            refresh_layers()
        return popup

    def refresh(
        self, figure: Any, canvas: Any, range_widgets: Any, _label: Any, popup: Any
    ) -> None:
        manual_ranges = self.host._read_manual_ranges(range_widgets)
        self.host._sync_single_popup_normalization(popup)
        popup.fixed_plot_params = self.host._get_current_plot_params(popup)
        data_list = popup.plot_data_snapshot or self.host.plot_data_list
        index = popup.current_idx
        current_data = data_list[index]
        normalization = getattr(popup, "normalization", None) or (
            popup.fixed_plot_params or {}
        ).get("normalization")
        plot_type = "f1_f2" if normalization else popup.fixed_plot_params.get("type", "f1_f2")
        key_suffix = (plot_type, normalization) if normalization else (plot_type,)
        offsets = self.host.custom_label_offsets.get((index, *key_suffix), {})
        filter_state = popup.get_filter_state()
        design = popup.get_design_settings() or self.host._get_default_design()
        overrides = popup.get_layer_design_overrides()
        if normalization:
            popup.fixed_plot_params = dict(
                popup.fixed_plot_params or {}, normalization=normalization
            )
            sigma_picker = getattr(popup, "cb_sigma", None)
            if sigma_picker:
                try:
                    popup.fixed_plot_params["sigma"] = float(sigma_picker.currentText())
                except (TypeError, ValueError):
                    pass
            dataframe = self.host._normalize_dataframe(
                current_data["df"], normalization, current_data
            )
            result = self.host.plot_engine.draw_single_normalized(
                figure,
                dataframe,
                normalization,
                manual_ranges=manual_ranges,
                filter_state=filter_state,
                design_settings=design,
                sigma=float(popup.fixed_plot_params.get("sigma", config.DEFAULT_SIGMA)),
                custom_label_offsets=offsets,
                layer_overrides=overrides,
                plot_params=popup.fixed_plot_params,
                layer_order=getattr(popup, "layer_order", []),
            )
            popup._update_window_title(current_data["name"])
        else:
            result = self.host.plot_engine.draw_plot(
                figure,
                current_data["df"],
                popup.fixed_plot_params,
                manual_ranges=manual_ranges,
                filter_state=filter_state,
                design_settings=design,
                custom_label_offsets=offsets,
                layer_overrides=overrides,
                layer_order=getattr(popup, "layer_order", []),
            )
        _, snapping, label_data, label_artists = result
        popup.set_draw_result(snapping, label_data, label_artists, (index, *key_suffix))
        self.host._sync_plot_session_from_popup(
            popup, manual_ranges, design, filter_state, overrides
        )
        self.host._present_popup_canvas(popup, canvas)
        self.host._sync_popup_tool_contexts(popup, figure, canvas)

    def navigate(
        self, direction: str, figure: Any, canvas: Any, label: Any, popup: Any, range_widgets: Any
    ) -> None:
        data_list = popup.plot_data_snapshot or self.host.plot_data_list
        if not data_list:
            return
        leaving_key = getattr(popup, "_plot_key", None)
        if leaving_key:
            self.host.custom_label_offsets.pop(leaving_key, None)
        if self.host.ruler_tool.active:
            self.host.ruler_tool.clear_all()
        index = (popup.current_idx - 1) % len(data_list) if direction == "prev" else (popup.current_idx + 1) % len(data_list)
        self.host.current_idx = index
        popup.current_idx = index
        set_draw_objects = getattr(popup, "_set_current_draw_objects", None)
        if callable(set_draw_objects):
            set_draw_objects([])
        dock = getattr(popup, "_layer_dock_content", None)
        if dock:
            dock._selected_draw_indices = set()
            dock.update_draw_layer_list([])
        current_data = data_list[index]
        update_indicator = getattr(popup, "update_file_nav_indicator", None)
        if callable(update_indicator):
            update_indicator(index, current_data)
        else:
            label.setText(format_file_label(index + 1, len(data_list), current_data["name"]))
            apply_file_indicator_style(label, current_data)
        self.refresh(figure, canvas, range_widgets, label, popup)

    def _apply_initial_axis_state(self, popup: Any, plot_type: str, normalization: str | None, session: Any) -> None:
        if normalization:
            self.host._apply_ranges_to_widgets(
                popup.range_widgets, self.host._norm_ranges_for_widgets(normalization)
            )
            popup._apply_normalization_axis_ui()
        else:
            f1_scale = popup.fixed_plot_params.get("f1_scale", "linear")
            f2_scale = popup.fixed_plot_params.get("f2_scale", "linear")
            use_bark = popup.fixed_plot_params.get("use_bark_units", False)
            f1_unit, f2_unit = self.host._get_axis_units_from_params(popup.fixed_plot_params)
            try:
                popup.update_unit_labels(f1_unit, f2_unit)
            except TypeError:
                popup.update_unit_labels(f1_unit)
            self.host._apply_ranges_to_widgets(
                popup.range_widgets,
                self.host._get_smart_ranges(plot_type, use_bark, f1_scale, f2_scale),
            )
        if session.ranges:
            self.host._apply_ranges_to_widgets(popup.range_widgets, session.ranges)
        sigma_picker = getattr(popup, "cb_sigma", None)
        if sigma_picker is not None:
            sigma_picker.setCurrentText(str(session.sigma))
