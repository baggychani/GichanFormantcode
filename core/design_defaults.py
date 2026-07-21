"""Canonical UI-independent defaults for single plots."""

from copy import deepcopy

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
    "font_family": "Noto Serif KR",
    "font_weight": "bold",
    "label_slash_wrap": False,
    "tick_label_size": 12,
}


def get_single_design_defaults() -> dict:
    return deepcopy(SINGLE_DESIGN_DEFAULTS)
