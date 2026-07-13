"""Runtime facilities required by the application layer."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class DebouncerPort(Protocol):
    def trigger(self, delay_ms: int) -> None: ...

    def cancel(self) -> None: ...


class RuntimePort(Protocol):
    def create_debouncer(self, callback: Callable[[], None]) -> DebouncerPort: ...

    def call_soon(self, callback: Callable[[], None]) -> None: ...

    def app_data_dir(self) -> str: ...

    def documents_dir(self) -> str: ...

    def downloads_dir(self) -> str: ...


class ManualDebouncer:
    def __init__(self, callback: Callable[[], None]):
        self.callback = callback
        self.delay_ms: int | None = None

    def trigger(self, delay_ms: int) -> None:
        self.delay_ms = delay_ms

    def cancel(self) -> None:
        self.delay_ms = None

    def fire(self) -> None:
        if self.delay_ms is None:
            return
        self.delay_ms = None
        self.callback()


class HeadlessRuntime:
    """Deterministic runtime for tests and non-GUI command hosts."""

    def __init__(
        self,
        *,
        app_data: str = "",
        documents: str = "",
        downloads: str = "",
    ):
        self._app_data = app_data
        self._documents = documents
        self._downloads = downloads
        self.debouncers: list[ManualDebouncer] = []

    def create_debouncer(self, callback: Callable[[], None]) -> ManualDebouncer:
        debouncer = ManualDebouncer(callback)
        self.debouncers.append(debouncer)
        return debouncer

    def call_soon(self, callback: Callable[[], None]) -> None:
        callback()

    def app_data_dir(self) -> str:
        return self._app_data

    def documents_dir(self) -> str:
        return self._documents

    def downloads_dir(self) -> str:
        return self._downloads
