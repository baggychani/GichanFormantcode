"""Combined/compare 표시 유틸 테스트."""

from ui.widgets.display_utils import (
    compare_item_legend_display,
    format_combined_group_short_label,
    format_combined_members_tooltip,
)


def test_format_combined_group_short_label():
    names = ["GichanFormant_박성진_Short.txt", "GichanFormant_김철수_Short.txt"]
    assert format_combined_group_short_label(names) == "박성진_Short 외 1명"


def test_format_combined_group_short_label_truncates_long_line():
    names = ["very_long_speaker_name_A.txt", "b.txt", "c.txt"]
    label = format_combined_group_short_label(names, max_first_len=20)
    assert len(label) <= 20
    assert label.endswith("...")


def test_format_combined_members_tooltip():
    names = ["a.txt", "b.txt", "c.txt"]
    tip = format_combined_members_tooltip(names)
    assert tip.startswith("포함 3명")
    assert "· a" in tip
    assert "· c" in tip


def test_compare_item_legend_display_combined():
    item = {
        "name": "GichanFormant_Combined (2명)",
        "is_combined": True,
        "combined_source_names": ["x.txt", "y.txt"],
    }
    short, tip, members = compare_item_legend_display(item)
    assert short == "x 외 1명"
    assert "포함 2명" in tip
    assert members == ["x.txt", "y.txt"]
