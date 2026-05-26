"""Compare N-way foundation tests."""

import pandas as pd
import pytest

from core.compare_runtime import (
    apply_compare_render_to_popup,
    build_compare_series_inputs,
    make_compare_plot_key,
    merged_label_move_context,
)
from core.compare_series import (
    CompareLabelBuckets,
    CompareRenderResult,
    CompareSession,
    CompareSeriesInput,
    build_compare_dataset_specs,
    compare_default_save_basename,
    compare_draw_suffix,
    compare_label_offset_key,
    compare_plot_key,
    compare_window_title,
    default_series_color,
    legacy_key_from_series_id,
    normalize_series_ref,
    series_id_from_legacy,
)
from core.compare_settings import (
    default_compare_design_settings,
    get_series_design_cfg,
    normalize_compare_design_settings,
    pack_compare_design_settings,
)


def test_legacy_series_roundtrip():
    assert legacy_key_from_series_id(0) == "blue"
    assert legacy_key_from_series_id(1) == "red"
    assert legacy_key_from_series_id(2) == "series_2"
    assert series_id_from_legacy("blue") == 0
    assert series_id_from_legacy("red") == 1
    assert series_id_from_legacy("series_3") == 3


def test_normalize_series_ref_accepts_int_and_legacy():
    assert normalize_series_ref(0) == 0
    assert normalize_series_ref("blue") == 0
    assert normalize_series_ref("1") == 1
    assert normalize_series_ref("red") == 1
    assert normalize_series_ref("series_2") == 2


def test_normalize_series_ref_rejects_unknown_legacy():
    with pytest.raises(ValueError):
        normalize_series_ref("green")


def test_compare_session_from_data_indices():
    session = CompareSession.from_data_indices(3, 7)
    assert session.count == 2
    assert session.data_index(0) == 3
    assert session.data_index(1) == 7
    assert session.legacy_key(0) == "blue"
    assert session.legacy_key(1) == "red"


def test_compare_session_requires_at_least_two_indices():
    with pytest.raises(ValueError):
        CompareSession.from_data_indices(1)


def test_default_series_palette():
    assert default_series_color(0) != default_series_color(1)
    assert default_series_color(2) != default_series_color(0)


def test_normalize_compare_design_settings_adds_series_mirror():
    settings = {
        "common": {"show_raw": True},
        "blue": {"ell_style": "-", "lbl_color": "#111111"},
        "red": {"ell_style": "--", "lbl_color": "#222222"},
    }
    out = normalize_compare_design_settings(settings)
    assert out["blue"]["lbl_color"] == "#111111"
    assert out["red"]["lbl_color"] == "#222222"
    assert out["series"]["0"]["lbl_color"] == "#111111"
    assert out["series"]["1"]["lbl_color"] == "#222222"


def test_get_series_design_cfg_from_series_block():
    settings = normalize_compare_design_settings(
        {
            "common": {},
            "series": {"0": {"ell_style": "---"}},
        }
    )
    assert get_series_design_cfg(settings, "blue")["ell_style"] == "---"
    assert get_series_design_cfg(settings, 1)["ell_style"] == "--"


def test_pack_compare_design_settings_legacy_and_series():
    packed = pack_compare_design_settings(
        common={"font_style": "serif"},
        series_cfgs=[{"ell_style": "-"}, {"ell_style": "--"}],
    )
    assert packed["blue"]["ell_style"] == "-"
    assert packed["red"]["ell_style"] == "--"
    assert packed["series"]["0"]["ell_style"] == "-"
    assert packed["series"]["1"]["ell_style"] == "--"


def test_default_compare_design_settings_shape():
    defaults = default_compare_design_settings()
    assert "common" in defaults
    assert "blue" in defaults
    assert "red" in defaults
    assert defaults["series"]["0"]["ell_style"] == "-"
    assert defaults["series"]["1"]["ell_style"] == "--"


def test_build_compare_dataset_specs():
    specs = build_compare_dataset_specs(
        [
            CompareSeriesInput(
                df="DF0",
                display_name="A",
                filter_state={"a": "ON"},
                design_cfg={"ell_style": "-"},
                custom_label_offsets={"a": (1, 2)},
            ),
            CompareSeriesInput(
                df="DF1",
                display_name="B",
                filter_state={"e": "OFF"},
                design_cfg={"ell_style": "--"},
            ),
        ]
    )
    assert len(specs) == 2
    assert specs[0].series_id == 0
    assert specs[0].legacy_key == "blue"
    assert specs[0].df == "DF0"
    assert specs[1].display_name == "B"
    assert specs[0].custom_label_offsets["a"] == (1, 2)


def test_build_compare_dataset_specs_requires_at_least_two():
    with pytest.raises(ValueError):
        build_compare_dataset_specs([CompareSeriesInput(df="DF0", display_name="A")])


def test_compare_label_buckets_store_all_series():
    buckets = CompareLabelBuckets()
    buckets.append_label_data(0, {"vowel": "a"})
    buckets.append_label_data(2, {"vowel": "u"})
    label_data, artists = buckets.as_dicts()
    assert label_data[0][0]["vowel"] == "a"
    assert label_data[2][0]["vowel"] == "u"
    assert buckets.label_data_blue == label_data[0]
    assert buckets.label_data_red == []


