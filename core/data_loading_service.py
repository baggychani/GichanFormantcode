"""Data loading helpers for controller-level plot items."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

import config
from core.plot_data_types import PlotDataItem
from model.data_processor import DataProcessor

SUPPORTED_DATA_EXTENSIONS = frozenset({".txt", ".csv", ".tsv", ".xlsx", ".xls"})
UNSUPPORTED_DATA_FILE_MESSAGE = (
    "지원하지 않는 데이터 파일 형식입니다. TXT, CSV, TSV, XLSX, XLS만 불러올 수 있습니다."
)


def is_supported_data_path(path: str) -> bool:
    return os.path.splitext(str(path))[1].lower() in SUPPORTED_DATA_EXTENSIONS


def make_plot_item(
    *,
    name: str,
    df: pd.DataFrame,
    has_f3: bool | None = None,
    is_pre_lobanov: bool = False,
) -> PlotDataItem:
    """Build the canonical controller plot item for a real source file."""
    resolved_has_f3 = (
        bool(has_f3)
        if has_f3 is not None
        else ("F3" in df.columns and bool(df["F3"].notna().any()))
    )
    return {
        "name": name,
        "df": df.copy(),
        "df_original": df.copy(),
        "has_f3": resolved_has_f3,
        "is_pre_lobanov": bool(is_pre_lobanov),
    }


def load_plot_item_from_file(
    path: str,
    *,
    existing_pre_lobanov: bool | None = None,
    processor_cls=None,
) -> dict[str, Any]:
    """Load one source path and return a structured load result."""
    processor_cls = processor_cls or DataProcessor
    filename = os.path.basename(path)
    processor = processor_cls()
    success, has_f3, errors = processor.load_files([path])
    is_pre_lobanov = bool(getattr(processor, "is_pre_lobanov", False))

    if success and existing_pre_lobanov is not None:
        if is_pre_lobanov != existing_pre_lobanov:
            success = False
            errors = [(path, config.PARSE_ERR_LOBANOV_MIXED)]

    row_dropped = []
    item = None
    if success:
        raw_df = processor.get_data(copy=False)
        item = make_plot_item(
            name=filename,
            df=raw_df,
            has_f3=has_f3,
            is_pre_lobanov=is_pre_lobanov,
        )
        for dropped_path, drop_report in getattr(processor, "row_drops", []):
            if drop_report:
                row_dropped.append((os.path.basename(dropped_path), drop_report))

    return {
        "success": bool(success),
        "path": path,
        "name": filename,
        "item": item,
        "errors": errors or [],
        "row_dropped": row_dropped,
        "has_f3": bool(has_f3),
        "is_pre_lobanov": is_pre_lobanov,
    }
