import os
import sys
import unittest

import pandas as pd
from matplotlib.figure import Figure

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.plot_engine import PlotEngine
from ui.widgets.label_manager import LabelManager


class _DummyPopup:
    def __init__(self):
        self.layer_design_overrides = {}
        self.layer_design_overrides_by_file = {}
        self.vowel_filter_state_by_file = {}
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


if __name__ == "__main__":
    unittest.main()
