# tests/test_math_utils.py
"""math_utils 정규화·변환 함수 단위 테스트."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import pandas as pd
import numpy as np
from core.normalization_service import NormalizationError, apply_normalization
from utils.math_utils import (
    hz_to_linear,
    hz_to_bark,
    bark_to_hz,
    hz_to_log,
    calc_f2_prime,
    compute_x_raw,
    lobanov_normalization,
    gerstman_normalization,
    nearey1_normalization,
    bigham_normalization,
    remove_outliers_tukey_iqr,
    remove_outliers_mahalanobis_scoped,
)


class TestScaleConversion(unittest.TestCase):
    def test_hz_to_linear(self):
        self.assertEqual(hz_to_linear(500), 500)
        self.assertEqual(hz_to_linear(0), 0)

    def test_hz_to_bark(self):
        self.assertGreater(hz_to_bark(1000), 0)
        self.assertTrue(np.isfinite(hz_to_bark(0.1)))
        x = hz_to_bark(np.array([100, 500, 1000]))
        self.assertEqual(len(x), 3)
        self.assertTrue(np.all(np.isfinite(x)))

    def test_bark_to_hz(self):
        x = bark_to_hz(np.array([0, 5, 10]))
        self.assertEqual(len(x), 3)
        self.assertTrue(np.all(np.isfinite(x)))

    def test_hz_to_log(self):
        self.assertAlmostEqual(hz_to_log(100), 2.0, places=5)
        x = hz_to_log(np.array([0.1, 1, 10]))
        self.assertTrue(np.all(np.isfinite(x)))

    def test_calc_f2_prime(self):
        f1 = np.array([300, 400])
        f2 = np.array([2000, 1800])
        f3 = np.array([2500, 2200])
        out = calc_f2_prime(f1, f2, f3)
        self.assertEqual(len(out), 2)
        self.assertTrue(np.all(out >= f2))
        self.assertTrue(np.all(out <= f3))


class TestComputeXRaw(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {
                "F1": [300, 500],
                "F2": [2000, 1800],
                "F3": [2500, 2400],
            }
        )

    def test_f1_f2(self):
        out = compute_x_raw(self.df, "f1_f2")
        pd.testing.assert_series_equal(out, self.df["F2"], check_names=False)

    def test_f1_f3(self):
        out = compute_x_raw(self.df, "f1_f3")
        pd.testing.assert_series_equal(out, self.df["F3"], check_names=False)

    def test_f1_f2_minus_f1(self):
        out = compute_x_raw(self.df, "f1_f2_minus_f1")
        expected = self.df["F2"] - self.df["F1"]
        pd.testing.assert_series_equal(out, expected, check_names=False)

    def test_unknown_plot_type_falls_back_to_f2(self):
        out = compute_x_raw(self.df, "unknown_type")
        pd.testing.assert_series_equal(out, self.df["F2"], check_names=False)


class TestNormalization(unittest.TestCase):
    def setUp(self):
        self.sample_df = pd.DataFrame(
            {
                "F1": [300, 500, 700],
                "F2": [2000, 1800, 1200],
                "F3": [2500, 2400, 2300],
                "Label": ["i", "e", "a"],
            }
        )

    def test_lobanov(self):
        out = lobanov_normalization(self.sample_df)
        self.assertIn("F1", out.columns)
        self.assertIn("F2", out.columns)
        self.assertEqual(len(out), len(self.sample_df))
        self.assertAlmostEqual(out["F1"].mean(), 0, places=10)
        self.assertAlmostEqual(out["F2"].mean(), 0, places=10)

    def test_lobanov_by_speaker_not_pooled(self):
        """Combined 등: 화자별 μ·σ — 통합 평균으로 섞이면 안 됨."""
        df = pd.DataFrame(
            {
                "F1": [200, 400, 800, 1000],
                "F2": [1200, 1400, 2200, 2400],
                "Speaker": ["A", "A", "B", "B"],
            }
        )
        out = lobanov_normalization(df)
        for spk in ("A", "B"):
            sub = out.loc[df["Speaker"] == spk, "F1"]
            self.assertAlmostEqual(sub.mean(), 0, places=10)
            self.assertAlmostEqual(sub.std(), 1, places=10)
        pooled = lobanov_normalization(df.drop(columns=["Speaker"]))
        self.assertFalse(np.allclose(out["F1"].values, pooled["F1"].values))

    def test_gerstman(self):
        out = gerstman_normalization(self.sample_df)
        self.assertEqual(out["F1"].min(), 0)
        self.assertEqual(out["F1"].max(), 999)
        self.assertEqual(out["F2"].min(), 0)
        self.assertEqual(out["F2"].max(), 999)

    def test_nearey1(self):
        out = nearey1_normalization(self.sample_df)
        self.assertIn("F1", out.columns)
        self.assertTrue(np.all(np.isfinite(out["F1"])))

    def test_bigham(self):
        out = bigham_normalization(self.sample_df)
        self.assertIn("F1", out.columns)
        self.assertIn("F2", out.columns)
        self.assertEqual(len(out), len(self.sample_df))

    def test_bigham_invalid_numeric_data_raises_normalization_error(self):
        invalid = self.sample_df.copy()
        invalid["F1"] = ["bad", "data", "here"]

        with self.assertRaisesRegex(NormalizationError, "Bigham 정규화"):
            apply_normalization(invalid, "Bigham")

    def test_watt_fabricius_invalid_numeric_data_raises_normalization_error(self):
        invalid = self.sample_df.copy()
        invalid["F1"] = ["bad", "data", "here"]

        with self.assertRaisesRegex(NormalizationError, "2mW/F 정규화"):
            apply_normalization(invalid, "2mW/F")


class TestNormalizationMissingF3(unittest.TestCase):
    """F3 측정이 없는 토큰(NaN)은 정규화 후에도 '측정 없음'으로 남아야 한다.

    0으로 채우면 Lobanov/Nearey1에서는 화자 평균, Gerstman에서는 최솟값이라는
    실제 좌표가 되어 F3 기반 통계(평균·SD·Pillai)에 섞인다.
    """

    def setUp(self):
        self.df = pd.DataFrame(
            {
                "F1": [300, 320, 310, 800, 780, 350],
                "F2": [2300, 2250, 2280, 1300, 1350, 800],
                "F3": [3000, np.nan, 2950, 2600, 2550, 2400],
                "Label": ["i", "i", "i", "a", "a", "u"],
            }
        )

    def test_missing_f3_stays_missing(self):
        for method in ("Lobanov", "Gerstman", "Nearey1"):
            with self.subTest(method=method):
                out = apply_normalization(self.df, method)
                self.assertTrue(pd.isna(out.loc[1, "F3"]))
                self.assertTrue(np.isfinite(out.loc[1, "F1"]))
                self.assertTrue(np.isfinite(out.loc[1, "F2"]))

    def test_measured_f3_uses_only_measured_tokens(self):
        measured = self.df.dropna(subset=["F3"])
        for method in ("Lobanov", "Gerstman", "Nearey1"):
            with self.subTest(method=method):
                out = apply_normalization(self.df, method)
                expected = apply_normalization(measured, method)
                np.testing.assert_allclose(
                    out.loc[measured.index, "F3"], expected["F3"]
                )


class TestNormalizationBySpeaker(unittest.TestCase):
    """화자 내재적(speaker-intrinsic) 정규화는 Combined에서도 화자별로 계산한다."""

    def setUp(self):
        male = pd.DataFrame(
            {
                "F1": [280, 290, 730, 720, 320, 330],
                "F2": [2250, 2200, 1100, 1150, 800, 850],
                "F3": [3000, 2950, 2450, 2500, 2300, 2350],
                "Label": ["i", "i", "a", "a", "u", "u"],
            }
        )
        female = pd.DataFrame(
            {
                "F1": [330, 340, 950, 930, 380, 390],
                "F2": [2800, 2750, 1400, 1450, 950, 1000],
                "F3": [3300, 3350, 2900, 2950, 2700, 2750],
                "Label": ["i", "i", "a", "a", "u", "u"],
            }
        )
        self.speakers = {"M": male, "F": female}
        # 화자 행을 교차 배치해 행 순서 복원까지 함께 검증한다.
        tagged = [df.assign(Speaker=name) for name, df in self.speakers.items()]
        combined = pd.concat(tagged, ignore_index=True)
        order = [i for pair in zip(range(6), range(6, 12)) for i in pair]
        self.combined = combined.iloc[order].reset_index(drop=True)

    def test_each_speaker_matches_individual_normalization(self):
        for method in ("Lobanov", "Gerstman", "Nearey1", "Bigham", "2mW/F"):
            with self.subTest(method=method):
                out = apply_normalization(self.combined, method)
                self.assertListEqual(
                    out["Speaker"].tolist(), self.combined["Speaker"].tolist()
                )
                for name, df in self.speakers.items():
                    expected = apply_normalization(df, method)
                    got = out[out["Speaker"] == name]
                    np.testing.assert_allclose(
                        got[["F1", "F2"]].to_numpy(),
                        expected[["F1", "F2"]].to_numpy(),
                    )

    def test_2mwf_leaves_all_speakers_unnormalized_when_one_lacks_corner(self):
        """한 화자만 Hz로 남으면 척도가 섞이므로 전체를 적용하지 않는다."""
        df = self.combined[
            ~((self.combined["Speaker"] == "F") & (self.combined["Label"] == "a"))
        ]
        out = apply_normalization(df, "2mW/F")
        np.testing.assert_allclose(
            out[["F1", "F2"]].to_numpy(), df[["F1", "F2"]].to_numpy()
        )


if __name__ == "__main__":
    unittest.main()


class TestOutlierRemovalScoped(unittest.TestCase):
    def test_tukey_iqr_bypass_when_n_lt_5(self):
        df = pd.DataFrame(
            {
                "F1": [300, 310, 320, 5000],  # extreme but N=4
                "F2": [1500, 1510, 1520, 6000],
                "Label": ["i", "i", "i", "i"],
            }
        )
        out, removed, _, meta = remove_outliers_tukey_iqr(
            df, "f1_f2", scope="individual"
        )
        self.assertEqual(len(out), len(df))
        self.assertEqual(removed, 0)

    def test_tukey_iqr_removes_extreme_when_n_ge_5(self):
        df = pd.DataFrame(
            {
                "F1": [300, 310, 320, 330, 340, 5000],
                "F2": [1500, 1510, 1520, 1530, 1540, 6000],
                "Label": ["i"] * 6,
            }
        )
        out, removed, _, _ = remove_outliers_tukey_iqr(df, "f1_f2", scope="individual")
        self.assertEqual(removed, 1)
        self.assertEqual(len(out), 5)

    def test_mahalanobis_scoped_bypass_when_n_lt_5(self):
        df = pd.DataFrame(
            {
                "F1": [500, 510, 520, 1000],
                "F2": [1500, 1510, 1520, 3000],
                "Label": ["i"] * 4,
            }
        )
        out, removed, _, _ = remove_outliers_mahalanobis_scoped(
            df, "f1_f2", scope="individual"
        )
        self.assertEqual(len(out), len(df))
        self.assertEqual(removed, 0)

    def test_combined_scope_tukey_pools_by_label_across_speakers(self):
        """combined scope: Speaker 무시, Label 풀(N>=5)에서만 이상치 판정."""
        df = pd.DataFrame(
            {
                "F1": [300, 310, 320, 330, 340, 5000],
                "F2": [1500, 1510, 1520, 1530, 1540, 6000],
                "Label": ["i"] * 6,
                "Speaker": ["A", "A", "A", "B", "B", "B"],
            }
        )
        out_ind, removed_ind, _, _ = remove_outliers_tukey_iqr(
            df, "f1_f2", scope="individual"
        )
        out_combined, removed_combined, _, meta = remove_outliers_tukey_iqr(
            df, "f1_f2", scope="combined"
        )
        # 화자별 N=3 → individual은 전부 bypass
        self.assertEqual(removed_ind, 0)
        self.assertEqual(len(out_ind), 6)
        # Label 'i' 6개 pooled → 극단값 1개 제거
        self.assertEqual(removed_combined, 1)
        self.assertEqual(len(out_combined), 5)
        self.assertIn("('i',)", meta.get("groups_tested", set()))

    # Auto Hybrid(개별+통합 혼합) 방식은 방법론적 일관성 위배로 폐기되었으므로 테스트하지 않는다.
