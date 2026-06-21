from __future__ import annotations

from copy import deepcopy

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

SINGLE_DESIGN_DEFAULTS = {
    "show_raw": True,
    "show_centroid": True,
    "raw_marker": "o",
    "raw_color": "#606060",
    "centroid_marker": "o",
    "lbl_color": "#FF0000",
    "lbl_size": 18,
    "lbl_bold": True,
    "lbl_italic": False,
    "ell_thick": 0.5,
    "ell_style": "-",
    "ell_color": "#606060",
    "ell_fill_color": None,
    "ell_fill_opacity": 0.15,
    "box_spines": False,
    "show_grid": False,
    "grid_opacity": 0.3,
    "y_label_rotation": False,
    "axis_position_swap": False,
    "show_axis_units": False,
    "show_minor_ticks": True,
    "font_style": "serif",
    "label_slash_wrap": False,
}


def get_single_design_defaults() -> dict:
    return deepcopy(SINGLE_DESIGN_DEFAULTS)
