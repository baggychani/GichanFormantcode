import math

import numpy as np

from utils.formant_pair_distance import compute_pair_distance, format_pair_distance
from utils.math_utils import hz_to_bark


def _hz_centroid(f1, x_hz):
    return {"raw_f1": f1, "raw_f2": x_hz}


def test_non_normalized_hz_euclidean():
    p1 = _hz_centroid(500.0, 1500.0)
    p2 = _hz_centroid(600.0, 1600.0)
    d = compute_pair_distance(p1, p2, {}, unit="hz")
    expected = math.sqrt(100**2 + 100**2)
    assert abs(d - expected) < 1e-6
    assert format_pair_distance(p1, p2, {}, unit="hz") == f"{expected:.1f}"


def test_non_normalized_bark_euclidean():
    p1 = _hz_centroid(500.0, 1500.0)
    p2 = _hz_centroid(600.0, 1600.0)
    z1_f1, z1_x = hz_to_bark(500.0), hz_to_bark(1500.0)
    z2_f1, z2_x = hz_to_bark(600.0), hz_to_bark(1600.0)
    expected = math.sqrt((z1_f1 - z2_f1) ** 2 + (z1_x - z2_x) ** 2)
    d = compute_pair_distance(p1, p2, {}, unit="bark")
    assert abs(d - expected) < 1e-6
    assert format_pair_distance(p1, p2, {}, unit="bark") == f"{expected:.2f}"


def test_normalized_uses_plot_coordinates():
    p1 = {"x": 0.0, "y": 0.0}
    p2 = {"x": 3.0, "y": 4.0}
    params = {"normalization": "Lobanov"}
    d = compute_pair_distance(p1, p2, params)
    assert abs(d - 5.0) < 1e-9
    assert format_pair_distance(p1, p2, params) == "5"


def test_default_non_normalized_is_hz():
    p1 = _hz_centroid(400.0, 1200.0)
    p2 = _hz_centroid(500.0, 1300.0)
    d_default = compute_pair_distance(p1, p2, {})
    d_hz = compute_pair_distance(p1, p2, {}, unit="hz")
    assert d_default == d_hz


def test_nan_returns_dash():
    p1 = {"raw_f1": np.nan, "raw_f2": 1500.0}
    p2 = _hz_centroid(600.0, 1600.0)
    assert format_pair_distance(p1, p2, {}, unit="hz") == "—"
