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


def test_load_files_bypasses_qt_executor_to_avoid_transport_timeout(monkeypatch):
    host = SidecarHost.create_headless()
    calls = []

    def fail_if_executed(_command):
        calls.append(True)
        raise AssertionError("load_files must not wait on a GUI executor")

    host._execute_command = fail_if_executed
    monkeypatch.setattr(
        host.service,
        "load_files",
        lambda _paths: {
            "load_result": {
                "success_count": 0,
                "failed": [],
            },
            "state": host.service.snapshot(),
        },
    )

    response = json.loads(
        host.handle_message(
            '{"v":1,"id":"load","method":"load_files",'
            '"params":{"paths":["a.csv"]}}'
        )
    )

    assert "error" not in response
    assert calls == []
    host.close()


def test_get_vowel_analysis_bypasses_qt_executor(monkeypatch):
    host = SidecarHost.create_headless()
    calls = []

    def fail_if_executed(_command):
        calls.append(True)
        raise AssertionError("get_vowel_analysis must not wait on a GUI executor")

    host._execute_command = fail_if_executed
    monkeypatch.setattr(
        host.service,
        "get_vowel_analysis",
        lambda index, sections=None: {
            "index": index,
            "name": "a.csv",
            "statistics": {},
            "centroid_distances": {},
            "pairwise_euclidean": {},
            "pairwise_mahalanobis": {},
            "pillai_scores": {},
            "metadata": {"total_points": 0, "vowel_count": 0},
            "sections": list(sections or ["core"]),
        },
    )

    response = json.loads(
        host.handle_message(
            '{"v":1,"id":"va","method":"get_vowel_analysis",'
            '"params":{"index":0,"sections":["core"]}}'
        )
    )

    assert "error" not in response
    assert response["result"]["index"] == 0
    assert calls == []
    host.close()


def test_host_returns_protocol_error_for_non_object_params():
    host = SidecarHost.create_headless()
    response = json.loads(
        host.handle_message(
            '{"v":1,"id":"bad","method":"load_files","params":[]}'
        )
    )
    assert response["error"]["code"] == "invalid_params"
    assert "JSON object" in response["error"]["message"]
    host.close()


def test_host_measure_distance_returns_ruler_geometry():
    host = SidecarHost.create_headless()
    response = json.loads(
        host.handle_message(
            '{"v":1,"id":"ruler","method":"measure_distance",'
            '"params":{"x1":0,"y1":0,"x2":3,"y2":4}}'
        )
    )
    assert response["result"]["distance"] == 5.0
    assert response["result"]["dx"] == 3.0
    assert response["result"]["dy"] == 4.0
    host.close()
