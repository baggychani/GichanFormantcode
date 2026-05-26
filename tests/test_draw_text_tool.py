"""DrawTextTool — 더블클릭 이벤트 필터 (다이얼로그 없이)."""

from unittest.mock import MagicMock, patch

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from draw.draw_text import DrawTextTool


def _make_tool(*, hit_text_at=None, on_complete=None):
    fig = Figure(figsize=(4, 4))
    ax = fig.add_subplot(111)
    canvas = FigureCanvasAgg(fig)
    tool = DrawTextTool(
        canvas,
        ax,
        axis_units="Hz",
        hit_text_at=hit_text_at,
        on_complete=on_complete,
    )
    return tool, ax


def _click_event(ax, *, dblclick=True, button=1, inaxes=True, xdata=1000.0, ydata=500.0):
    ev = MagicMock()
    ev.dblclick = dblclick
    ev.button = button
    ev.inaxes = ax if inaxes else None
    ev.xdata = xdata if inaxes else None
    ev.ydata = ydata if inaxes else None
    ev.x = 200
    ev.y = 200
    return ev


def test_on_click_ignores_single_click():
    on_complete = MagicMock()
    tool, ax = _make_tool(on_complete=on_complete)
    tool._on_click(_click_event(ax, dblclick=False))
    on_complete.assert_not_called()


def test_on_click_ignores_when_over_existing_text():
    hit = MagicMock(return_value=object())
    on_complete = MagicMock()
    tool, ax = _make_tool(hit_text_at=hit, on_complete=on_complete)
    with patch("draw.draw_text.DrawTextDialog") as dlg_cls:
        tool._on_click(_click_event(ax))
        dlg_cls.assert_not_called()
    hit.assert_called_once()


@patch("draw.draw_text.DrawTextDialog")
def test_on_click_creates_text_object_on_accept(mock_dialog_cls):
    completed = []

    dlg = MagicMock()
    dlg.exec.return_value = True
    dlg.get_text.return_value = "  hello  "
    mock_dialog_cls.return_value = dlg

    tool, ax = _make_tool(on_complete=completed.append)
    tool._on_click(_click_event(ax, xdata=1200.0, ydata=600.0))

    assert len(completed) == 1
    obj = completed[0]
    assert obj.text == "  hello  "
    assert obj.x == 1200.0
    assert obj.y == 600.0
    assert obj.axis_units == "Hz"
    assert obj.type == "text"


@patch("draw.draw_text.DrawTextDialog")
def test_on_click_skips_empty_text(mock_dialog_cls):
    dlg = MagicMock()
    dlg.exec.return_value = True
    dlg.get_text.return_value = "   \n  "
    mock_dialog_cls.return_value = dlg

    completed = []
    tool, ax = _make_tool(on_complete=completed.append)
    tool._on_click(_click_event(ax))
    assert completed == []


@patch("draw.draw_text.DrawTextDialog")
def test_on_click_cancel_dialog(mock_dialog_cls):
    dlg = MagicMock()
    dlg.exec.return_value = False
    mock_dialog_cls.return_value = dlg

    completed = []
    tool, ax = _make_tool(on_complete=completed.append)
    tool._on_click(_click_event(ax))
    assert completed == []
    dlg.get_text.assert_not_called()
