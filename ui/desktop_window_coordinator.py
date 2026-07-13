"""Creation and lifecycle operations for concrete PySide windows."""

from __future__ import annotations

from typing import Any

from ui.dialogs.file_guide import DataGuidePopup
from ui.dialogs.vowel_analysis_dialog import VowelAnalysisDialog
from ui.windows.compare_plot import ComparePlotPopup, SelectCompareDialog
from ui.windows.popup_plot import PlotPopup
from tools.label_move import LabelMoveTool
from tools.ruler import RulerTool
from core.workers import BatchSaveWorker


class PySideDesktopWindowCoordinator:
    def create_ruler_tool(self):
        return RulerTool()

    def create_label_move_tool(self):
        return LabelMoveTool()

    def create_batch_save_worker(self, *args, **kwargs):
        return BatchSaveWorker(*args, **kwargs)

    def open_guide(self, parent=None) -> None:
        DataGuidePopup(parent).exec()

    def create_single_plot(self, **kwargs):
        return PlotPopup(**kwargs)

    def create_vowel_analysis(self, **kwargs):
        return VowelAnalysisDialog(**kwargs)

    def open_compare_dialog(self, **kwargs) -> None:
        SelectCompareDialog(**kwargs).exec()

    def create_compare_plot(self, **kwargs):
        return ComparePlotPopup(**kwargs)

    def register(self, registry: list[Any], window: Any) -> None:
        if window not in registry:
            registry.append(window)

    def remove(self, registry: list[Any], window: Any) -> None:
        if window in registry:
            registry.remove(window)

    def cleanup(self, registry: list[Any]) -> list[Any]:
        active = []
        for window in registry:
            try:
                if window and not window.isHidden() and window.isVisible():
                    active.append(window)
            except (RuntimeError, AttributeError):
                continue
        return active


def create_pyside_window_coordinator():
    return PySideDesktopWindowCoordinator()
