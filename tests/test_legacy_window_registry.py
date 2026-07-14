from __future__ import annotations

from core.legacy_window_registry import LegacyWindowRegistry
from core.window_port import HeadlessWindowCoordinator


class _Window:
    def __init__(self, fail: bool = False):
        self.applied = 0
        self.fail = fail

    def on_apply(self):
        self.applied += 1
        if self.fail:
            raise RuntimeError("render failed")


def test_registry_owns_register_refresh_and_remove_lifecycle():
    registry = LegacyWindowRegistry(HeadlessWindowCoordinator())
    good, bad = _Window(), _Window(fail=True)
    registry.register(good)
    registry.register(bad)
    errors = []

    registry.refresh(on_error=errors.append)
    registry.remove(good, before_remove=lambda _window: None)
    registry.cleanup()

    assert good.applied == 1
    assert bad.applied == 1
    assert str(errors[0]) == "render failed"
    assert registry.windows == [bad]
