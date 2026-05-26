"""그리기 텍스트 — 설정 적용·렌더."""

from types import SimpleNamespace

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from draw.draw_common import TextObject
from draw.draw_layer_render import render_draw_objects
from draw.text_render import clamp_text_font_size, render_text_object
from ui.widgets.layer_logic import apply_text_settings


def _make_ax():
    fig = Figure(figsize=(6.5, 6.5), dpi=100)
    ax = fig.add_subplot(111)
    ax.set_xlim(500, 2500)
    ax.set_ylim(200, 900)
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    return ax, fig, canvas


def test_clamp_text_font_size():
    assert clamp_text_font_size(14.0) == 14.0
    assert clamp_text_font_size(2.0) == 4.0
    assert clamp_text_font_size(999.0) == 200.0


def test_apply_text_settings_partial_update():
    obj = TextObject(text="x", font_size=14.0, font_bold=False, text_color="#303133")
    apply_text_settings(obj, {"font_size": 20.0, "font_bold": True})
    assert obj.font_size == 20.0
    assert obj.font_bold is True
    assert obj.font_italic is False
    assert obj.text_color == "#303133"


def test_apply_text_settings_clamps_font_size():
    obj = TextObject(text="x")
    apply_text_settings(obj, {"font_size": 500.0})
    assert obj.font_size == 200.0
    apply_text_settings(obj, {"font_size": 1.0})
    assert obj.font_size == 4.0


def test_apply_text_settings_ignores_bad_font_size():
    obj = TextObject(text="x", font_size=14.0)
    apply_text_settings(obj, {"font_size": "not-a-number"})
    assert obj.font_size == 14.0


def test_render_text_object_creates_artists():
    ax, _fig, _canvas = _make_ax()
    ctx = SimpleNamespace(design_settings={"font_style": "sans"})
    obj = TextObject(text="heed", x=1500.0, y=500.0, font_size=12.0)
    artists = render_text_object(ax, obj, ctx)
    assert len(artists) >= 1


def test_render_text_object_mixed_korean_ipa():
    ax, _fig, _canvas = _make_ax()
    ctx = SimpleNamespace(design_settings={"font_style": "serif"})
    obj = TextObject(text="heed 안녕 [i]", x=1200.0, y=400.0)
    artists = render_text_object(ax, obj, ctx)
    assert len(artists) >= 2


def test_render_text_object_multiline():
    ax, _fig, _canvas = _make_ax()
    ctx = SimpleNamespace(design_settings={"font_style": "sans"})
    obj = TextObject(text="line1\nline2", x=1000.0, y=600.0)
    artists = render_text_object(ax, obj, ctx)
    assert len(artists) >= 2


def test_render_text_object_empty_or_hidden():
    ax, _fig, _canvas = _make_ax()
    ctx = SimpleNamespace(design_settings={})
    assert render_text_object(ax, TextObject(text="   "), ctx) == []
    hidden = TextObject(text="hi", visible=False)
    assert render_text_object(ax, hidden, ctx) == []


def test_render_text_object_selected_adds_outline():
    ax, fig, canvas = _make_ax()
    ctx = SimpleNamespace(design_settings={"font_style": "sans"})
    obj = TextObject(text="label", x=1500.0, y=500.0, id="t1")
    plain = render_text_object(ax, obj, ctx, selected=False, show_editor_chrome=True)
    selected = render_text_object(
        ax, obj, ctx, selected=True, show_editor_chrome=True
    )
    assert len(selected) > len(plain)


def test_render_draw_objects_includes_text():
    ax, _fig, _canvas = _make_ax()
    ctx = SimpleNamespace(
        design_settings={"font_style": "sans"},
        normalization=None,
        fixed_plot_params={},
    )
    objs = [
        TextObject(text="note", x=1500.0, y=500.0, id="txt1"),
    ]
    artists = render_draw_objects(ax, objs, ctx, show_editor_chrome=False)
    assert len(artists) >= 1


def test_render_draw_objects_skip_text_type():
    ax, _fig, _canvas = _make_ax()
    ctx = SimpleNamespace(
        design_settings={},
        normalization=None,
        fixed_plot_params={},
    )
    objs = [TextObject(text="note", x=1500.0, y=500.0)]
    artists = render_draw_objects(
        ax, objs, ctx, skip_types=frozenset({"text"}), show_editor_chrome=False
    )
    assert artists == []
