import json
import base64

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


def test_preview_event_is_json_safe():
    controller, _view = _headless_controller()
    service = ApplicationService(controller)
    previews = []
    service.events.subscribe("preview_ready", previews.append)

    service.publish_preview(b"png-data", "speaker\nF1 / F2")

    payload = previews[-1].payload
    assert base64.b64decode(payload["png_base64"]) == b"png-data"
    assert payload["info"] == "speaker\nF1 / F2"
    json.dumps(previews[-1].to_dict(), ensure_ascii=False)


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
