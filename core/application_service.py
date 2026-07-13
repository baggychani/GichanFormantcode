"""Serializable application facade for UI adapters and future IPC transports."""

from __future__ import annotations

import base64
from typing import Any, Mapping

from core.application_events import ApplicationError, ApplicationEventBus
from core.application_state import AnalysisSettings


class ApplicationService:
    """Expose controller commands without leaking concrete widget objects."""

    def __init__(self, controller, events: ApplicationEventBus | None = None):
        self.controller = controller
        self.events = events or ApplicationEventBus()

    def _emit_state(self, reason: str) -> dict[str, Any]:
        state = self.snapshot()
        self.events.emit("state_changed", {"reason": reason, "state": state})
        return state

    def snapshot(self) -> dict[str, Any]:
        sources = []
        real_index = 0
        for index, item in enumerate(self.controller.get_plot_data_list()):
            is_combined = bool(item.get("is_combined"))
            path = None
            if not is_combined:
                if real_index < len(self.controller.filepaths):
                    path = self.controller.filepaths[real_index]
                real_index += 1
            sources.append(
                {
                    "index": index,
                    "name": item.get("name", ""),
                    "path": path,
                    "has_f3": bool(item.get("has_f3", False)),
                    "is_combined": is_combined,
                    "is_pre_lobanov": bool(item.get("is_pre_lobanov", False)),
                }
            )
        real_count = sum(not source["is_combined"] for source in sources)
        return {
            "analysis": self.controller.get_analysis_settings().to_dict(),
            "current_index": self.controller.get_current_index(),
            "sources": sources,
            "capabilities": {
                "can_plot": bool(sources),
                "can_compare": real_count >= 2,
                "can_save_project": real_count > 0,
            },
        }

    def set_analysis_settings(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        previous = self.controller.get_analysis_settings()
        merged = previous.to_dict()
        merged.update(raw)
        settings = AnalysisSettings.from_mapping(merged)
        self.controller.apply_analysis_settings(settings)
        if (
            previous.outlier_mode != settings.outlier_mode
            or previous.outlier_scope != settings.outlier_scope
        ):
            self.controller.on_outlier_mode_changed()
        else:
            self.controller.update_live_preview()
        return self._emit_state("analysis_settings_changed")

    def load_files(self, paths: list[str]) -> dict[str, Any]:
        self.events.emit(
            "operation_progress",
            {
                "operation": "load_files",
                "status": "started",
                "total": len(paths),
            },
        )
        result = self.controller.load_files(paths)
        state = self._emit_state("files_loaded")
        self.events.emit(
            "files_changed",
            {
                "action": "load",
                "state": state,
                "success_count": result["success_count"],
            },
        )
        self.events.emit(
            "operation_progress",
            {
                "operation": "load_files",
                "status": "completed",
                "total": len(paths),
                "success_count": result["success_count"],
            },
        )
        return {
            "load_result": self._serialize_load_result(result),
            "state": state,
        }

    def remove_file(self, index: int) -> dict[str, Any]:
        self.controller.remove_file(index)
        state = self._emit_state("file_removed")
        self.events.emit("files_changed", {"action": "remove", "state": state})
        return state

    def reset(self) -> dict[str, Any]:
        self.controller.reset_data()
        state = self._emit_state("workspace_reset")
        self.events.emit("files_changed", {"action": "reset", "state": state})
        return state

    def save_project(self, path: str) -> None:
        try:
            self.controller.save_project_document(path)
        except Exception as exc:
            error = ApplicationError(
                code="project_save_failed",
                message=str(exc),
                details={"path": path},
            )
            self.events.emit("operation_failed", error.to_dict())
            raise error from exc
        else:
            self.events.emit("project_saved", {"path": path})

    def load_project(self, path: str) -> dict[str, Any]:
        try:
            self.controller.load_project_document(path)
        except Exception as exc:
            error = ApplicationError(
                code="project_load_failed",
                message=str(exc),
                details={"path": path},
            )
            self.events.emit("operation_failed", error.to_dict())
            raise error from exc
        state = self._emit_state("project_loaded")
        self.events.emit("project_loaded", {"path": path, "state": state})
        return state

    def open_single_plot(self) -> None:
        self.controller.open_single_plot()
        self.events.emit("window_requested", {"kind": "single_plot"})

    def open_guide(self) -> None:
        self.controller.open_guide()
        self.events.emit("window_requested", {"kind": "data_guide"})

    def request_file_open(self) -> None:
        self.controller.open_file_dialog()

    def prompt_open_project(self) -> None:
        self.controller.prompt_open_project()

    def refresh_open_plots(self) -> None:
        self.controller._refresh_open_popups()

    def apply_outlier_settings(self) -> None:
        self.controller.on_outlier_mode_changed()

    def request_preview(self) -> None:
        self.controller.update_live_preview()

    def publish_preview(self, png_data: bytes, info: str) -> None:
        self.events.emit(
            "preview_ready",
            {
                "png_base64": base64.b64encode(png_data).decode("ascii"),
                "info": info,
            },
        )

    def publish_empty_preview(self) -> None:
        self.events.emit("preview_cleared", {})

    def publish_preview_error(self, message: str) -> None:
        self.events.emit("preview_failed", {"message": message})

    def get_initial_open_dir(self) -> str:
        return self.controller.get_initial_open_dir()

    def get_default_save_dir(self) -> str:
        return self.controller.get_default_batch_save_dir()

    def remember_open_dir(self, path: str) -> None:
        self.controller.set_last_open_dir(path)

    def remember_save_dir(self, path: str) -> None:
        self.controller.set_last_save_dir(path)

    def open_compare(
        self, source_groups: list[list[int]], normalization: str | None = None
    ) -> None:
        self.controller.open_compare_plot_for_source_groups(
            source_groups, normalization=normalization
        )
        self.events.emit(
            "window_requested",
            {
                "kind": "compare_plot",
                "source_groups": source_groups,
                "normalization": normalization,
            },
        )

    @staticmethod
    def _serialize_load_result(result: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "success_count": int(result.get("success_count", 0)),
            "total_files": int(result.get("total_files", 0)),
            "has_f3_all": bool(result.get("has_f3_all", False)),
            "failed": [
                {
                    "name": name,
                    "errors": [
                        {"path": str(path), "message": str(message)}
                        for path, message in errors
                    ],
                }
                for name, errors in result.get("failed", [])
            ],
            "row_dropped": [
                {"name": name, "labels": dict(labels)}
                for name, labels in result.get("row_dropped", [])
            ],
        }
