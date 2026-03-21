# tests/test_controller.py
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.controller import MainController

class TestMainController(unittest.TestCase):
    @patch('core.controller.MainUI')
    @patch('core.controller.QTimer')
    def setUp(self, mock_timer, mock_ui):
        # UI 및 타이머 모킹하여 초기화 시 오류 방지
        self.mock_ui = mock_ui.return_value
        self.controller = MainController()
        # 테스트를 위해 빈 데이터셋으로 초기화 확인
        self.assertEqual(len(self.controller.filepaths), 0)
        self.assertEqual(len(self.controller.plot_data_list), 0)

    def test_add_remove_files(self):
        """파일 추가 및 삭제 로직 검증."""
        # DataProcessor.load_files 모킹
        with patch('core.controller.DataProcessor') as mock_proc_cls:
            mock_proc = mock_proc_cls.return_value
            mock_proc.load_files.return_value = (True, False, [])
            mock_proc.get_data.return_value = pd.DataFrame({
                "F1": [500, 600], "F2": [1500, 1600], "Label": ["i", "e"]
            })
            
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
        df = pd.DataFrame({
            "F1": [500, 600], "F2": [1500, 1600], "Label": ["i", "e"]
        })
        
        # Lobanov 정규화 호출 확인
        with patch('core.controller.lobanov_normalization') as mock_norm:
            self.controller._apply_normalization(df, "Lobanov")
            mock_norm.assert_called_once()
            
        # None일 경우 원본 복사본 반환
        res = self.controller._apply_normalization(df, None)
        pd.testing.assert_frame_equal(res, df)

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
        self.assertEqual(u1, "Hz") # f1은 linear이므로 Hz
        self.assertEqual(u2, "Bark") # f2는 bark이고 use_bark이므로 Bark

    def test_outlier_mode_toggle(self):
        """이상치 제거 모드 전환 시 df_original 보존 및 적용 여부 검증."""
        df_orig = pd.DataFrame({
            "F1": [500, 510, 520, 1000],  # 1000은 이상치 후보
            "F2": [1500, 1510, 1520, 3000], 
            "Label": ["i", "i", "i", "i"]
        })
        self.controller.plot_data_list = [{
            "name": "test.csv",
            "df": df_orig.copy(),
            "df_original": df_orig.copy()
        }]
        
        # UI에서 모드 읽어오는 부분 모킹
        self.mock_ui.get_outlier_mode.return_value = "1sigma"
        self.mock_ui.get_plot_type.return_value = "f1_f2"
        
        # 이상치 제거 함수 모킹 (실제 계산은 math_utils 테스트에서 검증됨)
        with patch('core.controller.remove_outliers_mahalanobis') as mock_remove:
            mock_remove.return_value = (df_orig.iloc[:3], 1, None, {})
            self.controller.on_outlier_mode_changed()
            
            # 결과 확인
            self.assertEqual(len(self.controller.plot_data_list[0]["df"]), 3)
            # 원본은 유지되어야 함
            self.assertEqual(len(self.controller.plot_data_list[0]["df_original"]), 4)

if __name__ == "__main__":
    unittest.main()
