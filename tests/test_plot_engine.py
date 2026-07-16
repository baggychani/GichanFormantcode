# tests/test_plot_engine.py
import sys
import os
import unittest
import numpy as np
from matplotlib.figure import Figure

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.plot_engine import PlotEngine
from utils.math_utils import hz_to_bark, hz_to_log


class TestPlotEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PlotEngine()

    def test_apply_scale(self):
        """linear, bark, log 스케일 적용 결과 검증."""
        data = np.array([500, 1000, 2000])

        # Linear (None or other)
        self.assertTrue(np.array_equal(self.engine._apply_scale(data, "linear"), data))

        # Bark
        expected_bark = hz_to_bark(data)
        np.testing.assert_array_almost_equal(
            self.engine._apply_scale(data, "bark"), expected_bark
        )

        # Log
        expected_log = hz_to_log(data)
        np.testing.assert_array_almost_equal(
            self.engine._apply_scale(data, "log"), expected_log
        )

    def test_set_ticks_hz_on_bark_scale(self):
        """Case: Bark 스케일이지만 Hz 단위를 사용하는 경우 (사용자 강조 사항).
        - 눈금 위치(major_val)는 Bark 스케일이 적용되어야 함.
        - 눈금 라벨(labels)은 원래의 Hz 값이어야 함.
        """
        fig = Figure()
        ax = fig.add_subplot(111)

        # f2_scale="bark", use_bark_units=False
        self.engine._set_ticks(
            ax,
            "x",
            scale_type="bark",
            min_val=500,
            max_val=2500,
            step_major=500,
            step_minor=100,
            use_bark_units=False,
        )

        ticks = ax.get_xticks()
        labels = [label.get_text() for label in ax.get_xticklabels()]

        # 500, 1000, 1500, 2000, 2500 Hz 위치에 눈금이 있어야 함 (Bark로 변환된 값)
        expected_ticks = [
            self.engine._apply_scale(h, "bark") for h in [500, 1000, 1500, 2000, 2500]
        ]
        np.testing.assert_array_almost_equal(ticks, expected_ticks)

        # 라벨은 Hz 값인 "500", "1000", ... 이어야 함
        expected_labels = ["500", "1000", "1500", "2000", "2500"]
        self.assertEqual(labels, expected_labels)

    def test_set_ticks_bark_on_bark_scale(self):
        """Case: Bark 스케일이고 Bark 단위를 사용하는 경우.
        - 눈금 위치와 라벨 모두 Bark 단위여야 함.
        """
        fig = Figure()
        ax = fig.add_subplot(111)

        # f2_scale="bark", use_bark_units=True
        # 500 Hz ≈ 4.92 Bark, 2500 Hz ≈ 14.54 Bark
        hz_min, hz_max = 500, 2500
        bark_min, bark_max = hz_to_bark(hz_min), hz_to_bark(hz_max)

        self.engine._set_ticks(
            ax,
            "x",
            scale_type="bark",
            min_val=bark_min,
            max_val=bark_max,
            step_major=500,
            step_minor=100,
            use_bark_units=True,
        )

        ticks = ax.get_xticks()
        labels = [label.get_text() for label in ax.get_xticklabels()]

        # 4.92 ~ 14.54 범위의 정수 눈금 [5, 6, ..., 14] 생성됨
        expected_bark_ticks = list(range(5, 15, 1))
        np.testing.assert_array_equal(ticks, expected_bark_ticks)
        self.assertEqual(labels, [str(b) for b in expected_bark_ticks])

    def test_get_axis_name(self):
        """플롯 타입에 따른 축 이름 반환 검증."""
        self.assertEqual(self.engine._get_axis_name("f1_f2"), "F2")
        self.assertEqual(self.engine._get_axis_name("f1_f3"), "F3")
        self.assertEqual(self.engine._get_axis_name("f1_f2_prime"), "F2'")
        self.assertEqual(self.engine._get_axis_name("unknown"), "X-Axis")

    def test_draw_plot_axis_units(self):
        """draw_plot 호출 시 축 라벨에 단위(Hz, Bark) 포함 여부 검증."""
        import pandas as pd

        fig = Figure()
        df = pd.DataFrame({"F1": [500], "F2": [1500], "Label": ["i"]})

        # Hz 단위 표시 설정
        params = {
            "type": "f1_f2",
            "origin": "top_left",
            "f1_scale": "linear",
            "f2_scale": "linear",
            "use_bark_units": False,
        }
        design = {"show_axis_units": True, "font_style": "serif"}

        ax, _, _, _ = self.engine.draw_plot(fig, df, params, design_settings=design)
        self.assertIn("(Hz)", ax.get_xlabel())
        self.assertIn("(Hz)", ax.get_ylabel())

        # Bark 단위 표시 설정
        params["f1_scale"] = "bark"
        params["f2_scale"] = "bark"
        params["use_bark_units"] = True
        ax, _, _, _ = self.engine.draw_plot(fig, df, params, design_settings=design)
        self.assertIn("(Bark)", ax.get_xlabel())
        self.assertIn("(Bark)", ax.get_ylabel())

    def test_draw_plot_uses_layer_slash_wrap_override(self):
        import pandas as pd

        fig = Figure()
        df = pd.DataFrame(
            {"F1": [500, 510, 520], "F2": [1500, 1510, 1520], "Label": ["a", "a", "a"]}
        )
        params = {
            "type": "f1_f2",
            "origin": "top_left",
            "f1_scale": "linear",
            "f2_scale": "linear",
            "use_bark_units": False,
        }

        _, _, label_data, _ = self.engine.draw_plot(
            fig,
            df,
            params,
            design_settings={"label_slash_wrap": False},
            layer_overrides={"a": {"label_slash_wrap": True}},
        )

        self.assertEqual(label_data[0]["display_vowel"], "/a/")

    def test_draw_plot_tick_label_size(self):
        import pandas as pd

        fig = Figure()
        df = pd.DataFrame({"F1": [500], "F2": [1500], "Label": ["i"]})
        params = {
            "type": "f1_f2",
            "origin": "top_left",
            "f1_scale": "linear",
            "f2_scale": "linear",
            "use_bark_units": False,
        }

        ax, _, _, _ = self.engine.draw_plot(
            fig, df, params, design_settings={"tick_label_size": 17}
        )

        self.assertEqual(ax.get_xticklabels()[0].get_fontsize(), 17)

    def test_draw_compare_normalized_labels(self):
        """정규화 비교 플롯에서 nF1, nF2 라벨이 사용되고 단위가 없는지 검증."""
        import pandas as pd

        fig = Figure()
        df = pd.DataFrame({"F1": [0.5], "F2": [1.2], "Label": ["i"]})

        # draw_compare_normalized 호출
        ax, _, _, _, _, _ = self.engine.draw_compare_normalized(
            fig, df, df, "Lobanov", name_blue="A", name_red="B"
        )

        # 라벨에 'nF2', 'nF1'이 포함되어야 하며, '(Hz)'나 '(Bark)'는 없어야 함
        self.assertEqual(ax.get_xlabel(), "nF2")
        self.assertEqual(ax.get_ylabel(), "nF1")
        self.assertNotIn("(Hz)", ax.get_xlabel())
        self.assertNotIn("(Bark)", ax.get_xlabel())

    def test_draw_single_normalized_labels_and_limits(self):
        """단일 정규화 플롯: nF1/nF2 라벨 및 Lobanov 기본 범위."""
        import pandas as pd

        fig = Figure()
        df = pd.DataFrame({"F1": [0.5, -0.5], "F2": [1.2, -1.0], "Label": ["i", "a"]})

        ax, _, _, _ = self.engine.draw_single_normalized(
            fig, df, "Lobanov", plot_params={"type": "f1_f2"}
        )

        self.assertEqual(ax.get_xlabel(), "nF2")
        self.assertEqual(ax.get_ylabel(), "nF1")
        xlim = sorted(ax.get_xlim())
        ylim = sorted(ax.get_ylim())
        self.assertAlmostEqual(xlim[0], -2.0, places=4)
        self.assertAlmostEqual(xlim[1], 2.0, places=4)
        self.assertAlmostEqual(ylim[0], -2.0, places=4)
        self.assertAlmostEqual(ylim[1], 2.0, places=4)

    def test_prepare_plot_df_consistent_across_calls(self):
        """단일/비교 경로 모두 _prepare_plot_df가 동일 x_raw·x_val을 만든다."""
        import pandas as pd

        df = pd.DataFrame(
            {
                "F1": [300, 500],
                "F2": [2000, 1800],
                "F3": [2500, 2400],
                "Label": ["i", "a"],
            }
        )
        params = {
            "type": "f1_f2_minus_f1",
            "f1_scale": "linear",
            "f2_scale": "linear",
        }
        first = self.engine._prepare_plot_df(df, params)
        second = self.engine._prepare_plot_df(df.copy(), params)
        pd.testing.assert_frame_equal(
            first[["x_raw", "x_val", "y_val"]],
            second[["x_raw", "x_val", "y_val"]],
        )

    def test_draw_compare_plot_shared_x_raw(self):
        """draw_compare_plot이 _prepare_plot_df 경로로 X축을 계산한다."""
        import pandas as pd
        from core.compare_series import CompareSeriesInput

        fig = Figure()
        df_a = pd.DataFrame(
            {"F1": [300], "F2": [2000], "F3": [2500], "Label": ["i"]}
        )
        df_b = pd.DataFrame(
            {"F1": [500], "F2": [1800], "F3": [2400], "Label": ["a"]}
        )
        params = {
            "type": "f1_f2_minus_f1",
            "origin": "top_left",
            "f1_scale": "linear",
            "f2_scale": "linear",
            "use_bark_units": False,
            "sigma": 2.0,
        }
        expected_x = self.engine._prepare_plot_df(df_a, params)["x_raw"].iloc[0]

        result = self.engine.draw_compare_plot(
            fig,
            [
                CompareSeriesInput(df=df_a, display_name="A"),
                CompareSeriesInput(df=df_b, display_name="B"),
            ],
            params,
        )
        self.assertIsNotNone(result.ax)
        prepared = self.engine._prepare_plot_df(df_a, params)
        self.assertAlmostEqual(float(prepared["x_raw"].iloc[0]), float(expected_x))


if __name__ == "__main__":
    unittest.main()
