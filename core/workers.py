# core/workers.py — 백그라운드 워커 (일괄 저장 등)

import os
import tempfile
import traceback
from types import SimpleNamespace

from PySide6.QtCore import QThread, Signal


def build_unique_batch_save_names(plot_data_list, img_format, suffix=""):
    """Return deterministic, case-insensitively unique names for one batch."""
    extension = str(img_format).lstrip(".") or "png"
    used = set()
    names = []
    for data in plot_data_list:
        # CI runs on Linux; Windows-style paths in fixtures must still basename.
        raw_name = str(data["name"]).replace("\\", "/")
        base_name = os.path.splitext(os.path.basename(raw_name))[0]
        base_name = base_name or "plot"
        stem = f"{base_name}{suffix}"
        candidate = f"{stem}.{extension}"
        sequence = 2
        while candidate.casefold() in used:
            candidate = f"{stem}_{sequence}.{extension}"
            sequence += 1
        used.add(candidate.casefold())
        names.append(candidate)
    return names


class BatchSaveWorker(QThread):
    """일괄 저장을 백그라운드 스레드에서 수행하여 GUI 멈춤 방지."""

    progress = Signal(int, int)  # current, total
    finished_with_count = Signal(int)
    cancelled_with_count = Signal(int)
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
        layer_order=None,
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
        self.layer_order = list(layer_order or [])
        self.apply_layer_visibility = apply_layer_visibility
        self.apply_layer_design = apply_layer_design
        self.apply_label_positions = apply_label_positions
        self.apply_legend = apply_legend
        self.apply_draw_annotations = apply_draw_annotations
        self.errors = []
        self._cancel_requested = False

    def cancel(self):
        """Request cancellation after the current rendering operation yields."""
        self._cancel_requested = True
        self.requestInterruption()

    def _should_cancel(self):
        return self._cancel_requested or self.isInterruptionRequested()

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
                layer_order=self.layer_order,
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
            layer_order=self.layer_order,
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

        save_names = build_unique_batch_save_names(
            self.plot_data_list, self.img_format, outlier_suffix
        )
        image_format = str(self.img_format).lstrip(".").lower()
        was_cancelled = self._should_cancel()
        for i, (data, save_name) in enumerate(zip(self.plot_data_list, save_names)):
            if self._should_cancel():
                was_cancelled = True
                break
            fname = data["name"]
            save_path = os.path.join(self.save_dir, save_name)
            temp_path = None
            temp_fig = None
            try:
                df = data["df"]
                if self.normalize_fn is not None:
                    df = self.normalize_fn(df)
                temp_fig = Figure(figsize=(6.5, 6.5), dpi=300)
                self._render_plot(temp_fig, df, i)
                self._render_draw_annotations(temp_fig, i)
                self._render_legend(temp_fig, i)
                file_descriptor, temp_path = tempfile.mkstemp(
                    prefix=f".{save_name}.",
                    suffix=".tmp",
                    dir=self.save_dir,
                )
                os.close(file_descriptor)
                if image_format == "png":
                    temp_fig.savefig(
                        temp_path, format="png", dpi=300, transparent=True
                    )
                else:
                    temp_fig.savefig(temp_path, format=image_format, facecolor="white")
                if self._should_cancel():
                    was_cancelled = True
                    break
                os.replace(temp_path, save_path)
                temp_path = None
                success_count += 1
            except Exception as e:
                traceback.print_exc()
                self.log_error.emit(f"파일 저장 실패 ({fname}): {e}")
                self.errors.append((fname, str(e)))
            finally:
                if temp_fig is not None:
                    temp_fig.clear()
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
            if was_cancelled:
                break
            self.progress.emit(i + 1, total)
        if was_cancelled:
            self.cancelled_with_count.emit(success_count)
        else:
            self.finished_with_count.emit(success_count)
        self.plot_data_list = None
