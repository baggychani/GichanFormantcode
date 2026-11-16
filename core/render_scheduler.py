"""Latest-wins background scheduler for interactive preview renders."""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class RenderJob:
    job_id: str
    payload: Any


class LatestRenderScheduler:
    """Run one render at a time and replace work that has not started yet."""

    def __init__(
        self,
        render: Callable[[Any], Any],
        on_result: Callable[[RenderJob, Any], None],
        on_error: Callable[[RenderJob, Exception], None],
    ) -> None:
        self._render = render
        self._on_result = on_result
        self._on_error = on_error
        self._condition = threading.Condition()
        self._pending: RenderJob | None = None
        self._latest_job_id: str | None = None
        self._closed = False
        self._thread = threading.Thread(
            target=self._run, name="interactive-render", daemon=True
        )
        self._thread.start()

    def submit(self, job: RenderJob) -> None:
        with self._condition:
            if self._closed:
                raise RuntimeError("render scheduler is closed")
            self._latest_job_id = job.job_id
            self._pending = job
            self._condition.notify()

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._pending = None
            self._condition.notify_all()
        if threading.current_thread() is not self._thread:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while True:
            with self._condition:
                while self._pending is None and not self._closed:
                    self._condition.wait()
                if self._closed:
                    return
                job = self._pending
                self._pending = None
            assert job is not None
            try:
                result = self._render(job.payload)
            except Exception as exc:  # noqa: BLE001 - reported through event boundary
                self._report_error(job, exc)
                continue
            if not self._is_latest(job):
                continue
            try:
                self._on_result(job, result)
            except Exception as exc:  # noqa: BLE001 - publishing can fail too
                # For example the preview file could not be written. Report it
                # like a render failure; an escaped exception would end this
                # thread and every later render would be accepted but never run.
                self._report_error(job, exc)

    def _report_error(self, job: RenderJob, error: Exception) -> None:
        if not self._is_latest(job):
            return
        try:
            self._on_error(job, error)
        except Exception:  # noqa: BLE001 - nothing left to notify; keep the worker alive
            pass

    def _is_latest(self, job: RenderJob) -> bool:
        with self._condition:
            return not self._closed and self._latest_job_id == job.job_id
