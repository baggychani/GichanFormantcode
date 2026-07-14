import zipfile

import pandas as pd
import pytest

from core.controller import MainController
from core.application_state import AnalysisSettings
from core.compare_series import CompareSession
from core.project_service import load_project, save_project
from core.interactive_plot_state import PlotSessionState
from draw.draw_common import LineObject


class _FakeUI:
    def get_plot_type(self):
        return "f1_f2"

    def get_f1_scale(self):
        return "linear"

    def get_f2_scale(self):
        return "linear"

    def get_use_bark_units(self):
        return False

    def get_origin(self):
        return "top_right"

    def get_normalization(self):
        return None

    def get_outlier_mode(self):
        return "mahalanobis_2sigma"

    def get_outlier_scope(self):
        return "combined"


class _FakeController:
    def __init__(self):
        df = pd.DataFrame(
            {
                "F1": [500.0, 520.0],
                "F2": [1500.0, 1520.0],
                "Label": ["a", "a"],
            }
        )
        self.filepaths = ["C:/data/a.txt"]
        self.plot_data_list = [
            {
                "name": "a.txt",
                "df": df.copy(),
                "df_original": df.copy(),
                "has_f3": False,
                "is_pre_lobanov": False,
            }
        ]
        self.open_popups = []
        self.current_idx = 0
        self.ui = _FakeUI()
        self.custom_label_offsets = {(0, "f1_f2"): {"a": (1.0, 2.0)}}

    def _get_main_ui_plot_params(self):
        return {
            "type": self.ui.get_plot_type(),
            "f1_scale": self.ui.get_f1_scale(),
            "f2_scale": self.ui.get_f2_scale(),
            "f1_unit": "Hz",
            "f2_unit": "Hz",
            "origin": self.ui.get_origin(),
            "use_bark_units": self.ui.get_use_bark_units(),
            "sigma": 2.0,
            "normalization": self.ui.get_normalization(),
        }

    def get_analysis_settings(self):
        return AnalysisSettings(
            plot_type=self.ui.get_plot_type(),
            f1_scale=self.ui.get_f1_scale(),
            f2_scale=self.ui.get_f2_scale(),
            origin=self.ui.get_origin(),
            use_bark_units=self.ui.get_use_bark_units(),
            outlier_mode=self.ui.get_outlier_mode(),
            outlier_scope=self.ui.get_outlier_scope(),
            normalization=self.ui.get_normalization(),
        )


class _FakeEdit:
    def __init__(self, value):
        self._value = value

    def text(self):
        return self._value

    def setText(self, value):
        self._value = str(value)


class _FakePopup:
    current_idx = 0
    fixed_plot_params = {"type": "f1_f2", "origin": "top_right"}
    design_settings = {"common": {"show_raw": True}}
    vowel_filter_state_by_file = {0: {"a": "ON"}}
    layer_design_overrides_by_file = {0: {"a": {"lbl_color": "#111111"}}}
    layer_locked_vowels_by_file = {0: {"a"}}
    layer_order = ["a"]
    _draw_objects_by_file = {0: [LineObject(points=[(1.0, 2.0), (3.0, 4.0)])]}

    range_widgets = {
        "y_min": _FakeEdit("200"),
        "y_max": _FakeEdit("900"),
        "x_min": _FakeEdit("500"),
        "x_max": _FakeEdit("3000"),
    }

    def _save_layer_overrides_for_current_file(self):
        pass

    def _save_filter_state_for_current_file(self):
        pass

    def get_sigma(self):
        return "2.0"


class _FakeComparePopup:
    compare_session = CompareSession.from_data_indices(-1, -2)
    compare_source_groups = ((0,), (1,))
    normalization = None
    fixed_plot_params = {"type": "f1_f2", "origin": "top_right"}
    design_settings = {
        "common": {"show_raw": False},
        "blue": {"ell_color": "#123456"},
        "red": {"ell_color": "#654321"},
    }
    vowel_filter_states = {0: {"a": "OFF"}, 1: {"i": "SEMI"}}
    layer_design_overrides_by_series = {
        0: {"a": {"lbl_color": "#111111"}},
        1: {"i": {"lbl_color": "#222222"}},
    }
    layer_locked_vowels_by_series = {0: {"a"}, 1: {"i"}}
    layer_order_by_series = {0: ["a"], 1: ["i"]}
    _draw_objects_shared = [LineObject(points=[(10.0, 20.0), (30.0, 40.0)])]
    _plot_key_compare = (-1, -2, "f1_f2")
    range_widgets = {
        "y_min": _FakeEdit("250"),
        "y_max": _FakeEdit("850"),
        "x_min": _FakeEdit("700"),
        "x_max": _FakeEdit("2800"),
    }

    def get_sigma(self):
        return "2.5"


