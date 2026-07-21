from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from core.application_service import ApplicationService
from core.application_state import AnalysisSettings
from core.controller import MainController
from core.ipc.protocol import EVENTS, protocol_manifest
from core.runtime_port import HeadlessRuntime
from core.view_port import NullMainView
from sidecar.host import SidecarHost
from scripts.generate_ipc_contract import render_command_specs, render_schema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "desktop" / "ipc" / "schema.json"
PROTOCOL_TS = ROOT / "desktop" / "ipc" / "protocol.ts"
COMMAND_SPECS_TS = ROOT / "desktop" / "ipc" / "command-specs.ts"


def _headless_service(settings: AnalysisSettings | None = None) -> ApplicationService:
    view = NullMainView(settings)
    controller = MainController(
        view_factory=lambda *_args: view,
        runtime=HeadlessRuntime(),
        render_initial_preview=False,
    )
    return controller.application_service


def test_schema_json_matches_python_manifest():
    on_disk = SCHEMA_PATH.read_text(encoding="utf-8")
    assert on_disk == render_schema()
    assert json.loads(on_disk) == protocol_manifest()


def test_typescript_contract_is_generated_from_python_specs():
    assert COMMAND_SPECS_TS.read_text(encoding="utf-8") == render_command_specs()
    text = PROTOCOL_TS.read_text(encoding="utf-8")
    for name in EVENTS:
        assert f'"{name}"' in text, f"missing event in protocol.ts: {name}"


def test_host_and_direct_service_agree_on_settings_and_snapshot():
    service = _headless_service(AnalysisSettings(f2_scale="log"))
    host = SidecarHost(service=service)

    direct = service.set_analysis_settings({"normalization": "Lobanov"})
    host_response = json.loads(
        host.handle_message(
            json.dumps(
                {
                    "v": 1,
                    "id": "a",
                    "method": "set_analysis_settings",
                    "params": {"settings": {"origin": "bottom_left"}},
                }
            )
        )
    )

    assert host_response["result"]["analysis"]["normalization"] == "Lobanov"
    assert host_response["result"]["analysis"]["origin"] == "bottom_left"
    assert (
        host_response["result"]["analysis"]["f2_scale"]
        == direct["analysis"]["f2_scale"]
    )

    snap = json.loads(
        host.handle_message('{"v":1,"id":"b","method":"snapshot","params":{}}')
    )
    assert snap["result"] == service.snapshot()
    assert {"can_plot", "can_compare", "can_save_project"} <= set(
        snap["result"]["capabilities"]
    )
    host.close()


def test_host_load_files_matches_service_capabilities(monkeypatch):
    csv_path = "C:/data/a.csv"
    df = pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["a"]})
    service = _headless_service()

    def fake_file_loader(_path, **_kwargs):
        return {
            "success": True,
            "name": "a.csv",
            "item": {
                "name": "a.csv",
                "df": df.copy(),
                "df_original": df.copy(),
                "has_f3": False,
                "is_pre_lobanov": False,
            },
            "errors": [],
            "row_dropped": [],
        }

    monkeypatch.setattr(service.controller, "_load_file_item", fake_file_loader)
    host = SidecarHost(service=service)

    via_service = service.load_files([csv_path])
    service.reset()
    service.controller.filepaths = []
    service.controller.plot_data_list = []
    response = json.loads(
        host.handle_message(
            json.dumps(
                {
                    "v": 1,
                    "id": "load",
                    "method": "load_files",
                    "params": {"paths": [csv_path]},
                }
            )
        )
    )
    assert response["result"]["state"]["capabilities"]["can_plot"] is True
    assert (
        response["result"]["load_result"]["success_count"]
        == via_service["load_result"]["success_count"]
    )
    host.close()


