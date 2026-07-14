"""Popup-level workflows that coordinate legacy Qt windows."""

from __future__ import annotations

from typing import Any

import config
from model.combined_dataset import build_compare_group_entry
from utils import app_logger


class PopupWorkflowService:
    def __init__(self, host: Any) -> None:
        self.host = host

    def open_vowel_analysis(self, popup: Any) -> Any | None:
        host = self.host
        host._cleanup_popups()
        snapshot = getattr(popup, "plot_data_snapshot", None)
        params = getattr(popup, "fixed_plot_params", None)
        if snapshot is None and hasattr(popup, "idx_blue") and hasattr(popup, "idx_red"):
            left, right = host.get_compare_data(popup.idx_blue, popup.idx_red)
            if left and right:
                snapshot = [left, right]
            params = params or host._get_current_plot_params(popup)
        if not snapshot or not params:
            return None
        suffix = {"1sigma": " (이상치 제거 : 1σ)", "2sigma": " (이상치 제거 : 2σ)"}.get(host.get_outlier_mode(), "")
        names = [item.get("name", "") for item in snapshot]
        if len(names) == 1:
            title = names[0] + suffix
        elif len(names) == 2 and hasattr(popup, "idx_blue"):
            title = f"{names[0]}, {names[1]}{suffix}"
        else:
            title = f"{names[0]} 외 {len(names) - 1}개{suffix}" if names else "데이터 없음" + suffix
        if params.get("normalization"):
            title += f" / {params['normalization']}"
        app_logger.info(config.LOG_MSG["ANALYSIS_OPEN"].format(title_suffix=title))
        dialog = host.window_coordinator.create_vowel_analysis(
            parent=popup, controller=host, plot_data_snapshot=snapshot,
            fixed_plot_params=params, title_suffix=title,
            initial_tab_idx=getattr(popup, "current_idx", 0),
        )
        popup.raise_()
        popup.activateWindow()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        host.legacy_windows.register(dialog)
        return dialog

    def open_compare_dialog(self, current_idx: int, parent_window: Any | None = None) -> Any | None:
        host = self.host
        real_count = sum(1 for item in host.plot_data_list if not item.get("is_combined"))
        if real_count < 2:
            host._show_warning("데이터 부족", "비교할 대상이 부족합니다.\n2개 이상의 데이터를 로드해 주세요.", parent_window)
            return None
        if 0 <= current_idx < len(host.plot_data_list) and host.plot_data_list[current_idx].get("is_combined"):
            host._show_warning("비교 불가", "Combined 항목은 다중 비교의 기준이 될 수 없습니다.\n비교를 시작하려면 개별 화자 파일로 먼저 이동해 주세요.", parent_window)
            return None
        host._disable_ruler_for_open_popups()
        host._disable_label_move_for_open_popups()
        return host.window_coordinator.open_compare_dialog(
            parent=parent_window or host.ui, controller=host, current_idx=current_idx
        )

    def open_compare_for_source_groups(self, groups, normalization=None, parent_window=None):
        host = self.host
        group_items = [self._build_group(group) for group in groups]
        if len(group_items) < 2 or any(item is None for item in group_items):
            host._show_warning("비교 불가", "선택한 그룹에서 비교할 데이터를 만들 수 없습니다.", parent_window)
            return None
        virtual_indices = tuple(host.register_compare_virtual_item(item) for item in group_items)
        return host.open_compare_plot_for_indices(
            list(virtual_indices), normalization=normalization, parent_window=parent_window,
            virtual_indices=virtual_indices, source_groups=tuple(tuple(group) for group in groups),
        )

    def _build_group(self, indices):
        items = [
            self.host.plot_data_list[index]
            for index in indices
            if 0 <= index < len(self.host.plot_data_list)
            and not self.host.plot_data_list[index].get("is_combined")
        ]
        return build_compare_group_entry(items)
