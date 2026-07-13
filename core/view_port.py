"""Main-window boundary shared by desktop and future web frontends."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from core.application_state import AnalysisSettings


@runtime_checkable
class MainViewPort(Protocol):
    """Operations the application layer needs from its main presentation."""

    native_window: Any | None

    def get_analysis_settings(self) -> AnalysisSettings: ...

    def apply_analysis_settings(self, settings: AnalysisSettings) -> None: ...

    def update_file_status(self, count: int) -> None: ...

    def toggle_f3_options(self, has_f3: bool) -> None: ...

    def sync_pre_lobanov_normalization(self, active: bool) -> None: ...

    def reset(self) -> None: ...

    def request_file_open(self, callback: Callable[[list[str]], None]) -> None: ...

    def request_project_open(
        self, callback: Callable[[str], None], parent_window: Any | None = None
    ) -> None: ...

    def request_project_save(
        self, callback: Callable[[str], None], parent_window: Any | None = None
    ) -> None: ...

    def show_warning(self, title: str, text: str) -> None: ...

    def show_critical(self, title: str, text: str) -> None: ...

    def supports_preview(self) -> bool: ...

    def get_display_scales(self) -> tuple[str, str]: ...

    def show_preview(self, png_data: bytes, info: str) -> None: ...

    def show_empty_preview(self) -> None: ...

    def show_preview_error(self, text: str) -> None: ...


class NullMainView:
    """In-memory view for headless application tests and service hosts."""

    native_window = None

    def __init__(self, settings: AnalysisSettings | None = None):
        self.settings = settings or AnalysisSettings()
        self.file_count = 0
        self.has_f3 = False
        self.pre_lobanov = False
        self.warnings: list[tuple[str, str]] = []
        self.criticals: list[tuple[str, str]] = []
        self.preview_png: bytes | None = None
        self.preview_info = ""

    def get_analysis_settings(self) -> AnalysisSettings:
        return self.settings

    def apply_analysis_settings(self, settings: AnalysisSettings) -> None:
        self.settings = settings

    def update_file_status(self, count: int) -> None:
        self.file_count = count

    def toggle_f3_options(self, has_f3: bool) -> None:
        self.has_f3 = has_f3

    def sync_pre_lobanov_normalization(self, active: bool) -> None:
        self.pre_lobanov = active

    def reset(self) -> None:
        self.settings = AnalysisSettings()
        self.file_count = 0
        self.has_f3 = False
        self.pre_lobanov = False
        self.show_empty_preview()

    def request_file_open(self, callback: Callable[[list[str]], None]) -> None:
        del callback

    def request_project_open(
        self, callback: Callable[[str], None], parent_window: Any | None = None
    ) -> None:
        del callback, parent_window

    def request_project_save(
        self, callback: Callable[[str], None], parent_window: Any | None = None
    ) -> None:
        del callback, parent_window

    def show_warning(self, title: str, text: str) -> None:
        self.warnings.append((title, text))

    def show_critical(self, title: str, text: str) -> None:
        self.criticals.append((title, text))

    def supports_preview(self) -> bool:
        return True

    def get_display_scales(self) -> tuple[str, str]:
        return self.settings.f1_scale, self.settings.f2_scale

    def show_preview(self, png_data: bytes, info: str) -> None:
        self.preview_png = bytes(png_data)
        self.preview_info = info

    def show_empty_preview(self) -> None:
        self.preview_png = None
        self.preview_info = ""

    def show_preview_error(self, text: str) -> None:
        self.preview_png = None
        self.preview_info = text
