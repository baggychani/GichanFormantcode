"""Typed contracts for controller-level plot data and render params."""

from __future__ import annotations

from typing import TypedDict

import pandas as pd


class _PlotDataItemRequired(TypedDict):
    name: str
    df: pd.DataFrame
    df_original: pd.DataFrame
    has_f3: bool


class PlotDataItem(_PlotDataItemRequired, total=False):
    """plot_data_list 항목의 canonical dict 계약."""

    is_pre_lobanov: bool
    is_combined: bool
    combined_source_names: list[str]


class _PlotParamsRequired(TypedDict):
    type: str
    f1_scale: str
    f2_scale: str
    origin: str
    use_bark_units: bool
    sigma: float


class PlotParams(_PlotParamsRequired, total=False):
    """플롯 렌더·저장에 쓰이는 파라미터 dict 계약."""

    f1_unit: str
    f2_unit: str
    normalization: str | None
    outlier_mode: str | None
    distance_unit: str
