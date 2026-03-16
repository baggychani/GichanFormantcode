# draw/draw_polygon.py — 영역(Polygon) 그리기·저장·표시·넓이 계산

from __future__ import annotations

import logging
import uuid
from typing import Callable

import numpy as np

from .draw_common import snap_query, PolygonObject

_log = logging.getLogger(__name__)


class DrawPolygonTool:
    """영역 그리기: 클릭으로 점 추가, 시작점 스냅 시 닫힌 순간 자동 완료, Esc 취소, Ctrl+Z 롤백."""

    def __init__(
        self,
        canvas,
        ax,
        snapping_data: list,
        axis_units: str = "Hz",
        on_complete: Callable[[PolygonObject], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ):
        self.canvas = canvas
        self.ax = ax
        self.snapping_data = snapping_data or []
        self.axis_units = axis_units
        self.on_complete = on_complete
        self.on_cancel = on_cancel

        self._points: list[tuple[float, float]] = []
        self._point_labels: list[str] = []
        self._line_artist = None
        self._fill_artist = None
        self._guide_line = None
        self._snap_marker = None
        self._tooltip_artist = None
        self._cid_click = None
        self._cid_move = None
        self._cid_key = None

    def activate(self):
        self._connect()

    def deactivate(self):
        self._disconnect()
        self._clear_current()

    def _connect(self):
        if self.canvas:
            self._cid_click = self.canvas.mpl_connect(
                "button_press_event", self._on_click
            )
            self._cid_move = self.canvas.mpl_connect(
                "motion_notify_event", self._on_move
            )
            self._cid_key = self.canvas.mpl_connect("key_press_event", self._on_key)

    def _disconnect(self):
        if self.canvas:
            for cid in (self._cid_click, self._cid_move, self._cid_key):
                if cid is not None:
                    self.canvas.mpl_disconnect(cid)
        self._cid_click = self._cid_move = self._cid_key = None

    def _clear_current(self):
        self._points.clear()
        self._point_labels.clear()
        self._remove_artist(self._line_artist)
        self._line_artist = None
        self._remove_artist(self._fill_artist)
        self._fill_artist = None
        self._remove_artist(self._guide_line)
        self._guide_line = None
        self._remove_artist(self._snap_marker)
        self._snap_marker = None
        self._remove_artist(self._tooltip_artist)
        self._tooltip_artist = None
        if self.canvas:
            self.canvas.draw_idle()

    @staticmethod
    def _remove_artist(artist):
        if artist is None:
            return
        try:
            artist.remove()
        except Exception as e:
            _log.warning("DrawPolygonTool remove artist: %s", e)

    def _on_move(self, event):
        self._remove_artist(self._guide_line)
        self._guide_line = None
        if event.inaxes is not self.ax or not self.snapping_data:
            self._remove_artist(self._snap_marker)
            self._snap_marker = None
            self._remove_artist(self._tooltip_artist)
            self._tooltip_artist = None
            if self.canvas:
                self.canvas.draw_idle()
            return
        pt = snap_query(self.ax, self.snapping_data, event.x, event.y, max_dist_px=20)
        if pt is not None:
            self._draw_snap_feedback(pt)
            if self._points:
                x1, y1 = self._points[-1]
                x2, y2 = pt["x"], pt["y"]
                (self._guide_line,) = self.ax.plot(
                    [x1, x2],
                    [y1, y2],
                    color="gray",
                    ls=":",
                    lw=1,
                    alpha=0.5,
                    zorder=2,
                    clip_on=False,
                )
        else:
            self._remove_artist(self._snap_marker)
            self._snap_marker = None
            self._remove_artist(self._tooltip_artist)
            self._tooltip_artist = None
            if self._points and event.xdata is not None and event.ydata is not None:
                x1, y1 = self._points[-1]
                (self._guide_line,) = self.ax.plot(
                    [x1, event.xdata],
                    [y1, event.ydata],
                    color="gray",
                    ls=":",
                    lw=1,
                    alpha=0.5,
                    zorder=2,
                    clip_on=False,
                )
        if self.canvas:
            self.canvas.draw_idle()

    def _draw_snap_feedback(self, pt):
        self._remove_artist(self._snap_marker)
        x, y = pt["x"], pt["y"]
        m_style = "s" if pt.get("type") == "mean" else "o"
        (self._snap_marker,) = self.ax.plot(
            x,
            y,
            m_style,
            markersize=12 if pt.get("type") == "mean" else 10,
            markerfacecolor="none",
            markeredgecolor=pt.get("color", "gray"),
            markeredgewidth=2,
            zorder=200,
            clip_on=False,
        )
        self._remove_artist(self._tooltip_artist)
        label = pt.get("label", pt.get("Label", "")) or ""
        txt = f"{label}\n({x:.0f}, {y:.0f})" if label else f"({x:.0f}, {y:.0f})"
        self._tooltip_artist = self.ax.annotate(
            txt,
            xy=(x, y),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="#ffffe0", ec="gray", alpha=0.9),
            fontsize=9,
            zorder=300,
            clip_on=False,
        )

    def _on_click(self, event):
        if event.inaxes is not self.ax or event.button != 1:
            return
        pt = snap_query(self.ax, self.snapping_data, event.x, event.y, max_dist_px=20)
        if pt is None:
            return
        x, y = pt["x"], pt["y"]
        # 시작점 근처 클릭이면 닫고 완료
        if len(self._points) >= 3 and self._points:
            x0, y0 = self._points[0]
            # 픽셀 거리로 판단 (대략)
            pt0_px = self.ax.transData.transform([(x0, y0)])[0]
            pt_px = self.ax.transData.transform([(x, y)])[0]
            if np.hypot(pt_px[0] - pt0_px[0], pt_px[1] - pt0_px[1]) < 20:
                self._points.append((x0, y0))
                self._complete()
                return
        self._points.append((x, y))
        lbl = pt.get("label") or pt.get("Label") or ""
        if lbl is None:
            lbl = ""
        lbl = str(lbl).strip()
        self._point_labels.append(lbl if lbl else "?")
        self._redraw()

    def _on_key(self, event):
        if event.key == "escape":
            self._clear_current()
        elif event.key == "ctrl+z":
            if self._points:
                self._points.pop()
                if self._point_labels:
                    self._point_labels.pop()
                self._redraw()

    def cancel(self):
        """외부에서 호출: 현재 영역 그리기 취소."""
        self._clear_current()

    def complete(self):
        """외부에서 호출: 점 3개 이상이면 시작점을 붙여 닫고 완료."""
        if len(self._points) >= 3:
            self._points.append(self._points[0])
            self._complete()

    def rollback(self):
        """외부에서 호출: 점 하나 롤백."""
        if self._points:
            self._points.pop()
            self._redraw()

    def _redraw(self):
        self._remove_artist(self._line_artist)
        self._line_artist = None
        self._remove_artist(self._fill_artist)
        self._fill_artist = None
        if not self._points:
            if self.canvas:
                self.canvas.draw_idle()
            return
        xs = [p[0] for p in self._points]
        ys = [p[1] for p in self._points]
        # 임시(그리는 중) 외곽선은 확정 외곽선보다 연하게 표시
        (self._line_artist,) = self.ax.plot(
            xs, ys, "k-", linewidth=1.5, alpha=0.4, zorder=1, clip_on=False
        )
        from matplotlib.patches import Polygon as MplPolygon

        poly = MplPolygon(
            self._points,
            facecolor=(0.2, 0.4, 0.8, 0.15),
            edgecolor="none",
            zorder=1,
        )
        self.ax.add_patch(poly)
        self._fill_artist = poly
        if self.canvas:
            self.canvas.draw_idle()

    def _complete(self):
        if len(self._points) < 3:
            self._clear_current()
            return
        # 닫힌 점 리스트 (마지막 = 시작점 복사는 이미 포함됨). 넓이 계산은 popup_plot에서 AreaLabelObject 생성 시 수행.
        points = self._points.copy()
        obj = PolygonObject(
            points=points,
            point_labels=self._point_labels.copy(),
            axis_units=self.axis_units,
            id=uuid.uuid4().hex[:12],
        )
        self._clear_current()
        if self.on_complete:
            self.on_complete(obj)
