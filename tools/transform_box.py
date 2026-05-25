"""Figure fraction 박스 — 이동·핸들 리사이즈."""

from __future__ import annotations

from typing import Callable

from draw.draw_common import LegendObject
from draw.legend_helpers import clamp_legend_bounds, legend_box_axes_bounds


class TransformBoxTool:
    """범례(LegendObject) transform 편집 — figure fraction 좌표."""

    def __init__(
        self,
        canvas,
        ax,
        *,
        on_changed: Callable[[], None] | None = None,
        on_select: Callable[[], None] | None = None,
    ):
        self.canvas = canvas
        self.ax = ax
        self.on_changed = on_changed
        self.on_select = on_select
        self.target: LegendObject | None = None
        self.active = False
        self._drag_mode: str | None = None
        self._press_fig_xy: tuple[float, float] | None = None
        self._start_bounds: tuple[float, float, float, float] | None = None
        self._cids: list[int] = []

    def set_target(self, legend: LegendObject | None) -> None:
        self.target = legend

    def activate(self) -> None:
        if self.active:
            return
        self.active = True
        self._cids = [
            self.canvas.mpl_connect("button_press_event", self._on_press),
            self.canvas.mpl_connect("motion_notify_event", self._on_motion),
            self.canvas.mpl_connect("button_release_event", self._on_release),
        ]

    def deactivate(self) -> None:
        if not self.active:
            return
        for cid in self._cids:
            try:
                self.canvas.mpl_disconnect(cid)
            except Exception:
                pass
        self._cids = []
        self.active = False
        self._drag_mode = None

    def _event_fig_xy(self, event) -> tuple[float, float] | None:
        if event.x is None or event.y is None or self.ax is None:
            return None
        try:
            fig = self.ax.figure
            bbox = fig.bbox
            x = (event.x - bbox.x0) / bbox.width
            y = (event.y - bbox.y0) / bbox.height
            return float(x), float(y)
        except Exception:
            return None

    def _handle_hit(self, fig_xy: tuple[float, float]) -> str | None:
        if self.target is None:
            return None
        x0, y0, x1, y1 = legend_box_axes_bounds(self.target)
        pts = {
            "sw": (x0, y0),
            "s": ((x0 + x1) / 2, y0),
            "se": (x1, y0),
            "e": (x1, (y0 + y1) / 2),
            "ne": (x1, y1),
            "n": ((x0 + x1) / 2, y1),
            "nw": (x0, y1),
            "w": (x0, (y0 + y1) / 2),
        }
        tol = max(0.012, min(self.target.width_frac, self.target.height_frac) * 0.10)
        x, y = fig_xy
        for name, (hx, hy) in pts.items():
            if abs(x - hx) <= tol and abs(y - hy) <= tol:
                return name
        return None

    def _inside_box(self, fig_xy: tuple[float, float]) -> bool:
        if self.target is None:
            return False
        x0, y0, x1, y1 = legend_box_axes_bounds(self.target)
        x, y = fig_xy
        return x0 <= x <= x1 and y0 <= y <= y1

    def _on_press(self, event):
        if event.button != 1 or self.target is None:
            return
        if getattr(event, "canvas", None) is not self.canvas:
            return
        if getattr(self.target, "locked", False):
            return
        fig_xy = self._event_fig_xy(event)
        if fig_xy is None:
            return
        handle = self._handle_hit(fig_xy)
        if handle:
            self._drag_mode = f"resize:{handle}"
        elif self._inside_box(fig_xy):
            self._drag_mode = "move"
        else:
            return
        self._press_fig_xy = fig_xy
        self._start_bounds = legend_box_axes_bounds(self.target)
        if self.on_select:
            self.on_select()

    def _on_motion(self, event):
        if not self._drag_mode or self.target is None or self._press_fig_xy is None:
            return
        if self._start_bounds is None:
            return
        fig_xy = self._event_fig_xy(event)
        if fig_xy is None:
            return
        dx = fig_xy[0] - self._press_fig_xy[0]
        dy = fig_xy[1] - self._press_fig_xy[1]
        x0, y0, x1, y1 = self._start_bounds

        if self._drag_mode == "move":
            w = x1 - x0
            h = y1 - y0
            self.target.fx = x0 + dx
            self.target.fy = y1 + dy
            self.target.width_frac = w
            self.target.height_frac = h
        else:
            handle = self._drag_mode.split(":", 1)[1]
            nx0, ny0, nx1, ny1 = x0, y0, x1, y1
            west = {"nw", "w", "sw"}
            east = {"ne", "e", "se"}
            south = {"sw", "s", "se"}
            north = {"nw", "n", "ne"}
            if handle in west:
                nx0 = x0 + dx
            if handle in east:
                nx1 = x1 + dx
            if handle in south:
                ny0 = y0 + dy
            if handle in north:
                ny1 = y1 + dy
            if nx1 - nx0 < 0.05:
                if handle in west:
                    nx0 = nx1 - 0.05
                else:
                    nx1 = nx0 + 0.05
            if ny1 - ny0 < 0.035:
                if handle in south:
                    ny0 = ny1 - 0.035
                else:
                    ny1 = ny0 + 0.035
            self.target.fx = nx0
            self.target.fy = ny1
            self.target.width_frac = nx1 - nx0
            self.target.height_frac = ny1 - ny0

        clamp_legend_bounds(self.target)
        if self.on_changed:
            self.on_changed()

    def _on_release(self, event):
        self._drag_mode = None
        self._press_fig_xy = None
        self._start_bounds = None