def test_health_and_unknown_method():
    host = SidecarHost.create_headless()
    health = json.loads(
        host.handle_message('{"v":1,"id":"h","method":"health","params":{}}')
    )
    assert health["result"]["ok"] is True
    assert health["result"]["protocol_version"] == 1
    assert health["result"]["python_version"]
    assert health["result"]["python_executable"]
    assert health["result"]["working_directory"]
    err = json.loads(
        host.handle_message('{"v":1,"id":"x","method":"nope","params":{}}')
    )
    assert err["error"]["code"] == "unknown_method"
    host.close()


def test_get_vowel_analysis_core_omits_heavy_pairwise_work(monkeypatch):
    df = pd.DataFrame(
        {
            "F1": [500.0, 510.0, 700.0, 710.0],
            "F2": [1500.0, 1510.0, 1200.0, 1210.0],
            "Label": ["a", "a", "u", "u"],
        }
    )
    service = _headless_service()
    service.controller.plot_data_list = [
        {
            "name": "vowels.csv",
            "df": df,
            "df_original": df.copy(),
            "has_f3": False,
            "is_pre_lobanov": False,
        }
    ]
    service.controller.filepaths = ["vowels.csv"]

    calls = {"mahalanobis": 0, "pillai": 0}
    import core.application_service as application_service_module

    original_maha = application_service_module.calculate_pairwise_mahalanobis_distances
    original_pillai = application_service_module.calculate_pillai_score

    def counting_maha(*args, **kwargs):
        calls["mahalanobis"] += 1
        return original_maha(*args, **kwargs)

    def counting_pillai(*args, **kwargs):
        calls["pillai"] += 1
        return original_pillai(*args, **kwargs)

    monkeypatch.setattr(
        application_service_module,
        "calculate_pairwise_mahalanobis_distances",
        counting_maha,
    )
    monkeypatch.setattr(
        application_service_module,
        "calculate_pillai_score",
        counting_pillai,
    )

    host = SidecarHost(service=service)
    core_only = json.loads(
        host.handle_message(
            '{"v":1,"id":"core","method":"get_vowel_analysis",'
            '"params":{"index":0,"sections":["core"]}}'
        )
    )
    assert "error" not in core_only
    assert core_only["result"]["statistics"]
    assert core_only["result"]["pairwise_euclidean"]
    assert core_only["result"]["pairwise_mahalanobis"] == {}
    assert core_only["result"]["pillai_scores"] == {}
    assert calls == {"mahalanobis": 0, "pillai": 0}

    full = json.loads(
        host.handle_message(
            '{"v":1,"id":"full","method":"get_vowel_analysis",'
            '"params":{"index":0,"sections":["core","mahalanobis","pillai"]}}'
        )
    )
    assert "error" not in full
    assert full["result"]["pairwise_mahalanobis"]
    assert full["result"]["pillai_scores"]
    assert calls["mahalanobis"] == 1
    assert calls["pillai"] >= 1
    host.close()


def test_get_vowel_analysis_caches_identical_section_requests(monkeypatch):
    df = pd.DataFrame(
        {
            "F1": [500.0, 510.0, 700.0, 710.0],
            "F2": [1500.0, 1510.0, 1200.0, 1210.0],
            "Label": ["a", "a", "u", "u"],
        }
    )
    service = _headless_service()
    service.controller.plot_data_list = [
        {
            "name": "vowels.csv",
            "df": df,
            "df_original": df.copy(),
            "has_f3": False,
            "is_pre_lobanov": False,
        }
    ]
    analyze_calls = {"count": 0}
    import core.application_service as application_service_module

    original_analyze = application_service_module.analyze_vowels

    def counting_analyze(*args, **kwargs):
        analyze_calls["count"] += 1
        return original_analyze(*args, **kwargs)

    monkeypatch.setattr(application_service_module, "analyze_vowels", counting_analyze)
    first = service.get_vowel_analysis(0, sections=["core"])
    second = service.get_vowel_analysis(0, sections=["core"])
    assert first["statistics"] == second["statistics"]
    assert analyze_calls["count"] == 1
    service.set_analysis_settings({"normalization": "Lobanov"})
    service.get_vowel_analysis(0, sections=["core"])
    assert analyze_calls["count"] == 2
    service.close()
