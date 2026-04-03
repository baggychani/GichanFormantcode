"""
모음 무게중심 간 거리 문자열.

- 정규화: 플롯 좌표 기준 유클리드 거리
- 비정규화: Bark 기준 유클리드 거리
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from utils.math_utils import hz_to_bark


def format_pair_distance(
    p1: Dict[str, Any],
    p2: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None,
) -> str:
    """
    정규화: p1/p2 에 x, y (플롯 좌표와 동일 척도).
    비정규화: p1/p2 에 raw_f1(F1 Hz), raw_f2(X축 Hz 물리량).
    params: fixed_plot_params 호환 (normalization 등).
    """
    params = params or {}
    if params.get("normalization"):
        d = np.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)
        if np.isnan(d):
            return "—"
        return f"{d:.4g}"

    f1a, x_hz_a = p1["raw_f1"], p1["raw_f2"]
    f1b, x_hz_b = p2["raw_f1"], p2["raw_f2"]

    z1_f1, z1_x = hz_to_bark(f1a), hz_to_bark(x_hz_a)
    z2_f1, z2_x = hz_to_bark(f1b), hz_to_bark(x_hz_b)

    dist_bk = np.sqrt((z1_f1 - z2_f1) ** 2 + (z1_x - z2_x) ** 2)
    if np.isnan(dist_bk):
        return "—"
    return f"{dist_bk:.2f}"
