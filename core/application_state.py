"""UI-independent application state contracts.

These values are intentionally plain Python data so a PySide view, a future
Tauri frontend, or a headless test can exchange the same state.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import config
from core.plot_data_types import PlotParams

_SCALE_VALUES = frozenset({"linear", "log", "bark"})
_ORIGIN_VALUES = frozenset({"top_right", "bottom_left"})
_OUTLIER_MODE_VALUES = frozenset(
    {None, *(value for _label, value in config.OUTLIER_SIGMA_OPTIONS)}
)
_OUTLIER_SCOPE_VALUES = frozenset(
    {None, *(value for _label, value in config.OUTLIER_SCOPE_OPTIONS)}
)
_NORMALIZATION_VALUES = frozenset(
    value for _label, value in config.NORMALIZATION_OPTIONS
)


def _validate_choice(name: str, value: Any, allowed: frozenset[Any]) -> None:
    try:
        valid = value in allowed
    except TypeError:
        valid = False
    if not valid:
        choices = ", ".join(repr(item) for item in sorted(allowed, key=str))
        raise ValueError(f"invalid {name} {value!r}; expected one of: {choices}")


@dataclass(frozen=True, slots=True)
class AnalysisSettings:
    """Analysis controls shown by the main window."""

    plot_type: str = "f1_f2"
    f1_scale: str = "linear"
    f2_scale: str = "bark"
    origin: str = "top_right"
    # The Bark axis scale is independent from the displayed unit.  Keep the
    # latter in Hz until the user explicitly enables the unit switch.
    use_bark_units: bool = False
    outlier_mode: str | None = None
    outlier_scope: str | None = None
    normalization: str | None = None

    def __post_init__(self) -> None:
        _validate_choice("plot type", self.plot_type, config.PLOT_TYPE_IDS)
        _validate_choice("F1 scale", self.f1_scale, _SCALE_VALUES)
        _validate_choice("F2 scale", self.f2_scale, _SCALE_VALUES)
        _validate_choice("origin", self.origin, _ORIGIN_VALUES)
        if not isinstance(self.use_bark_units, bool):
            raise TypeError("use_bark_units must be a boolean")
        _validate_choice("outlier mode", self.outlier_mode, _OUTLIER_MODE_VALUES)
        _validate_choice("outlier scope", self.outlier_scope, _OUTLIER_SCOPE_VALUES)
        _validate_choice("normalization", self.normalization, _NORMALIZATION_VALUES)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> AnalysisSettings:
        if raw is not None and not isinstance(raw, Mapping):
            raise TypeError("analysis settings must be an object")
        data = raw or {}
        return cls(
            plot_type=str(data.get("type") or data.get("plot_type") or "f1_f2"),
            f1_scale=str(data.get("f1_scale") or "linear"),
            f2_scale=str(data.get("f2_scale") or "bark"),
            origin=str(data.get("origin") or "top_right"),
            use_bark_units=data.get("use_bark_units", False),
            outlier_mode=data.get("outlier_mode"),
            outlier_scope=data.get("outlier_scope"),
            normalization=data.get("normalization"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.plot_type,
            "f1_scale": self.f1_scale,
            "f2_scale": self.f2_scale,
            "origin": self.origin,
            "use_bark_units": self.use_bark_units,
            "outlier_mode": self.outlier_mode,
            "outlier_scope": self.outlier_scope,
            "normalization": self.normalization,
        }

    def to_plot_params(self) -> PlotParams:
        f1_unit = "Bark" if self.f1_scale == "bark" and self.use_bark_units else "Hz"
        f2_unit = "Bark" if self.f2_scale == "bark" and self.use_bark_units else "Hz"
        return {
            "type": self.plot_type,
            "f1_scale": self.f1_scale,
            "f2_scale": self.f2_scale,
            "f1_unit": f1_unit,
            "f2_unit": f2_unit,
            "origin": self.origin,
            "use_bark_units": self.use_bark_units,
            "sigma": config.DEFAULT_SIGMA,
            "normalization": self.normalization,
        }
