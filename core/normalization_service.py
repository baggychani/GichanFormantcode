"""Normalization service for formant DataFrames.

Controller keeps thin compatibility wrappers, while the actual method dispatch
and pre-normalized Lobanov handling live here.
"""

from __future__ import annotations

import pandas as pd

from utils import app_logger
from utils.math_utils import (
    bigham_normalization,
    gerstman_normalization,
    lobanov_normalization,
    nearey1_normalization,
    to_phonetic_vowel,
    watt_fabricius_normalization,
)


def apply_normalization(
    df: pd.DataFrame,
    norm_name: str | None,
    *,
    is_pre_lobanov: bool = False,
) -> pd.DataFrame:
    """Apply a named normalization method to a raw formant DataFrame."""
    if df is None:
        return df
    if not norm_name:
        return df.copy()
    if norm_name == "Lobanov" and is_pre_lobanov:
        return df.copy()

    df_norm = df.copy()
    label_col = "Label" if "Label" in df_norm.columns else "label"

    if norm_name == "Lobanov":
        return lobanov_normalization(df_norm)
    if norm_name == "Gerstman":
        return gerstman_normalization(df_norm)
    if norm_name == "2mW/F":
        df_norm["Vowel"] = df_norm[label_col].apply(to_phonetic_vowel)
        if not (df_norm["Vowel"] == "i").any() or not (df_norm["Vowel"] == "a").any():
            unique_vowels = sorted(df_norm["Vowel"].dropna().unique())
            app_logger.warning(
                "[2mW/F] 코너 모음 'i' 또는 'a' 토큰이 없어 정규화가 적용되지 않았습니다. "
                f"(현재 라벨: {unique_vowels[:10]}{' …' if len(unique_vowels) > 10 else ''})"
            )
        return watt_fabricius_normalization(df_norm, variant="2m")
    if norm_name == "Bigham":
        return bigham_normalization(df_norm)
    if norm_name == "Nearey1":
        return nearey1_normalization(df_norm)
    return df_norm


def normalize_dataframe(
    df: pd.DataFrame,
    norm_name: str | None,
    data_item: dict | None = None,
) -> pd.DataFrame:
    """Normalize a DataFrame while respecting the item pre-Lobanov flag."""
    is_pre_lobanov = bool(data_item and data_item.get("is_pre_lobanov"))
    return apply_normalization(df, norm_name, is_pre_lobanov=is_pre_lobanov)
