"""Pure-ish outlier filtering for workspace plot items."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from utils.math_utils import remove_outliers_mahalanobis_scoped, remove_outliers_tukey_iqr


@dataclass
class OutlierResult:
    total_removed: int = 0
    file_removed: list[tuple[str, int]] = field(default_factory=list)
    files_with_small_labels: list[tuple[str, list[str]]] = field(default_factory=list)
    any_label_tested: bool = False


class OutlierProcessingService:
    """Apply one outlier policy to real source items, never derived Combined data."""

    def __init__(self, *, mahalanobis_filter=None, tukey_filter=None) -> None:
        self.mahalanobis_filter = mahalanobis_filter or remove_outliers_mahalanobis_scoped
        self.tukey_filter = tukey_filter or remove_outliers_tukey_iqr

    def apply(
        self,
        items: list[dict[str, Any]],
        *,
        mode: str | None,
        plot_type: str,
        scope: str,
    ) -> OutlierResult:
        real_items = [item for item in items if not item.get("is_combined")]
        self._ensure_originals(real_items)
        if mode is None:
            for item in real_items:
                item["df"] = item["df_original"].copy()
            return OutlierResult()
        if scope == "combined" and len(real_items) >= 2:
            return self._apply_combined(real_items, mode, plot_type)
        return self._apply_individual(real_items, mode, plot_type)

    @staticmethod
    def _ensure_originals(items: list[dict[str, Any]]) -> None:
        for item in items:
            if "df_original" not in item:
                item["df_original"] = item["df"].copy()

    def _filter(self, dataframe: pd.DataFrame, mode: str, plot_type: str, scope: str):
        if mode == "tukey_iqr":
            return self.tukey_filter(dataframe, plot_type, scope=scope)
        return self.mahalanobis_filter(dataframe, plot_type, scope=scope)

    def _apply_combined(
        self, items: list[dict[str, Any]], mode: str, plot_type: str
    ) -> OutlierResult:
        pieces: list[pd.DataFrame] = []
        originals: dict[str, pd.DataFrame] = {}
        for item in items:
            name = str(item.get("name", ""))
            original = item.get("df_original")
            if original is None or original.empty:
                continue
            original = original.reset_index(drop=True).copy()
            originals[name] = original
            piece = original.copy()
            piece["_src_name"] = name
            piece["_src_row"] = np.arange(len(original), dtype=int)
            pieces.append(piece)
        combined = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
        filtered, removed, _unused, meta = self._filter(combined, mode, plot_type, "combined")
        self._distribute_combined(filtered, items, originals)
        result = OutlierResult(total_removed=int(removed or 0))
        if not combined.empty and filtered is not None:
            before = combined["_src_name"].value_counts().to_dict()
            after = filtered["_src_name"].value_counts().to_dict() if not filtered.empty else {}
            result.file_removed = [
                (item.get("name", ""), int(before.get(str(item.get("name", "")), 0)) - int(after.get(str(item.get("name", "")), 0)))
                for item in items
                if int(before.get(str(item.get("name", "")), 0)) > int(after.get(str(item.get("name", "")), 0))
            ]
        too_small = (meta or {}).get("groups_too_small") or set()
        if too_small:
            result.files_with_small_labels.append(("Combined(통합)", sorted(too_small)))
        result.any_label_tested = bool((meta or {}).get("groups_tested"))
        return result

    @staticmethod
    def _distribute_combined(
        filtered: pd.DataFrame | None,
        items: list[dict[str, Any]],
        originals: dict[str, pd.DataFrame],
    ) -> None:
        if filtered is None or filtered.empty:
            for item in items:
                original = item.get("df_original")
                item["df"] = original.iloc[0:0].copy() if hasattr(original, "iloc") else original
            return
        kept = set(zip(filtered["_src_name"].astype(str), filtered["_src_row"].astype(int)))
        for item in items:
            name = str(item.get("name", ""))
            original = originals.get(name)
            if original is None:
                item["df"] = item.get("df_original", item.get("df")).copy()
                continue
            item["df"] = original.iloc[[row for row in range(len(original)) if (name, row) in kept]].copy()

    def _apply_individual(
        self, items: list[dict[str, Any]], mode: str, plot_type: str
    ) -> OutlierResult:
        result = OutlierResult()
        for item in items:
            source = item["df_original"].copy()
            source["Speaker"] = item.get("name", "")
            filtered, removed, _unused, meta = self._filter(source, mode, plot_type, "individual")
            if isinstance(filtered, pd.DataFrame):
                filtered = filtered.drop(columns=["Speaker"], errors="ignore")
            item["df"] = filtered
            removed = int(removed or 0)
            result.total_removed += removed
            if removed:
                result.file_removed.append((item["name"], removed))
            too_small = (meta or {}).get("groups_too_small") or set()
            if too_small:
                result.files_with_small_labels.append((item["name"], sorted(too_small)))
            result.any_label_tested = result.any_label_tested or bool(
                (meta or {}).get("groups_tested")
            )
        return result
