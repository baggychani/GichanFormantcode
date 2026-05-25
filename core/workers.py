# core/workers.py — 백그라운드 워커 (일괄 저장 등)

import os
import traceback
from types import SimpleNamespace

from PySide6.QtCore import QThread, Signal


class BatchSaveWorker(QThread):
    """일괄 저장을 백그라운드 스레드에서 수행하여 GUI 멈춤 방지."""

    progress = Signal(int, int)  # current, total
    finished_with_count = Signal(int)
    log_error = Signal(str)

    def __init__(
        self,
        save_dir,
        plot_data_list,
        plot_engine,
        plot_params,
        ranges,
        ds_settings,
        img_format,
        *,
        normalize_fn=None,
        per_file_filters=None,
        per_file_overrides=None,
        label_offsets=None,
        per_file_draw_objects=None,
        apply_layer_visibility=True,
        apply_layer_design=True,
        apply_label_positions=True,
        apply_legend=False,
        apply_draw_annotations=True,
    ):
        super().__init__()
        self.save_dir = save_dir
        self.plot_data_list = list(plot_data_list)
        self.plot_engine = plot_engine
        self.plot_params = dict(plot_params)
        self.ranges = ranges
        self.ds_settings = ds_settings
        self.img_format = img_format
        self.normalize_fn = normalize_fn
        self.per_file_filters = per_file_filters or {}
        self.per_file_overrides = per_file_overrides or {}
        self.label_offsets = label_offsets or {}
        self.per_file_draw_objects = per_file_draw_objects or {}
        self.apply_layer_visibility = apply_layer_visibility
        self.apply_layer_design = apply_layer_design
        self.apply_label_positions = apply_label_positions
        self.apply_legend = apply_legend
        self.apply_draw_annotations = apply_draw_annotations
        self.errors = []

    def _plot_key_suffix(self):
        norm = self.plot_params.get("normalization")
        plot_type = "f1_f2" if norm else self.plot_params.get("type", "f1_f2")
        return (plot_type, norm) if norm else (plot_type,)

    def _render_plot(self, figure, df, file_index):
        suffix = self._plot_key_suffix()
        filter_state = None
        if self.apply_layer_visibility:
            filter_state = self.per_file_filters.get(file_index, {})

        layer_overrides = (
            self.per_file_overrides.get(file_index, {})
            if self.apply_layer_design
            else {}
        )
        custom_offsets = (
            self.label_offsets.get((file_index, *suffix), {})
            if self.apply_label_positions
            else {}
        )

        norm = self.plot_params.get("normalization")
        if norm:
            return self.plot_engine.draw_single_normalized(
                figure,
                df,
                norm,
                manual_ranges=self.ranges,
                filter_state=filter_state,
                design_settings=self.ds_settings,
                sigma=float(self.plot_params.get("sigma", 2.0)),
                custom_label_offsets=custom_offsets,
                layer_overrides=layer_overrides,
                plot_params=self.plot_params,
            )
        return self.plot_engine.draw_plot(
            figure,
            df,
            self.plot_params,
            manual_ranges=self.ranges,
            filter_state=filter_state,
            design_settings=self.ds_settings,
            custom_label_offsets=custom_offsets,
            layer_overrides=layer_overrides,
        )

    def _render_draw_annotations(self, figure, file_index):
        if not self.apply_draw_annotations or not figure.axes:
            return
        import copy

        from draw.draw_layer_render import render_draw_objects

        objs = self.per_file_draw_objects.get(file_index, [])
        if not objs:
            return
        objs = copy.deepcopy(objs)
        popup_ctx = SimpleNamespace(
            design_settings=self.ds_settings,
            fixed_plot_params=self.plot_params,
            normalization=self.plot_params.get("normalization"),
        )
        render_draw_objects(
            figure.axes[0],
            objs,
            popup_ctx,
            skip_types=frozenset({"legend"}),
            show_editor_chrome=False,
        )

    def _render_legend(self, figure, file_index):
        if not self.apply_legend or not figure.axes:
            return
        import copy

        from draw.legend_helpers import find_legend_object
        from draw.legend_render import render_legend

        objs = self.per_file_draw_objects.get(file_index, [])
        legend = find_legend_object(objs)
        if legend is None or not getattr(legend, "visible", True):
            return
        legend = copy.deepcopy(legend)
        popup_ctx = SimpleNamespace(
            design_settings=self.ds_settings,
            fixed_plot_params=self.plot_params,
        )
        render_legend(
            figure.axes[0],
            legend,
            popup_ctx,
            selected=False,
            show_editor_chrome=False,
        )

    def run(self):
        from matplotlib.figure import Figure

        success_count = 0
        total = len(self.plot_data_list)
        outlier_mode = self.plot_params.get("outlier_mode")
        outlier_suffix = ""
        if outlier_mode == "1sigma":
            outlier_suffix = "_이상치 제거 1σ"
        elif outlier_mode == "2sigma":
            outlier_suffix = "_이상치 제거 2σ"

        for i, data in enumerate(self.plot_data_list):
            fname = data["name"]
            base_name = os.path.splitext(fname)[0]
            save_name = f"{base_name}{outlier_suffix}.{self.img_format}"
            save_path = os.path.join(self.save_dir, save_name)
            try:
                df = data["df"]
                if self.normalize_fn is not None:
                    df = self.normalize_fn(df)
                temp_fig = Figure(figsize=(6.5, 6.5), dpi=300)
                self._render_plot(temp_fig, df, i)
                self._render_draw_annotations(temp_fig, i)
                self._render_legend(temp_fig, i)
                if self.img_format.lower() == "png":
                    temp_fig.savefig(save_path, format="png", dpi=300, transparent=True)
                else:
                    temp_fig.savefig(
                        save_path, format=self.img_format, facecolor="white"
                    )
                success_count += 1
            except Exception as e:
                traceback.print_exc()
                self.log_error.emit(f"파일 저장 실패 ({fname}): {e}")
                self.errors.append((fname, str(e)))
            self.progress.emit(i + 1, total)
        self.finished_with_count.emit(success_count)
        self.plot_data_list = None
