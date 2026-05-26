"""Combined plot_data_list 항목 구성 테스트."""

import pandas as pd

from model.combined_dataset import build_combined_entry, build_compare_group_entry
from ui.widgets.display_utils import strip_gichan_prefix


def _item(name: str, rows: int = 1):
    df = pd.DataFrame(
        {"F1": [500.0] * rows, "F2": [1500.0] * rows, "label": ["a"] * rows}
    )
    return {"name": name, "df": df, "df_original": df.copy(), "has_f3": False}


def test_build_combined_entry_uses_gichan_prefix_and_display_strip():
    real = [_item("GichanFormant_spk1.txt"), _item("GichanFormant_spk2.txt")]
    combined = build_combined_entry(real)
    assert combined is not None
    assert combined["is_combined"] is True
    assert combined["name"].startswith("GichanFormant_")
    assert strip_gichan_prefix(combined["name"]) == "Combined (2명)"


def test_build_combined_entry_requires_two_speakers():
    assert build_combined_entry([_item("a.txt")]) is None


def test_build_compare_group_entry_single_file():
    one = _item("spk1.txt")
    group = build_compare_group_entry([one])
    assert group is not None
    assert group["is_combined"] is False
    assert group["name"] == "spk1.txt"
    assert len(group["df"]) == 1


def test_build_combined_entry_stores_source_names():
    real = [_item("GichanFormant_a.txt"), _item("GichanFormant_b.txt")]
    combined = build_combined_entry(real)
    assert combined is not None
    assert combined["combined_source_names"] == [
        "GichanFormant_a.txt",
        "GichanFormant_b.txt",
    ]


def test_build_compare_group_entry_multi_combines():
    group = build_compare_group_entry([_item("a.txt"), _item("b.txt")])
    assert group is not None
    assert group["is_combined"] is True
    assert len(group["df"]) == 2
    assert group["combined_source_names"] == ["a.txt", "b.txt"]
