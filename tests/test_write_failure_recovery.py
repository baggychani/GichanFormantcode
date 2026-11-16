"""A failed write must not disable rendering or disturb other open files."""

import os
import shutil
import threading

import pytest

import core.application_service as application_service_module
from core.controller import MainController
from core.render_scheduler import LatestRenderScheduler, RenderJob
from core.runtime_port import HeadlessRuntime
from core.view_port import NullMainView


@pytest.fixture
def service():
    controller = MainController(
        view_factory=lambda *_args: NullMainView(),
        runtime=HeadlessRuntime(),
        render_initial_preview=False,
    )
    result = controller.application_service
    try:
        yield result
    finally:
        result.close()


def test_render_worker_survives_a_failing_result_callback():
    delivered: list[str] = []
    errors: list[tuple[str, str]] = []
    second_done = threading.Event()

    def on_result(job, _result):
        if job.job_id == "first":
            raise FileNotFoundError("preview directory vanished")
        delivered.append(job.job_id)
        second_done.set()

    first_reported = threading.Event()

    def on_error(job, error):
        errors.append((job.job_id, str(error)))
        first_reported.set()

    scheduler = LatestRenderScheduler(lambda payload: payload, on_result, on_error)
    try:
        scheduler.submit(RenderJob("first", 1))
        assert first_reported.wait(2)
        scheduler.submit(RenderJob("second", 2))
        assert second_done.wait(2)
    finally:
        scheduler.close()

    assert errors == [("first", "preview directory vanished")]
    assert delivered == ["second"]


def test_preview_publish_recreates_a_removed_preview_directory(service):
    shutil.rmtree(service._preview_dir)
    ready = []
    service.events.subscribe("preview_ready", ready.append)

    service.publish_preview(b"png-bytes", "info", target="interactive")

    assert len(ready) == 1
    with open(ready[0].payload["png_path"], "rb") as stream:
        assert stream.read() == b"png-bytes"


def test_failed_atomic_write_does_not_close_a_reused_descriptor(tmp_path, monkeypatch):
    target = tmp_path / "plot.png"
    opened: list[int] = []

    def failing_replace(*_args, **_kwargs):
        # Another thread opening a file now receives the descriptor number the
        # temporary file just released.
        opened.append(os.open(tmp_path / "other.bin", os.O_CREAT | os.O_WRONLY))
        raise PermissionError("target is open in an image viewer")

    monkeypatch.setattr(application_service_module.os, "replace", failing_replace)
    try:
        with pytest.raises(PermissionError):
            application_service_module._atomic_write_bytes(target, b"data")
        assert os.write(opened[0], b"x") == 1
    finally:
        for descriptor in opened:
            try:
                os.close(descriptor)
            except OSError:
                pass

    assert not target.exists()
    assert sorted(entry.name for entry in tmp_path.iterdir()) == ["other.bin"]
