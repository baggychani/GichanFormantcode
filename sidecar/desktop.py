"""QApplication-backed sidecar runtime for legacy PySide child windows."""

from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QMetaObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import QApplication

from core.view_port import NullMainView
from sidecar.host import SidecarHost


class _QtCommandBridge(QObject):
    requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.requested.connect(self._run, Qt.ConnectionType.QueuedConnection)

    @Slot(object)
    def _run(self, command: Callable[[], None]) -> None:
        command()


class QtMainThreadExecutor:
    """Synchronously marshal a sidecar command onto the QApplication thread."""

    def __init__(self, app: QApplication, *, timeout_s: float = 65.0) -> None:
        self.app = app
        self.timeout_s = timeout_s
        self._bridge = _QtCommandBridge()

    def __call__(self, command: Callable[[], Any]) -> Any:
        if QThread.currentThread() == self.app.thread():
            return command()

        finished = threading.Event()
        result: dict[str, Any] = {}

        def invoke() -> None:
            try:
                result["value"] = command()
            except BaseException as exc:  # noqa: BLE001 - re-raised on IPC thread
                result["error"] = exc
            finally:
                finished.set()

        self._bridge.requested.emit(invoke)
        if not finished.wait(self.timeout_s):
            raise TimeoutError("timed out waiting for Qt main-thread command")
        if "error" in result:
            raise result["error"]
        return result.get("value")


def warm_desktop_imports() -> None:
    """Import heavy scientific stacks off the critical health path.

    Failures are ignored: analysis/render paths still import on demand.
    Also touch PlotEngine so the first main-window preview is not cold.
    """
    try:
        import matplotlib

        matplotlib.use("Agg", force=False)
        import matplotlib.pyplot as plt
        import numpy  # noqa: F401
        import pandas  # noqa: F401
        from scipy import stats  # noqa: F401
        from engine.plot_engine import PlotEngine  # noqa: F401

        PlotEngine()
        figure = plt.figure(figsize=(1.0, 1.0), dpi=72)
        figure.add_subplot(111)
        plt.close(figure)
    except Exception:  # noqa: BLE001 - warm must never break sidecar startup
        pass


def create_desktop_host(
    *, writer: Callable[[str], None] | None = None
) -> tuple[QApplication, SidecarHost]:
    """Create a hidden-main-window host that can open legacy PySide dialogs."""
    from core.controller import MainController
    from ui.desktop_window_coordinator import create_pyside_window_coordinator
    from ui.qt_runtime_adapter import create_qt_runtime

    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    view = NullMainView()
    controller = MainController(
        view_factory=lambda *_args: view,
        runtime=create_qt_runtime(),
        window_coordinator=create_pyside_window_coordinator(),
        render_initial_preview=False,
    )
    executor = QtMainThreadExecutor(app)
    host = SidecarHost(
        service=controller.application_service,
        writer=writer,
        headless=False,
        command_executor=executor,
    )
    return app, host


def run_desktop_sidecar() -> int:
    """Run stdio on a worker while QApplication owns the process main thread."""
    app, host = create_desktop_host()
    result = {"code": 0}

    def serve() -> None:
        try:
            result["code"] = host.run()
        finally:
            QMetaObject.invokeMethod(
                app,
                "quit",
                Qt.ConnectionType.QueuedConnection,
            )

    # Warm scipy/matplotlib after the host exists so health can answer immediately
    # while first plot/analysis pays less cold-import cost.
    warm_thread = threading.Thread(
        target=warm_desktop_imports,
        name="sidecar-warm",
        daemon=True,
    )
    warm_thread.start()

    worker = threading.Thread(target=serve, name="sidecar-stdio", daemon=True)
    worker.start()
    app.exec()
    host.close()
    worker.join(timeout=1.0)
    return int(result["code"])
