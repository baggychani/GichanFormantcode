import zipfile

import pandas as pd

from core.project_service import load_project, save_project
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


class _FakeEdit:
    def __init__(self, value):
        self._value = value

    def text(self):
        return self._value


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
