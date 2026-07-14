"""Canonical state and validation for the interactive single-plot editor."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
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
        elif key == "ell_thick":
            value = _finite_number(value, "design.ell_thick", 0.1, 12)
        elif key in {"ell_fill_opacity", "grid_opacity"}:
            value = _finite_number(value, f"design.{key}", 0, 1)
        elif key == "ell_style":
            if value not in {"-", "--", ":", "-."}:
                raise InteractiveOptionsError("unsupported ellipse line style")
        elif key == "font_style":
            if value not in {"serif", "sans"}:
                raise InteractiveOptionsError("unsupported font style")
        result[str(key)] = value
    if partial:
        return result
    merged = get_single_design_defaults()
    merged.update(result)
    return merged


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
        self.revision += 1

    def remove_file(self, removed_idx: int) -> None:
        """Drop a removed source and keep index-keyed state aligned."""
        for mapping in (
            self.vowel_filter_state_by_file,
            self.layer_design_overrides_by_file,
            self.layer_locked_vowels_by_file,
            self.layer_order_by_file,
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
            draw_objects_by_file=indexed("draw_objects_by_file"),
        )
