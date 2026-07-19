"""Canonical state and validation for the interactive single-plot editor."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, is_dataclass
import math
import re
from typing import Any, Mapping

from core.design_defaults import get_single_design_defaults


DESIGN_KEYS = frozenset(get_single_design_defaults())
_BOOL_DESIGN_KEYS = {
    "show_raw",
    "show_centroid",
    "lbl_bold",
    "lbl_italic",
    "box_spines",
    "show_grid",
    "y_label_rotation",
    "axis_position_swap",
    "show_axis_units",
    "show_minor_ticks",
    "label_slash_wrap",
}
_COLOR_KEYS = {"raw_color", "lbl_color", "ell_color", "ell_fill_color"}
_MARKER_KEYS = {"raw_marker", "centroid_marker"}
_ALLOWED_MARKERS = {"o", "s", "^", "D", "wo", "ws", "x", "a"}
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_RANGE_KEYS = ("y_min", "y_max", "x_min", "x_max")
_VISIBILITY = {"ON", "SEMI", "OFF"}
_DRAW_LINE_STYLES = {"-", "--", ":", "-."}
_DRAW_ARROW_MODES = {"none", "end", "all"}
_DRAW_ARROW_HEADS = {"stealth", "open", "latex"}
_DRAW_BORDER_STYLES = {"-", "--", ":", "-."}
_DRAW_FONT_FAMILIES = {"Noto Sans KR", "Noto Serif KR", "Charis SIL", "Andika"}
_DRAW_FONT_WEIGHTS = {"regular", "medium", "semibold", "bold"}


class InteractiveOptionsError(ValueError):
    """Raised when untrusted interactive plot options are malformed."""


def _finite_number(value: Any, name: str, low: float, high: float) -> float:
    if isinstance(value, bool):
        raise InteractiveOptionsError(f"{name} must be a number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InteractiveOptionsError(f"{name} must be a number") from exc
    if not math.isfinite(number) or not low <= number <= high:
        raise InteractiveOptionsError(f"{name} must be between {low:g} and {high:g}")
    return number


def _validate_design(raw: Any, *, partial: bool) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise InteractiveOptionsError("design must be an object")
    unknown = set(raw) - DESIGN_KEYS
    if unknown:
        raise InteractiveOptionsError(
            f"unknown design option(s): {', '.join(sorted(map(str, unknown)))}"
        )
    result: dict[str, Any] = {}
    for key, value in raw.items():
        if key in _BOOL_DESIGN_KEYS:
            if not isinstance(value, bool):
                raise InteractiveOptionsError(f"design.{key} must be a boolean")
        elif key in _COLOR_KEYS:
            if value is not None and (
                not isinstance(value, str) or not _HEX_COLOR.fullmatch(value)
            ):
                raise InteractiveOptionsError(f"design.{key} must be a hex color")
            if key in {"raw_color", "lbl_color"} and value is None:
                raise InteractiveOptionsError(f"design.{key} cannot be transparent")
        elif key in _MARKER_KEYS:
            if value not in _ALLOWED_MARKERS:
                raise InteractiveOptionsError(f"unsupported marker for design.{key}")
        elif key == "lbl_size":
            value = int(_finite_number(value, "design.lbl_size", 6, 96))
        elif key == "tick_label_size":
            value = int(_finite_number(value, "design.tick_label_size", 6, 48))
        elif key == "ell_thick":
            value = _finite_number(value, "design.ell_thick", 0.1, 12)
        elif key in {"ell_fill_opacity", "grid_opacity"}:
            value = _finite_number(value, f"design.{key}", 0, 1)
        elif key == "ell_style":
            # PySide STYLE_VALS: '-' 실선, '---' 긴 점선, '--' 짧은 점선 (: 하위호환)
            if value not in {"-", "--", "---", ":", "-."}:
                raise InteractiveOptionsError("unsupported ellipse line style")
        elif key == "font_style":
            if value not in {"serif", "sans"}:
                raise InteractiveOptionsError("unsupported font style")
        elif key == "font_family":
            if value not in {"Noto Sans KR", "Noto Serif KR", "Charis SIL", "Andika"}:
                raise InteractiveOptionsError("unsupported font family")
        elif key == "font_weight":
            if value not in {"regular", "medium", "semibold", "bold"}:
                raise InteractiveOptionsError("unsupported font weight")
        result[str(key)] = value
    if partial:
        return result
    merged = get_single_design_defaults()
    merged.update(result)
    return merged


def _validate_draw_objects(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) > 512:
        raise InteractiveOptionsError("draw_objects must be an array with at most 512 items")
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise InteractiveOptionsError("draw objects must be objects")
        object_type = item.get("type", "line")
        if object_type == "legend":
            entries = item.get("entries", [])
            if not isinstance(entries, list) or len(entries) > 128:
                raise InteractiveOptionsError("a legend must contain at most 128 entries")
            normalized_entries = []
            for entry in entries:
                if not isinstance(entry, Mapping):
                    raise InteractiveOptionsError("legend entries must be objects")
                series_id = int(_finite_number(entry.get("series_id", 0), "legend.series_id", 0, 512))
                text = str(entry.get("text", ""))
                if len(text) > 512:
                    raise InteractiveOptionsError("legend entry text is too long")
                normalized_entries.append({"series_id": series_id, "text": text})
            colors = {}
            for key, default in (("border_color", "#3f4650"), ("fill_color", "#ffffff")):
                value = item.get(key, default)
                if not isinstance(value, str) or not _HEX_COLOR.fullmatch(value):
                    raise InteractiveOptionsError(f"legend.{key} must be a hex color")
                colors[key] = value
            border_style = item.get("border_style", "-")
            if border_style not in _DRAW_BORDER_STYLES:
                raise InteractiveOptionsError("unsupported legend border style")
            font_family = item.get("font_family", "Noto Sans KR")
            if font_family not in _DRAW_FONT_FAMILIES:
                raise InteractiveOptionsError("unsupported legend font family")
            font_weight = item.get("font_weight", "regular")
            if font_weight not in _DRAW_FONT_WEIGHTS:
                raise InteractiveOptionsError("unsupported legend font weight")
            result.append({
                "type": "legend",
                "id": str(item.get("id", ""))[:64],
                "name": str(item.get("name", "범례"))[:128],
                "entries": normalized_entries,
                "fx": _finite_number(item.get("fx", 0.016), "legend.fx", 0, 1),
                "fy": _finite_number(item.get("fy", 0.20), "legend.fy", 0, 1),
                "width_frac": _finite_number(item.get("width_frac", 0.30), "legend.width_frac", 0.05, 0.92),
                "height_frac": _finite_number(item.get("height_frac", 0.14), "legend.height_frac", 0.028, 0.92),
                "font_size": _finite_number(item.get("font_size", 10), "legend.font_size", 6, 20),
                "show_border": bool(item.get("show_border", True)),
                "border_style": border_style,
                "border_color": colors["border_color"],
                "show_fill": bool(item.get("show_fill", True)),
                "fill_color": colors["fill_color"],
                "fill_opacity": _finite_number(item.get("fill_opacity", 1), "legend.fill_opacity", 0, 1),
                "font_family": font_family,
                "font_weight": font_weight,
                "font_italic": bool(item.get("font_italic", False)),
                "visible": bool(item.get("visible", True)),
                "semi": bool(item.get("semi", False)),
            })
            continue
        if object_type == "reference":
            mode = item.get("mode", "horizontal")
            if mode not in {"horizontal", "vertical"}:
                raise InteractiveOptionsError("unsupported reference mode")
            axis_scale = str(item.get("axis_scale", "linear") or "linear")
            if axis_scale not in {"linear", "log", "bark"}:
                raise InteractiveOptionsError("unsupported reference axis_scale")
            axis_units = str(item.get("axis_units", "Hz") or "Hz")[:32]
            axis_name = str(item.get("axis_name", "") or "")[:64]
            line_color = item.get("line_color")
            if line_color is not None and (not isinstance(line_color, str) or not _HEX_COLOR.fullmatch(line_color)):
                raise InteractiveOptionsError("reference.line_color must be a hex color")
            line_style = item.get("line_style", "-")
            if line_style not in _DRAW_LINE_STYLES:
                raise InteractiveOptionsError("unsupported reference line style")
            result.append({
                "type": "reference",
                "id": str(item.get("id", ""))[:64],
                "mode": mode,
                "value": _finite_number(item.get("value", 0), "reference.value", -1_000_000, 1_000_000),
                "axis_units": axis_units,
                "axis_name": axis_name,
                "axis_scale": axis_scale,
                "line_style": line_style,
                "line_color": line_color,
                "semi": bool(item.get("semi", False)),
                "visible": bool(item.get("visible", True)),
            })
            continue
        if object_type == "polygon":
            points = item.get("points")
            if not isinstance(points, list) or not 3 <= len(points) <= 128:
                raise InteractiveOptionsError("a polygon must contain between 3 and 128 points")
            normalized_points = []
            for point in points:
                if not isinstance(point, (list, tuple)) or len(point) != 2:
                    raise InteractiveOptionsError("draw polygon points must contain x and y")
                normalized_points.append([
                    _finite_number(point[0], "draw_objects.points.x", -1_000_000, 1_000_000),
                    _finite_number(point[1], "draw_objects.points.y", -1_000_000, 1_000_000),
                ])
            border_color = item.get("border_color", "#000000")
            if not isinstance(border_color, str) or not _HEX_COLOR.fullmatch(border_color):
                raise InteractiveOptionsError("polygon.border_color must be a hex color")
            fill_color = item.get("fill_color", "#3366CC")
            if fill_color is not None:
                if not isinstance(fill_color, str):
                    raise InteractiveOptionsError("polygon.fill_color must be a hex color or transparent")
                if fill_color.lower() != "transparent" and not _HEX_COLOR.fullmatch(fill_color):
                    raise InteractiveOptionsError("polygon.fill_color must be a hex color or transparent")
            border_style = item.get("border_style", "-")
            if border_style not in _DRAW_BORDER_STYLES:
                raise InteractiveOptionsError("unsupported polygon border style")
            result.append({
                "type": "polygon",
                "id": str(item.get("id", ""))[:64],
                "points": normalized_points,
                "border_style": border_style,
                "border_color": border_color,
                "fill_color": fill_color,
                "fill_opacity": _finite_number(item.get("fill_opacity", 0.15), "polygon.fill_opacity", 0, 1),
                "show_area_label": bool(item.get("show_area_label", False)),
                "semi": bool(item.get("semi", False)),
                "visible": bool(item.get("visible", True)),
            })
            continue
        if object_type == "text":
            text = str(item.get("text", ""))
            if len(text) > 4096:
                raise InteractiveOptionsError("draw text is too long")
            if not text.strip():
                raise InteractiveOptionsError("draw text must not be empty")
            text_color = item.get("text_color", "#303133")
            if not isinstance(text_color, str) or not _HEX_COLOR.fullmatch(text_color):
                raise InteractiveOptionsError("text.text_color must be a hex color")
            font_family = item.get("font_family", "Noto Sans KR")
            if font_family not in _DRAW_FONT_FAMILIES:
                raise InteractiveOptionsError("unsupported text font family")
            font_weight = item.get("font_weight")
            if font_weight is None:
                font_weight = "bold" if item.get("font_bold", False) else "regular"
            if font_weight not in _DRAW_FONT_WEIGHTS:
                raise InteractiveOptionsError("unsupported text font weight")
            axis_units = str(item.get("axis_units", "Hz") or "Hz")[:32]
            result.append({
                "type": "text",
                "id": str(item.get("id", ""))[:64],
                "name": str(item.get("name", ""))[:128],
                "text": text,
                "x": _finite_number(item.get("x", 0), "text.x", -1_000_000, 1_000_000),
                "y": _finite_number(item.get("y", 0), "text.y", -1_000_000, 1_000_000),
                "font_size": _finite_number(item.get("font_size", 13), "text.font_size", 4, 32),
                "font_family": font_family,
                "font_weight": font_weight,
                "font_bold": font_weight in {"bold", "semibold"} or bool(item.get("font_bold", False)),
                "font_italic": bool(item.get("font_italic", False)),
                "line_spacing": _finite_number(item.get("line_spacing", 1.15), "text.line_spacing", 0.8, 2.5),
                "text_color": text_color,
                "axis_units": axis_units,
                "semi": bool(item.get("semi", False)),
                "visible": bool(item.get("visible", True)),
            })
            continue
        if object_type != "line":
            raise InteractiveOptionsError("unsupported draw object type")
        points = item.get("points")
        if not isinstance(points, list) or not 2 <= len(points) <= 128:
            raise InteractiveOptionsError("a line must contain between 2 and 128 points")
        normalized_points = []
        for point in points:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise InteractiveOptionsError("draw line points must contain x and y")
            normalized_points.append([
                _finite_number(point[0], "draw_objects.points.x", -1_000_000, 1_000_000),
                _finite_number(point[1], "draw_objects.points.y", -1_000_000, 1_000_000),
            ])
        color = item.get("line_color", "#2563eb")
        if not isinstance(color, str) or not _HEX_COLOR.fullmatch(color):
            raise InteractiveOptionsError("draw_objects.line_color must be a hex color")
        style = item.get("line_style", "-")
        if style not in _DRAW_LINE_STYLES:
            raise InteractiveOptionsError("unsupported draw line style")
        arrow_mode = item.get("arrow_mode", "none")
        if arrow_mode not in _DRAW_ARROW_MODES:
            raise InteractiveOptionsError("unsupported draw arrow mode")
        arrow_head = item.get("arrow_head", "stealth")
        if arrow_head not in _DRAW_ARROW_HEADS:
            raise InteractiveOptionsError("unsupported draw arrow head")
        result.append({
            "type": "line",
            "id": str(item.get("id", ""))[:64],
            "points": normalized_points,
            "line_color": color,
            "line_style": style,
            "line_width": _finite_number(item.get("line_width", 0.5), "draw_objects.line_width", 0.25, 3),
            "arrow_mode": arrow_mode,
            "arrow_head": arrow_head,
            "semi": bool(item.get("semi", False)),
            "visible": bool(item.get("visible", True)),
        })
    return result


def validate_interactive_options(raw: Any) -> dict[str, Any]:
    """Return a normalized, JSON-safe interactive render/session payload."""
    if not isinstance(raw, Mapping):
        raise InteractiveOptionsError("interactive options must be an object")
    allowed = {
        "request_id",
        "ranges",
        "sigma",
        "show_ellipse",
        "design",
        "filter_state",
        "layer_overrides",
        "layer_order",
        "locked_layers",
        "label_offsets",
        "draw_objects",
        "batch_options",
    }
    unknown = set(raw) - allowed
    if unknown:
        raise InteractiveOptionsError(
            f"unknown interactive option(s): {', '.join(sorted(map(str, unknown)))}"
        )
    result: dict[str, Any] = {}
    request_id = raw.get("request_id")
    if request_id is not None:
        if isinstance(request_id, bool) or not isinstance(request_id, (str, int)):
            raise InteractiveOptionsError("request_id must be a string or integer")
        if len(str(request_id)) > 128:
            raise InteractiveOptionsError("request_id is too long")
        result["request_id"] = request_id

    if "ranges" in raw:
        ranges = raw["ranges"]
        if not isinstance(ranges, Mapping):
            raise InteractiveOptionsError("ranges must be an object")
        unknown_ranges = set(ranges) - set(_RANGE_KEYS)
        if unknown_ranges:
            raise InteractiveOptionsError("ranges contains unknown axes")
        normalized_ranges = {
            key: f"{_finite_number(value, f'ranges.{key}', -1_000_000, 1_000_000):g}"
            for key, value in ranges.items()
            if value not in (None, "")
        }
        for low_key, high_key in (("y_min", "y_max"), ("x_min", "x_max")):
            if low_key in normalized_ranges and high_key in normalized_ranges:
                if float(normalized_ranges[low_key]) >= float(normalized_ranges[high_key]):
                    raise InteractiveOptionsError(f"{low_key} must be less than {high_key}")
        result["ranges"] = normalized_ranges

    if "sigma" in raw:
        result["sigma"] = f"{_finite_number(raw['sigma'], 'sigma', 0.1, 10):g}"
    if "show_ellipse" in raw:
        if not isinstance(raw["show_ellipse"], bool):
            raise InteractiveOptionsError("show_ellipse must be a boolean")
        result["show_ellipse"] = raw["show_ellipse"]
    if "design" in raw:
        result["design"] = _validate_design(raw["design"], partial=True)

    if "filter_state" in raw:
        filters = raw["filter_state"]
        if not isinstance(filters, Mapping):
            raise InteractiveOptionsError("filter_state must be an object")
        if len(filters) > 512:
            raise InteractiveOptionsError("filter_state has too many layers")
        normalized_filters = {}
        for name, value in filters.items():
            if not isinstance(name, str) or not name or len(name) > 128:
                raise InteractiveOptionsError("invalid filter layer name")
            if value not in _VISIBILITY:
                raise InteractiveOptionsError(f"invalid visibility for layer {name!r}")
            normalized_filters[name] = value
        result["filter_state"] = normalized_filters

    if "layer_overrides" in raw:
        overrides = raw["layer_overrides"]
        if not isinstance(overrides, Mapping):
            raise InteractiveOptionsError("layer_overrides must be an object")
        if len(overrides) > 512:
            raise InteractiveOptionsError("layer_overrides has too many layers")
        result["layer_overrides"] = {
            str(name): _validate_design(values, partial=True)
            for name, values in overrides.items()
            if isinstance(name, str) and name and len(name) <= 128
        }
        if len(result["layer_overrides"]) != len(overrides):
            raise InteractiveOptionsError("invalid layer override name")

    for key in ("layer_order", "locked_layers"):
        if key not in raw:
            continue
        values = raw[key]
        if not isinstance(values, list) or not all(
            isinstance(value, str) and value and len(value) <= 128 for value in values
        ):
            raise InteractiveOptionsError(f"{key} must be an array of layer names")
        if len(values) > 512 or len(set(values)) != len(values):
            raise InteractiveOptionsError(f"{key} contains duplicate or excessive layers")
        result[key] = list(values)
    if "label_offsets" in raw:
        offsets = raw["label_offsets"]
        if not isinstance(offsets, Mapping) or len(offsets) > 512:
            raise InteractiveOptionsError("label_offsets must be an object")
        normalized_offsets: dict[str, tuple[float, float]] = {}
        for vowel, value in offsets.items():
            if not isinstance(vowel, str) or not vowel or len(vowel) > 128:
                raise InteractiveOptionsError("invalid label offset name")
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise InteractiveOptionsError("label offset must contain x and y")
            normalized_offsets[vowel] = (
                _finite_number(value[0], f"label_offsets.{vowel}.x", -1_000_000, 1_000_000),
                _finite_number(value[1], f"label_offsets.{vowel}.y", -1_000_000, 1_000_000),
            )
        result["label_offsets"] = normalized_offsets
    if "draw_objects" in raw:
        result["draw_objects"] = _validate_draw_objects(raw["draw_objects"])
    if "batch_options" in raw:
        batch = raw["batch_options"]
        allowed_batch = {"apply_global_design", "apply_layer_design", "apply_layer_visibility", "apply_label_positions"}
        if not isinstance(batch, Mapping) or set(batch) - allowed_batch:
            raise InteractiveOptionsError("invalid batch options")
        if not all(isinstance(value, bool) for value in batch.values()):
            raise InteractiveOptionsError("batch options must be boolean")
        result["batch_options"] = {str(key): bool(value) for key, value in batch.items()}
    return result


@dataclass(slots=True)
class PlotSessionState:
    """UI-independent single-plot state shared by React, PySide, and projects."""

    revision: int = 0
    active: bool = False
    current_idx: int = 0
    fixed_plot_params: dict[str, Any] = field(default_factory=dict)
    ranges: dict[str, str] = field(default_factory=dict)
    sigma: str = "2"
    show_ellipse: bool = True
    design_settings: dict[str, Any] = field(default_factory=get_single_design_defaults)
    vowel_filter_state_by_file: dict[int, dict[str, str]] = field(default_factory=dict)
    layer_design_overrides_by_file: dict[int, dict[str, dict[str, Any]]] = field(
        default_factory=dict
    )
    layer_locked_vowels_by_file: dict[int, list[str]] = field(default_factory=dict)
    layer_order_by_file: dict[int, list[str]] = field(default_factory=dict)
    label_offsets_by_file: dict[int, dict[str, tuple[float, float]]] = field(default_factory=dict)
    draw_objects_by_file: dict[int, list[Any]] = field(default_factory=dict)

    def apply(self, options: Mapping[str, Any], current_idx: int) -> None:
        self.active = True
        self.current_idx = int(current_idx)
        if "ranges" in options:
            self.ranges.update(dict(options["ranges"]))
        if "sigma" in options:
            self.sigma = str(options["sigma"])
        if "show_ellipse" in options:
            self.show_ellipse = bool(options["show_ellipse"])
        if "design" in options:
            self.design_settings.update(dict(options["design"]))
        if "filter_state" in options:
            self.vowel_filter_state_by_file[self.current_idx] = dict(
                options["filter_state"]
            )
        if "layer_overrides" in options:
            self.layer_design_overrides_by_file[self.current_idx] = deepcopy(
                options["layer_overrides"]
            )
        if "locked_layers" in options:
            self.layer_locked_vowels_by_file[self.current_idx] = list(
                options["locked_layers"]
            )
        if "layer_order" in options:
            self.layer_order_by_file[self.current_idx] = list(options["layer_order"])
        if "label_offsets" in options:
            self.label_offsets_by_file[self.current_idx] = {
                **self.label_offsets_by_file.get(self.current_idx, {}),
                **dict(options["label_offsets"]),
            }
        if "draw_objects" in options:
            self.draw_objects_by_file[self.current_idx] = deepcopy(options["draw_objects"])
        self.revision += 1

    def remove_file(self, removed_idx: int) -> None:
        """Drop a removed source and keep index-keyed state aligned."""
        for mapping in (
            self.vowel_filter_state_by_file,
            self.layer_design_overrides_by_file,
            self.layer_locked_vowels_by_file,
            self.layer_order_by_file,
            self.label_offsets_by_file,
            self.draw_objects_by_file,
        ):
            remapped = {
                (index - 1 if index > removed_idx else index): value
                for index, value in mapping.items()
                if index != removed_idx
            }
            mapping.clear()
            mapping.update(remapped)
        if self.current_idx > removed_idx:
            self.current_idx -= 1
        elif self.current_idx == removed_idx:
            self.current_idx = max(0, self.current_idx - 1)
        self.revision += 1

    def to_public_dict(self) -> dict[str, Any]:
        draw_objects = {
            str(index): [asdict(obj) if is_dataclass(obj) else deepcopy(obj) for obj in objects]
            for index, objects in self.draw_objects_by_file.items()
        }
        return {
            "revision": self.revision,
            "active": self.active,
            "current_idx": self.current_idx,
            "ranges": dict(self.ranges),
            "sigma": self.sigma,
            "show_ellipse": self.show_ellipse,
            "design_settings": deepcopy(self.design_settings),
            "vowel_filter_state_by_file": deepcopy(self.vowel_filter_state_by_file),
            "layer_design_overrides_by_file": deepcopy(
                self.layer_design_overrides_by_file
            ),
            "layer_locked_vowels_by_file": deepcopy(
                self.layer_locked_vowels_by_file
            ),
            "layer_order_by_file": deepcopy(self.layer_order_by_file),
            "label_offsets_by_file": deepcopy(self.label_offsets_by_file),
            "draw_objects_by_file": draw_objects,
        }

    def to_project_dict(self) -> dict[str, Any]:
        result = self.to_public_dict()
        result.update(
            {
                "fixed_plot_params": deepcopy(self.fixed_plot_params),
                "layer_order": list(
                    self.layer_order_by_file.get(self.current_idx, [])
                ),
                "draw_objects_by_file": deepcopy(self.draw_objects_by_file),
            }
        )
        return result

    @classmethod
    def from_project_dict(cls, raw: Mapping[str, Any] | None) -> "PlotSessionState":
        if not isinstance(raw, Mapping):
            return cls()
        current_idx = int(raw.get("current_idx", 0))

        def indexed(name: str) -> dict[int, Any]:
            values = raw.get(name) or {}
            return {int(key): deepcopy(value) for key, value in values.items()}

        orders = indexed("layer_order_by_file")
        label_offsets = {
            index: {
                str(vowel): (float(value[0]), float(value[1]))
                for vowel, value in offsets.items()
                if isinstance(value, (list, tuple)) and len(value) == 2
            }
            for index, offsets in indexed("label_offsets_by_file").items()
            if isinstance(offsets, Mapping)
        }
        if not orders and raw.get("layer_order"):
            orders[current_idx] = list(raw["layer_order"])
        design = get_single_design_defaults()
        design.update(dict(raw.get("design_settings") or {}))
        return cls(
            revision=int(raw.get("revision", 0)),
            active=bool(raw.get("active", True)),
            current_idx=current_idx,
            fixed_plot_params=dict(raw.get("fixed_plot_params") or {}),
            ranges={str(k): str(v) for k, v in (raw.get("ranges") or {}).items()},
            sigma=str(raw.get("sigma", "2")),
            show_ellipse=bool(raw.get("show_ellipse", True)),
            design_settings=design,
            vowel_filter_state_by_file=indexed("vowel_filter_state_by_file"),
            layer_design_overrides_by_file=indexed(
                "layer_design_overrides_by_file"
            ),
            layer_locked_vowels_by_file=indexed("layer_locked_vowels_by_file"),
            layer_order_by_file=orders,
            label_offsets_by_file=label_offsets,
            draw_objects_by_file=indexed("draw_objects_by_file"),
        )
