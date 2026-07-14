"""Headless/desktop ApplicationService host over NDJSON stdio."""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from collections.abc import Callable
from typing import Any, TextIO

import config
from core.application_events import ApplicationError, ApplicationEvent
from core.application_service import ApplicationService
from core.controller import MainController
from core.ipc.protocol import (
    COMMANDS,
    ProtocolError,
    decode_line,
    encode_error,
    encode_event,
    encode_response,
    protocol_manifest,
    validate_params,
)
from core.runtime_port import HeadlessRuntime
from core.render_scheduler import LatestRenderScheduler, RenderJob
from core.view_port import NullMainView


class SidecarHost:
    """Dispatch IPC commands to ApplicationService and forward events."""

    def __init__(
        self,
        *,
        service: ApplicationService | None = None,
        writer: Callable[[str], None] | None = None,
        headless: bool = True,
        command_executor: Callable[[Callable[[], Any]], Any] | None = None,
    ):
        self.started_at = time.monotonic()
        self.pid = os.getpid()
        self.headless = headless
        self._shutting_down = False
        self._write = writer or self._default_write
        self._write_lock = threading.Lock()
        self._execute_command = command_executor or (lambda command: command())
        if service is None:
            if not headless:
                raise ValueError(
                    "desktop hosts require an explicit QApplication-backed service"
                )
            view = NullMainView()
            controller = MainController(
                view_factory=lambda *_args: view,
                runtime=HeadlessRuntime(),
                render_initial_preview=False,
            )
            service = controller.application_service
        self.service = service
        self._unsubscribe = self.service.events.subscribe("*", self._on_event)
        self._render_scheduler = LatestRenderScheduler(
            self.service.render_prepared_interactive_preview,
            self._on_render_result,
            self._on_render_error,
        )

    @classmethod
    def create_headless(cls, **kwargs: Any) -> "SidecarHost":
        return cls(headless=True, **kwargs)

    def close(self) -> None:
        if self._render_scheduler is not None:
            self._render_scheduler.close()
            self._render_scheduler = None
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        close_service = getattr(self.service, "close", None)
        if callable(close_service):
            close_service()

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "pid": self.pid,
            "uptime_ms": int((time.monotonic() - self.started_at) * 1000),
            "version": config.APP_VERSION,
            "protocol_version": protocol_manifest()["protocol_version"],
            "headless": self.headless,
            "commands": sorted(COMMANDS),
        }

    def handle_message(self, raw: str | bytes) -> str | None:
        request_id: str | None = None
        try:
            message = decode_line(raw)
            if "event" in message:
                raise ProtocolError(
                    "invalid_envelope",
                    "client must not send event envelopes",
                )
            request_id = message.get("id")
            if request_id is None:
                raise ProtocolError("invalid_envelope", "request id is required")
            method = message.get("method")
            if not isinstance(method, str):
                raise ProtocolError("invalid_envelope", "method must be a string")
            params = validate_params(method, message.get("params") or {})
            result = self.dispatch(method, params)
            if method == "shutdown":
                # Response is written before the run loop exits.
                return encode_response(str(request_id), result)
            return encode_response(str(request_id), result)
        except ProtocolError as exc:
            return encode_error(
                str(request_id) if request_id else None, **exc.to_dict()
            )
        except ApplicationError as exc:
            return encode_error(
                str(request_id) if request_id else None,
                exc.code,
                exc.message,
                exc.details,
            )
        except Exception as exc:  # noqa: BLE001 - transport must never die silently
            return encode_error(
                str(request_id) if request_id else None,
                "internal_error",
                str(exc),
            )

    def dispatch(self, method: str, params: dict[str, Any]) -> Any:
        return self._execute_command(lambda: self._dispatch_command(method, params))

    def _dispatch_command(self, method: str, params: dict[str, Any]) -> Any:
        if method in {"ping", "health"}:
            return self.health()
        if method == "shutdown":
            self._shutting_down = True
            self.emit_raw("sidecar_shutting_down", {"pid": self.pid})
            return {"ok": True}
        if method in {"get_state", "snapshot"}:
            return self.service.snapshot()
        if method == "set_analysis_settings":
            return self.service.set_analysis_settings(params["settings"])
        if method == "load_files":
            return self.service.load_files(list(params["paths"]))
        if method == "remove_file":
            return self.service.remove_file(int(params["index"]))
        if method == "set_current_index":
            return self.service.set_current_index(int(params["index"]))
        if method == "reset":
            return self.service.reset()
        if method == "save_project":
            self.service.save_project(str(params["path"]))
            return {"ok": True, "path": params["path"]}
        if method == "load_project":
            return self.service.load_project(
                str(params["path"]), restore_windows=False
            )
        if method == "open_single_plot":
            self.service.open_single_plot()
            return {"ok": True}
        if method == "open_compare":
            self.service.open_compare(
                params["source_groups"],
                normalization=params.get("normalization"),
            )
            return {"ok": True}
        if method == "open_guide":
            self.service.open_guide()
            return {"ok": True}
        if method == "request_preview":
            self.service.request_preview(params.get("request_id"))
            runtime = getattr(self.service.controller, "runtime", None)
            for debouncer in getattr(runtime, "debouncers", []):
                if hasattr(debouncer, "fire"):
                    debouncer.fire()
            return {"ok": True}
        if method == "update_interactive_session":
            return self.service.update_interactive_session(params["options"])
        if method == "render_interactive_preview":
            try:
                prepared = self.service.prepare_interactive_preview(params["options"])
            except Exception as exc:
                # Preparation runs before the async renderer.  Surface errors
                # through the same preview channel as worker failures so the
                # React window never waits silently for an image that cannot
                # be produced.
                self.service.publish_preview_error(
                    str(exc),
                    target="interactive",
                    request_id=params["options"].get("request_id"),
                )
                raise
            job_id = uuid.uuid4().hex
            self._render_scheduler.submit(RenderJob(job_id, prepared))
            return {
                "ok": True,
                "accepted": True,
                "job_id": job_id,
                "request_id": prepared.get("request_id"),
                "revision": prepared.get("revision"),
            }
        raise ProtocolError("unknown_method", f"unknown method {method!r}")

    def _on_render_result(self, _job: RenderJob, result: Any) -> None:
        self.service.publish_interactive_render_result(result)

    def _on_render_error(self, job: RenderJob, error: Exception) -> None:
        request_id = None
        if isinstance(job.payload, dict):
            request_id = job.payload.get("request_id")
        self.service.publish_preview_error(
            str(error), target="interactive", request_id=request_id
        )

    def emit_raw(self, name: str, payload: dict[str, Any] | None = None) -> None:
        self._write_line(encode_event(name, payload))

    def run(
        self,
        stdin: TextIO | None = None,
        *,
        announce: bool = True,
    ) -> int:
        stream = stdin or sys.stdin
        if announce:
            self.emit_raw(
                "sidecar_ready",
                {
                    "pid": self.pid,
                    "version": config.APP_VERSION,
                    "protocol_version": protocol_manifest()["protocol_version"],
                    "headless": self.headless,
                },
            )
        for line in stream:
            response = self.handle_message(line)
            if response is not None:
                self._write_line(response)
            if self._shutting_down:
                break
        self.close()
        return 0

    def _on_event(self, event: ApplicationEvent) -> None:
        self._write_line(encode_event(event.name, event.payload))

    def _write_line(self, line: str) -> None:
        """Keep concurrent application events from corrupting NDJSON output."""
        with self._write_lock:
            self._write(line)

    @staticmethod
    def _default_write(line: str) -> None:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


def new_request_id() -> str:
    return uuid.uuid4().hex
