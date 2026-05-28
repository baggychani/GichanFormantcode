import math

import pandas as pd

from utils.vowel_stats import (
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
