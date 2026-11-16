"""Outlier removal must drop the outlying rows, from the right file."""

import numpy as np
import pandas as pd
import pytest

from core.outlier_processing_service import OutlierProcessingService
from utils.math_utils import (
    remove_outliers_mahalanobis_scoped,
    remove_outliers_tukey_iqr,
)

_F1_OFFSETS = [0, 3, -2, 5, -4, 1, -1, 4, -5, 2, -3, 0]
_F3_OFFSETS = [2, -4, 5, -1, 3, 0, -5, 1, 4, -2, 0, -3]


def _vowel_frame(label: str, f1_center: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "F1": [f1_center + offset for offset in _F1_OFFSETS],
            "F2": [1500.0 + offset for offset in _F3_OFFSETS],
            "F3": [2500.0 + offset for offset in _F3_OFFSETS],
            "Label": [label] * len(_F1_OFFSETS),
        }
    )


@pytest.mark.parametrize(
    "remove_outliers",
    [remove_outliers_mahalanobis_scoped, remove_outliers_tukey_iqr],
)
def test_f3_plot_outlier_removal_drops_the_outlier_not_its_neighbour(remove_outliers):
    df = pd.concat(
        [_vowel_frame("a", 700.0), _vowel_frame("i", 300.0)], ignore_index=True
    )
    df.loc[0, "F3"] = np.nan  # token without F3 shifts every later position
    df.loc[5, "F3"] = 2900.0  # the only real outlier

    filtered, removed, _per_group, _meta = remove_outliers(
        df, "f1_f3", scope="individual"
    )

    assert sorted(set(df.index) - set(filtered.index)) == [5]
    assert removed == 1
    assert 0 in filtered.index, "tokens without F3 stay available for F1/F2 plots"


@pytest.mark.parametrize(
    "remove_outliers",
    [remove_outliers_mahalanobis_scoped, remove_outliers_tukey_iqr],
)
def test_f3_plot_outlier_removal_handles_outlier_in_last_row(remove_outliers):
    df = _vowel_frame("a", 700.0)
    last = len(df) - 1
    df.loc[0, "F3"] = np.nan
    df.loc[last, "F3"] = 2900.0

    filtered, removed, _per_group, _meta = remove_outliers(
        df, "f1_f3", scope="individual"
    )

    assert sorted(set(df.index) - set(filtered.index)) == [last]
    assert removed == 1


def test_combined_scope_keeps_same_named_files_separate():
    first = _vowel_frame("a", 400.0).drop(columns=["F3"])
    second = _vowel_frame("a", 700.0).drop(columns=["F3"])
    items = [
        {"name": "a.txt", "df": first.copy(), "df_original": first.copy()},
        {"name": "a.txt", "df": second.copy(), "df_original": second.copy()},
    ]

    OutlierProcessingService().apply(
        items, mode="mahalanobis_2sigma", plot_type="f1_f2", scope="combined"
    )

    for item, original in zip(items, (first, second)):
        assert not item["df"].empty
        assert set(item["df"]["F1"]) <= set(original["F1"])
