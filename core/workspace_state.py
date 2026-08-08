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


class WorkspaceStateMixin:
    """Compatibility properties backed by a controller's ``WorkspaceState``."""

    def _ensure_workspace(self) -> WorkspaceState:
        workspace = self.__dict__.get("workspace")
        if workspace is None:
            workspace = WorkspaceState()
            self.__dict__["workspace"] = workspace
        return workspace

    @property
    def filepaths(self):
        return self._ensure_workspace().filepaths

    @filepaths.setter
    def filepaths(self, value):
        self._ensure_workspace().filepaths = value

    @property
    def plot_data_list(self):
        return self._ensure_workspace().plot_data_list

    @plot_data_list.setter
    def plot_data_list(self, value):
        self._ensure_workspace().plot_data_list = value

    @property
    def current_idx(self):
        return self._ensure_workspace().current_idx

    @current_idx.setter
    def current_idx(self, value):
        self._ensure_workspace().current_idx = value

    @property
    def last_outlier_mode(self):
        return self._ensure_workspace().last_outlier_mode

    @last_outlier_mode.setter
    def last_outlier_mode(self, value):
        self._ensure_workspace().last_outlier_mode = value

    @property
    def last_save_dir(self):
        return self._ensure_workspace().last_save_dir

    @last_save_dir.setter
    def last_save_dir(self, value):
        self._ensure_workspace().last_save_dir = value

    @property
    def last_open_dir(self):
        return self._ensure_workspace().last_open_dir

    @last_open_dir.setter
    def last_open_dir(self, value):
        self._ensure_workspace().last_open_dir = value

    @property
    def custom_label_offsets(self):
        return self._ensure_workspace().custom_label_offsets

    @custom_label_offsets.setter
    def custom_label_offsets(self, value):
        self._ensure_workspace().custom_label_offsets = value
