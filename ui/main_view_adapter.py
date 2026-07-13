"""PySide implementation of the application main-view port."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from core.application_state import AnalysisSettings
from ui.windows.main_window import MainUI


class PySideMainViewAdapter:
    def __init__(self, controller: Any, status_callback=None):
        self.native_window = MainUI(controller, status_callback=status_callback)

    def get_analysis_settings(self) -> AnalysisSettings:
        window = self.native_window
        return AnalysisSettings(
            plot_type=window.get_plot_type(),
            f1_scale=window.get_f1_scale(),
            f2_scale=window.get_f2_scale(),
            origin=window.get_origin(),
            use_bark_units=window.get_use_bark_units(),
            outlier_mode=window.get_outlier_mode(),
            outlier_scope=window.get_outlier_scope(),
            normalization=window.get_normalization(),
        )

    def apply_analysis_settings(self, settings: AnalysisSettings) -> None:
        self.native_window.apply_project_analysis_state(settings.to_dict())

    def update_file_status(self, count: int) -> None:
        self.native_window.update_file_status(count)

    def toggle_f3_options(self, has_f3: bool) -> None:
        self.native_window.toggle_f3_options(has_f3)

    def sync_pre_lobanov_normalization(self, active: bool) -> None:
        self.native_window.sync_pre_lobanov_normalization(active)

    def reset(self) -> None:
        self.native_window.reset_ui_state()

    def request_file_open(self, callback: Callable[[list[str]], None]) -> None:
        self.native_window.request_file_open(callback)

    def request_project_open(
        self, callback: Callable[[str], None], parent_window: Any | None = None
    ) -> None:
        self.native_window.request_project_open(callback, parent_window=parent_window)

    def request_project_save(
        self, callback: Callable[[str], None], parent_window: Any | None = None
    ) -> None:
        self.native_window.request_project_save(callback, parent_window=parent_window)

    def show_warning(self, title: str, text: str) -> None:
        self.native_window.show_warning(title, text)

    def show_critical(self, title: str, text: str) -> None:
        self.native_window.show_critical(title, text)

    def supports_preview(self) -> bool:
        return hasattr(self.native_window, "preview_label")

    def get_display_scales(self) -> tuple[str, str]:
        return self.native_window.get_display_scale_for_preview()

    def show_preview(self, png_data: bytes, info: str) -> None:
        label = self.native_window.preview_label
        pixmap = QPixmap()
        pixmap.loadFromData(png_data)
        dpr = label.devicePixelRatio()
        scaled = pixmap.scaled(
            int(label.width() * dpr),
            int(label.height() * dpr),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(dpr)
        label.setPixmap(scaled)
        if hasattr(self.native_window, "preview_info_label"):
            self.native_window.preview_info_label.setText(info)

    def show_empty_preview(self) -> None:
        self.native_window.preview_label.clear()
        self.native_window.preview_label.setText("LIVE")
        if hasattr(self.native_window, "preview_info_label"):
            self.native_window.preview_info_label.setText("")

    def show_preview_error(self, text: str) -> None:
        self.native_window.preview_label.clear()
        self.native_window.preview_label.setText("LIVE 렌더링 오류")
        if hasattr(self.native_window, "preview_info_label"):
            self.native_window.preview_info_label.setText(text)


def create_pyside_main_view(controller: Any, status_callback=None):
    return PySideMainViewAdapter(controller, status_callback=status_callback)
