from __future__ import annotations

import json
import threading
import time

import pytest

from core.application_events import ApplicationEventBus
from core.interactive_plot_state import (
    InteractiveOptionsError,
    PlotSessionState,
    validate_interactive_options,
)
from core.render_scheduler import LatestRenderScheduler, RenderJob
from sidecar.host import SidecarHost


def test_interactive_options_validate_nested_values():
    options = validate_interactive_options(
        {
            "request_id": 4,
            "ranges": {"y_min": "200", "y_max": 1000},
            "sigma": "2.5",
            "design": {"lbl_size": 20, "ell_color": "#112233", "tick_label_size": 15},
            "filter_state": {"a": "ON"},
            "layer_order": ["a"],
            "locked_layers": ["a"],
            "label_offsets": {"a": [12.5, -4]},
            "draw_objects": [{
                "type": "line",
                "points": [[500, 300], [1500, 700]],
                "line_color": "#2563eb",
                "line_width": 3,
                "arrow_mode": "end",
                "arrow_head": "open",
                "semi": True,
            }, {
                "type": "legend",
                "name": "파일 안내",
                "entries": [{"series_id": 0, "text": "매우 긴 파일 이름도 범례 안에서 유지됩니다"}],
                "show_border": True,
                "border_style": "--",
                "border_color": "#3f4650",
                "show_fill": True,
                "fill_opacity": 0.8,
                "font_family": "Noto Serif KR",
                "font_weight": "bold",
                "font_italic": True,
                "semi": True,
            }],
        }
    )

    assert options["ranges"] == {"y_min": "200", "y_max": "1000"}
    assert options["sigma"] == "2.5"
    assert options["design"]["tick_label_size"] == 15
    assert options["label_offsets"] == {"a": (12.5, -4.0)}
    assert options["draw_objects"][0]["arrow_mode"] == "end"
    assert options["draw_objects"][0]["line_width"] == 3.0
    assert options["draw_objects"][1]["border_style"] == "--"
    assert options["draw_objects"][1]["fill_opacity"] == 0.8
    assert all(item["semi"] for item in options["draw_objects"])

    with pytest.raises(InteractiveOptionsError, match="less than"):
        validate_interactive_options(
            {"ranges": {"x_min": 3500, "x_max": 500}}
        )
    with pytest.raises(InteractiveOptionsError, match="visibility"):
        validate_interactive_options({"filter_state": {"a": "MAYBE"}})
    with pytest.raises(InteractiveOptionsError, match="hex color"):
        validate_interactive_options({"design": {"lbl_color": "red"}})


def test_plot_session_roundtrip_and_index_removal():
    state = PlotSessionState()
    state.apply(
        validate_interactive_options(
            {
                "ranges": {
                    "y_min": 200,
                    "y_max": 1000,
                    "x_min": 500,
                    "x_max": 3500,
                },
                "design": {"lbl_size": 24},
                "filter_state": {"a": "SEMI"},
                "layer_overrides": {"a": {"lbl_color": "#112233"}},
                "layer_order": ["a", "i"],
                "locked_layers": ["a"],
                "label_offsets": {"a": [12, -4]},
                "draw_objects": [
                    {"type": "line", "points": [[500, 300], [1500, 700]], "arrow_mode": "all"},
                    {"type": "legend", "entries": [{"series_id": 0, "text": "파일"}], "show_fill": True},
                ],
            }
        ),
        1,
    )
    restored = PlotSessionState.from_project_dict(
        json.loads(json.dumps(state.to_project_dict()))
    )

    assert restored.design_settings["lbl_size"] == 24
    assert restored.vowel_filter_state_by_file[1]["a"] == "SEMI"
    assert restored.layer_order_by_file[1] == ["a", "i"]
    assert restored.label_offsets_by_file[1]["a"] == (12.0, -4.0)
    assert restored.draw_objects_by_file[1][0]["arrow_mode"] == "all"
    assert restored.draw_objects_by_file[1][1]["type"] == "legend"

    restored.remove_file(0)
    assert restored.vowel_filter_state_by_file[0]["a"] == "SEMI"
    assert restored.current_idx == 0


def test_latest_render_scheduler_discards_stale_and_replaces_pending_work():
    started = threading.Event()
    release = threading.Event()
    results: list[str] = []

    def render(value: str) -> str:
        if value == "first":
            started.set()
            release.wait(2)
        return value

    scheduler = LatestRenderScheduler(
        render,
        lambda _job, value: results.append(value),
        lambda _job, error: pytest.fail(str(error)),
    )
    try:
        scheduler.submit(RenderJob("1", "first"))
        assert started.wait(1)
        scheduler.submit(RenderJob("2", "second"))
        scheduler.submit(RenderJob("3", "third"))
        release.set()
        deadline = time.monotonic() + 2
        while not results and time.monotonic() < deadline:
            time.sleep(0.01)
        assert results == ["third"]
    finally:
        release.set()
        scheduler.close()


class _BlockingRenderService:
    def __init__(self):
        self.events = ApplicationEventBus()
        self.started = threading.Event()
        self.release = threading.Event()

    def prepare_interactive_preview(self, options):
        return {"request_id": options.get("request_id")}

    def prepare_interactive_navigation(self, index, options):
        return {
            "state": {"current_index": index},
            "prepared": {"request_id": options.get("request_id")},
        }

    def render_prepared_interactive_preview(self, prepared):
        self.started.set()
        self.release.wait(2)
        return {"empty": True, **prepared}

    def publish_interactive_render_result(self, _result):
        return None

    def publish_preview_error(self, *_args, **_kwargs):
        return None


def test_host_accepts_render_without_blocking_followup_health():
    service = _BlockingRenderService()
    host = SidecarHost(service=service)
    try:
        response = json.loads(
            host.handle_message(
                '{"v":1,"id":"r","method":"render_interactive_preview",'
                '"params":{"options":{"request_id":1}}}'
            )
        )
        assert response["result"]["accepted"] is True
        assert service.started.wait(1)

        health = json.loads(
            host.handle_message('{"v":1,"id":"h","method":"health","params":{}}')
        )
        assert health["result"]["ok"] is True
    finally:
        service.release.set()
        host.close()


def test_host_accepts_navigate_interactive_preview():
    service = _BlockingRenderService()
    host = SidecarHost(service=service)
    try:
        response = json.loads(
            host.handle_message(
                '{"v":1,"id":"n","method":"navigate_interactive_preview",'
                '"params":{"index":2,"options":{"request_id":5}}}'
            )
        )
        assert response["result"]["state"]["current_index"] == 2
        assert response["result"]["render"]["accepted"] is True
        assert response["result"]["render"]["request_id"] == 5
    finally:
        service.release.set()
        host.close()
