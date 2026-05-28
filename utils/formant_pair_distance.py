"""
모음 무게중심 간 거리 문자열.

- 정규화: 플롯 좌표 기준 유클리드 거리
- 비정규화: Hz 기준 유클리드 거리 (기본), 필요 시 Bark 변환 후 거리
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from utils.math_utils import hz_to_bark


def compute_pair_distance(
    p1: Dict[str, Any],
    p2: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None,
    *,
    unit: str = "hz",
) -> float:
    """
    두 무게중심 간 유클리드 거리(숫자).

    정규화: p1/p2 에 x, y (플롯 좌표).
    비정규화: p1/p2 에 raw_f1(F1 Hz), raw_f2(X축 Hz 물리량).
    unit: 비정규화 시 "hz" | "bark".
    """
    params = params or {}
    if params.get("normalization"):
        d = np.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)
        return float(d) if not np.isnan(d) else float("nan")

    f1a, x_hz_a = p1["raw_f1"], p1["raw_f2"]
    f1b, x_hz_b = p2["raw_f1"], p2["raw_f2"]

    if unit == "bark":
        z1_f1, z1_x = hz_to_bark(f1a), hz_to_bark(x_hz_a)
        z2_f1, z2_x = hz_to_bark(f1b), hz_to_bark(x_hz_b)
        d = np.sqrt((z1_f1 - z2_f1) ** 2 + (z1_x - z2_x) ** 2)
    else:
        d = np.sqrt((f1a - f1b) ** 2 + (x_hz_a - x_hz_b) ** 2)

    return float(d) if not np.isnan(d) else float("nan")


def format_pair_distance(
    p1: Dict[str, Any],
    p2: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None,
    *,
    unit: Optional[str] = None,
) -> str:
    """
    정규화: p1/p2 에 x, y (플롯 좌표와 동일 척도).
    비정규화: p1/p2 에 raw_f1(F1 Hz), raw_f2(X축 Hz 물리량).
    params: fixed_plot_params 호환 (normalization, distance_unit 등).
    unit: 비정규화 표시 단위 ("hz" | "bark"). None이면 params.distance_unit 또는 hz.
    """
    params = params or {}
    if params.get("normalization"):
        d = compute_pair_distance(p1, p2, params)
        if np.isnan(d):
            return "—"
        return f"{d:.4g}"

    resolved_unit = unit or params.get("distance_unit", "hz")
    d = compute_pair_distance(p1, p2, params, unit=resolved_unit)
    if np.isnan(d):
        return "—"
    if resolved_unit == "bark":
        return f"{d:.2f}"
    return f"{d:.1f}"
