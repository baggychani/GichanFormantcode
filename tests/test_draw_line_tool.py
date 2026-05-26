"""DrawLineTool — 완료·롤백·스냅 클릭 (다이얼로그/캔버스 없이)."""

from unittest.mock import MagicMock, patch

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from draw.draw_line import DrawLineTool


def _make_tool(*, on_complete=None):
    fig = Figure(figsize=(4, 4))
    ax = fig.add_subplot(111)
    canvas = FigureCanvasAgg(fig)
    tool = DrawLineTool(
        canvas,
        ax,
        snapping_data=[{"x": 1000.0, "y": 500.0, "label": "a", "color": "blue"}],
        on_complete=on_complete,
    )
    return tool, ax


def _key_event(key):
    ev = MagicMock()
    ev.key = key
    return ev


def _snap_click(tool, ax):
    ev = MagicMock()
    ev.inaxes = ax
    ev.button = 1
    ev.dblclick = False
    with patch("draw.draw_line.snap_query") as sq:
        sq.return_value = {"x": 1000.0, "y": 500.0, "label": "a"}
        tool._on_click(ev)


def test_complete_requires_two_points():
    completed = []
    tool, ax = _make_tool(on_complete=completed.append)
    _snap_click(tool, ax)
    tool.complete()
    assert completed == []


def test_complete_with_two_points():
    completed = []
    tool, ax = _make_tool(on_complete=completed.append)
    _snap_click(tool, ax)
    with patch("draw.draw_line.snap_query") as sq:
        sq.return_value = {"x": 1500.0, "y": 600.0, "label": "i"}
        ev = MagicMock(inaxes=ax, button=1, dblclick=False)
        tool._on_click(ev)
    tool.complete()
    assert len(completed) == 1
    obj = completed[0]
    assert obj.type == "line"
    assert len(obj.points) == 2
    assert obj.point_labels == ["a", "i"]


def test_rollback_removes_last_point():
    tool, ax = _make_tool()
    _snap_click(tool, ax)
    with patch("draw.draw_line.snap_query") as sq:
        sq.return_value = {"x": 1500.0, "y": 600.0, "label": "i"}
        ev = MagicMock(inaxes=ax, button=1, dblclick=False)
        tool._on_click(ev)
    tool.rollback()
    assert len(tool._points) == 1


def test_escape_clears_points():
    tool, ax = _make_tool()
    _snap_click(tool, ax)
    tool._on_key(_key_event("escape"))
    assert tool._points == []
