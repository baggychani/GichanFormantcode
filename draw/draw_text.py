# draw/draw_text.py — 캔버스 텍스트 배치

from __future__ import annotations

import logging
import uuid
from typing import Callable

from ui.dialogs.draw_text_dialog import DrawTextDialog

from .draw_common import TextObject

_log = logging.getLogger(__name__)


class DrawTextTool:
    """텍스트 그리기: 더블클릭 → 다이얼로그 → 레이어 등록 (단일 클릭은 이동용)."""

    def __init__(
        self,
        canvas,
        ax,
        *,
        axis_units: str = "Hz",
        parent_window=None,
        ui_font_name: str = "Malgun Gothic",
        hit_text_at=None,
        on_complete: Callable[[TextObject], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ):
        self.canvas = canvas
        self.ax = ax
        self.axis_units = axis_units
        self.parent_window = parent_window
        self.ui_font_name = ui_font_name
        self.hit_text_at = hit_text_at
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self._cid_click = None

    def activate(self):
        self._connect()

    def deactivate(self):
        self._disconnect()

    def complete(self):
        pass

    def rollback(self):
        pass

    def _connect(self):
        if self.canvas:
            self._cid_click = self.canvas.mpl_connect(
                "button_press_event", self._on_click
            )

    def _disconnect(self):
        if self.canvas and self._cid_click is not None:
            try:
                self.canvas.mpl_disconnect(self._cid_click)
            except Exception:
                pass
            self._cid_click = None

    def _on_click(self, event):
        if not getattr(event, "dblclick", False):
            return
        if event.button != 1 or event.inaxes != self.ax:
            return
        if event.xdata is None or event.ydata is None:
            return
        if self.hit_text_at is not None:
            try:
                if self.hit_text_at(event.x, event.y) is not None:
                    return
            except Exception:
                pass

        dlg = DrawTextDialog(
            ui_font_name=self.ui_font_name,
            parent=self.parent_window,
        )
        if not dlg.exec():
            return

        text = dlg.get_text()
        if not str(text).strip():
            return

        obj = TextObject(
            text=text,
            x=float(event.xdata),
            y=float(event.ydata),
            axis_units=self.axis_units,
            id=uuid.uuid4().hex[:8],
        )
        if self.on_complete:
            self.on_complete(obj)
