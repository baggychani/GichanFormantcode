from __future__ import annotations

from core.compare_series import compare_draw_suffix
from ui.widgets.segmented_control import create_line_preview_button_group


COLOR_NAMES = {
    "#E64A19": "Red",
    "#F57C00": "Orange",
    "#FFEB3B": "Yellow",
    "#388E3C": "Green",
    "#00BCD4": "Cyan",
    "#1976D2": "Blue",
    "#7B1FA2": "Purple",
    "#E91E63": "Pink",
    "#606060": "Dark Gray",
    "#000000": "Black",
    "#AAAAAA": "Light Gray",
    "#795548": "Brown",
    "#009688": "Teal",
    "#FF9800": "Amber",
    "transparent": "Transparent",
    "custom": "Custom Color",
}


def _label_suffix_for_series(series) -> str | None:
    if series is None:
        return None
    try:
        return compare_draw_suffix(series)
    except (TypeError, ValueError):
        return None


def _normalize_compare_point_labels(labels, series) -> list[str]:
    suffix = _label_suffix_for_series(series)
    if not suffix:
        return labels
    normalized = []
    for label in labels:
        text = str(label).strip()
        if text in ("", "?"):
            normalized.append(text)
        elif text.endswith(suffix):
            normalized.append(text)
        elif len(text) >= 2 and text[-1].isdigit():
            normalized.append(text)
        else:
            normalized.append(f"{text}{suffix}")
    return normalized


def draw_object_display_name(draw_objects, index, normalization=None):
    """그리기 객체의 레이어 목록 표시명."""
    if not draw_objects or index < 0 or index >= len(draw_objects):
        return ""
    obj = draw_objects[index]
    obj_type = getattr(obj, "type", "")
    if obj_type == "legend":
        return getattr(obj, "name", None) or "범례"
    if obj_type == "text":
        n = 1 + sum(
            1 for i in range(index) if getattr(draw_objects[i], "type", "") == "text"
        )
        preview = str(getattr(obj, "text", "") or "").strip().split("\n", 1)[0]
        if len(preview) > 18:
            preview = preview[:17] + "..."
        suffix = f" : {preview}" if preview else ""
        return f"텍스트 {n}{suffix}"
    if obj_type == "line":
        n = 1 + sum(
            1 for i in range(index) if getattr(draw_objects[i], "type", "") == "line"
        )
        labels = getattr(obj, "point_labels", None) or []
        labels = _normalize_compare_point_labels(labels, getattr(obj, "series", None))
        suffix = " : " + "-".join(labels) if labels else ""
        return f"선 {n}{suffix}"
    if obj_type == "polygon":
        n = 1 + sum(
            1 for i in range(index) if getattr(draw_objects[i], "type", "") == "polygon"
        )
        labels = getattr(obj, "point_labels", None) or []
        labels = _normalize_compare_point_labels(labels, getattr(obj, "series", None))
        if labels:
            suffix = " : " + "-".join(labels) + "-" + labels[0]
        else:
            suffix = ""
        return f"영역 {n}{suffix}"
    if obj_type == "reference":
        value = getattr(obj, "value", 0)
        axis_name = getattr(obj, "axis_name", None) or ""
        unit = (getattr(obj, "axis_units", "Hz") or "Hz").strip().lower()
        is_norm = unit == "norm" or "norm" in unit
        if not axis_name and getattr(obj, "mode", "") == "horizontal":
            axis_name = "nF1" if is_norm else "F1"
        if not axis_name:
            axis_name = "nF2" if is_norm else "F2"
        if unit == "norm" or "norm" in unit:
            if "gerstman" in str(normalization or "").strip().lower():
                rendered_value = f"{int(round(float(value)))}"
            else:
                rendered_value = f"{value:.2f}"
        elif unit in ("bk", "bark"):
            rendered_value = f"{value:.1f}"
        else:
            rendered_value = str(int(value))
        return f"참조선 : {axis_name}={rendered_value}"
    if obj_type == "area_label":
        value = getattr(obj, "value", 0)
        unit = (getattr(obj, "axis_units", "Hz") or "Hz").strip().lower()
        if unit == "norm" or "norm" in unit:
            rendered_value = f"{value:.2f}"
        else:
            rendered_value = str(int(round(value)))
        return f"넓이 : {rendered_value}"
    return f"그리기 {index + 1}"


def format_color_display(color_hex):
    if not color_hex or color_hex == "transparent":
        return "Transparent"
    key = color_hex if color_hex in COLOR_NAMES else color_hex.upper()
    name = COLOR_NAMES.get(key, "Custom Color")
    if name == "Custom Color":
        return f"Custom ({color_hex})"
    return f"{name} ({color_hex})"


def create_visual_button_group(parent, options, default_idx):
    return create_line_preview_button_group(parent, options, default_idx)
