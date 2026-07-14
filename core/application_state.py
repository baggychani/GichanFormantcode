"""UI-independent application state contracts.

These values are intentionally plain Python data so a PySide view, a future
Tauri frontend, or a headless test can exchange the same state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import config
from core.plot_data_types import PlotParams


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

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> "AnalysisSettings":
        data = raw or {}
        return cls(
            plot_type=str(data.get("type") or data.get("plot_type") or "f1_f2"),
            f1_scale=str(data.get("f1_scale") or "linear"),
            f2_scale=str(data.get("f2_scale") or "bark"),
            origin=str(data.get("origin") or "top_right"),
            use_bark_units=bool(data.get("use_bark_units", False)),
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
