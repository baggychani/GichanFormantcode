"""참조선 렌더 — 깨진 객체 필드 누락 시에도 크래시 없음."""

from types import SimpleNamespace

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from draw.draw_layer_render import render_draw_objects


def _make_ax():
    fig = Figure(figsize=(6.5, 6.5), dpi=100)
    ax = fig.add_subplot(111)
    ax.set_xlim(500, 2500)
    ax.set_ylim(200, 900)
    FigureCanvasAgg(fig).draw()
    return ax


def test_render_reference_missing_value_does_not_crash():
    ax = _make_ax()

    class RefWithoutValue:
        type = "reference"
        visible = True
        semi = False
        mode = "horizontal"
        id = "r1"
        axis_units = "Hz"
        axis_scale = "linear"

    ctx = SimpleNamespace(
        design_settings={},
        normalization=None,
        fixed_plot_params={},
    )
    artists = render_draw_objects(
        ax, [RefWithoutValue()], ctx, show_editor_chrome=False
    )
    assert len(artists) >= 2
