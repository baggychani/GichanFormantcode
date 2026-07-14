"""Project-document restoration workflow for the legacy desktop controller."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

from core.compare_series import compare_label_offset_key
from core.compare_runtime import make_compare_plot_key
from core.application_state import AnalysisSettings
from core.data_loading_service import load_plot_item_from_file, make_plot_item
from core.interactive_plot_state import PlotSessionState
from model.combined_dataset import build_combined_entry
from model.data_processor import DataProcessor


class ProjectRestoreService:
    """Validate, apply, and optionally reopen a persisted project.

    ``MainController`` remains a compatibility host for Qt-specific popup
    helpers while this service owns the all-or-nothing restore sequence.
    """

    def __init__(self, host: Any) -> None:
        self.host = host

    def load_source_item(self, source: dict, snapshots: dict) -> tuple[str, dict]:
        source_id = str(source.get("id", ""))
        path = source.get("path") or ""
        name = source.get("name") or os.path.basename(path) or f"source_{source_id}"
        snapshot = snapshots.get(source_id)
        if snapshot is not None:
            if not isinstance(snapshot, pd.DataFrame):
                raise ValueError(f"프로젝트 데이터 스냅샷이 손상되었습니다: {name}")
            return path, make_plot_item(
                name=name,
                df=snapshot,
                has_f3=source.get("has_f3"),
                is_pre_lobanov=bool(source.get("is_pre_lobanov", False)),
            )
        if path and os.path.exists(path):
            loaded = load_plot_item_from_file(path)
            if loaded["success"]:
                return path, loaded["item"]
        raise ValueError(f"프로젝트 데이터 스냅샷을 찾을 수 없습니다: {name}")

    def prepare(self, project: dict) -> dict:
        filepaths: list[str] = []
        items: list[dict] = []
        snapshots = project.get("snapshots", {}) or {}
        for source in project.get("sources", []) or []:
            path, item = self.host._load_project_source_item(source, snapshots)
            filepaths.append(path)
            items.append(item)
        combined = build_combined_entry(items)
        if combined is not None:
            items.append(combined)

        real_count = len(filepaths)
        for compare_state in project.get("compare_sessions", []) or []:
            source_groups = compare_state.get("source_groups") or []
            if len(source_groups) < 2:
                raise ValueError("프로젝트의 비교 세션 정보가 손상되었습니다.")
            for group in source_groups:
                if not group or any(
                    not isinstance(index, int) or index < 0 or index >= real_count
                    for index in group
                ):
                    raise ValueError("프로젝트의 비교 세션이 없는 소스를 참조합니다.")

        requested = int((project.get("analysis") or {}).get("current_idx", 0))
        current_idx = max(0, min(requested, len(items) - 1))
        return {
            "filepaths": filepaths,
            "plot_data_list": items,
            "current_idx": current_idx,
            "custom_label_offsets": dict(project.get("label_offsets", {}) or {}),
            "data_processor": DataProcessor(),
        }

    def apply(self, project: dict, *, restore_windows: bool = True) -> None:
        """Prepare first, then mutate once validation has succeeded."""
        prepared = self.prepare(project)
        host = self.host
        host._cleanup_popups()
        host.filepaths = prepared["filepaths"]
        host.plot_data_list = prepared["plot_data_list"]
        host.current_idx = prepared["current_idx"]
        host.custom_label_offsets = prepared["custom_label_offsets"]
        host.data_processor = prepared["data_processor"]

        host.view.update_file_status(len(host.filepaths))
        real_items = [item for item in host.plot_data_list if not item.get("is_combined")]
        host.view.toggle_f3_options(all(item.get("has_f3") for item in real_items))
        host.apply_analysis_settings(AnalysisSettings.from_mapping(project.get("analysis")))
        host._sync_pre_lobanov_ui()
        if host.get_analysis_settings().outlier_mode is not None:
            host.on_outlier_mode_changed()
        else:
            host.update_live_preview()

        single_state = project.get("single_plot")
        if isinstance(single_state, dict) and host.plot_data_list:
            host.plot_session_state = PlotSessionState.from_project_dict(single_state)
            if restore_windows:
                self.restore_single(single_state)
        else:
            host.plot_session_state = PlotSessionState(current_idx=host.current_idx)
        if restore_windows:
            self.restore_compares(project.get("compare_sessions", []) or [])

    def restore_single(self, single_state: dict) -> None:
        host = self.host
        host.current_idx = max(
            0, min(int(single_state.get("current_idx", 0)), len(host.plot_data_list) - 1)
        )
        host.open_single_plot()
        popup = host._active_single_plot_popup()
        if popup is None:
            return
        popup.current_idx = host.current_idx
        popup.fixed_plot_params = dict(
            single_state.get("fixed_plot_params") or popup.fixed_plot_params or {}
        )
        popup.design_settings = dict(single_state.get("design_settings") or {})
        popup.vowel_filter_state_by_file = dict(
            single_state.get("vowel_filter_state_by_file") or {}
        )
        popup.layer_design_overrides_by_file = dict(
            single_state.get("layer_design_overrides_by_file") or {}
        )
        popup.layer_locked_vowels_by_file = {
            int(key): set(value)
            for key, value in (single_state.get("layer_locked_vowels_by_file") or {}).items()
        }
        popup.layer_order = list(single_state.get("layer_order") or [])
        popup._draw_objects_by_file = dict(single_state.get("draw_objects_by_file") or {})
        ranges = single_state.get("ranges") or {}
        if ranges:
            host._apply_ranges_to_widgets(popup.range_widgets, ranges)
        sigma = single_state.get("sigma")
        if sigma is not None and hasattr(popup, "cb_sigma"):
            popup.cb_sigma.setCurrentText(str(sigma))
        if hasattr(popup, "_on_navigate_update"):
            popup._on_navigate_update()
        host.refresh_plot(
            popup.figure, popup.canvas, popup.range_widgets, popup.lbl_info, popup
        )

    def restore_compares(self, compare_sessions: list[dict]) -> None:
        host = self.host
        for state in compare_sessions:
            source_groups = [
                [int(index) for index in group]
                for group in (state.get("source_groups") or [])
            ]
            normalization = state.get("normalization") or (
                state.get("fixed_plot_params") or {}
            ).get("normalization")
            popup = host.open_compare_plot_for_source_groups(
                source_groups, normalization=normalization, parent_window=host.ui
            )
            if popup is None:
                raise ValueError("프로젝트의 비교 창을 복원할 수 없습니다.")
            popup.fixed_plot_params = dict(
                state.get("fixed_plot_params") or popup.fixed_plot_params or {}
            )
            popup.normalization = normalization
            design = dict(state.get("design_settings") or {})
            if design and hasattr(popup.design_tab, "apply_settings"):
                popup.design_tab.apply_settings(design, emit=False)
                popup.design_settings = popup.design_tab.get_current_settings()
            else:
                popup.design_settings = design
            popup.vowel_filter_states = {
                int(key): dict(value)
                for key, value in (state.get("vowel_filter_states") or {}).items()
            }
            popup.layer_design_overrides_by_series = {
                int(key): dict(value)
                for key, value in (state.get("layer_design_overrides_by_series") or {}).items()
            }
            popup.layer_locked_vowels_by_series = {
                int(key): set(value)
                for key, value in (state.get("layer_locked_vowels_by_series") or {}).items()
            }
            popup.layer_order_by_series = {
                int(key): list(value)
                for key, value in (state.get("layer_order_by_series") or {}).items()
            }
            popup._draw_objects_shared = list(state.get("draw_objects") or [])
            ranges = state.get("ranges") or {}
            if ranges:
                host._apply_ranges_to_widgets(popup.range_widgets, ranges)
            sigma = state.get("sigma")
            if sigma is not None and hasattr(popup, "cb_sigma"):
                popup.cb_sigma.setCurrentText(str(sigma))
            plot_type = "f1_f2" if normalization else popup.fixed_plot_params.get("type", "f1_f2")
            plot_key = make_compare_plot_key(popup.compare_session, plot_type, normalization)
            for series_id, offsets in (state.get("label_offsets_by_series") or {}).items():
                host.custom_label_offsets[
                    compare_label_offset_key(plot_key, int(series_id))
                ] = dict(offsets)
            if hasattr(popup, "_refresh_compare_draw_layer_lists"):
                popup._refresh_compare_draw_layer_lists()
            for dock in getattr(popup, "_iter_compare_layer_docks", lambda: [])():
                dock.refresh_design_ui()
            popup.request_plot_refresh(debounce_ms=0)