def test_project_save_load_roundtrip(tmp_path):
    path = tmp_path / "sample.gfproj"
    save_project(str(path), _FakeController(), _FakePopup())

    assert path.exists()
    with zipfile.ZipFile(path, "r") as zf:
        assert "manifest.json" in zf.namelist()
        assert "data/0.json" in zf.namelist()

    project = load_project(str(path))
    assert project["schema_version"] == 1
    assert project["analysis"]["outlier_mode"] == "mahalanobis_2sigma"
    assert project["snapshots"]["0"].iloc[0]["Label"] == "a"
    assert project["label_offsets"][(0, "f1_f2")]["a"] == [1.0, 2.0]
    assert project["single_plot"]["vowel_filter_state_by_file"][0]["a"] == "ON"
    assert project["single_plot"]["layer_locked_vowels_by_file"][0] == ["a"]
    assert project["single_plot"]["draw_objects_by_file"][0][0].type == "line"


def test_project_save_without_popup_persists_canonical_plot_session(tmp_path):
    controller = _FakeController()
    controller.plot_session_state = PlotSessionState()
    controller.plot_session_state.apply(
        {
            "sigma": "3",
            "design": {"lbl_size": 22},
            "filter_state": {"a": "OFF"},
            "layer_order": ["a"],
            "locked_layers": ["a"],
        },
        0,
    )
    path = tmp_path / "react-session.gfproj"

    save_project(str(path), controller)
    project = load_project(str(path))
    restored = PlotSessionState.from_project_dict(project["single_plot"])

    assert restored.sigma == "3"
    assert restored.design_settings["lbl_size"] == 22
    assert restored.vowel_filter_state_by_file[0]["a"] == "OFF"
    assert restored.layer_locked_vowels_by_file[0] == ["a"]


def test_compare_session_save_load_roundtrip(tmp_path):
    controller = _FakeController()
    second = dict(controller.plot_data_list[0])
    second["name"] = "b.txt"
    second["df"] = second["df"].copy()
    second["df_original"] = second["df_original"].copy()
    controller.plot_data_list.append(second)
    controller.filepaths.append("C:/data/b.txt")
    popup = _FakeComparePopup()
    controller.open_popups = [popup]
    controller.custom_label_offsets[(-1, -2, "f1_f2", "blue")] = {"a": (3.0, 4.0)}

    path = tmp_path / "compare.gfproj"
    save_project(str(path), controller, popup)
    project = load_project(str(path))

    assert project["single_plot"] is None
    assert len(project["compare_sessions"]) == 1
    state = project["compare_sessions"][0]
    assert state["source_groups"] == [[0], [1]]
    assert state["ranges"]["x_max"] == "2800"
    assert state["sigma"] == "2.5"
    assert state["vowel_filter_states"][0]["a"] == "OFF"
    assert state["layer_locked_vowels_by_series"][1] == ["i"]
    assert state["label_offsets_by_series"][0]["a"] == [3.0, 4.0]
    assert state["draw_objects"][0].type == "line"


def test_project_save_failure_preserves_existing_file(tmp_path, monkeypatch):
    path = tmp_path / "existing.gfproj"
    original = b"existing project remains intact"
    path.write_bytes(original)

    original_writestr = zipfile.ZipFile.writestr
    call_count = 0

    def fail_after_manifest(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise OSError("simulated disk failure")
        return original_writestr(self, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "writestr", fail_after_manifest)

    with pytest.raises(OSError, match="simulated disk failure"):
        save_project(str(path), _FakeController(), _FakePopup())

    assert path.read_bytes() == original
    assert not list(tmp_path.glob(".existing.gfproj.*.tmp"))


def test_project_source_prefers_embedded_snapshot(tmp_path, monkeypatch):
    original_path = tmp_path / "source.txt"
    original_path.write_text("a valid but changed source", encoding="utf-8")
    snapshot = pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["snapshot"]})
    controller = MainController.__new__(MainController)

    def unexpected_file_load(_path):
        raise AssertionError("existing source must not override the snapshot")

    monkeypatch.setattr(
        "core.controller.load_plot_item_from_file", unexpected_file_load
    )
    path, item = controller._load_project_source_item(
        {
            "id": "0",
            "path": str(original_path),
            "name": "saved-name.txt",
            "has_f3": False,
            "is_pre_lobanov": False,
        },
        {"0": snapshot},
    )

    assert path == str(original_path)
    assert item["name"] == "saved-name.txt"
    assert item["df"].iloc[0]["Label"] == "snapshot"


