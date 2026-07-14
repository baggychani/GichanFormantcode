"""Lazy factory for the optional PySide presentation adapters.

This is the only core-side seam that imports the legacy ``ui`` package. The
Controller depends on ports and factories only, so headless/sidecar imports do
not pull in PySide widgets.
"""

from __future__ import annotations

from core.window_port import HeadlessWindowCoordinator


def create_default_runtime(*, timer_factory=None):
    """Create the Qt runtime only for the legacy desktop entry point."""
    from ui.qt_runtime_adapter import create_qt_runtime

    return create_qt_runtime(timer_factory=timer_factory)


def create_default_view(controller, status_callback=None):
    """Create the legacy main-window adapter on demand."""
    from ui.main_view_adapter import create_pyside_main_view

    return create_pyside_main_view(controller, status_callback)


def create_default_window_coordinator(native_window):
    """Select a headless or PySide popup coordinator from the active view."""
    if native_window is None:
        return HeadlessWindowCoordinator()

    from ui.desktop_window_coordinator import create_pyside_window_coordinator

    return create_pyside_window_coordinator()
