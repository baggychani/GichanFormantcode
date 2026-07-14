"""Framework-free file/workspace lifecycle operations.

This service owns mutations of :class:`WorkspaceState`.  Presentation updates,
logging, preview scheduling, and popup refreshes deliberately stay outside it.
That makes the same lifecycle usable from PySide, the sidecar, and tests.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.data_loading_service import load_plot_item_from_file
from core.workspace_state import WorkspaceState
from model.combined_dataset import build_combined_entry


class WorkspaceService:
    def __init__(self, state: WorkspaceState) -> None:
        self.state = state

    def real_items(self) -> list[dict[str, Any]]:
        return [item for item in self.state.plot_data_list if not item.get("is_combined")]

    def rebuild_combined_entry(self) -> None:
        real_items = self.real_items()
        self.state.plot_data_list[:] = real_items
        combined = build_combined_entry(real_items)
        if combined is not None:
            self.state.plot_data_list.append(combined)
        self.state.current_idx = self.clamp_index(self.state.current_idx)

    def add_files(
        self,
        paths: list[str],
        *,
        loader: Callable[..., dict[str, Any]] = load_plot_item_from_file,
    ) -> dict[str, Any]:
        # Remove the derived combined item while appending real source items.
        self.state.plot_data_list[:] = self.real_items()
        result: dict[str, Any] = {
            "success_count": 0,
            "failed": [],
            "has_f3_all": False,
            "total_files": len(self.state.filepaths),
            "row_dropped": [],
        }
        new_paths = [path for path in paths if path not in self.state.filepaths]
        if not new_paths:
            self.rebuild_combined_entry()
            return self._finish_load_result(result)

        existing = self.real_items()
        existing_pre_lobanov = (
            all(item.get("is_pre_lobanov") for item in existing) if existing else None
        )
        for path in new_paths:
            loaded = loader(
                path, existing_pre_lobanov=existing_pre_lobanov
            )
            if loaded["success"]:
                self.state.filepaths.append(path)
                self.state.plot_data_list.append(loaded["item"])
                result["success_count"] += 1
                result["row_dropped"].extend(loaded["row_dropped"])
            else:
                result["failed"].append((loaded["name"], loaded["errors"]))
        self.rebuild_combined_entry()
        return self._finish_load_result(result)

    def remove_file(self, index: int) -> dict[str, Any] | None:
        if index < 0 or index >= len(self.state.plot_data_list):
            return None
        item = self.state.plot_data_list[index]
        if item.get("is_combined"):
            return None
        removed = self.state.plot_data_list.pop(index)
        self.state.filepaths.pop(index)
        if index < self.state.current_idx:
            self.state.current_idx -= 1
        self.rebuild_combined_entry()
        return {
            "name": str(removed.get("name", "")),
            "total_files": len(self.state.filepaths),
            "has_f3_all": self._has_f3_all(),
        }

    def set_current_index(self, index: int) -> int:
        self.state.current_idx = self.clamp_index(index)
        return self.state.current_idx

    def current_item(self) -> tuple[dict[str, Any] | None, int]:
        if not self.state.plot_data_list:
            return None, 0
        index = self.clamp_index(self.state.current_idx)
        return self.state.plot_data_list[index], index

    def clamp_index(self, index: int) -> int:
        if not self.state.plot_data_list:
            return 0
        return max(0, min(int(index), len(self.state.plot_data_list) - 1))

    def _finish_load_result(self, result: dict[str, Any]) -> dict[str, Any]:
        result["total_files"] = len(self.state.filepaths)
        result["has_f3_all"] = self._has_f3_all()
        return result

    def _has_f3_all(self) -> bool:
        real_items = self.real_items()
        return bool(real_items) and all(item.get("has_f3") for item in real_items)
