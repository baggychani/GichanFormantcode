# core/workers.py — 백그라운드 워커 (일괄 저장 등)

import os
import traceback
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
    ):
        super().__init__()
        self.save_dir = save_dir
        self.plot_data_list = list(plot_data_list)
        self.plot_engine = plot_engine
        self.plot_params = dict(plot_params)
        self.ranges = ranges
        self.ds_settings = ds_settings
        self.img_format = img_format
        self.errors = []

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
                temp_fig = Figure(figsize=(6.5, 6.5), dpi=300)
                self.plot_engine.draw_plot(
                    temp_fig,
                    data["df"],
                    self.plot_params,
                    manual_ranges=self.ranges,
                    design_settings=self.ds_settings,
                )
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
