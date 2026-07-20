import json
from pathlib import Path

import pandas as pd
import pytest

from core.application_events import ApplicationError
from core.application_state import AnalysisSettings
from core.application_service import ApplicationService
from core.controller import MainController
from core.project_service import collect_project_document
from core.runtime_port import HeadlessRuntime
from core.view_port import NullMainView


def _headless_controller(settings=None):
    view = NullMainView(settings)
    controller = MainController(
        view_factory=lambda *_args: view,
        runtime=HeadlessRuntime(),
        render_initial_preview=False,
    )
    return controller, view


def test_analysis_settings_roundtrip_and_plot_params():
    settings = AnalysisSettings.from_mapping(
        {
            "type": "f1_f3",
            "f1_scale": "bark",
            "f2_scale": "log",
            "origin": "bottom_left",
            "use_bark_units": True,
            "outlier_mode": "tukey_iqr",
            "outlier_scope": "combined",
            "normalization": "Lobanov",
        }
    )

    assert AnalysisSettings.from_mapping(settings.to_dict()) == settings
    params = settings.to_plot_params()
    assert params["type"] == "f1_f3"
    assert params["f1_unit"] == "Bark"
    assert params["f2_unit"] == "Hz"


def test_default_axis_scales_keep_bark_scale_but_display_hz():
    settings = AnalysisSettings.from_mapping({})

    assert settings.f1_scale == "linear"
    assert settings.f2_scale == "bark"
    assert settings.use_bark_units is False
    params = settings.to_plot_params()
    assert params["f1_unit"] == "Hz"
    assert params["f2_unit"] == "Hz"


def test_controller_initializes_without_native_window():
    controller, view = _headless_controller()

    assert controller.ui is None
    assert controller.view is view
    controller.open_single_plot()
    assert view.warnings == [("데이터 없음", "분석할 데이터를 먼저 로드해 주세요.")]


def test_project_collection_reads_state_from_view_port():
    settings = AnalysisSettings(
        plot_type="f1_f2",
        f1_scale="linear",
        f2_scale="log",
        origin="bottom_left",
        outlier_mode="mahalanobis_2sigma",
        outlier_scope="individual",
        normalization="Lobanov",
    )
    controller, _view = _headless_controller(settings)
    df = pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["a"]})
    controller.filepaths = ["C:/data/a.csv"]
    controller.plot_data_list = [
        {
            "name": "a.csv",
            "df": df.copy(),
            "df_original": df.copy(),
            "has_f3": False,
            "is_pre_lobanov": False,
        }
    ]

    document = collect_project_document(controller)

    assert document["analysis"]["origin"] == "bottom_left"
    assert document["analysis"]["outlier_mode"] == "mahalanobis_2sigma"
    assert document["analysis"]["outlier_scope"] == "individual"
    assert document["analysis"]["normalization"] == "Lobanov"


def test_application_service_snapshot_is_json_safe_and_accepts_partial_settings():
    controller, view = _headless_controller(
        AnalysisSettings(f2_scale="log", origin="bottom_left")
    )
    service = ApplicationService(controller)
    events = []
    service.events.subscribe("state_changed", events.append)

    state = service.set_analysis_settings({"normalization": "Lobanov"})

    assert state["analysis"]["f2_scale"] == "log"
    assert state["analysis"]["origin"] == "bottom_left"
    assert state["analysis"]["normalization"] == "Lobanov"
    assert view.settings == controller.get_analysis_settings()
    assert json.loads(json.dumps(state, ensure_ascii=False)) == state
    assert events[-1].payload["reason"] == "analysis_settings_changed"


