import os
import sys

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.windows.popup_plot import PlotPopup


class _ControllerStub:
    def __init__(self, current_idx=0):
        self.current_idx = current_idx

    def get_current_index(self):
        return self.current_idx


class _LayerDockStub:
    def __init__(self):
        self.rebuilt = False

    def _rebuild_effects(self):
        self.rebuilt = True


class _PopupStub:
    def __init__(self):
        self.controller = _ControllerStub(current_idx=1)
        self.current_idx = 1
        self.layer_design_overrides = {}
        self.layer_design_overrides_by_file = {}
        self.vowel_filter_state = {}
        self.vowel_filter_state_by_file = {}
        self._layer_dock_content = _LayerDockStub()


def test_save_layer_overrides_copies_nested_values():
    popup = _PopupStub()
    popup.layer_design_overrides = {"a": {"lbl_color": "#111111", "lbl_size": 20}}

    PlotPopup._save_layer_overrides_for_current_file(popup)
    saved = popup.layer_design_overrides_by_file[1]
    assert saved["a"]["lbl_color"] == "#111111"

    # 원본 변경이 저장본에 전파되지 않아야 한다.
    popup.layer_design_overrides["a"]["lbl_color"] = "#222222"
    assert popup.layer_design_overrides_by_file[1]["a"]["lbl_color"] == "#111111"


def test_load_layer_overrides_restores_and_rebuilds_effects():
    popup = _PopupStub()
    popup.layer_design_overrides_by_file[1] = {"i": {"lbl_color": "#1976D2"}}

    PlotPopup._load_layer_overrides_for_file(popup, 1)
    assert popup.layer_design_overrides == {"i": {"lbl_color": "#1976D2"}}
    assert popup._layer_dock_content.rebuilt is True

    # 로드된 상태 변경이 저장본을 오염시키지 않아야 한다(deep copy)
    popup.layer_design_overrides["i"]["lbl_color"] = "#E64A19"
    assert popup.layer_design_overrides_by_file[1]["i"]["lbl_color"] == "#1976D2"


def test_save_and_load_filter_state_per_file():
    popup = _PopupStub()
    popup.vowel_filter_state = {"a": "SEMI", "i": "OFF"}

    PlotPopup._save_filter_state_for_current_file(popup)
    assert popup.vowel_filter_state_by_file[1] == {"a": "SEMI", "i": "OFF"}

    popup.vowel_filter_state = {"a": "ON"}
    PlotPopup._load_filter_state_for_file(popup, 1)
    assert popup.vowel_filter_state == {"a": "SEMI", "i": "OFF"}


def test_load_filter_state_defaults_to_empty_when_missing():
    popup = _PopupStub()
    popup.vowel_filter_state = {"a": "OFF"}

    PlotPopup._load_filter_state_for_file(popup, 999)
    assert popup.vowel_filter_state == {}
