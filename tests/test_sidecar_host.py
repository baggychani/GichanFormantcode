from __future__ import annotations

import json
import threading
import time

from sidecar.host import SidecarHost
from sidecar.supervisor import SidecarSupervisor, SupervisorConfig


def test_host_run_loop_ping_and_shutdown(monkeypatch):
    host = SidecarHost.create_headless()
    outputs: list[str] = []
    host._write = outputs.append

    class FakeStdin:
        def __iter__(self):
            yield '{"v":1,"id":"1","method":"ping","params":{}}\n'
            yield '{"v":1,"id":"2","method":"shutdown","params":{}}\n'

    code = host.run(FakeStdin(), announce=True)
    assert code == 0
    events = [json.loads(line) for line in outputs]
    assert events[0]["event"] == "sidecar_ready"
    assert events[1]["id"] == "1" and events[1]["result"]["ok"] is True
    assert any(item.get("event") == "sidecar_shutting_down" for item in events)
    assert any(
        item.get("id") == "2" and item.get("result", {}).get("ok") for item in events
    )


def test_supervisor_starts_health_and_stops():
    supervisor = SidecarSupervisor(
        SupervisorConfig(health_timeout_s=10.0, max_restarts=1)
    )
    try:
        health = supervisor.ensure_healthy()
        assert health["ok"] is True
        assert health["pid"] > 0
        state = supervisor.call("get_state")
        assert "analysis" in state
        assert "capabilities" in state
    finally:
        supervisor.stop()


def test_desktop_sidecar_process_starts_and_stops():
    supervisor = SidecarSupervisor(
        SupervisorConfig(
            args=["--desktop"],
            env={"QT_QPA_PLATFORM": "offscreen"},
            health_timeout_s=15.0,
            max_restarts=0,
        )
    )
    try:
        health = supervisor.ensure_healthy()
        assert health["ok"] is True
        assert health["headless"] is False
    finally:
        supervisor.stop(timeout_s=5.0)
    assert supervisor.running is False


def test_desktop_host_uses_qapplication_and_pyside_coordinator():
    from PySide6.QtWidgets import QApplication

    from sidecar.desktop import create_desktop_host
    from ui.desktop_window_coordinator import PySideDesktopWindowCoordinator

    app, host = create_desktop_host(writer=lambda _line: None)
    try:
        assert app is QApplication.instance()
        assert host.health()["headless"] is False
        assert isinstance(
            host.service.controller.window_coordinator,
            PySideDesktopWindowCoordinator,
        )
    finally:
        host.close()


def test_qt_executor_marshals_worker_commands_to_main_thread():
    from PySide6.QtCore import QThread
    from PySide6.QtWidgets import QApplication

    from sidecar.desktop import QtMainThreadExecutor

    app = QApplication.instance() or QApplication([])
    executor = QtMainThreadExecutor(app, timeout_s=2.0)
    result: list[bool] = []

    worker = threading.Thread(
        target=lambda: result.append(
            executor(lambda: QThread.currentThread() == app.thread())
        )
    )
    worker.start()
    deadline = time.monotonic() + 2.0
    while worker.is_alive() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.001)
    worker.join(timeout=0.1)

    assert not worker.is_alive()
    assert result == [True]
