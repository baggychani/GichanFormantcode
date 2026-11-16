"""Batch export must produce images without changing existing work."""

from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from core.application_service import ApplicationService
from core.controller import MainController
from core.data_loading_service import make_plot_item
from core.runtime_port import HeadlessRuntime
from core.view_port import NullMainView


@pytest.fixture
def service():
    controller = MainController(
        view_factory=lambda *_args: NullMainView(),
        runtime=HeadlessRuntime(),
        render_initial_preview=False,
    )
    controller.filepaths = ["a.txt", "b.txt"]
    controller.plot_data_list = [
        make_plot_item(
            name=name,
            df=pd.DataFrame({
                "F1": [400.0, 500.0, 600.0],
                "F2": [1400.0, 1500.0, 1600.0],
                "Label": ["a", "a", "a"],
            }),
        )
        for name in controller.filepaths
    ]
    result = ApplicationService(controller)
    result.update_interactive_session({
        "filter_state": {"a": "ON"},
        "draw_objects": [],
    })
    controller.set_current_index(1)
    result.update_interactive_session({
        "filter_state": {"a": "OFF"},
        "layer_overrides": {"a": {"lbl_color": "#112233"}},
        "locked_layers": ["a"],
        "draw_objects": [{
            "type": "text", "id": "b-note", "text": "Keep B",
            "x": 1500, "y": 500,
        }],
    })
    controller.set_current_index(0)
    try:
        yield result
    finally:
        result.close()


@pytest.mark.parametrize("apply_options", [True, False])
def test_batch_export_preserves_session_and_renders_requested_options(
    service, tmp_path, monkeypatch, apply_options,
):
    session = service.controller.plot_session_state
    before = deepcopy(session)
    prepared_images = []
    render = service._interactive_renderer.render_export

    def capture(prepared, extension):
        prepared_images.append(prepared)
        return render(prepared, extension)

    monkeypatch.setattr(service._interactive_renderer, "render_export", capture)
    result = service.export_interactive_batch(str(tmp_path), "png", {
        "filter_state": {"a": "SEMI"},
        "layer_overrides": {},
        "locked_layers": [],
        "draw_objects": [],
        "batch_options": {
            "apply_layer_visibility": apply_options,
            "apply_draw_annotations": apply_options,
        },
    })

    assert result["errors"] == []
    assert len(result["exported"]) == 2
    for path in result["exported"]:
        with Image.open(path) as image:
            assert image.format == "PNG"
            image.verify()
    assert all(
        image["filter_state"] == ({"a": "SEMI"} if apply_options else None)
        for image in prepared_images
    )
    assert service.controller.plot_session_state is session
    assert session == before
    assert service.controller.get_current_index() == 0


@pytest.mark.parametrize("failure", ["render", "write"])
def test_failed_batch_export_preserves_session(service, tmp_path, monkeypatch, failure):
    session = service.controller.plot_session_state
    before = deepcopy(session)

    def fail(*_args, **_kwargs):
        raise OSError("simulated export failure")

    if failure == "render":
        monkeypatch.setattr(service._interactive_renderer, "render_export", fail)
    else:
        monkeypatch.setattr(service._interactive_renderer, "render_export", lambda *_: b"png")
        monkeypatch.setattr("core.application_service._atomic_write_bytes", fail)

    result = service.export_interactive_batch(str(tmp_path), "png", {
        "filter_state": {"a": "ON"}, "draw_objects": [],
    })

    assert len(result["errors"]) == 2
    assert result["exported"] == []
    assert service.controller.plot_session_state is session
    assert session == before
    assert service.controller.get_current_index() == 0


def test_batch_export_preserves_existing_names_and_repeated_exports(
    service, tmp_path, monkeypatch,
):
    service.controller.plot_data_list[1]["name"] = "A.csv"
    existing = {"a.png": b"original", "A_2.PNG": b"another original"}
    for name, content in existing.items():
        (tmp_path / name).write_bytes(content)
    # A directory is a name collision too.
    (tmp_path / "a_3.png").mkdir()
    monkeypatch.setattr(service._interactive_renderer, "render_export", lambda *_: b"new")

    first = service.export_interactive_batch(str(tmp_path), "png", {})
    second = service.export_interactive_batch(str(tmp_path), "png", {})

    assert first["errors"] == second["errors"] == []
    assert [Path(path).name for path in first["exported"]] == ["a_4.png", "A_5.png"]
    assert [Path(path).name for path in second["exported"]] == ["a_6.png", "A_7.png"]
    for name, content in existing.items():
        assert (tmp_path / name).read_bytes() == content
    assert (tmp_path / "a_3.png").is_dir()
