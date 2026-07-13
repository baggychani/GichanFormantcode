from __future__ import annotations

from core.design_defaults import (
    SINGLE_DESIGN_DEFAULTS as SINGLE_DESIGN_DEFAULTS,
    get_single_design_defaults as get_single_design_defaults,
)

# design_panel / layer_dock 공통 매핑
MARKER_IDS = {"o": 0, "s": 1, "^": 2, "D": 3, "wo": 4, "ws": 5, "w^": 6, "wD": 7}
MARKER_VALS = ["o", "s", "^", "D", "wo", "ws", "w^", "wD"]
MARKER_LABELS = {
    "o": "원",
    "s": "사각형",
    "^": "삼각형",
    "D": "다이아몬드",
    "wo": "원(흰색)",
    "ws": "사각형(흰색)",
    "w^": "삼각형(흰색)",
    "wD": "다이아몬드(흰색)",
}

THICK_IDS = {0.5: 0, 1.0: 1, 2.0: 2}
THICK_VALS = [0.5, 1.0, 2.0]
THICK_LABELS = {0.5: "얇게", 1.0: "보통", 2.0: "두껍게"}

STYLE_IDS = {"-": 0, "---": 1, "--": 2}
STYLE_VALS = ["-", "---", "--"]
STYLE_LABELS = {"-": "실선", "---": "긴 점선", "--": "짧은 점선"}
