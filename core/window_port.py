"""Window creation boundary for optional desktop presentation backends."""

from __future__ import annotations

from typing import Any, Protocol

from core.application_events import ApplicationError


class DesktopWindowPort(Protocol):
    def create_ruler_tool(self) -> Any: ...

    def create_label_move_tool(self) -> Any: ...

    def create_batch_save_worker(self, *args, **kwargs) -> Any: ...

    def open_guide(self, parent: Any | None) -> None: ...

    def create_single_plot(self, **kwargs) -> Any: ...

    def create_vowel_analysis(self, **kwargs) -> Any: ...

    def open_compare_dialog(self, **kwargs) -> None: ...

    def create_compare_plot(self, **kwargs) -> Any: ...

    def register(self, registry: list[Any], window: Any) -> None: ...

    def remove(self, registry: list[Any], window: Any) -> None: ...

    def cleanup(self, registry: list[Any]) -> list[Any]: ...


class HeadlessWindowCoordinator:
    def create_ruler_tool(self):
        return _NullInteractionTool()

    def create_label_move_tool(self):
        return _NullInteractionTool()

    def create_batch_save_worker(self, *args, **kwargs):
        del args, kwargs
        self._unavailable()

    def _unavailable(self):
        raise ApplicationError(
            code="window_backend_unavailable",
            message="이 실행 환경에서는 데스크톱 창을 열 수 없습니다.",
        )

    def open_guide(self, parent=None) -> None:
        del parent
        self._unavailable()

    def create_single_plot(self, **kwargs):
        del kwargs
        self._unavailable()

    def create_vowel_analysis(self, **kwargs):
        del kwargs
        self._unavailable()

    def open_compare_dialog(self, **kwargs) -> None:
        del kwargs
        self._unavailable()

    def create_compare_plot(self, **kwargs):
        del kwargs
        self._unavailable()

    def register(self, registry: list[Any], window: Any) -> None:
        registry.append(window)

    def remove(self, registry: list[Any], window: Any) -> None:
        if window in registry:
            registry.remove(window)

    def cleanup(self, registry: list[Any]) -> list[Any]:
        return list(registry)


class _NullInteractionTool:
    active = False

    def detach(self) -> None:
        self.active = False

    def toggle(self) -> bool:
        self.active = not self.active
        return self.active

    def set_context(self, *_args, **_kwargs) -> None:
        pass
