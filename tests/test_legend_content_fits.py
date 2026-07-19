from __future__ import annotations

from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure

from draw.draw_common import LegendEntry, LegendObject
from draw.legend_helpers import build_legend_pixel_layout, ensure_legend_content_fits


def _popup():
    return SimpleNamespace(design_settings={"font_style": "sans"})


def test_legend_width_shrinks_when_text_shortens():
    fig = Figure(figsize=(8, 6), dpi=120)
    legend = LegendObject(
        entries=[LegendEntry(series_id=0, text="아주아주아주아주아주긴파일이름입니다")],
        fx=0.05,
        fy=0.25,
        width_frac=0.42,
        height_frac=0.08,
        font_size=10,
        font_family="Noto Sans KR",
    )
    popup = _popup()

    ensure_legend_content_fits(legend, fig, popup)
    wide = float(legend.width_frac)
    assert wide > 0.12

    legend.entries = [LegendEntry(series_id=0, text="짧은이름")]
    ensure_legend_content_fits(legend, fig, popup)
    narrow = float(legend.width_frac)
    assert narrow < wide
    assert narrow >= 0.05


def test_legend_width_grows_when_text_lengthens():
    fig = Figure(figsize=(8, 6), dpi=120)
    legend = LegendObject(
        entries=[LegendEntry(series_id=0, text="짧음")],
        fx=0.05,
        fy=0.25,
        width_frac=0.10,
        height_frac=0.08,
        font_size=12,
        font_family="Noto Sans KR",
    )
    popup = _popup()

    ensure_legend_content_fits(legend, fig, popup)
    short_w = float(legend.width_frac)

    legend.entries = [LegendEntry(series_id=0, text="2000년대_여성_강현지")]
    ensure_legend_content_fits(legend, fig, popup)
    long_w = float(legend.width_frac)
    assert long_w > short_w


def test_legend_box_covers_longest_entry_pixel_layout():
    """가장 긴 줄 기준으로 박스가 아이콘+텍스트+좌우동일패딩을 덮는지."""
    fig = Figure(figsize=(8, 6), dpi=120)
    long = "2000년대_여성_강현지"
    legend = LegendObject(
        entries=[
            LegendEntry(series_id=0, text="짧음"),
            LegendEntry(series_id=1, text=long),
        ],
        fx=0.05,
        fy=0.30,
        width_frac=0.12,
        height_frac=0.08,
        font_size=10,
        font_family="Noto Sans KR",
    )
    layout = build_legend_pixel_layout(legend, fig, _popup())
    assert layout.pad_l == layout.pad_r
    # 박스 내부: pad + icon + gap + text + pad
    needed = layout.pad_l + layout.icon_w + layout.gap + layout.max_text_w + layout.pad_r
    assert layout.box_w_px + 1e-6 >= needed
    assert legend.width_frac * layout.fig_w + 1e-6 >= needed


def test_legend_padding_does_not_scale_with_text_length():
    """글자가 길어져도 좌우 패딩(px)은 동일·고정."""
    fig = Figure(figsize=(8, 6), dpi=120)
    popup = _popup()
    short = LegendObject(
        entries=[LegendEntry(series_id=0, text="짧음")],
        fx=0.05,
        fy=0.25,
        width_frac=0.10,
        height_frac=0.08,
        font_size=10,
        font_family="Noto Sans KR",
    )
    long = LegendObject(
        entries=[
            LegendEntry(
                series_id=0,
                text="2000년대_개병신_홍명보남아공상대로도짐병신OUT",
            )
        ],
        fx=0.05,
        fy=0.25,
        width_frac=0.10,
        height_frac=0.08,
        font_size=10,
        font_family="Noto Sans KR",
    )
    a = build_legend_pixel_layout(short, fig, popup)
    b = build_legend_pixel_layout(long, fig, popup)
    assert a.pad_l == b.pad_l == a.pad_r == b.pad_r
    # 여유분이 글자 길이에 비례하지 않음 (박스 증가분 ≈ 텍스트 증가분)
    delta_box = b.box_w_px - a.box_w_px
    delta_text = b.max_text_w - a.max_text_w
    assert abs(delta_box - delta_text) < 1.0
