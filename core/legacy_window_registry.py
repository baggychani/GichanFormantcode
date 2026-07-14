"""Lifecycle registry for optional PySide plot windows.

The registry deliberately knows only the desktop window port.  Plot-specific
cleanup remains a callback supplied by the controller, so no PySide classes or
analysis state leak into this small lifecycle boundary.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class LegacyWindowRegistry:
    def __init__(self, coordinator: Any) -> None:
        self._coordinator = coordinator
        self._windows: list[Any] = []

    @property
    def windows(self) -> list[Any]:
        return self._windows

    def replace(self, windows: list[Any]) -> None:
        self._windows = list(windows)

    def register(self, window: Any) -> None:
        self._coordinator.register(self._windows, window)

    def remove(self, window: Any, *, before_remove: Callable[[Any], None]) -> None:
        before_remove(window)
        self._coordinator.remove(self._windows, window)

    def cleanup(self) -> None:
        self._windows = self._coordinator.cleanup(self._windows)

    def refresh(self, *, on_error: Callable[[Exception], None]) -> None:
        for window in tuple(self._windows):
            apply = getattr(window, "on_apply", None)
            if not callable(apply):
                continue
            try:
                apply()
            except Exception as exc:  # noqa: BLE001 - legacy GUI boundary
                on_error(exc)
