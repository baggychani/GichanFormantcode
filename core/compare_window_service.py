"""Creation lifecycle for legacy compare plot windows."""

from __future__ import annotations

from typing import Any

from matplotlib.figure import Figure

from core.compare_series import CompareSession


class CompareWindowService:
    """Create a compare popup; rendering itself belongs to CompareRenderService."""

    def __init__(self, host: Any) -> None:
        self.host = host

    def open_for_indices(
        self,
        indices: list[int],
        *,
        normalization: str | None,
        parent_window: Any | None,
        virtual_indices: tuple[int, ...] | None,
        source_groups: tuple[tuple[int, ...], ...] | None,
    ) -> Any | None:
        if len(indices) < 2:
            self.host._show_warning(
                "비교 불가", "compare에는 두 개 이상의 데이터가 필요합니다.", parent_window
            )
            return None
        self.host.sync_analysis_settings_from_view()
        self.host._cleanup_popups()
        session = CompareSession.from_data_indices(*indices)
        try:
            figure = Figure(figsize=(6.5, 6.5), dpi=100)
            plot_type = self.host.get_analysis_settings().plot_type
            popup = self.host.window_coordinator.create_compare_plot(
                parent=parent_window or self.host.ui,
                controller=self.host,
                figure=figure,
                idx_blue=indices[0],
                idx_red=indices[1],
                x_axis_label=self.host._get_x_axis_label(plot_type),
                normalization=normalization,
            )
            popup.compare_session = session
            popup.compare_source_groups = source_groups or tuple(
                (index,) for index in indices
            )
            popup.fixed_plot_params = self.host._get_current_plot_params()
            if virtual_indices:
                popup._compare_virtual_indices = tuple(virtual_indices)
                popup.destroyed.connect(
                    lambda *_args, values=tuple(virtual_indices): self.host._release_compare_virtual_indices(values)
                )
            if not normalization:
                self._apply_initial_axis_state(popup, plot_type)
            self.host._disable_ruler_for_open_popups()
            self.host._disable_label_move_for_open_popups()
            popup.show()
            self.host.runtime.call_soon(
                lambda: self.host._refresh_compare_plot_for_session(
                    figure, popup.canvas, popup.range_widgets, None, popup, session
                )
            )
            self.host.legacy_windows.register(popup)
            return popup
        except Exception as exc:
            if virtual_indices:
                self.host._release_compare_virtual_indices(tuple(virtual_indices))
            self.host._show_critical(
                "비교 플롯 오류",
                f"비교 플롯 창을 열 수 없습니다.\n\n{exc}",
                parent_window,
            )
            return None

    def _apply_initial_axis_state(self, popup: Any, plot_type: str) -> None:
        f1_scale = popup.fixed_plot_params.get("f1_scale", "linear")
        f2_scale = popup.fixed_plot_params.get("f2_scale", "linear")
        use_bark = popup.fixed_plot_params.get("use_bark_units", False)
        f1_unit, _ = self.host._get_axis_units_from_params(popup.fixed_plot_params)
        try:
            popup.update_unit_labels(f1_unit)
        except TypeError:
            popup.update_unit_labels(f1_unit, "Hz")
        ranges = self.host._get_smart_ranges(plot_type, use_bark, f1_scale, f2_scale)
        self.host._apply_ranges_to_widgets(popup.range_widgets, ranges)
