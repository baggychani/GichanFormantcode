"""QApplication-backed sidecar runtime for legacy PySide child windows."""

from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QMetaObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import QApplication

from core.controller import MainController
from core.view_port import NullMainView
from sidecar.host import SidecarHost
from ui.desktop_window_coordinator import create_pyside_window_coordinator
from ui.qt_runtime_adapter import create_qt_runtime


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


def create_desktop_host(
    *, writer: Callable[[str], None] | None = None
) -> tuple[QApplication, SidecarHost]:
    """Create a hidden-main-window host that can open legacy PySide dialogs."""
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

    worker = threading.Thread(target=serve, name="sidecar-stdio", daemon=True)
    worker.start()
    app.exec()
    host.close()
    worker.join(timeout=1.0)
    return int(result["code"])
