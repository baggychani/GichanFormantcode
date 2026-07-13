"""Framework-neutral application events and structured failures."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ApplicationEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "payload": self.payload}


class ApplicationEventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable[[ApplicationEvent], None]]] = (
            defaultdict(list)
        )

    def subscribe(
        self, name: str, callback: Callable[[ApplicationEvent], None]
    ) -> Callable[[], None]:
        self._subscribers[name].append(callback)

        def unsubscribe() -> None:
            callbacks = self._subscribers.get(name, [])
            if callback in callbacks:
                callbacks.remove(callback)

        return unsubscribe

    def emit(self, name: str, payload: dict[str, Any] | None = None) -> list[Exception]:
        event = ApplicationEvent(name=name, payload=dict(payload or {}))
        failures = []
        callbacks = [
            *self._subscribers.get(name, []),
            *self._subscribers.get("*", []),
        ]
        for callback in tuple(callbacks):
            try:
                callback(event)
            except Exception as exc:  # subscribers cannot break application commands
                failures.append(exc)
        return failures


@dataclass(frozen=True, slots=True)
class ApplicationError(Exception):
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }
