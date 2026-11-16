# tests/test_data_processor.py
"""DataProcessor._parse_fixed_columns 단위 테스트."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import pandas as pd
import pytest
import config
from model.data_processor import DataProcessor, is_lobanov_file_header
from core.data_loading_service import load_plot_item_from_file
from core.normalization_service import normalize_dataframe
from utils.math_utils import filter_for_plot_type, lobanov_normalization


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

    def test_format_load_error_maps_parser_error(self):
        from model.data_processor import _format_load_error

        err = pd.errors.ParserError("Expected 3 fields in line 12, saw 4")
        self.assertEqual(_format_load_error(err), config.PARSE_ERR_RAGGED_ROWS)

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

    def test_lobanov_mode_skips_hz_f1_less_than_f2(self):
        """Lobanov z: F1 > F2(음수 F2) 허용."""
        df = pd.DataFrame({0: [2.6, 1.9], 1: [-0.12, -0.52], 2: ["/a/", "/i/"]})
        result_df, error, _ = self.processor._parse_fixed_columns(df, lobanov_mode=True)
        self.assertIsNone(error)
        self.assertEqual(len(result_df), 2)

    def test_is_lobanov_file_header(self):
        self.assertTrue(is_lobanov_file_header("Lobanov"))
        self.assertTrue(is_lobanov_file_header("  lobanov  "))
        self.assertFalse(is_lobanov_file_header("F1"))

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


def test_pre_lobanov_f3_zero_survives_file_loading_and_plot_filter(tmp_path):
    raw = pd.DataFrame({
        "F1": [400.0, 500.0, 600.0],
        "F2": [1400.0, 1500.0, 1600.0],
        "F3": [2400.0, 2500.0, 2600.0],
        "Label": ["i", "e", "a"],
    })
    normalized = lobanov_normalization(raw)
    assert normalized.loc[1, "F3"] == 0.0
    path = tmp_path / "normalized.tsv"
    path.write_text(
        "Lobanov\n" + normalized.to_csv(sep="\t", header=False, index=False),
        encoding="utf-8",
    )

    loaded = load_plot_item_from_file(str(path))

    assert loaded["success"], loaded["errors"]
    assert loaded["is_pre_lobanov"]
    working = normalize_dataframe(loaded["item"]["df"], "Lobanov", loaded["item"])
    pd.testing.assert_frame_equal(working, normalized)
    assert len(filter_for_plot_type(working, "f1_f3")) == 3


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16"])
def test_pre_lobanov_header_encoding_preserves_z_scores(tmp_path, encoding):
    path = tmp_path / "normalized.txt"
    path.write_text("Lobanov\n2.6\t-0.12\t/a/\n1.9\t-0.52\t/i/\n", encoding=encoding)

    loaded = load_plot_item_from_file(str(path))

    assert loaded["success"], loaded["errors"]
    assert loaded["is_pre_lobanov"]
    assert loaded["item"]["df"]["F1"].tolist() == [2.6, 1.9]
    assert loaded["item"]["df"]["F2"].tolist() == [-0.12, -0.52]


_KOREAN_ROWS = "400\t2200\t/이/\n700\t1300\t/아/\n450\t900\t/우/\n500\t1900\t/에/\n"


@pytest.mark.parametrize("padding", ["", "\n"])
def test_cp949_file_loads_regardless_of_byte_length(tmp_path, padding):
    path = tmp_path / "korean.txt"
    path.write_bytes((_KOREAN_ROWS + padding).encode("cp949"))

    loaded = load_plot_item_from_file(str(path))

    assert loaded["success"], loaded["errors"]
    assert loaded["item"]["df"]["Label"].tolist() == ["이", "아", "우", "에"]


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le", "utf-16-be"])
def test_utf16_files_still_load_with_and_without_bom(tmp_path, encoding):
    path = tmp_path / "wide.txt"
    path.write_bytes(_KOREAN_ROWS.encode(encoding))

    loaded = load_plot_item_from_file(str(path))

    assert loaded["success"], loaded["errors"]
    assert loaded["item"]["df"]["Label"].tolist() == ["이", "아", "우", "에"]


if __name__ == "__main__":
    unittest.main()
