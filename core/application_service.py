"""Serializable application facade for UI adapters and future IPC transports."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
import os
from pathlib import Path
import shutil
import tempfile
import time
import threading
import uuid
from typing import Any, Mapping

from core.application_events import ApplicationError, ApplicationEventBus
from core.application_state import AnalysisSettings
from core.data_loading_service import (
    UNSUPPORTED_DATA_FILE_MESSAGE,
    is_supported_data_path,
)
from core.design_defaults import get_single_design_defaults
from core.interactive_plot_state import (
    PlotSessionState,
    validate_interactive_options,
)
from core.interactive_render_worker import InteractiveRenderer
from utils.math_utils import compute_x_raw
from utils.pillai_stats import calculate_pillai_score
from utils.vowel_stats import analyze_vowels, calculate_pairwise_mahalanobis_distances


class ApplicationService:
    """Expose controller commands without leaking concrete widget objects."""

    def __init__(self, controller, events: ApplicationEventBus | None = None):
        self.controller = controller
        self.events = events or ApplicationEventBus()
        self._interactive_renderer = InteractiveRenderer()
        self._preview_dir = (
            Path(tempfile.gettempdir())
            / "GichanFormant"
            / "previews"
            / str(os.getpid())
        )
        self._cleanup_stale_preview_dirs()
        self._preview_dir.mkdir(parents=True, exist_ok=True)
        self._preview_files: deque[Path] = deque()
        self._preview_file_lock = threading.Lock()

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
        current_data, _current_index = self.controller.get_current_file_data()
        current_vowels: list[str] = []
        if current_data is not None:
            dataframe = current_data.get("df")
            if dataframe is not None:
                label_column = "Label" if "Label" in dataframe.columns else "label"
                if label_column in dataframe.columns:
                    current_vowels = sorted(
                        dataframe[label_column].dropna().astype(str).unique().tolist()
                    )
        return {
            "analysis": self.controller.get_analysis_settings().to_dict(),
            "current_index": self.controller.get_current_index(),
            "current_vowels": current_vowels,
            "design_defaults": get_single_design_defaults(),
            "plot_session": self._plot_session().to_public_dict(),
            "sources": sources,
            "capabilities": {
                "can_plot": bool(sources),
                "can_compare": real_count >= 2,
                "can_save_project": real_count > 0,
            },
        }

    def get_vowel_analysis(self, index: int) -> dict[str, Any]:
        """Return structured vowel statistics for the React analysis surface."""
        item = self.controller.get_data_item_at(index)
        if item is None:
            raise ApplicationError("file_not_found", "분석할 파일을 찾을 수 없습니다.")
        dataframe = item.get("df")
        if dataframe is None or dataframe.empty:
            return {"index": index, "name": item.get("name", ""), "statistics": {}, "metadata": {"total_points": 0, "vowel_count": 0}}
        label_col = "Label" if "Label" in dataframe.columns else "label"
        if label_col not in dataframe.columns or "F1" not in dataframe.columns or "F2" not in dataframe.columns:
            raise ApplicationError("analysis_columns_missing", "F1, F2, Label 열이 필요합니다.")
        settings = self.controller.get_analysis_settings()
        if settings.normalization and hasattr(self.controller, "_normalize_dataframe"):
            dataframe = self.controller._normalize_dataframe(dataframe, settings.normalization, item)
        x_values = compute_x_raw(dataframe, settings.plot_type)
        working = dataframe[[label_col, "F1"]].copy()
        working["analysis_x"] = x_values
        result = analyze_vowels(working, x_col="analysis_x", y_col="F1", label_col=label_col)
        statistics = result.get("statistics", {})
        labels = [str(label) for label in statistics]
        pairwise_euclidean = {}
        for left_index, left in enumerate(labels):
            for right in labels[left_index + 1 :]:
                left_stat = statistics[left]
                right_stat = statistics[right]
                pairwise_euclidean[f"{left}::{right}"] = float(((left_stat["x_mean"] - right_stat["x_mean"]) ** 2 + (left_stat["y_mean"] - right_stat["y_mean"]) ** 2) ** 0.5)
        pairwise_mahalanobis = calculate_pairwise_mahalanobis_distances(working, x_col="analysis_x", y_col="F1", label_col=label_col)
        pillai_scores = {}
        for left_index, left in enumerate(labels):
            left_coords = working[working[label_col].astype(str) == left][["analysis_x", "F1"]].dropna().to_numpy(dtype=float)
            for right in labels[left_index + 1 :]:
                right_coords = working[working[label_col].astype(str) == right][["analysis_x", "F1"]].dropna().to_numpy(dtype=float)
                score, p_value = calculate_pillai_score(left_coords, right_coords)
                pillai_scores[f"{left}::{right}"] = {"score": score, "p_value": p_value}
        return {
            "index": index,
            "name": item.get("name", ""),
            "x_label": "F2" if settings.plot_type == "f1_f2" else settings.plot_type,
            "y_label": "F1",
            "normalization": settings.normalization,
            "statistics": result.get("statistics", {}),
            "centroid": list(result.get("centroid") or (None, None)),
            "centroid_distances": result.get("centroid_distances", {}),
            "pairwise_euclidean": pairwise_euclidean,
            "pairwise_mahalanobis": {f"{left}::{right}": value.get("distance") for (left, right), value in pairwise_mahalanobis.items()},
            "pillai_scores": pillai_scores,
            "point_distances": result.get("point_distances", {}),
            "metadata": result.get("metadata", {}),
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
        valid_paths = [path for path in paths if is_supported_data_path(path)]
        skipped_failed = [
            (
                os.path.basename(str(path)) or str(path),
                [(str(path), UNSUPPORTED_DATA_FILE_MESSAGE)],
            )
            for path in paths
            if not is_supported_data_path(path)
        ]
        self.events.emit(
            "operation_progress",
            {
                "operation": "load_files",
                "status": "started",
                "total": len(paths),
            },
        )
        if valid_paths:
            if getattr(self.controller.view, "native_window", None) is None:
                result = self.controller.workspace_service.add_files(
                    valid_paths, loader=self.controller._load_file_item
                )
                self.controller._sync_pre_lobanov_ui()
            else:
                result = self.controller.load_files(valid_paths)
            if skipped_failed:
                result = dict(result)
                result["failed"] = [*skipped_failed, *result.get("failed", [])]
        else:
            result = {
                "success_count": 0,
                "failed": skipped_failed,
                "has_f3_all": False,
                "total_files": len(self.controller.filepaths),
                "row_dropped": [],
            }
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
        removed = self.controller.remove_file(index)
        if not removed:
            error = ApplicationError(
                code="file_remove_failed",
                message="파일을 삭제할 수 없습니다.",
                details={"index": index},
            )
            self.events.emit("operation_failed", error.to_dict())
            raise error
        self._plot_session().remove_file(index)
        state = self._emit_state("file_removed")
        self.events.emit("files_changed", {"action": "remove", "state": state})
        return state

    def set_current_index(self, index: int) -> dict[str, Any]:
        self.controller.set_current_index(index)
        # Keep the project/session cursor coherent even when navigation comes
        # from the React plot rather than the legacy popup.
        self._plot_session().current_idx = self.controller.get_current_index()
        state = self._emit_state("current_file_changed")
        return state

    def prepare_interactive_navigation(
        self, index: int, raw: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Move to a file and prepare its interactive render in one UI-thread hop."""
        self.controller.set_current_index(index)
        self._plot_session().current_idx = self.controller.get_current_index()
        prepared = self.prepare_interactive_preview(raw)
        state = self._emit_state("current_file_changed")
        return {"state": state, "prepared": prepared}

    def reset(self) -> dict[str, Any]:
        self.controller.reset_data()
        self.controller.plot_session_state = PlotSessionState()
        state = self._emit_state("workspace_reset")
        self.events.emit("files_changed", {"action": "reset", "state": state})
        return state

    def save_project(self, path: str, popup_window: Any | None = None) -> None:
        try:
            self.controller.save_project_document(path, popup_window)
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

    def load_project(self, path: str, *, restore_windows: bool = True) -> dict[str, Any]:
        try:
            if restore_windows:
                self.controller.load_project_document(path)
            else:
                self.controller.load_project_document(path, restore_windows=False)
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

    def request_preview(self, request_id: int | None = None) -> None:
        self._main_preview_request_id = request_id
        self.controller.update_live_preview()

    def _plot_session(self) -> PlotSessionState:
        session = getattr(self.controller, "plot_session_state", None)
        if not isinstance(session, PlotSessionState):
            session = PlotSessionState(current_idx=self.controller.get_current_index())
            self.controller.plot_session_state = session
        return session

    def update_interactive_session(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        options = validate_interactive_options(raw)
        session = self._plot_session()
        session.apply(options, self.controller.get_current_index())
        payload = session.to_public_dict()
        # Do not emit a broad state_changed here: that snapshot can overwrite
        # in-progress local React controls. Consumers that need the durable
        # session receive this narrow event and compare revisions instead.
        self.events.emit("plot_session_changed", {"plot_session": payload})
        return payload

    def prepare_interactive_preview(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        """Capture a validated immutable-enough render snapshot on the UI thread."""
        options = validate_interactive_options(raw)
        session = self._plot_session()
        current_index = self.controller.get_current_index()
        session.apply(options, current_index)
        current_data, _index = self.controller.get_current_file_data()
        if current_data is None:
            return {
                "empty": True,
                "request_id": options.get("request_id"),
                "revision": session.revision,
            }

        params = self.controller._get_main_ui_plot_params()
        params["sigma"] = float(session.sigma)
        session.fixed_plot_params = dict(params)

        normalization = params.get("normalization")
        if normalization:
            ranges = self.controller._norm_ranges_for_widgets(normalization)
        else:
            ranges = self.controller.get_smart_ranges_for_params(
                params["type"],
                params.get("use_bark_units", False),
                params.get("f1_scale"),
                params.get("f2_scale"),
            )
        ranges.update(session.ranges)

        design = deepcopy(session.design_settings)
        if not session.show_ellipse:
            design["ell_color"] = None
            design["ell_fill_color"] = None

        data_snapshot = self._interactive_render_data(current_data)
        return {
            "empty": False,
            "current_data": data_snapshot,
            "params": dict(params),
            "ranges": dict(ranges),
            "design": design,
            "filter_state": deepcopy(
                session.vowel_filter_state_by_file.get(current_index)
            ),
            "layer_overrides": deepcopy(
                session.layer_design_overrides_by_file.get(current_index)
            ),
            "layer_order": list(
                session.layer_order_by_file.get(current_index, [])
            ),
            "custom_label_offsets": deepcopy(
                getattr(self.controller, "custom_label_offsets", {}).get(
                    (current_index, params.get("type", "f1_f2")), {}
                )
            ),
            "filename": str(current_data.get("name", "")),
            "request_id": options.get("request_id"),
            "revision": session.revision,
        }

    @staticmethod
    def _interactive_render_data(current_data: Mapping[str, Any]) -> dict[str, Any]:
        """Return only the fields the interactive renderer needs.

        Carrying ``df_original`` across the preview boundary is unnecessary
        for drawing and used to add an avoidable deep copy to navigation.
        """
        snapshot: dict[str, Any] = {}
        for key in (
            "name",
            "df",
            "has_f3",
            "is_pre_lobanov",
            "is_combined",
            "combined_source_names",
        ):
            if key in current_data:
                snapshot[key] = current_data[key]
        return snapshot

    def render_prepared_interactive_preview(
        self, prepared: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Render a prepared snapshot; safe to call on the dedicated render worker."""
        if prepared.get("empty"):
            return dict(prepared)
        return self._interactive_renderer.render(prepared)

    def publish_interactive_render_result(self, result: Mapping[str, Any]) -> None:
        if result.get("empty"):
            self.publish_empty_preview(
                target="interactive", request_id=result.get("request_id")
            )
            return
        self.publish_preview(
            result["png_data"],
            str(result.get("filename", "")),
            target="interactive",
            request_id=result.get("request_id"),
            revision=result.get("revision"),
        )

    def close(self) -> None:
        self._interactive_renderer.close()
        with self._preview_file_lock:
            try:
                shutil.rmtree(self._preview_dir, ignore_errors=True)
            finally:
                self._preview_files.clear()

    def render_interactive_preview(self, raw: Mapping[str, Any]) -> None:
        """Synchronous compatibility entry point used outside the desktop scheduler."""
        prepared = self.prepare_interactive_preview(raw)
        self.publish_interactive_render_result(
            self.render_prepared_interactive_preview(prepared)
        )

    def publish_preview(
        self,
        png_data: bytes,
        info: str,
        *,
        target: str = "main",
        request_id: Any | None = None,
        revision: Any | None = None,
    ) -> None:
        preview_path = self._write_preview_asset(png_data, revision=revision)
        payload = {
            "png_path": str(preview_path),
            "info": info,
            "target": target,
        }
        if request_id is not None:
            payload["request_id"] = request_id
        if revision is not None:
            payload["revision"] = revision
        self.events.emit(
            "preview_ready",
            payload,
        )

    def _write_preview_asset(
        self, png_data: bytes, *, revision: Any | None = None
    ) -> Path:
        filename = f"preview-{revision}-{uuid.uuid4().hex}.png"
        preview_path = self._preview_dir / filename
        with self._preview_file_lock:
            preview_path.write_bytes(png_data)
            self._preview_files.append(preview_path)
            while len(self._preview_files) > 3:
                stale = self._preview_files.popleft()
                try:
                    stale.unlink(missing_ok=True)
                except OSError:
                    pass
        return preview_path

    @staticmethod
    def _cleanup_stale_preview_dirs() -> None:
        """Remove abandoned crash leftovers without touching another live run."""
        root = Path(tempfile.gettempdir()) / "GichanFormant" / "previews"
        if not root.exists():
            return
        cutoff = time.time() - 24 * 60 * 60
        for child in root.iterdir():
            try:
                if child.is_dir() and child.stat().st_mtime < cutoff:
                    shutil.rmtree(child, ignore_errors=True)
            except OSError:
                continue

    def publish_empty_preview(
        self, *, target: str = "main", request_id: Any | None = None
    ) -> None:
        payload: dict[str, Any] = {"target": target}
        if request_id is not None:
            payload["request_id"] = request_id
        self.events.emit("preview_cleared", payload)

    def publish_preview_error(
        self,
        message: str,
        *,
        target: str = "main",
        request_id: Any | None = None,
    ) -> None:
        payload = {"message": message, "target": target}
        if request_id is not None:
            payload["request_id"] = request_id
        self.events.emit("preview_failed", payload)

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
