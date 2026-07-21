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
from core.export_service import export_combined_txt_file
from engine.plot_engine import PlotEngine
from utils.math_utils import compute_x_raw
from utils.pillai_stats import calculate_pillai_score
from utils.vowel_stats import analyze_vowels, calculate_pairwise_mahalanobis_distances


def _session_ranges_compatible(
    ranges: Mapping[str, Any] | None,
    normalization: str | None,
    *,
    use_bark_units: bool = False,
) -> bool:
    """Reject Hz-scale session ranges under Lobanov (and the reverse).

    Wrong limits with tiny NORM steps create thousands of tick labels and can
    stall interactive preview for tens of seconds.
    """
    if not isinstance(ranges, Mapping):
        return False
    try:
        vals = {key: float(ranges[key]) for key in ("x_min", "x_max", "y_min", "y_max")}
    except (KeyError, TypeError, ValueError):
        return False
    if vals["x_min"] >= vals["x_max"] or vals["y_min"] >= vals["y_max"]:
        return False
    max_abs = max(abs(value) for value in vals.values())
    if normalization:
        preset = PlotEngine.NORM_RANGES.get(
            normalization, PlotEngine.NORM_RANGES["Lobanov"]
        )
        span_x = abs(float(preset["x_max"]) - float(preset["x_min"]))
        span_y = abs(float(preset["y_max"]) - float(preset["y_min"]))
        pad_x = max(span_x * 3.0, 5.0)
        pad_y = max(span_y * 3.0, 5.0)
        if vals["x_min"] < float(preset["x_min"]) - pad_x:
            return False
        if vals["x_max"] > float(preset["x_max"]) + pad_x:
            return False
        if vals["y_min"] < float(preset["y_min"]) - pad_y:
            return False
        if vals["y_max"] > float(preset["y_max"]) + pad_y:
            return False
        if abs(vals["x_max"] - vals["x_min"]) > max(span_x * 4.0, 20.0):
            return False
        if abs(vals["y_max"] - vals["y_min"]) > max(span_y * 4.0, 20.0):
            return False
        return True
    if use_bark_units:
        return max_abs <= 40.0
    return max_abs >= 50.0


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
        self._vowel_analysis_cache: dict[tuple[Any, ...], dict[str, Any]] = {}
        self._vowel_analysis_cache_lock = threading.Lock()

    def _clear_vowel_analysis_cache(self) -> None:
        with self._vowel_analysis_cache_lock:
            self._vowel_analysis_cache.clear()

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

    _VOWEL_ANALYSIS_SECTIONS = frozenset({"core", "mahalanobis", "pillai"})

    def get_vowel_analysis(
        self,
        index: int,
        sections: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return structured vowel statistics for the React analysis surface.

        ``sections`` defaults to ``["core"]``. Heavy pairwise work
        (Mahalanobis / Pillai) runs only when those sections are requested.
        """
        requested = self._normalize_vowel_analysis_sections(sections)
        item = self.controller.get_data_item_at(index)
        if item is None:
            raise ApplicationError("file_not_found", "분석할 파일을 찾을 수 없습니다.")
        dataframe = item.get("df")
        if dataframe is None or dataframe.empty:
            return self._empty_vowel_analysis(index, item.get("name", ""))
        label_col = "Label" if "Label" in dataframe.columns else "label"
        if (
            label_col not in dataframe.columns
            or "F1" not in dataframe.columns
            or "F2" not in dataframe.columns
        ):
            raise ApplicationError(
                "analysis_columns_missing", "F1, F2, Label 열이 필요합니다."
            )
        settings = self.controller.get_analysis_settings()
        cache_key = (
            index,
            settings.normalization,
            settings.plot_type,
            id(dataframe),
            frozenset(requested),
        )
        with self._vowel_analysis_cache_lock:
            cached = self._vowel_analysis_cache.get(cache_key)
            if cached is not None:
                return deepcopy(cached)

        working_df = dataframe
        if settings.normalization and hasattr(self.controller, "_normalize_dataframe"):
            working_df = self.controller._normalize_dataframe(
                dataframe, settings.normalization, item
            )
        x_values = compute_x_raw(working_df, settings.plot_type)
        working = working_df[[label_col, "F1"]].copy()
        working["analysis_x"] = x_values
        result = analyze_vowels(
            working, x_col="analysis_x", y_col="F1", label_col=label_col
        )
        statistics = result.get("statistics", {})
        labels = [str(label) for label in statistics]
        pairwise_euclidean: dict[str, float] = {}
        for left_index, left in enumerate(labels):
            for right in labels[left_index + 1 :]:
                left_stat = statistics[left]
                right_stat = statistics[right]
                pairwise_euclidean[f"{left}::{right}"] = float(
                    (
                        (left_stat["x_mean"] - right_stat["x_mean"]) ** 2
                        + (left_stat["y_mean"] - right_stat["y_mean"]) ** 2
                    )
                    ** 0.5
                )

        pairwise_mahalanobis: dict[str, float] = {}
        if "mahalanobis" in requested:
            mahalanobis = calculate_pairwise_mahalanobis_distances(
                working, x_col="analysis_x", y_col="F1", label_col=label_col
            )
            pairwise_mahalanobis = {
                f"{left}::{right}": value.get("distance")
                for (left, right), value in mahalanobis.items()
            }

        pillai_scores: dict[str, dict[str, Any]] = {}
        if "pillai" in requested:
            for left_index, left in enumerate(labels):
                left_coords = (
                    working[working[label_col].astype(str) == left][
                        ["analysis_x", "F1"]
                    ]
                    .dropna()
                    .to_numpy(dtype=float)
                )
                for right in labels[left_index + 1 :]:
                    right_coords = (
                        working[working[label_col].astype(str) == right][
                            ["analysis_x", "F1"]
                        ]
                        .dropna()
                        .to_numpy(dtype=float)
                    )
                    score, p_value = calculate_pillai_score(left_coords, right_coords)
                    pillai_scores[f"{left}::{right}"] = {
                        "score": score,
                        "p_value": p_value,
                    }

        payload = {
            "index": index,
            "name": item.get("name", ""),
            "x_label": "F2" if settings.plot_type == "f1_f2" else settings.plot_type,
            "y_label": "F1",
            "normalization": settings.normalization,
            "statistics": result.get("statistics", {}),
            "centroid": list(result.get("centroid") or (None, None)),
            "centroid_distances": result.get("centroid_distances", {}),
            "pairwise_euclidean": pairwise_euclidean,
            "pairwise_mahalanobis": pairwise_mahalanobis,
            "pillai_scores": pillai_scores,
            "point_distances": result.get("point_distances", {}),
            "metadata": result.get("metadata", {}),
            "sections": sorted(requested),
        }
        with self._vowel_analysis_cache_lock:
            self._vowel_analysis_cache[cache_key] = deepcopy(payload)
        return payload

    def _normalize_vowel_analysis_sections(
        self, sections: list[str] | None
    ) -> frozenset[str]:
        if sections is None:
            return frozenset({"core"})
        if not sections:
            raise ApplicationError(
                "invalid_analysis_sections",
                "sections must include at least one of: core, mahalanobis, pillai",
            )
        requested = frozenset(sections)
        unknown = sorted(requested - self._VOWEL_ANALYSIS_SECTIONS)
        if unknown:
            raise ApplicationError(
                "invalid_analysis_sections",
                f"unknown analysis sections: {', '.join(unknown)}",
                {"unknown": unknown},
            )
        # Core stats are always needed to label pairs and fill the formant page.
        return requested | {"core"}

    @staticmethod
    def _empty_vowel_analysis(index: int, name: str) -> dict[str, Any]:
        return {
            "index": index,
            "name": name,
            "statistics": {},
            "centroid": [None, None],
            "centroid_distances": {},
            "pairwise_euclidean": {},
            "pairwise_mahalanobis": {},
            "pillai_scores": {},
            "point_distances": {},
            "metadata": {"total_points": 0, "vowel_count": 0},
            "sections": ["core"],
        }

    def set_analysis_settings(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        previous = self.controller.get_analysis_settings()
        merged = previous.to_dict()
        merged.update(raw)
        plot_type = str(merged.get("type") or merged.get("plot_type") or "f1_f2")
        # PySide: derived X types cannot use speaker normalization.
        if plot_type in ("f1_f2_minus_f1", "f1_f2_prime_minus_f1"):
            merged["normalization"] = None
        # PySide sync_pre_lobanov_normalization: all real files pre-Lobanov → force.
        if self.controller.all_real_items_pre_lobanov():
            merged["normalization"] = "Lobanov"
        # PySide MainUI.get_f*_scale: Bark display mode forces BOTH axes to bark.
        if merged.get("use_bark_units"):
            merged["f1_scale"] = "bark"
            merged["f2_scale"] = "bark"
        # Normalization makes Hz/Bark axis controls meaningless (still store values).
        settings = AnalysisSettings.from_mapping(merged)
        self.controller.apply_analysis_settings(settings)
        if (
            previous.normalization != settings.normalization
            or previous.plot_type != settings.plot_type
        ):
            self._clear_vowel_analysis_cache()

        unit_family_changed = (
            previous.use_bark_units != settings.use_bark_units
            or previous.f1_scale != settings.f1_scale
            or previous.f2_scale != settings.f2_scale
            or previous.normalization != settings.normalization
            or previous.plot_type != settings.plot_type
        )
        if unit_family_changed:
            # Stale Hz/Bark session limits must not override smart/norm defaults.
            self._plot_session().ranges.clear()

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
                # The sidecar intentionally bypasses the Qt executor for file
                # parsing, but its headless view still represents the same
                # workspace state as the PySide path.
                self.controller.view.update_file_status(result["total_files"])
                self.controller.view.toggle_f3_options(result["has_f3_all"])
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
        self._clear_vowel_analysis_cache()
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

    def export_combined_txt(self, path: str) -> dict[str, Any]:
        """Export the derived combined source through the headless boundary."""
        combined = next(
            (item for item in self.controller.get_plot_data_list() if item.get("is_combined")),
            None,
        )
        target = Path(path).expanduser()
        if target.suffix.lower() != ".txt":
            target = target.with_suffix(".txt")
        ok, message = export_combined_txt_file(combined, str(target))
        if not ok:
            raise ApplicationError(
                "combined_export_failed",
                message,
                {"path": str(target)},
            )
        set_last_save_dir = getattr(self.controller, "set_last_save_dir", None)
        if callable(set_last_save_dir):
            set_last_save_dir(str(target.parent))
        return {"ok": True, "path": str(target), "format": "txt"}

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
        self._clear_vowel_analysis_cache()
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
        self._clear_vowel_analysis_cache()
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
        self._clear_vowel_analysis_cache()
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
        params = self.controller._get_main_ui_plot_params()
        normalization = params.get("normalization")
        use_bark = bool(params.get("use_bark_units", False))

        # Drop stale Hz/norm ranges before they poison the session or tick count.
        if "ranges" in options and not _session_ranges_compatible(
            options["ranges"], normalization, use_bark_units=use_bark
        ):
            options = dict(options)
            options.pop("ranges", None)
        if session.ranges and not _session_ranges_compatible(
            session.ranges, normalization, use_bark_units=use_bark
        ):
            session.ranges.clear()

        session.apply(options, current_index)
        current_data, _index = self.controller.get_current_file_data()
        if current_data is None:
            return {
                "empty": True,
                "request_id": options.get("request_id"),
                "revision": session.revision,
            }

        params["sigma"] = float(session.sigma)
        session.fixed_plot_params = dict(params)

        if normalization:
            ranges = self.controller._norm_ranges_for_widgets(normalization)
        else:
            ranges = self.controller.get_smart_ranges_for_params(
                params["type"],
                params.get("use_bark_units", False),
                params.get("f1_scale"),
                params.get("f2_scale"),
            )
        if session.ranges and _session_ranges_compatible(
            session.ranges, normalization, use_bark_units=use_bark
        ):
            ranges.update(session.ranges)
        elif session.ranges:
            session.ranges.clear()

        batch_options = options.get("batch_options", {})
        design = deepcopy(
            session.design_settings
            if batch_options.get("apply_global_design", True)
            else get_single_design_defaults()
        )
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
            ) if batch_options.get("apply_layer_visibility", True) else None,
            "layer_overrides": deepcopy(
                session.layer_design_overrides_by_file.get(current_index)
            ) if batch_options.get("apply_layer_design", True) else None,
            "layer_order": list(
                session.layer_order_by_file.get(current_index, [])
            ),
            "custom_label_offsets": {
                **deepcopy(getattr(self.controller, "custom_label_offsets", {}).get(
                    (current_index, params.get("type", "f1_f2")), {}
                )),
                **deepcopy(session.label_offsets_by_file.get(current_index, {})),
            } if batch_options.get("apply_label_positions", True) else {},
            "draw_objects": deepcopy(
                session.draw_objects_by_file.get(current_index, [])
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

    @staticmethod
    def _export_extension(image_format: str) -> str:
        extension = str(image_format).lower().lstrip(".")
        if extension == "jpeg":
            extension = "jpg"
        if extension not in {"png", "jpg", "svg"}:
            raise ValueError("format must be png, jpg, or svg")
        return extension

    def export_interactive_preview(
        self, path: str, image_format: str, options: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Render the current React plot directly to a user-selected path."""
        target = Path(path).expanduser()
        extension = self._export_extension(image_format)
        if target.suffix.lower().lstrip(".") != extension:
            target = target.with_suffix(f".{extension}")
        prepared = self.prepare_interactive_preview(options)
        data = self._interactive_renderer.render_export(prepared, extension)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return {"ok": True, "path": str(target), "format": extension}

    def export_interactive_batch(
        self, directory: str, image_format: str, options: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Render every loaded source using the current React session settings."""
        output_dir = Path(directory).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        extension = self._export_extension(image_format)
        original_index = self.controller.get_current_index()
        items = list(self.controller.get_plot_data_list())
        used: set[str] = set()
        exported: list[str] = []
        errors: list[dict[str, str]] = []
        try:
            for index, item in enumerate(items):
                try:
                    self.controller.set_current_index(index)
                    prepared = self.prepare_interactive_preview(options)
                    raw_name = Path(str(item.get("name", "plot"))).stem or "plot"
                    safe_name = "".join(char if char.isalnum() or char in " ._-" else "_" for char in raw_name).strip() or "plot"
                    candidate = f"{safe_name}.{extension}"
                    serial = 2
                    while candidate.casefold() in used:
                        candidate = f"{safe_name}_{serial}.{extension}"
                        serial += 1
                    used.add(candidate.casefold())
                    target = output_dir / candidate
                    target.write_bytes(self._interactive_renderer.render_export(prepared, extension))
                    exported.append(str(target))
                except Exception as exc:  # noqa: BLE001 - preserve per-file result
                    errors.append({"name": str(item.get("name", index)), "message": str(exc)})
        finally:
            self.controller.set_current_index(original_index)
            self._plot_session().current_idx = original_index
        return {"ok": not errors or bool(exported), "directory": str(output_dir), "format": extension, "exported": exported, "errors": errors}

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
            ruler_context=result.get("ruler_context"),
        )

    def close(self) -> None:
        self._interactive_renderer.close()
        self._clear_vowel_analysis_cache()
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
        ruler_context: Mapping[str, Any] | None = None,
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
        if ruler_context is not None:
            payload["ruler_context"] = ruler_context
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
