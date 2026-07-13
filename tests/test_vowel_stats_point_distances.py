import math

import numpy as np
import pandas as pd

from utils.vowel_stats import (
    calculate_pairwise_mahalanobis_distances,
    calculate_point_distances_from_centroid,
    calculate_point_distances_from_centroid_bark,
)


def _sample_df():
    return pd.DataFrame(
        {
            "Label": ["o", "o", "o", "u", "u", "u"],
            "F1": [400.0, 420.0, 380.0, 350.0, 370.0, 330.0],
            "F2": [900.0, 920.0, 880.0, 1100.0, 1120.0, 1080.0],
        }
    )


def test_point_distances_hz_uses_plot_hz_axes():
    df = _sample_df()
    df_hz = df.copy()
    df_hz["x_hz"] = df["F2"].values
    result = calculate_point_distances_from_centroid(
        df_hz, x_col="x_hz", y_col="F1", label_col="Label"
    )
    assert set(result) == {"o", "u"}
    for vowel in ("o", "u"):
        assert result[vowel]["distance_mean"] > 0
        assert result[vowel]["distance_std"] >= 0


def test_point_distances_bark_differs_from_hz():
    df = _sample_df()
    x_hz = df["F2"].values
    hz = calculate_point_distances_from_centroid(
        df.assign(x_hz=x_hz), x_col="x_hz", y_col="F1", label_col="Label"
    )
    bark = calculate_point_distances_from_centroid_bark(
        df, label_col="Label", x_hz=x_hz
    )
    assert hz["o"]["distance_mean"] != bark["o"]["distance_mean"]


def test_centroid_pair_hz_matches_pythagorean_formula():
    """논문 표 8류: F1·F2 Hz 무게중심 간 유클리드 거리."""
    df = _sample_df()
    stats = {}
    for vowel, group in df.groupby("Label"):
        stats[vowel] = (group["F2"].mean(), group["F1"].mean())
    x_o, y_o = stats["o"]
    x_u, y_u = stats["u"]
    expected = math.sqrt((x_o - x_u) ** 2 + (y_o - y_u) ** 2)
    assert abs(expected - math.sqrt(200**2 + 50**2)) < 1e-6


def test_pairwise_mahalanobis_distances_between_vowel_centroids():
    df = _sample_df()
    result = calculate_pairwise_mahalanobis_distances(df)

    assert ("o", "u") in result
    assert result[("o", "u")]["distance"] > 0
    assert result[("o", "u")]["n_a"] == 3
    assert result[("o", "u")]["n_b"] == 3


def test_pairwise_mahalanobis_distances_respects_min_group_size():
    df = _sample_df()
    result = calculate_pairwise_mahalanobis_distances(df, min_group_size=4)

    assert result == {}


def test_pairwise_mahalanobis_uses_pooled_within_group_covariance():
    group_a = np.array(
        [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    )
    group_b = group_a + np.array([10.0, 0.0])
    df = pd.DataFrame(
        np.vstack([group_a, group_b]),
        columns=["F2", "F1"],
    )
    df["Label"] = ["a"] * len(group_a) + ["b"] * len(group_b)

    result = calculate_pairwise_mahalanobis_distances(df)

    cov_a = np.cov(group_a, rowvar=False, ddof=1)
    cov_b = np.cov(group_b, rowvar=False, ddof=1)
    pooled_cov = (
        (len(group_a) - 1) * cov_a + (len(group_b) - 1) * cov_b
    ) / (len(group_a) + len(group_b) - 2)
    mean_diff = group_a.mean(axis=0) - group_b.mean(axis=0)
    expected = float(
        np.sqrt(mean_diff.T @ np.linalg.pinv(pooled_cov) @ mean_diff)
    )

    assert math.isclose(
        result[("a", "b")]["distance"], expected, rel_tol=1e-12
    )
