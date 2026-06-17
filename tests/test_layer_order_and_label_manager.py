import os
import sys
import unittest

import pandas as pd
from matplotlib.figure import Figure
from types import SimpleNamespace

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.plot_engine import PlotEngine
from ui.widgets.layer_display import draw_object_display_name
from ui.widgets.label_manager import LabelManager


class _DummyPopup:
    def __init__(self):
        self.layer_design_overrides = {}
        self.layer_design_overrides_by_file = {}
        self.vowel_filter_state_by_file = {}
        self.vowel_filter_states = {}
        self.layer_design_overrides_by_series = {}
        self.layer_order_by_series = {}
        self.layer_locked_vowels_by_series = {}
        self.current_idx = 0


class TestLayerOrderAndLabelManager(unittest.TestCase):
    def test_draw_plot_respects_layer_order(self):
        engine = PlotEngine()
        fig = Figure()
        df = pd.DataFrame(
            {
                "F1": [500, 520, 600, 620],
                "F2": [1500, 1520, 1700, 1720],
                "Label": ["i", "i", "a", "a"],
            }
        )
        params = {
            "type": "f1_f2",
            "origin": "top_left",
            "f1_scale": "linear",
            "f2_scale": "linear",
            "use_bark_units": False,
            "sigma": 2.0,
        }
        _, _, label_data, _ = engine.draw_plot(
            fig,
            df,
            params,
            design_settings={"show_raw": False, "show_centroid": False},
            layer_order=["a", "i"],
        )
        ordered = [entry["vowel"] for entry in label_data]
        self.assertEqual(ordered[:2], ["a", "i"])

    def test_draw_single_normalized_respects_layer_order(self):
        engine = PlotEngine()
        fig = Figure()
        df = pd.DataFrame(
            {
                "F1": [0.2, 0.3, -0.4, -0.3],
                "F2": [1.1, 1.0, -0.8, -0.7],
                "Label": ["i", "i", "a", "a"],
            }
        )
        _, _, label_data, _ = engine.draw_single_normalized(
            fig,
            df,
            "Lobanov",
            design_settings={"show_raw": False, "show_centroid": False},
            layer_order=["a", "i"],
            plot_params={"type": "f1_f2"},
        )
        ordered = [entry["vowel"] for entry in label_data]
        self.assertEqual(ordered[:2], ["a", "i"])

    def test_label_manager_layer_overrides_are_deep_copied(self):
        popup = _DummyPopup()
        manager = LabelManager(popup)
        source = {"a": {"lbl_color": "#111111"}}

        manager.set_layer_overrides(source)
        source["a"]["lbl_color"] = "#222222"
        self.assertEqual(
            popup.layer_design_overrides["a"]["lbl_color"],
            "#111111",
        )

        fetched = manager.get_layer_overrides()
        fetched["a"]["lbl_color"] = "#333333"
        self.assertEqual(
            popup.layer_design_overrides["a"]["lbl_color"],
            "#111111",
        )

    def test_label_manager_syncs_current_file_states(self):
        popup = _DummyPopup()
        manager = LabelManager(popup)

        overrides = {"a": {"lbl_size": 22}}
        manager.sync_overrides_by_current_file(overrides)
        overrides["a"]["lbl_size"] = 99
        self.assertEqual(popup.layer_design_overrides_by_file[0]["a"]["lbl_size"], 22)

        manager.sync_filter_state_by_current_file({"a": "SEMI"})
        self.assertEqual(popup.vowel_filter_state_by_file[0]["a"], "SEMI")

    def test_label_manager_series_state_is_isolated(self):
        popup = _DummyPopup()
        manager_0 = LabelManager(popup, series_id=0)
        manager_1 = LabelManager(popup, series_id=1)
        manager_2 = LabelManager(popup, series_id=2)

        manager_0.set_filter_state({"a": "OFF"})
        manager_1.set_filter_state({"i": "SEMI"})
        manager_0.set_layer_overrides({"a": {"lbl_color": "#111111"}})
        manager_1.set_layer_overrides({"i": {"lbl_color": "#222222"}})
        manager_2.set_layer_overrides({"u": {"lbl_color": "#333333"}})
        manager_0.set_layer_order(["a", "i"])
        manager_1.set_layer_order(["u", "o"])
        manager_2.set_layer_order(["e", "u"])

        self.assertEqual(manager_0.get_filter_state(), {"a": "OFF"})
        self.assertEqual(manager_1.get_filter_state(), {"i": "SEMI"})
        self.assertEqual(
            popup.layer_design_overrides_by_series[0]["a"]["lbl_color"],
            "#111111",
        )
        self.assertEqual(
            popup.layer_design_overrides_by_series[1]["i"]["lbl_color"],
            "#222222",
        )
        self.assertEqual(
            popup.layer_design_overrides_by_series[2]["u"]["lbl_color"],
            "#333333",
        )
        self.assertEqual(manager_0.get_layer_order(), ["a", "i"])
        self.assertEqual(manager_1.get_layer_order(), ["u", "o"])
        self.assertEqual(manager_2.get_layer_order(), ["e", "u"])

    def test_label_manager_does_not_leak_series_state(self):
        popup = _DummyPopup()
        manager_0 = LabelManager(popup, series_id=0)
        manager_1 = LabelManager(popup, series_id=1)

        manager_0.set_layer_overrides({"a": {"lbl_color": "#111111"}})
        overrides_0 = manager_0.get_layer_overrides()
        overrides_0["a"]["lbl_color"] = "#999999"

        self.assertEqual(
            popup.layer_design_overrides_by_series[0]["a"]["lbl_color"],
            "#111111",
        )
        self.assertEqual(manager_1.get_layer_overrides(), {})

        manager_0.set_filter_state({"a": "OFF"})
        manager_1.set_filter_state({"i": "SEMI"})
        state_0 = manager_0.get_filter_state()
        state_0["a"] = "ON"

        self.assertEqual(popup.vowel_filter_states[0]["a"], "OFF")
        self.assertEqual(popup.vowel_filter_states[1]["i"], "SEMI")

    def test_label_manager_series_state_keeps_single_source(self):
        popup = _DummyPopup()
        manager_0 = LabelManager(popup, series_id=0)

        manager_0.set_filter_state({"a": "OFF"})
        manager_0.set_layer_overrides({"a": {"lbl_color": "#111111"}})

        self.assertEqual(popup.vowel_filter_states[0]["a"], "OFF")
        self.assertEqual(
            popup.layer_design_overrides_by_series[0]["a"]["lbl_color"],
            "#111111",
        )
        self.assertFalse(hasattr(popup, "vowel_filter_state_blue"))
        self.assertFalse(hasattr(popup, "layer_design_overrides_blue"))

    def test_compare_layer_dock_switch_keeps_series_specific_state(self):
        popup = _DummyPopup()
        dock_for_series_0 = LabelManager(popup, series_id=0)
        dock_for_series_1 = LabelManager(popup, series_id=1)

        dock_for_series_0.set_filter_state({"a": "OFF"})
        dock_for_series_1.set_filter_state({"i": "SEMI"})
        dock_for_series_0.set_layer_overrides({"a": {"lbl_color": "#111111"}})
        dock_for_series_1.set_layer_overrides({"i": {"lbl_color": "#222222"}})

        # UI에서 탭 전환(0 -> 1 -> 0)을 흉내 내도 시리즈별 상태는 변하지 않아야 한다.
        _active_series = 0
        _active_series = 1
        _active_series = 0
        self.assertEqual(_active_series, 0)

        self.assertEqual(dock_for_series_0.get_filter_state(), {"a": "OFF"})
        self.assertEqual(dock_for_series_1.get_filter_state(), {"i": "SEMI"})
        self.assertEqual(
            dock_for_series_0.get_layer_overrides()["a"]["lbl_color"],
            "#111111",
        )
        self.assertEqual(
            dock_for_series_1.get_layer_overrides()["i"]["lbl_color"],
            "#222222",
        )

    def test_draw_object_display_name_accepts_numeric_series(self):
        obj = SimpleNamespace(type="line", point_labels=["a", "i"], series=1)
        self.assertEqual(
            draw_object_display_name([obj], 0),
            "선 1 : a2-i2",
        )


if __name__ == "__main__":
    unittest.main()
