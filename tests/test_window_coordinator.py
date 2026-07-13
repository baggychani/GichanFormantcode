import pytest

from core.application_events import ApplicationError
from core.window_port import HeadlessWindowCoordinator
from ui.desktop_window_coordinator import PySideDesktopWindowCoordinator


class _Window:
    def __init__(self, visible=True, hidden=False):
        self.visible = visible
        self.hidden = hidden

    def isVisible(self):
        return self.visible

    def isHidden(self):
        return self.hidden


def test_pyside_window_coordinator_owns_registry_lifecycle():
    coordinator = PySideDesktopWindowCoordinator()
    visible = _Window()
    hidden = _Window(visible=False, hidden=True)
    registry = []

    coordinator.register(registry, visible)
    coordinator.register(registry, visible)
    coordinator.register(registry, hidden)

    assert registry == [visible, hidden]
    assert coordinator.cleanup(registry) == [visible]
    coordinator.remove(registry, visible)
    assert registry == [hidden]


def test_headless_window_coordinator_returns_structured_error():
    coordinator = HeadlessWindowCoordinator()

    with pytest.raises(ApplicationError) as exc_info:
        coordinator.create_single_plot()

    assert exc_info.value.code == "window_backend_unavailable"
