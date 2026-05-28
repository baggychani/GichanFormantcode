# tests/test_math_utils.py
"""math_utils 정규화·변환 함수 단위 테스트."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import pandas as pd
import numpy as np
from utils.math_utils import (
    hz_to_linear,
    hz_to_bark,
    bark_to_hz,
    hz_to_log,
    calc_f2_prime,
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
        out, removed, _, meta = remove_outliers_tukey_iqr(df, "f1_f2", scope="individual")
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
        out, removed, _, _ = remove_outliers_mahalanobis_scoped(df, "f1_f2", scope="individual")
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
