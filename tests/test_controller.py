# tests/test_controller.py
import sys
import os
import unittest
from unittest.mock import patch
import pandas as pd

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.controller import MainController


class TestMainController(unittest.TestCase):
    @patch("core.controller.MainUI")
    @patch("core.controller.QTimer")
    def setUp(self, mock_timer, mock_ui):
        # UI 및 타이머 모킹하여 초기화 시 오류 방지
        self.mock_ui = mock_ui.return_value
        self.mock_ui.get_normalization.return_value = None
        self.controller = MainController()
        # 테스트를 위해 빈 데이터셋으로 초기화 확인
        self.assertEqual(len(self.controller.filepaths), 0)
        self.assertEqual(len(self.controller.plot_data_list), 0)

    def test_add_remove_files(self):
        """파일 추가 및 삭제 로직 검증."""
        # DataProcessor.load_files 모킹
        with patch("core.controller.DataProcessor") as mock_proc_cls:
            mock_proc = mock_proc_cls.return_value
            mock_proc.load_files.return_value = (True, False, [])
            mock_proc.get_data.return_value = pd.DataFrame(
                {"F1": [500, 600], "F2": [1500, 1600], "Label": ["i", "e"]}
            )

            # 파일 추가
            test_files = [os.path.abspath("test1.csv")]
            result = self.controller.add_files(test_files)

            self.assertEqual(result["success_count"], 1)
            self.assertEqual(len(self.controller.filepaths), 1)
            self.assertEqual(self.controller.plot_data_list[0]["name"], "test1.csv")

            # 파일 삭제
            self.controller.remove_file(0)
            self.assertEqual(len(self.controller.filepaths), 0)
            self.assertEqual(len(self.controller.plot_data_list), 0)

    def test_apply_normalization(self):
        """컨트롤러의 정규화 래퍼 함수 검증."""
        df = pd.DataFrame({"F1": [500, 600], "F2": [1500, 1600], "Label": ["i", "e"]})

        # Lobanov 정규화 호출 확인
        with patch("core.controller.lobanov_normalization") as mock_norm:
            self.controller._apply_normalization(df, "Lobanov")
            mock_norm.assert_called_once()

        # None일 경우 원본 복사본 반환
        res = self.controller._apply_normalization(df, None)
        pd.testing.assert_frame_equal(res, df)

    def test_get_main_ui_plot_params_includes_normalization(self):
        """메인 UI 파라미터에 정규화 설정이 포함되는지 검증."""
        self.mock_ui.get_plot_type.return_value = "f1_f2"
        self.mock_ui.get_f1_scale.return_value = "linear"
        self.mock_ui.get_f2_scale.return_value = "log"
        self.mock_ui.get_origin.return_value = "bottom_left"
        self.mock_ui.get_use_bark_units.return_value = False
        self.mock_ui.get_normalization.return_value = "Lobanov"

        params = self.controller._get_main_ui_plot_params()
        self.assertEqual(params["normalization"], "Lobanov")

    def test_refresh_plot_uses_single_normalized(self):
        """단일 플롯 refresh 시 Lobanov면 draw_single_normalized를 호출."""
        import pandas as pd
        from unittest.mock import MagicMock

        df = pd.DataFrame({"F1": [500, 600], "F2": [1500, 1600], "Label": ["i", "e"]})
        popup = MagicMock()
        popup.uses_main_normalization = True
        popup.normalization = "Lobanov"
        popup.plot_data_snapshot = [{"name": "t.csv", "df": df}]
        popup.current_idx = 0
        popup.fixed_plot_params = {"type": "f1_f2", "sigma": 2.0}
        popup.get_filter_state.return_value = {}
        popup.get_design_settings.return_value = {}
        popup.get_layer_design_overrides.return_value = {}
        popup.range_widgets = {
            k: MagicMock(text=MagicMock(return_value=str(v)))
            for k, v in {
                "y_min": "-2",
                "y_max": "2",
                "x_min": "-2",
                "x_max": "2",
            }.items()
        }
        popup.cb_sigma = None

        self.mock_ui.get_normalization.return_value = "Lobanov"
        fig = MagicMock()
        canvas = MagicMock()

        with patch.object(
            self.controller.plot_engine, "draw_single_normalized"
        ) as mock_draw:
            mock_draw.return_value = (MagicMock(), [], [], [])
            with patch.object(self.controller.plot_engine, "draw_plot") as mock_raw:
                self.controller.refresh_plot(
                    fig, canvas, popup.range_widgets, None, popup
                )
                mock_draw.assert_called_once()
                mock_raw.assert_not_called()

    def test_get_axis_units(self):
        """파라미터에 따른 축 단위 문자열 반환 검증."""
        # Hz 모드
        params = {"f1_scale": "linear", "f2_scale": "bark", "use_bark_units": False}
        u1, u2 = self.controller._get_axis_units_from_params(params)
        self.assertEqual(u1, "Hz")
        self.assertEqual(u2, "Hz")

        # Bark 모드
        params["use_bark_units"] = True
        u1, u2 = self.controller._get_axis_units_from_params(params)
        self.assertEqual(u1, "Hz")  # f1은 linear이므로 Hz
        self.assertEqual(u2, "Bark")  # f2는 bark이고 use_bark이므로 Bark

    def test_outlier_mode_toggle(self):
        """이상치 제거 모드 전환 시 df_original 보존 및 적용 여부 검증."""
        df_orig = pd.DataFrame(
            {
                "F1": [500, 510, 520, 1000],  # 1000은 이상치 후보
                "F2": [1500, 1510, 1520, 3000],
                "Label": ["i", "i", "i", "i"],
            }
        )
        self.controller.plot_data_list = [
            {"name": "test.csv", "df": df_orig.copy(), "df_original": df_orig.copy()}
        ]

        # UI에서 모드 읽어오는 부분 모킹
        self.mock_ui.get_outlier_mode.return_value = "mahalanobis_2sigma"
        self.mock_ui.get_plot_type.return_value = "f1_f2"
        self.mock_ui.get_outlier_scope.return_value = "individual"
        # 이상치 제거 함수 모킹 (실제 계산은 math_utils 테스트에서 검증됨)
        with patch("core.controller.remove_outliers_mahalanobis_scoped") as mock_remove:
            mock_remove.return_value = (df_orig.iloc[:3], 1, None, {})
            self.controller.on_outlier_mode_changed()

            # 결과 확인
            self.assertEqual(len(self.controller.plot_data_list[0]["df"]), 3)
            # 원본은 유지되어야 함
            self.assertEqual(len(self.controller.plot_data_list[0]["df_original"]), 4)

    def test_combined_scope_tags_concat_and_backtracks_to_files(self):
        """통합 scope: concat 시 _src_name/_src_row 부여 후 역산으로 개별 df 갱신."""
        df1 = pd.DataFrame(
            {
                "F1": [500, 510, 999],
                "F2": [1500, 1510, 3000],
                "Label": ["i", "i", "i"],
            }
        )
        df2 = pd.DataFrame(
            {
                "F1": [520, 530],
                "F2": [1520, 1530],
                "Label": ["i", "i"],
            }
        )
        self.controller.plot_data_list = [
            {"name": "spk1.csv", "df": df1.copy(), "df_original": df1.copy()},
            {"name": "spk2.csv", "df": df2.copy(), "df_original": df2.copy()},
        ]
        self.mock_ui.get_outlier_mode.return_value = "mahalanobis_2sigma"
        self.mock_ui.get_outlier_scope.return_value = "combined"
        self.mock_ui.get_plot_type.return_value = "f1_f2"

        kept = pd.concat(
            [
                df1.iloc[[0, 1]].assign(_src_name="spk1.csv", _src_row=[0, 1]),
                df2.assign(_src_name="spk2.csv", _src_row=[0, 1]),
            ],
            ignore_index=True,
        )

        with patch("core.controller.remove_outliers_mahalanobis_scoped") as mock_remove:
            mock_remove.return_value = (
                kept,
                1,
                {},
                {"groups_tested": {"i"}, "groups_too_small": set()},
            )
            with patch.object(self.controller, "update_live_preview"):
                self.controller.on_outlier_mode_changed()

            df_combined = mock_remove.call_args[0][0]
            self.assertIn("_src_name", df_combined.columns)
            self.assertIn("_src_row", df_combined.columns)
            self.assertEqual(len(df_combined), 5)
            self.assertEqual(mock_remove.call_args[1]["scope"], "combined")

        real_items = [
            it for it in self.controller.plot_data_list if not it.get("is_combined")
        ]
        self.assertEqual(len(real_items[0]["df"]), 2)
        self.assertEqual(len(real_items[1]["df"]), 2)
        self.assertEqual(len(real_items[0]["df_original"]), 3)
        pd.testing.assert_frame_equal(
            real_items[0]["df"].reset_index(drop=True),
            df1.iloc[[0, 1]].reset_index(drop=True),
        )

    def test_combined_scope_end_to_end_removes_outlier_in_one_file(self):
        """통합 scope 실제 Tukey IQR: pooled Label 기준 제거가 개별 파일 df에 반영."""
        df1 = pd.DataFrame(
            {
                "F1": [300, 310, 320],
                "F2": [1500, 1510, 1520],
                "Label": ["i", "i", "i"],
            }
        )
        df2 = pd.DataFrame(
            {
                "F1": [330, 340, 5000],
                "F2": [1530, 1540, 6000],
                "Label": ["i", "i", "i"],
            }
        )
        self.controller.plot_data_list = [
            {"name": "a.csv", "df": df1.copy(), "df_original": df1.copy()},
            {"name": "b.csv", "df": df2.copy(), "df_original": df2.copy()},
        ]
        self.mock_ui.get_outlier_mode.return_value = "tukey_iqr"
        self.mock_ui.get_outlier_scope.return_value = "combined"
        self.mock_ui.get_plot_type.return_value = "f1_f2"

        with patch.object(self.controller, "update_live_preview"):
            self.controller.on_outlier_mode_changed()

        by_name = {
            it["name"]: it
            for it in self.controller.plot_data_list
            if not it.get("is_combined")
        }
        self.assertEqual(len(by_name["a.csv"]["df"]), 3)
        self.assertEqual(len(by_name["b.csv"]["df"]), 2)
        self.assertEqual(len(by_name["a.csv"]["df_original"]), 3)
        self.assertEqual(len(by_name["b.csv"]["df_original"]), 3)

    def test_combined_scope_falls_back_to_individual_with_one_file(self):
        """파일 1개면 scope=combined여도 파일 단위 individual 경로."""
        df_orig = pd.DataFrame(
            {
                "F1": [500, 510, 520, 1000],
                "F2": [1500, 1510, 1520, 3000],
                "Label": ["i", "i", "i", "i"],
            }
        )
        self.controller.plot_data_list = [
            {"name": "solo.csv", "df": df_orig.copy(), "df_original": df_orig.copy()}
        ]
        self.mock_ui.get_outlier_mode.return_value = "mahalanobis_2sigma"
        self.mock_ui.get_outlier_scope.return_value = "combined"
        self.mock_ui.get_plot_type.return_value = "f1_f2"

        with patch("core.controller.remove_outliers_mahalanobis_scoped") as mock_remove:
            mock_remove.return_value = (df_orig.iloc[:3], 1, {}, {})
            with patch.object(self.controller, "update_live_preview"):
                self.controller.on_outlier_mode_changed()

            self.assertEqual(mock_remove.call_count, 1)
            self.assertEqual(mock_remove.call_args[1]["scope"], "individual")
            df_passed = mock_remove.call_args[0][0]
            self.assertNotIn("_src_name", df_passed.columns)

    def test_outlier_off_restores_all_files_from_original(self):
        """이상치 OFF 시 모든 real 파일 df가 df_original로 복원."""
        df1 = pd.DataFrame({"F1": [500], "F2": [1500], "Label": ["i"]})
        df2 = pd.DataFrame({"F1": [600], "F2": [1600], "Label": ["e"]})
        self.controller.plot_data_list = [
            {"name": "a.csv", "df": df1.iloc[0:0], "df_original": df1.copy()},
            {"name": "b.csv", "df": df2.iloc[0:0], "df_original": df2.copy()},
        ]
        self.controller.last_outlier_mode = "mahalanobis_2sigma"
        self.mock_ui.get_outlier_mode.return_value = None

        with patch.object(self.controller, "update_live_preview"):
            with patch.object(self.controller, "_rebuild_combined_entry"):
                self.controller.on_outlier_mode_changed()

        for it in self.controller.plot_data_list:
            if it.get("is_combined"):
                continue
            pd.testing.assert_frame_equal(it["df"], it["df_original"])


if __name__ == "__main__":
    unittest.main()
