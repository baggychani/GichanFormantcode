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
import zipfile
from typing import Any

import pandas as pd

import config
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
        "compare_sessions": [],
    }


def save_project(path: str, controller: Any, popup_window: Any | None = None) -> None:
    doc = collect_project_document(controller, popup_window)
    target = Path(path)
    if target.suffix.lower() != ".gfproj":
        target = target.with_suffix(".gfproj")

    real_items = [it for it in controller.plot_data_list if not it.get("is_combined")]
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            MANIFEST_NAME,
            json.dumps(doc, ensure_ascii=False, indent=2, default=_json_default),
        )
        for idx, item in enumerate(real_items):
            snapshot_df = item.get("df_original", item.get("df"))
            if isinstance(snapshot_df, pd.DataFrame):
                zf.writestr(f"data/{idx}.json", _df_to_json(snapshot_df))


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
    return doc
