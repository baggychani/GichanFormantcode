"""draw_layer_render — 선·영역·참조선·넓이 라벨 렌더 및 오류 로그."""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from draw.draw_common import (
    AreaLabelObject,
    LineObject,
    PolygonObject,
    ReferenceLineObject,
)
from draw.draw_layer_render import _line_style_to_mpl, render_draw_objects
from ui.widgets.layer_logic import apply_line_settings


def _make_ax():
    fig = Figure(figsize=(6.5, 6.5), dpi=100)
    ax = fig.add_subplot(111)
    ax.set_xlim(500, 2500)
    ax.set_ylim(200, 900)
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    return ax


def _ctx(**kwargs):
    base = {
        "design_settings": {"font_style": "sans"},
        "normalization": None,
        "fixed_plot_params": {},
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_line_style_to_mpl():
    assert _line_style_to_mpl("-") == "-"
    assert _line_style_to_mpl("---") == (0, (6.0, 3.0))
    assert _line_style_to_mpl("unknown") == "--"


def test_render_line_basic():
    ax = _make_ax()
    obj = LineObject(points=[(800.0, 400.0), (1200.0, 500.0), (1600.0, 450.0)])
    apply_line_settings(obj, {"line_color": "#FF0000"})
    artists = render_draw_objects(ax, [obj], _ctx(), show_editor_chrome=False)
    assert len(artists) >= 1


def test_render_line_with_end_arrow():
    ax = _make_ax()
    obj = LineObject(
        points=[(800.0, 400.0), (1600.0, 450.0)],
        arrow_mode="end",
        arrow_head="stealth",
    )
    artists = render_draw_objects(ax, [obj], _ctx(), show_editor_chrome=False)
    assert len(artists) >= 2


def test_render_polygon_and_area_label():
    ax = _make_ax()
    poly = PolygonObject(
        points=[(900.0, 350.0), (1400.0, 350.0), (1150.0, 550.0)],
        id="p1",
        fill_color="#3366CC",
    )
    label = AreaLabelObject(parent_id="p1", value=12345.0, x=1150.0, y=420.0)
    artists = render_draw_objects(ax, [poly, label], _ctx(), show_editor_chrome=False)
    assert len(artists) >= 2


def test_render_polygon_transparent_fill():
    ax = _make_ax()
    poly = PolygonObject(
        points=[(900.0, 350.0), (1400.0, 350.0), (1150.0, 550.0)],
        fill_color="transparent",
    )
    artists = render_draw_objects(ax, [poly], _ctx(), show_editor_chrome=False)
    assert len(artists) == 1


def test_render_reference_horizontal():
    ax = _make_ax()
    ref = ReferenceLineObject(mode="horizontal", value=500.0, axis_units="Hz")
    artists = render_draw_objects(ax, [ref], _ctx(), show_editor_chrome=False)
    assert len(artists) >= 2


def test_render_reference_vertical():
    ax = _make_ax()
    ref = ReferenceLineObject(mode="vertical", value=1500.0, axis_units="Hz")
    artists = render_draw_objects(ax, [ref], _ctx(), show_editor_chrome=False)
    assert len(artists) >= 2


def test_render_skips_invisible():
    ax = _make_ax()
    hidden = LineObject(
        points=[(800.0, 400.0), (1600.0, 450.0)],
        visible=False,
    )
    assert render_draw_objects(ax, [hidden], _ctx(), show_editor_chrome=False) == []


def test_render_skip_types():
    ax = _make_ax()
    ref = ReferenceLineObject(mode="horizontal", value=500.0)
    artists = render_draw_objects(
        ax,
        [ref],
        _ctx(),
        skip_types=frozenset({"reference"}),
        show_editor_chrome=False,
    )
    assert artists == []


def test_render_logs_on_primary_failure(caplog, monkeypatch):
    ax = _make_ax()
    bad = MagicMock()
    bad.visible = True
    bad.type = "line"
    bad.semi = False
    bad.id = "bad1"
    bad.points = [(0.0, 0.0)]

    def _boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr("draw.draw_layer_render._render_line", _boom)

    with caplog.at_level(logging.DEBUG, logger="draw.draw_layer_render"):
        artists = render_draw_objects(ax, [bad], _ctx(), show_editor_chrome=False)

    assert artists == []
    assert any("draw render skip (primary)" in r.message for r in caplog.records)


def test_area_label_refs_populated():
    ax = _make_ax()
    label = AreaLabelObject(value=100.0, x=1000.0, y=500.0, axis_units="Hz")
    refs = []
    render_draw_objects(
        ax,
        [label],
        _ctx(),
        show_editor_chrome=False,
        area_label_refs=refs,
    )
    assert len(refs) == 1
    assert refs[0][1] is label
