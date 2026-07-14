"""Isolated Agg renderer for React's interactive preview.

The desktop sidecar owns a QApplication for legacy PySide windows.  Matplotlib
objects are not safe to create or draw from a random worker thread in that
process, even when the figure is nominally off-screen.  This small process owns
its own Agg-only Matplotlib runtime and is deliberately the only place where
interactive PNGs are rendered.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import queue
import threading
from typing import Any, Mapping


def _render_worker(requests, responses) -> None:
    # Must be set before importing any Matplotlib module in this child process.
    os.environ["MPLBACKEND"] = "Agg"
    from matplotlib.figure import Figure

    from core.preview_renderer import PreviewRenderer
    from engine.plot_engine import PlotEngine

    renderer = PreviewRenderer(PlotEngine(), Figure(figsize=(6.5, 6.5), dpi=150))
    while True:
        message = requests.get()
        if message is None:
            return
        job_id, prepared = message
        try:
            png_data = renderer.render_png(
                prepared["current_data"],
                prepared["params"],
                prepared["ranges"],
                prepared["design"],
                filter_state=prepared.get("filter_state"),
                layer_overrides=prepared.get("layer_overrides"),
                layer_order=prepared.get("layer_order"),
                custom_label_offsets=prepared.get("custom_label_offsets"),
            )
            responses.put((job_id, True, png_data))
        except Exception as exc:  # noqa: BLE001 - cross-process error boundary
            responses.put((job_id, False, f"interactive render failed: {exc}"))


class IsolatedInteractiveRenderer:
    """Persistent spawn-process renderer, called by one scheduler thread."""

    _TIMEOUT_S = 120.0

    def __init__(self) -> None:
        self._context = mp.get_context("spawn")
        self._lock = threading.Lock()
        self._process: mp.Process | None = None
        self._requests = None
        self._responses = None
        self._next_job_id = 0

    def render(self, prepared: Mapping[str, Any]) -> dict[str, Any]:
        if prepared.get("empty"):
            return dict(prepared)
        with self._lock:
            self._ensure_started()
            assert self._requests is not None and self._responses is not None
            self._next_job_id += 1
            job_id = self._next_job_id
            self._requests.put((job_id, dict(prepared)))
            try:
                returned_id, ok, payload = self._responses.get(timeout=self._TIMEOUT_S)
            except queue.Empty as exc:
                self._stop_locked()
                raise TimeoutError("interactive renderer process timed out") from exc
            if returned_id != job_id:
                # The scheduler is single-consumer, so this signals a corrupted
                # worker protocol rather than an ordinary stale render.
                self._stop_locked()
                raise RuntimeError("interactive renderer response order mismatch")
            if not ok:
                raise RuntimeError(str(payload))
            return {
                "empty": False,
                "png_data": payload,
                "filename": prepared["filename"],
                "request_id": prepared.get("request_id"),
                "revision": prepared.get("revision"),
            }

    def close(self) -> None:
        with self._lock:
            self._stop_locked()

    def _ensure_started(self) -> None:
        if self._process is not None and self._process.is_alive():
            return
        self._stop_locked()
        self._requests = self._context.Queue(maxsize=1)
        self._responses = self._context.Queue(maxsize=1)
        self._process = self._context.Process(
            target=_render_worker,
            args=(self._requests, self._responses),
            name="gichan-interactive-render",
            daemon=True,
        )
        self._process.start()

    def _stop_locked(self) -> None:
        process = self._process
        requests = self._requests
        if process is not None:
            if process.is_alive() and requests is not None:
                try:
                    requests.put_nowait(None)
                except (queue.Full, OSError):
                    pass
            process.join(timeout=1.0)
            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
        for channel in (self._requests, self._responses):
            if channel is not None:
                channel.close()
        self._process = None
        self._requests = None
        self._responses = None
