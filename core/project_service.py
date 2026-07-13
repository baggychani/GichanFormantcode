"""Project save/load service for GichanFormant.

The ``.gfproj`` file is a zip container with a versioned JSON manifest and
per-source DataFrame snapshots. Source paths are kept for transparency, while
snapshots make projects recoverable when the original data files move.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import zipfile
from typing import Any

import pandas as pd

import config
from core.compare_series import legacy_key_from_series_id
from draw.draw_common import (
    AreaLabelObject,
    LegendEntry,
    LegendObject,
    LineObject,
    PolygonObject,
    ReferenceLineObject,
    TextObject,
)

PROJECT_SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"

_DRAW_TYPES = {
    "line": LineObject,
    "polygon": PolygonObject,
    "reference": ReferenceLineObject,
    "area_label": AreaLabelObject,
    "legend": LegendObject,
    "text": TextObject,
}


def _json_default(value: Any):
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, tuple):
        return list(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def _df_to_json(df: pd.DataFrame) -> str:
    return df.to_json(orient="table", force_ascii=False, index=False)


def _df_from_json(raw: str) -> pd.DataFrame:
    return pd.read_json(StringIO(raw), orient="table")


def _serialize_key(key: Any) -> str:
    return json.dumps(key if isinstance(key, tuple) else key, ensure_ascii=False)


def _deserialize_key(raw: str) -> Any:
    value = json.loads(raw)
    return tuple(value) if isinstance(value, list) else value


def _serialize_keyed_dict(data: dict | None) -> dict[str, Any]:
    return {_serialize_key(k): v for k, v in (data or {}).items()}


def _deserialize_keyed_dict(data: dict | None) -> dict[Any, Any]:
    return {_deserialize_key(k): v for k, v in (data or {}).items()}


def _serialize_draw_object(obj: Any) -> dict[str, Any]:
    if is_dataclass(obj):
        return asdict(obj)
    return dict(obj)


def _deserialize_draw_object(raw: dict[str, Any]) -> Any:
    if not isinstance(raw, dict):
        return raw
    obj_type = raw.get("type")
    cls = _DRAW_TYPES.get(obj_type)
    if cls is None:
        return raw
    data = dict(raw)
    if cls is LegendObject:
        data["entries"] = [
            entry if isinstance(entry, LegendEntry) else LegendEntry(**entry)
            for entry in data.get("entries", [])
            if isinstance(entry, dict) or isinstance(entry, LegendEntry)
        ]
    if "points" in data and isinstance(data["points"], list):
        data["points"] = [tuple(pt) for pt in data["points"]]
    return cls(**data)


def _serialize_draw_objects_by_file(data: dict | None) -> dict[str, list[dict]]:
    return {
        str(idx): [_serialize_draw_object(obj) for obj in objects]
        for idx, objects in (data or {}).items()
    }


def _deserialize_draw_objects_by_file(data: dict | None) -> dict[int, list[Any]]:
    return {
        int(idx): [_deserialize_draw_object(obj) for obj in objects]
        for idx, objects in (data or {}).items()
    }


def _serialize_compare_popup(popup: Any, controller: Any) -> dict | None:
    session = getattr(popup, "compare_session", None)
    if session is None:
        return None
    source_groups = getattr(popup, "compare_source_groups", None)
    if not source_groups and all(index >= 0 for index in session.data_indices):
        source_groups = tuple((index,) for index in session.data_indices)
    if not source_groups:
        return None

    range_widgets = getattr(popup, "range_widgets", {}) or {}
    plot_key = getattr(popup, "_plot_key_compare", None)
    label_offsets_by_series = {}
    if plot_key:
        for series_id in range(session.count):
            legacy = legacy_key_from_series_id(series_id)
            offsets = getattr(controller, "custom_label_offsets", {}).get(
                (*plot_key, legacy)
            )
            if offsets:
                label_offsets_by_series[series_id] = offsets

    return {
        "source_groups": [list(group) for group in source_groups],
        "normalization": getattr(popup, "normalization", None),
        "fixed_plot_params": dict(getattr(popup, "fixed_plot_params", {}) or {}),
        "ranges": {
            key: widget.text()
            for key, widget in range_widgets.items()
            if hasattr(widget, "text")
        },
        "sigma": (
            popup.get_sigma()
            if hasattr(popup, "get_sigma")
            else str(config.DEFAULT_SIGMA)
        ),
        "design_settings": dict(getattr(popup, "design_settings", {}) or {}),
        "vowel_filter_states": _serialize_keyed_dict(
            getattr(popup, "vowel_filter_states", {})
        ),
        "layer_design_overrides_by_series": _serialize_keyed_dict(
            getattr(popup, "layer_design_overrides_by_series", {})
        ),
        "layer_locked_vowels_by_series": _serialize_keyed_dict(
            getattr(popup, "layer_locked_vowels_by_series", {})
        ),
        "layer_order_by_series": _serialize_keyed_dict(
            getattr(popup, "layer_order_by_series", {})
        ),
        "label_offsets_by_series": _serialize_keyed_dict(label_offsets_by_series),
        "draw_objects": [
            _serialize_draw_object(obj)
            for obj in (getattr(popup, "_draw_objects_shared", []) or [])
        ],
    }


def _collect_compare_sessions(controller: Any, popup_window: Any | None) -> list[dict]:
    candidates = list(getattr(controller, "open_popups", []) or [])
    if popup_window is not None:
        candidates.append(popup_window)
    sessions = []
    seen = set()
    for popup in candidates:
        if id(popup) in seen or not hasattr(popup, "compare_session"):
            continue
        seen.add(id(popup))
        serialized = _serialize_compare_popup(popup, controller)
        if serialized is not None:
            sessions.append(serialized)
    return sessions


def _flush_single_popup_state(popup_window: Any | None) -> None:
    if popup_window is None:
        return
    for method_name in (
        "_save_layer_overrides_for_current_file",
        "_save_filter_state_for_current_file",
    ):
        method = getattr(popup_window, method_name, None)
        if method is not None:
            method()


def collect_project_document(controller: Any, popup_window: Any | None = None) -> dict:
    """Collect a versioned project document from controller and optional popup."""
    _flush_single_popup_state(popup_window)

    real_items = [it for it in controller.plot_data_list if not it.get("is_combined")]
    sources = []
    for idx, item in enumerate(real_items):
        source_path = (
            controller.filepaths[idx]
            if idx < len(getattr(controller, "filepaths", []))
            else ""
        )
        sources.append(
            {
                "id": str(idx),
                "path": source_path,
                "name": item.get("name") or os.path.basename(source_path),
                "has_f3": bool(item.get("has_f3", False)),
                "is_pre_lobanov": bool(item.get("is_pre_lobanov", False)),
                "snapshot": f"data/{idx}.json",
            }
        )

    analysis = {
        **controller._get_main_ui_plot_params(),
        "outlier_mode": controller.ui.get_outlier_mode(),
        "outlier_scope": controller.ui.get_outlier_scope(),
        "current_idx": int(getattr(controller, "current_idx", 0)),
    }

    single_plot = None
    if popup_window is not None and not hasattr(popup_window, "compare_session"):
        range_widgets = getattr(popup_window, "range_widgets", {}) or {}
        single_plot = {
            "current_idx": int(getattr(popup_window, "current_idx", 0)),
            "fixed_plot_params": dict(
                getattr(popup_window, "fixed_plot_params", {}) or {}
            ),
            "ranges": {
                k: widget.text()
                for k, widget in range_widgets.items()
                if hasattr(widget, "text")
            },
            "sigma": (
                popup_window.get_sigma()
                if hasattr(popup_window, "get_sigma")
                else str(config.DEFAULT_SIGMA)
            ),
            "design_settings": dict(getattr(popup_window, "design_settings", {}) or {}),
            "vowel_filter_state_by_file": _serialize_keyed_dict(
                getattr(popup_window, "vowel_filter_state_by_file", {})
            ),
            "layer_design_overrides_by_file": _serialize_keyed_dict(
                getattr(popup_window, "layer_design_overrides_by_file", {})
            ),
            "layer_locked_vowels_by_file": _serialize_keyed_dict(
                getattr(popup_window, "layer_locked_vowels_by_file", {})
            ),
            "layer_order": list(getattr(popup_window, "layer_order", []) or []),
            "draw_objects_by_file": _serialize_draw_objects_by_file(
                getattr(popup_window, "_draw_objects_by_file", {})
            ),
        }

    return {
        "schema_version": PROJECT_SCHEMA_VERSION,
        "app_version": config.APP_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "analysis": analysis,
        "label_offsets": _serialize_keyed_dict(
            getattr(controller, "custom_label_offsets", {})
        ),
        "single_plot": single_plot,
        "compare_sessions": _collect_compare_sessions(controller, popup_window),
    }


def save_project(path: str, controller: Any, popup_window: Any | None = None) -> None:
    doc = collect_project_document(controller, popup_window)
    target = Path(path)
    if target.suffix.lower() != ".gfproj":
        target = target.with_suffix(".gfproj")

    real_items = [it for it in controller.plot_data_list if not it.get("is_combined")]
    manifest = json.dumps(doc, ensure_ascii=False, indent=2, default=_json_default)
    snapshots = []
    for idx, item in enumerate(real_items):
        snapshot_df = item.get("df_original", item.get("df"))
        if isinstance(snapshot_df, pd.DataFrame):
            snapshots.append((f"data/{idx}.json", _df_to_json(snapshot_df)))

    file_descriptor, temp_path = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    os.close(file_descriptor)
    try:
        with zipfile.ZipFile(
            temp_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as zf:
            zf.writestr(MANIFEST_NAME, manifest)
            for snapshot_name, snapshot_json in snapshots:
                zf.writestr(snapshot_name, snapshot_json)
        os.replace(temp_path, target)
        temp_path = None
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def load_project(path: str) -> dict:
    with zipfile.ZipFile(path, "r") as zf:
        doc = json.loads(zf.read(MANIFEST_NAME).decode("utf-8"))
        if int(doc.get("schema_version", 0)) > PROJECT_SCHEMA_VERSION:
            raise ValueError("이 프로젝트 파일은 현재 앱보다 새로운 형식입니다.")
        snapshots = {}
        for source in doc.get("sources", []):
            ref = source.get("snapshot")
            if ref and ref in zf.namelist():
                snapshots[str(source.get("id"))] = _df_from_json(
                    zf.read(ref).decode("utf-8")
                )

    doc["snapshots"] = snapshots
    doc["label_offsets"] = _deserialize_keyed_dict(doc.get("label_offsets", {}))
    single_plot = doc.get("single_plot")
    if isinstance(single_plot, dict):
        single_plot["vowel_filter_state_by_file"] = _deserialize_keyed_dict(
            single_plot.get("vowel_filter_state_by_file", {})
        )
        single_plot["layer_design_overrides_by_file"] = _deserialize_keyed_dict(
            single_plot.get("layer_design_overrides_by_file", {})
        )
        single_plot["layer_locked_vowels_by_file"] = _deserialize_keyed_dict(
            single_plot.get("layer_locked_vowels_by_file", {})
        )
        single_plot["draw_objects_by_file"] = _deserialize_draw_objects_by_file(
            single_plot.get("draw_objects_by_file", {})
        )
    for compare_state in doc.get("compare_sessions", []) or []:
        if not isinstance(compare_state, dict):
            continue
        for key in (
            "vowel_filter_states",
            "layer_design_overrides_by_series",
            "layer_locked_vowels_by_series",
            "layer_order_by_series",
            "label_offsets_by_series",
        ):
            compare_state[key] = _deserialize_keyed_dict(compare_state.get(key, {}))
        compare_state["draw_objects"] = [
            _deserialize_draw_object(obj)
            for obj in compare_state.get("draw_objects", [])
        ]
    return doc
