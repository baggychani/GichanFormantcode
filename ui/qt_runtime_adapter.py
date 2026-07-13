"""Qt implementation of runtime facilities used by the application layer."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QStandardPaths, QTimer


class QtDebouncer:
    def __init__(self, callback: Callable[[], None], timer_factory=None):
        self._timer = (timer_factory or QTimer)()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(callback)

    def trigger(self, delay_ms: int) -> None:
        self._timer.stop()
        self._timer.start(delay_ms)

    def cancel(self) -> None:
        self._timer.stop()


class QtRuntimeAdapter:
    def __init__(self, timer_factory=None):
        self._timer_factory = timer_factory

    def create_debouncer(self, callback: Callable[[], None]) -> QtDebouncer:
        return QtDebouncer(callback, timer_factory=self._timer_factory)

    def call_soon(self, callback: Callable[[], None]) -> None:
        QTimer.singleShot(0, callback)

    def app_data_dir(self) -> str:
        return QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )

    def documents_dir(self) -> str:
        return QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )

    def downloads_dir(self) -> str:
        return QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )


def create_qt_runtime(timer_factory=None):
    return QtRuntimeAdapter(timer_factory=timer_factory)
