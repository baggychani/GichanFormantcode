"""Creation and lifecycle operations for concrete PySide windows."""

from __future__ import annotations

from typing import Any


class PySideDesktopWindowCoordinator:
    """Factory for legacy PySide windows.

    Heavy ``ui.windows`` / ``ui.dialogs`` imports stay inside methods so the
    React ``--desktop`` sidecar can answer ``health`` before PlotPopup etc. load.
    Standalone PySide still uses the same coordinator; first open pays the cost.
    """

    def create_ruler_tool(self):
        from tools.ruler import RulerTool

        return RulerTool()

    def create_label_move_tool(self):
        from tools.label_move import LabelMoveTool

        return LabelMoveTool()

    def create_batch_save_worker(self, *args, **kwargs):
        from core.workers import BatchSaveWorker

        return BatchSaveWorker(*args, **kwargs)

    def open_guide(self, parent=None) -> None:
        from ui.dialogs.file_guide import DataGuidePopup

        DataGuidePopup(parent).exec()

    def create_single_plot(self, **kwargs):
        from ui.windows.popup_plot import PlotPopup

        return PlotPopup(**kwargs)

    def create_vowel_analysis(self, **kwargs):
        from ui.dialogs.vowel_analysis_dialog import VowelAnalysisDialog

        return VowelAnalysisDialog(**kwargs)

    def open_compare_dialog(self, **kwargs) -> None:
        from ui.windows.compare_plot import SelectCompareDialog

        SelectCompareDialog(**kwargs).exec()

    def create_compare_plot(self, **kwargs):
        from ui.windows.compare_plot import ComparePlotPopup

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
