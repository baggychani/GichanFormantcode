"""Export paths and batch-render worker construction."""

from __future__ import annotations

import os
from typing import Any

from core.compare_runtime import get_compare_names
from core.compare_series import compare_default_save_basename
from core.display_utils import default_combined_export_txt_basename, strip_gichan_prefix
from core.export_service import export_combined_txt_file, save_dir_from_path, save_figure_file
from utils import path_prefs


class ExportWorkflowService:
    """Own export policy while the host supplies legacy UI and plot adapters."""

    def __init__(self, host: Any) -> None:
        self.host = host

    def initial_dir(self) -> str:
        host = self.host
        if host.last_save_dir and os.path.isdir(host.last_save_dir):
            return host.last_save_dir
        base = host.runtime.app_data_dir()
        if base:
            saved = path_prefs.load_path_prefs(base).get("last_save_dir")
            if saved and os.path.isdir(saved):
                host.last_save_dir = saved
                return saved
        return host.runtime.downloads_dir() or ""

    @staticmethod
    def normalize_tag(normalization: str) -> str:
        return {
            "Lobanov": "Lobanov",
            "Gerstman": "Gerstman",
            "2mW/F": "2mWF",
            "Bigham": "Bigham",
        }.get(normalization, normalization.replace("/", "").replace(" ", ""))

    def default_save_name(self, fmt: str, parent_window: Any | None = None) -> str:
        host = self.host
        suffix = host._get_outlier_save_suffix()
        session = getattr(parent_window, "compare_session", None)
        if session is not None and session.count >= 2:
            normalization = getattr(parent_window, "normalization", None)
            base = compare_default_save_basename(
                get_compare_names(host, session),
                outlier_suffix=suffix,
                norm=normalization,
                norm_tag=self.normalize_tag(normalization) if normalization else None,
            )
            return f"{base}.{fmt}"
        if parent_window and getattr(parent_window, "idx_blue", None) is not None and getattr(parent_window, "idx_red", None) is not None:
            blue = os.path.splitext(host.plot_data_list[parent_window.idx_blue]["name"])[0]
            red = os.path.splitext(host.plot_data_list[parent_window.idx_red]["name"])[0]
            base = f"{blue}_{red}{suffix}"
            normalization = getattr(parent_window, "normalization", None)
            if normalization:
                base += "_" + self.normalize_tag(normalization)
            return f"{base}.{fmt}"
        current = os.path.splitext(host.plot_data_list[host.current_idx]["name"])[0]
        return f"{current}{suffix}.{fmt}"

    def default_save_path(self, fmt: str, parent_window: Any | None = None) -> tuple[str, str]:
        if not self.host.plot_data_list:
            return "", ""
        directory = self.initial_dir()
        name = self.default_save_name(fmt, parent_window)
        return (os.path.join(directory, name) if directory else name), directory

    def default_combined_txt_path(self, parent_window: Any | None = None) -> tuple[str, str]:
        item, _index = self.host._get_plot_item_at(parent_window)
        if not item or not item.get("is_combined"):
            return "", ""
        fallback = os.path.splitext(strip_gichan_prefix(item.get("name", "")))[0]
        name = default_combined_export_txt_basename(
            item.get("combined_source_names") or [], fallback=fallback or "Combined"
        ) + ".txt"
        directory = self.initial_dir()
        return (os.path.join(directory, name) if directory else name), directory

    def export_combined_txt(self, path: str, parent_window: Any | None = None) -> tuple[bool, str]:
        item, _index = self.host._get_plot_item_at(parent_window)
        ok, message = export_combined_txt_file(item, path)
        if ok:
            self.host.set_last_save_dir(save_dir_from_path(path))
        return ok, message

    def save_plot(self, figure: Any, path: str, fmt: str, parent_window: Any | None = None) -> None:
        self.host.set_last_save_dir(save_dir_from_path(path))
        if self.host.ruler_tool.active:
            self.host.ruler_tool.clear_all()
        save_figure_file(figure, path, fmt, parent_window=parent_window)

    def create_batch_worker(self, save_dir, ranges, sigma, image_format, design_settings=None, parent_popup=None, batch_options=None):
        host = self.host
        host.set_last_save_dir(save_dir)
        options = batch_options or {}
        apply_global = options.get("apply_global_design", True)
        apply_layer = options.get("apply_layer_design", True)
        apply_visibility = options.get("apply_layer_visibility", True)
        apply_labels = options.get("apply_label_positions", True)
        apply_legend = options.get("apply_legend", False)
        apply_draw = options.get("apply_draw_annotations", True)
        params = host._get_current_plot_params(parent_popup)
        params["sigma"] = sigma
        params["outlier_mode"] = host.get_analysis_settings().outlier_mode
        design = design_settings if apply_global and design_settings else host._get_default_design()
        normalization = params.get("normalization")
        if normalization and host.all_real_items_pre_lobanov() and normalization == "Lobanov":
            def normalize_fn(dataframe):
                return dataframe.copy()
        elif normalization:
            def normalize_fn(dataframe):
                return host._apply_normalization(dataframe, normalization)
        else:
            normalize_fn = None
        overrides = dict(getattr(parent_popup, "layer_design_overrides_by_file", {})) if parent_popup and apply_layer else {}
        filters = dict(getattr(parent_popup, "vowel_filter_state_by_file", {})) if parent_popup and apply_visibility else {}
        draw_objects = dict(getattr(parent_popup, "_draw_objects_by_file", {})) if parent_popup and (apply_legend or apply_draw) else {}
        return host.window_coordinator.create_batch_save_worker(
            save_dir, host.plot_data_list, host.plot_engine, params, ranges, design, image_format,
            normalize_fn=normalize_fn, per_file_filters=filters, per_file_overrides=overrides,
            label_offsets=dict(host.custom_label_offsets) if apply_labels else {},
            per_file_draw_objects=draw_objects,
            layer_order=list(getattr(parent_popup, "layer_order", []) or []) if parent_popup else [],
            apply_layer_visibility=apply_visibility, apply_layer_design=apply_layer,
            apply_label_positions=apply_labels, apply_legend=apply_legend,
            apply_draw_annotations=apply_draw,
        )