def test_failed_project_preparation_keeps_current_session(monkeypatch):
    controller = MainController.__new__(MainController)
    old_paths = ["current.txt"]
    old_items = [{"name": "current.txt", "df": pd.DataFrame({"F1": [1]})}]
    old_offsets = {(0, "f1_f2"): {"a": (1, 2)}}
    old_processor = object()
    controller.filepaths = old_paths
    controller.plot_data_list = old_items
    controller.current_idx = 0
    controller.custom_label_offsets = old_offsets
    controller.data_processor = old_processor

    def fail_source(*_args):
        raise ValueError("broken source")

    monkeypatch.setattr(controller, "_load_project_source_item", fail_source)

    with pytest.raises(ValueError, match="broken source"):
        controller._apply_loaded_project(
            {"sources": [{"id": "0"}], "snapshots": {}, "analysis": {}}
        )

    assert controller.filepaths is old_paths
    assert controller.plot_data_list is old_items
    assert controller.custom_label_offsets is old_offsets
    assert controller.data_processor is old_processor


def test_compare_session_restore_rebinds_state_and_label_offsets(monkeypatch):
    class FakeDesignTab:
        def __init__(self):
            self.applied = None

        def apply_settings(self, settings, *, emit):
            assert emit is False
            self.applied = settings

        def get_current_settings(self):
            return self.applied

    class FakeCombo:
        def __init__(self):
            self.value = ""

        def setCurrentText(self, value):
            self.value = str(value)

    class FakeDock:
        def __init__(self):
            self.refreshed = False

        def refresh_design_ui(self):
            self.refreshed = True

    dock = FakeDock()
    popup = type("Popup", (), {})()
    popup.compare_session = CompareSession.from_data_indices(-3, -4)
    popup.fixed_plot_params = {"type": "f1_f2"}
    popup.design_tab = FakeDesignTab()
    popup.range_widgets = {
        "y_min": _FakeEdit("0"),
        "y_max": _FakeEdit("0"),
        "x_min": _FakeEdit("0"),
        "x_max": _FakeEdit("0"),
    }
    popup.cb_sigma = FakeCombo()
    popup._iter_compare_layer_docks = lambda: [dock]
    popup._refresh_compare_draw_layer_lists = lambda: None
    popup.request_plot_refresh = lambda debounce_ms: setattr(
        popup, "refresh_delay", debounce_ms
    )

    controller = MainController.__new__(MainController)
    controller.ui = object()
    controller.custom_label_offsets = {}
    opened = []

    def open_groups(groups, normalization=None, parent_window=None):
        opened.append((groups, normalization, parent_window))
        return popup

    monkeypatch.setattr(controller, "open_compare_plot_for_source_groups", open_groups)
    controller._restore_compare_sessions_from_project(
        [
            {
                "source_groups": [[0], [1]],
                "normalization": None,
                "fixed_plot_params": {"type": "f1_f2", "origin": "top_right"},
                "design_settings": {"common": {"show_raw": False}},
                "vowel_filter_states": {0: {"a": "OFF"}},
                "layer_design_overrides_by_series": {0: {"a": {}}},
                "layer_locked_vowels_by_series": {0: ["a"]},
                "layer_order_by_series": {0: ["a"]},
                "draw_objects": [LineObject(points=[(0, 0), (1, 1)])],
                "ranges": {
                    "y_min": "250",
                    "y_max": "850",
                    "x_min": "700",
                    "x_max": "2800",
                },
                "sigma": "2.5",
                "label_offsets_by_series": {0: {"a": [3.0, 4.0]}},
            }
        ]
    )

    assert opened == [([[0], [1]], None, controller.ui)]
    assert popup.range_widgets["x_min"].text() == "700"
    assert popup.cb_sigma.value == "2.5"
    assert popup.vowel_filter_states[0]["a"] == "OFF"
    assert popup.layer_locked_vowels_by_series[0] == {"a"}
    assert popup.design_settings["common"]["show_raw"] is False
    assert popup.refresh_delay == 0
    assert dock.refreshed is True
    assert controller.custom_label_offsets[(-3, -4, "f1_f2", "blue")]["a"] == [
        3.0,
        4.0,
    ]