def test_application_service_load_files_updates_headless_view(monkeypatch, tmp_path):
    controller, view = _headless_controller()
    service = ApplicationService(controller)
    progress = []
    service.events.subscribe("operation_progress", progress.append)
    source = tmp_path / "speaker.csv"
    df = pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["a"]})

    monkeypatch.setattr(
        "core.controller.load_plot_item_from_file",
        lambda _path, **_kwargs: {
            "success": True,
            "name": source.name,
            "item": {
                "name": source.name,
                "df": df.copy(),
                "df_original": df.copy(),
                "has_f3": False,
                "is_pre_lobanov": False,
            },
            "errors": [],
            "row_dropped": [],
        },
    )

    response = service.load_files([str(source)])

    assert response["load_result"]["success_count"] == 1
    assert response["state"]["sources"][0]["name"] == source.name
    assert response["state"]["capabilities"]["can_plot"] is True
    assert view.file_count == 1
    assert view.has_f3 is False
    assert [event.payload["status"] for event in progress] == [
        "started",
        "completed",
    ]
    json.dumps(response, ensure_ascii=False)


def test_application_service_exports_combined_txt_from_headless_state(tmp_path):
    controller, _view = _headless_controller()
    service = ApplicationService(controller)
    controller.plot_data_list = [
        {
            "name": "Combined (2)",
            "is_combined": True,
            "has_f3": False,
            "df": pd.DataFrame(
                {"Label": ["a"], "F1": [500.0], "F2": [1500.0]}
            ),
        }
    ]

    result = service.export_combined_txt(str(tmp_path / "combined"))

    assert result["ok"] is True
    output = tmp_path / "combined.txt"
    assert output.exists()
    assert "a" in output.read_text(encoding="utf-8")


def test_application_service_rejects_unsupported_data_files_before_loading(monkeypatch, tmp_path):
    controller, view = _headless_controller()
    service = ApplicationService(controller)
    source = tmp_path / "not-data.pdf"
    source.write_bytes(b"%PDF-1.7")

    def fail_load(_paths):
        raise AssertionError("unsupported files should not reach the data loader")

    monkeypatch.setattr(controller, "load_files", fail_load)

    response = service.load_files([str(source)])

    assert response["load_result"]["success_count"] == 0
    assert response["load_result"]["failed"][0]["name"] == source.name
    assert response["state"]["capabilities"]["can_plot"] is False
    assert view.file_count == 0


def test_preview_event_is_json_safe():
    controller, _view = _headless_controller()
    service = ApplicationService(controller)
    previews = []
    service.events.subscribe("preview_ready", previews.append)

    service.publish_preview(b"png-data", "speaker\nF1 / F2")

    payload = previews[-1].payload
    assert Path(payload["png_path"]).read_bytes() == b"png-data"
    assert payload["info"] == "speaker\nF1 / F2"
    json.dumps(previews[-1].to_dict(), ensure_ascii=False)
    service.close()


def test_set_analysis_settings_derived_plot_clears_normalization():
    controller, _view = _headless_controller()
    service = ApplicationService(controller)
    service.set_analysis_settings({"normalization": "Lobanov", "type": "f1_f2"})
    state = service.set_analysis_settings({"type": "f1_f2_minus_f1"})
    assert state["analysis"]["type"] == "f1_f2_minus_f1"
    assert state["analysis"]["normalization"] is None
    service.close()


def test_set_analysis_settings_bark_units_forces_both_scales():
    controller, _view = _headless_controller()
    service = ApplicationService(controller)
    service.set_analysis_settings(
        {"f1_scale": "linear", "f2_scale": "log", "use_bark_units": False}
    )
    state = service.set_analysis_settings({"use_bark_units": True})
    analysis = state["analysis"]
    assert analysis["use_bark_units"] is True
    assert analysis["f1_scale"] == "bark"
    assert analysis["f2_scale"] == "bark"
    service.close()


def test_interactive_preview_rejects_hz_ranges_under_lobanov():
    controller, _view = _headless_controller()
    service = ApplicationService(controller)
    df = pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["a"]})
    controller.filepaths = ["C:/data/a.csv"]
    controller.plot_data_list = [
        {
            "name": "a.csv",
            "df": df,
            "df_original": df.copy(),
            "has_f3": False,
            "is_pre_lobanov": False,
        }
    ]
    service.set_analysis_settings({"normalization": "Lobanov"})
    session = service._plot_session()
    session.ranges = {
        "y_min": "200",
        "y_max": "1000",
        "x_min": "500",
        "x_max": "3500",
    }

    prepared = service.prepare_interactive_preview(
        {
            "request_id": 9,
            "ranges": {
                "y_min": "200",
                "y_max": "1000",
                "x_min": "500",
                "x_max": "3500",
            },
        }
    )

    assert {key: float(value) for key, value in prepared["ranges"].items()} == {
        "y_min": -2.0,
        "y_max": 2.0,
        "x_min": -2.0,
        "x_max": 2.0,
    }
    assert session.ranges == {}
    service.close()


