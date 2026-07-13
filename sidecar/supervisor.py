"""Development/test supervisor for the GichanFormant Python sidecar.

The production Tauri process owns its child through the Rust bridge. This
supervisor remains useful for Python integration tests and local diagnostics.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from core.ipc.protocol import ProtocolError, decode_line, encode_request


@dataclass
class SupervisorConfig:
    python_executable: str = field(default_factory=lambda: sys.executable)
    module: str = "sidecar"
    args: Sequence[str] = field(default_factory=lambda: ["--headless"])
    health_timeout_s: float = 5.0
    restart_backoff_s: float = 0.25
    max_restarts: int = 3
    cwd: str | None = None
    env: dict[str, str] | None = None


class SidecarSupervisor:
    """Own a single sidecar child process with crash recovery."""

    def __init__(self, config: SupervisorConfig | None = None):
        self.config = config or SupervisorConfig()
        self.process: subprocess.Popen[str] | None = None
        self.restarts = 0
        self._request_counter = 0
        self._messages: queue.Queue[dict[str, Any]] = queue.Queue()
        self._stderr_lines: deque[str] = deque(maxlen=100)
        self._call_lock = threading.RLock()

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> None:
        with self._call_lock:
            if self.running:
                return
            self._start_locked()

    def _start_locked(self) -> None:
        command = [
            self.config.python_executable,
            "-m",
            self.config.module,
            *self.config.args,
        ]
        env = os.environ.copy()
        if self.config.env:
            env.update(self.config.env)
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.config.cwd,
            env=env,
        )
        messages: queue.Queue[dict[str, Any]] = queue.Queue()
        stderr_lines: deque[str] = deque(maxlen=100)
        self._messages = messages
        self._stderr_lines = stderr_lines
        assert self.process.stdout is not None and self.process.stderr is not None
        threading.Thread(
            target=self._read_stdout,
            args=(self.process.stdout, messages, stderr_lines),
            name="sidecar-supervisor-stdout",
            daemon=True,
        ).start()
        threading.Thread(
            target=self._read_stderr,
            args=(self.process.stderr, stderr_lines),
            name="sidecar-supervisor-stderr",
            daemon=True,
        ).start()
        self._wait_until_ready()

    def stop(self, *, timeout_s: float = 5.0) -> None:
        with self._call_lock:
            if not self.process:
                return
            if self.running:
                try:
                    self._call_locked("shutdown", {}, timeout_s=timeout_s)
                except Exception:
                    self.process.terminate()
            try:
                self.process.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=timeout_s)
            self.process = None

    def ensure_healthy(self) -> dict[str, Any]:
        try:
            return self.call("health", {})
        except Exception:
            self._restart()
            return self.call("health", {})

    def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout_s: float | None = None,
    ) -> Any:
        with self._call_lock:
            return self._call_locked(method, params, timeout_s=timeout_s)

    def _call_locked(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout_s: float | None = None,
    ) -> Any:
        if not self.running:
            self._start_locked()
        assert self.process is not None and self.process.stdin and self.process.stdout
        self._request_counter += 1
        request_id = f"sup-{self._request_counter}"
        line = encode_request(method, params, request_id=request_id)
        try:
            self.process.stdin.write(line + "\n")
            self.process.stdin.flush()
        except BrokenPipeError:
            self._restart()
            return self._call_locked(method, params, timeout_s=timeout_s)

        deadline = time.monotonic() + (
            timeout_s if timeout_s is not None else self.config.health_timeout_s
        )
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"sidecar exited with code {self.process.returncode}"
                )
            message = self._next_message(deadline)
            if message.get("event"):
                continue
            if message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                raise ProtocolError(
                    error.get("code", "remote_error"),
                    error.get("message", "sidecar error"),
                    error.get("details") or {},
                )
            return message.get("result")
        raise TimeoutError(f"timed out waiting for {method} response")

    def _restart(self) -> None:
        if self.restarts >= self.config.max_restarts:
            raise RuntimeError("sidecar exceeded max restart attempts")
        self.restarts += 1
        if self.process is not None:
            try:
                self.process.kill()
                self.process.wait(timeout=2.0)
            except Exception:
                pass
            self.process = None
        time.sleep(self.config.restart_backoff_s)
        self.start()

    def _wait_until_ready(self) -> None:
        assert self.process is not None
        deadline = time.monotonic() + self.config.health_timeout_s
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                stderr = "\n".join(self._stderr_lines)
                raise RuntimeError(
                    f"sidecar failed to start (code={self.process.returncode}): {stderr}"
                )
            message = self._next_message(deadline)
            if message.get("event") == "sidecar_ready":
                return
        raise TimeoutError("sidecar did not emit sidecar_ready")

    def _next_message(self, deadline: float) -> dict[str, Any]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("timed out waiting for sidecar output")
        try:
            message = self._messages.get(timeout=remaining)
        except queue.Empty as exc:
            raise TimeoutError("timed out waiting for sidecar output") from exc
        if transport_error := message.get("_transport_error"):
            raise RuntimeError(str(transport_error))
        return message

    @staticmethod
    def _read_stdout(stream, messages, stderr_lines) -> None:
        for raw in stream:
            try:
                messages.put(decode_line(raw))
            except ProtocolError as exc:
                stderr_lines.append(f"invalid sidecar stdout: {exc}")
        messages.put({"_transport_error": "sidecar stdout closed"})

    @staticmethod
    def _read_stderr(stream, stderr_lines) -> None:
        for line in stream:
            stderr_lines.append(line.rstrip())
