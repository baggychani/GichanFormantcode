# tests/test_data_processor.py
"""DataProcessor._parse_fixed_columns 단위 테스트."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import pandas as pd
import config
from model.data_processor import DataProcessor


class TestParseFixedColumns(unittest.TestCase):
    def setUp(self):
        self.processor = DataProcessor()

    def test_too_few_columns(self):
        """열이 2개 미만이면 (None, PARSE_ERR_COLUMNS_TOO_FEW, None) 반환."""
        df = pd.DataFrame({0: [1, 2, 3]})
        result_df, error, drop_report = self.processor._parse_fixed_columns(df)
        self.assertIsNone(result_df)
        self.assertEqual(error, config.PARSE_ERR_COLUMNS_TOO_FEW)
        self.assertIsNone(drop_report)

    def test_empty_single_column(self):
        """열 1개만 있으면 동일한 에러 메시지."""
        df = pd.DataFrame({0: [100, 200]})
        result_df, error, drop_report = self.processor._parse_fixed_columns(df)
        self.assertIsNone(result_df)
        self.assertEqual(error, config.PARSE_ERR_COLUMNS_TOO_FEW)

    def test_f1_f2_validation_fail(self):
        """F1 >= F2만 있으면 (None, PARSE_ERR_F1_F2_INVALID, None) 반환."""
        df = pd.DataFrame({0: [500, 600], 1: [300, 200]})
        result_df, error, drop_report = self.processor._parse_fixed_columns(df)
        self.assertIsNone(result_df)
        self.assertEqual(error, config.PARSE_ERR_F1_F2_INVALID)

    def test_f1_eq_f2_fail(self):
        df = pd.DataFrame({0: [400, 400], 1: [400, 400]})
        result_df, error, drop_report = self.processor._parse_fixed_columns(df)
        self.assertIsNone(result_df)
        self.assertEqual(error, config.PARSE_ERR_F1_F2_INVALID)

    def test_non_numeric(self):
        """F1/F2가 숫자로 변환 불가면 실패."""
        df = pd.DataFrame({0: ["a", "b"], 1: [1000, 2000]})
        result_df, error, drop_report = self.processor._parse_fixed_columns(df)
        self.assertIsNone(result_df)
        self.assertIn("F1/F2", error)

    def test_success(self):
        """정상 입력: F1 < F2, 라벨 있으면 (DataFrame, None, drop_report) 반환."""
        df = pd.DataFrame(
            {0: [300, 400, 500], 1: [2000, 1800, 1500], 2: ["/i/", "/e/", "/a/"]}
        )
        result_df, error, drop_report = self.processor._parse_fixed_columns(df)
        self.assertIsNone(error)
        self.assertIsNotNone(result_df)
        self.assertIn("F1", result_df.columns)
        self.assertIn("F2", result_df.columns)
        self.assertIn("Label", result_df.columns)
        self.assertEqual(len(result_df), 3)

    def test_success_no_label_gets_unknown(self):
        """열 2개만 있으면 라벨 열이 없어 Label='Unknown'으로 채움."""
        df = pd.DataFrame({0: [300, 400], 1: [2000, 1800]})
        result_df, error, drop_report = self.processor._parse_fixed_columns(df)
        self.assertIsNone(error)
        self.assertIsNotNone(result_df)
        self.assertIn("Label", result_df.columns)
        self.assertTrue((result_df["Label"] == "Unknown").all())

    def test_plain_label_last_column(self):
        """마지막 열의 슬래시 없는 IPA 기호를 라벨로 인식."""
        df = pd.DataFrame(
            {
                0: [300.0, 325.0],
                1: [700.0, 800.0],
                2: ["o", "u"],
            }
        )
        result_df, error, _ = self.processor._parse_fixed_columns(df)
        self.assertIsNone(error)
        self.assertListEqual(result_df["Label"].tolist(), ["o", "u"])

    def test_f3_zero_kept_with_nan(self):
        """F3=0은 NaN(측정 없음)으로 두고 F1/F2 조건만 맞으면 행 유지."""
        df = pd.DataFrame(
            {
                0: [300.0, 325.0, 290.0],
                1: [700.0, 800.0, 950.0],
                2: [0.0, 2614.2, 0.0],
                3: ["o", "o", "u"],
            }
        )
        result_df, error, drop_report = self.processor._parse_fixed_columns(df)
        self.assertIsNone(error)
        self.assertEqual(len(result_df), 3)
        self.assertTrue(pd.isna(result_df.loc[0, "F3"]))
        self.assertFalse(pd.isna(result_df.loc[1, "F3"]))
        self.assertIsNone(drop_report)

    def test_f1_f2_f3_ipa_four_columns(self):
        """F1, F2, F3, IPA(마지막 열) 4열 형식."""
        df = pd.DataFrame(
            {
                0: [300.0, 325.0],
                1: [700.0, 828.0],
                2: [2500.0, 2614.2],
                3: ["/o/", "o"],
            }
        )
        result_df, error, _ = self.processor._parse_fixed_columns(df)
        self.assertIsNone(error)
        self.assertEqual(len(result_df), 2)
        self.assertEqual(result_df["Label"].tolist(), ["o", "o"])

    def test_plotformant_trailing_column(self):
        """PlotFormant 형식: F1 F2 0 /라벨/ trailing숫자 — trailing은 무시."""
        df = pd.DataFrame(
            {
                0: [723.0, 482.0],
                1: [1366.0, 1924.0],
                2: [0.0, 0.0],
                3: ["/a/", "/e/"],
                4: [1.0, 3.0],
            }
        )
        result_df, error, _ = self.processor._parse_fixed_columns(df)
        self.assertIsNone(error)
        self.assertEqual(len(result_df), 2)
        self.assertEqual(result_df["Label"].tolist(), ["a", "e"])

    def test_bracket_label_column(self):
        """[모음] 형식 라벨."""
        df = pd.DataFrame(
            {
                0: [300.0, 325.0],
                1: [700.0, 800.0],
                2: ["[o]", "[u]"],
            }
        )
        result_df, error, _ = self.processor._parse_fixed_columns(df)
        self.assertIsNone(error)
        self.assertListEqual(result_df["Label"].tolist(), ["o", "u"])

    def test_skip_placeholder_column_before_label(self):
        """// placeholder 열을 건너뛰고 라벨 인식."""
        df = pd.DataFrame(
            {
                0: [300.0, 325.0],
                1: [700.0, 800.0],
                2: ["//", "//"],
                3: ["/o/", "/u/"],
            }
        )
        result_df, error, _ = self.processor._parse_fixed_columns(df)
        self.assertIsNone(error)
        self.assertListEqual(result_df["Label"].tolist(), ["o", "u"])


if __name__ == "__main__":
    unittest.main()