def test_interactive_preview_preparation_sends_only_render_data():
    controller, _view = _headless_controller()
    service = ApplicationService(controller)
    df = pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["a"]})
    controller.filepaths = ["C:/data/a.csv"]
    controller.plot_data_list = [
        {
            "name": "a.csv",
            "df": df,
            "df_original": df.copy(),
            "has_f3": False,
            "is_pre_lobanov": False,
        }
    ]

    prepared = service.prepare_interactive_preview({"request_id": 7})

    current_data = prepared["current_data"]
    assert current_data["df"] is df
    assert "df_original" not in current_data
    assert current_data["name"] == "a.csv"
    assert prepared["request_id"] == 7
    service.close()


@pytest.mark.parametrize(
    ("method_name", "service_call", "error_code"),
    [
        ("save_project_document", "save_project", "project_save_failed"),
        ("load_project_document", "load_project", "project_load_failed"),
    ],
)
def test_application_service_returns_structured_project_errors(
    monkeypatch, method_name, service_call, error_code
):
    controller, _view = _headless_controller()
    service = ApplicationService(controller)
    failures = []
    service.events.subscribe("operation_failed", failures.append)

    def fail(_path):
        raise OSError("disk unavailable")

    monkeypatch.setattr(controller, method_name, fail)

    with pytest.raises(ApplicationError) as exc_info:
        getattr(service, service_call)("C:/project.gfproj")

    assert exc_info.value.code == error_code
    assert exc_info.value.details["path"] == "C:/project.gfproj"
    assert failures[-1].payload["code"] == error_code


def test_file_dialog_callback_routes_through_application_service(monkeypatch, tmp_path):
    controller, view = _headless_controller()
    service = controller.application_service
    progress = []
    service.events.subscribe("operation_progress", progress.append)
    source = tmp_path / "speaker.csv"
    df = pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["a"]})

    monkeypatch.setattr(
        "core.controller.load_plot_item_from_file",
        lambda _path, **_kwargs: {
            "success": True,
            "name": source.name,
            "item": {
                "name": source.name,
                "df": df.copy(),
                "df_original": df.copy(),
                "has_f3": False,
                "is_pre_lobanov": False,
            },
            "errors": [],
            "row_dropped": [],
        },
    )

    captured = {}

    def fake_request_file_open(callback):
        captured["callback"] = callback

    view.request_file_open = fake_request_file_open
    controller.open_file_dialog()
    captured["callback"]([str(source)])

    assert [event.payload["status"] for event in progress] == ["started", "completed"]
    assert view.file_count == 1


def test_project_ui_callbacks_emit_service_events(monkeypatch, tmp_path):
    controller, view = _headless_controller()
    service = controller.application_service
    saved = []
    loaded = []
    service.events.subscribe("project_saved", saved.append)
    service.events.subscribe("project_loaded", loaded.append)

    monkeypatch.setattr(controller, "save_project_document", lambda _path, _popup=None: None)
    monkeypatch.setattr(
        controller,
        "load_project_document",
        lambda _path: {"ok": True},
    )

    path = str(tmp_path / "demo.gfproj")
    controller.save_project_file(path)
    controller.load_project_file(path)

    assert saved[-1].payload["path"] == path
    assert loaded[-1].payload["path"] == path
    assert view.criticals == []


def test_remove_file_invalid_index_does_not_emit_success():
    controller, _view = _headless_controller()
    service = ApplicationService(controller)
    changed = []
    failed = []
    service.events.subscribe("files_changed", changed.append)
    service.events.subscribe("operation_failed", failed.append)

    with pytest.raises(ApplicationError) as exc_info:
        service.remove_file(0)

    assert exc_info.value.code == "file_remove_failed"
    assert changed == []
    assert failed[-1].payload["code"] == "file_remove_failed"
