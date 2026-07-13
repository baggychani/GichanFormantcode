"""Mutable workspace state with no presentation-framework dependency."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.plot_data_types import PlotDataItem


@dataclass(slots=True)
class WorkspaceState:
    filepaths: list[str] = field(default_factory=list)
    plot_data_list: list[PlotDataItem] = field(default_factory=list)
    current_idx: int = 0
    last_outlier_mode: str | None = None
    last_save_dir: str | None = None
    last_open_dir: str | None = None
    custom_label_offsets: dict[Any, dict[str, tuple[float, float]]] = field(
        default_factory=dict
    )

    def clear_data(self) -> None:
        self.filepaths.clear()
        self.plot_data_list.clear()
        self.current_idx = 0
        self.last_outlier_mode = None
        self.custom_label_offsets.clear()
