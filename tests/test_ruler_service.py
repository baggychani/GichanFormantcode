from __future__ import annotations

import math

import pytest

from core.ruler_service import measure_distance


def test_measure_distance_returns_geometry_for_ruler_overlay():
    result = measure_distance(1.0, 2.0, 4.0, 6.0)

    assert result["dx"] == 3.0
    assert result["dy"] == 4.0
    assert result["distance"] == 5.0
    assert result["angle_degrees"] == pytest.approx(math.degrees(math.atan2(4, 3)))


def test_measure_distance_rejects_non_finite_coordinates():
    with pytest.raises(ValueError, match="finite"):
        measure_distance(float("nan"), 0.0, 1.0, 1.0)