def test_compare_render_result_legacy_tuple():
    result = CompareRenderResult(
        ax="AX",
        snapping_data=[{"x": 1}],
        label_data={0: [{"vowel": "a"}], 1: [{"vowel": "i"}]},
        label_text_artists={0: ["T0"], 1: ["T1"]},
    )
    ax, snap, blue, red, ta_blue, ta_red = result.legacy_tuple()
    assert ax == "AX"
    assert snap == [{"x": 1}]
    assert blue[0]["vowel"] == "a"
    assert red[0]["vowel"] == "i"
    assert ta_blue == ["T0"]
    assert ta_red == ["T1"]


def test_compare_plot_key_and_offset_key():
    plot_key = compare_plot_key((1, 2, 3), "f1_f2")
    assert plot_key == (1, 2, 3, "f1_f2")
    assert compare_label_offset_key(plot_key, "series_2") == (
        1,
        2,
        3,
        "f1_f2",
        "series_2",
    )


def test_compare_naming_helpers():
    assert compare_window_title(["A", "B", "C"]) == "A 외 2개"
    assert compare_default_save_basename(["a.txt", "b.txt", "c.txt"]) == "a_b_c"
    assert compare_draw_suffix(2) == "3"


def _dummy_df():
    return pd.DataFrame(
        {
            "F1": [500.0, 520.0, 510.0],
            "F2": [1500.0, 1600.0, 1550.0],
            "Label": ["a", "a", "a"],
        }
    )


def test_draw_compare_plot_supports_three_series():
    from matplotlib.figure import Figure

    from engine.plot_engine import PlotEngine

    engine = PlotEngine()
    fig = Figure(figsize=(4, 4))
    result = engine.draw_compare_plot(
        fig,
        [
            CompareSeriesInput(df=_dummy_df(), display_name="A"),
            CompareSeriesInput(df=_dummy_df(), display_name="B"),
            CompareSeriesInput(df=_dummy_df(), display_name="C"),
        ],
        {
            "type": "f1_f2",
            "origin": "bottom_left",
            "f1_scale": "linear",
            "f2_scale": "linear",
        },
    )
    assert isinstance(result, CompareRenderResult)
    assert 0 in result.label_data
    assert 1 in result.label_data
    assert 2 in result.label_data
    assert len(result.label_data[2]) >= 1


class _PopupStub:
    compare_session = CompareSession.from_data_indices(0, 1, 2)

    def get_design_settings(self):
        return None

    def get_filter_state_for_series(self, series_id):
        return {}

    def get_layer_design_overrides_for_series(self, series_id):
        return {}


class _ControllerStub:
    plot_data_list = [
        {"name": "A.txt", "df": _dummy_df()},
        {"name": "B.txt", "df": _dummy_df()},
        {"name": "C.txt", "df": _dummy_df()},
    ]
    custom_label_offsets = {}

    def get_data_item_at(self, idx):
        return self.plot_data_list[idx]

    def _apply_normalization(self, df, norm):
        return df


def test_build_compare_series_inputs_for_three_series():
    session = CompareSession.from_data_indices(0, 1, 2)
    plot_key = make_compare_plot_key(session, "f1_f2")
    inputs = build_compare_series_inputs(
        _ControllerStub(),
        session,
        _PopupStub(),
        design_settings=None,
        plot_type="f1_f2",
        norm=None,
        plot_key=plot_key,
    )
    assert len(inputs) == 3
    assert inputs[2].display_name == "C.txt"


def test_apply_compare_render_to_popup_sets_by_series():
    popup = _PopupStub()
    result = CompareRenderResult(
        ax=None,
        snapping_data=[],
        label_data={0: [{"vowel": "a"}], 2: [{"vowel": "u"}]},
        label_text_artists={0: ["A"], 2: ["U"]},
    )
    session = CompareSession.from_data_indices(0, 1, 2)
    apply_compare_render_to_popup(popup, result, session, (0, 1, 2, "f1_f2"))
    assert popup.label_data_by_series[2][0]["vowel"] == "u"
    assert popup.label_text_artists_by_series[2] == ["U"]


def test_merged_label_move_context_combines_all_series():
    popup = _PopupStub()
    popup.label_data_by_series = {
        0: [{"vowel": "a", "lx": 1.0, "ly": 2.0}],
        1: [{"vowel": "i", "lx": 3.0, "ly": 4.0}],
    }
    popup.label_text_artists_by_series = {0: ["A-art"], 1: ["I-art"]}
    label_data, artists = merged_label_move_context(popup)
    assert len(label_data) == 2
    assert {entry["series"] for entry in label_data} == {"blue", "red"}
    assert artists == ["A-art", "I-art"]


def test_merged_label_move_context_legacy_blue_red():
    class _LegacyPopup:
        label_data_blue = [{"vowel": "a", "lx": 1.0, "ly": 2.0}]
        label_data_red = [{"vowel": "u", "lx": 5.0, "ly": 6.0}]
        label_text_artists_blue = ["A"]
        label_text_artists_red = ["U"]

    label_data, artists = merged_label_move_context(_LegacyPopup())
    assert len(label_data) == 2
    assert label_data[0]["series"] == "blue"
    assert label_data[1]["series"] == "red"
    assert artists == ["A", "U"]
