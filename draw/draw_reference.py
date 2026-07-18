# draw/draw_reference.py — 참조선(수평/수직) 그리기·저장·표시

from __future__ import annotations

import logging
from typing import Callable

from .draw_common import ReferenceLineObject

_log = logging.getLogger(__name__)

try:
    from utils.math_utils import bark_to_hz, hz_to_bark
except ImportError:
    bark_to_hz = lambda x: x  # noqa: E731
    hz_to_bark = lambda x: x  # noqa: E731

# 그리드와 동일한 색 (plot_engine에서 ax.grid(..., color="#AAAAAA"))
REF_LINE_COLOR = "#AAAAAA"
REF_LINE_ALPHA = 0.3


def format_ref_label(
    value: float,
    unit: str,
    is_snapped: bool = False,
    normalization: str | None = None,
) -> str:
    """참조선 라벨. value는 이미 단위(Unit) 기준 저장된 순수 데이터 값."""
    u = (unit or "Hz").strip().lower()
    if u == "norm" or "norm" in u:
        norm_str = str(normalization or "").strip().lower()
        if "gerstman" in norm_str:
            return f"  {int(round(float(value)))}"
        return f"  {value:.2f}"
    if u in ("bk", "bark"):
        if is_snapped:
            return f"  {value:.2f}"
        return f"  {value:.1f}"
    # Hz 등: 레이어 이름(프론트 Math.round)과 플롯 라벨을 동일하게
    return f"  {int(round(float(value)))}"


def _plot_coord_to_data_value(
    plot_coord: float, scale: str, unit: str | None = None
) -> float:
    """plot 좌표를 단위(Unit) 기준 데이터 값으로 변환(반올림 없음)."""
    u = (unit or "").strip().lower() if unit else ""
    s = (scale or "linear").strip().lower()
    if s == "bark" and u in ("hz",):
        try:
            return float(bark_to_hz(plot_coord))
        except Exception:
            return float(plot_coord)
    return float(plot_coord)


def round_ref_value(
    plot_coord: float,
    scale: str,
    unit: str | None = None,
    extra_snap_values: list[float] | None = None,
    normalization: str | None = None,
) -> tuple[float, bool]:
    """plot_coord(Matplotlib 축 좌표)를 단위(Unit) 기준 데이터 값으로 변환·스냅하여 반환.
    반환값은 항상 사용자 눈금 단위(Hz/Bark/norm) 기준의 순수 데이터 값.
    - unit norm: plot_coord 그대로 소수 둘째 자리 스냅
    - scale bark & unit hz: plot_coord(Bark) -> Hz 변환 -> 10 단위 스냅 -> Hz 반환
    - scale bark & unit bark: 0.1 Bark 스냅
    - scale linear/log & unit hz: 10 단위 스냅 (plot_coord가 이미 Hz)
    """
    u = (unit or "").strip().lower() if unit else ""
    s = (scale or "linear").strip().lower()
    raw_data_value = _plot_coord_to_data_value(plot_coord, s, u)
    norm_str = str(normalization or "").strip().lower() if u == "norm" else ""

    if u == "norm":
        if "lobanov" in norm_str:
            stepped = round(raw_data_value * 10.0) / 10.0
            tol = 0.05
        elif "gerstman" in norm_str:
            stepped = round(raw_data_value / 10.0) * 10.0
            tol = 5.0
        elif any(x in norm_str for x in ("2mw", "bigham", "nearey")):
            # 2mW/F, Bigham, Nearey1 모두 0.05 단위
            stepped = round(raw_data_value * 20.0) / 20.0
            tol = 0.02
        else:
            stepped = round(raw_data_value, 2)
            tol = 0.01
    elif s == "bark" and u in ("bk", "bark"):
        stepped = round(raw_data_value, 1)
        tol = 0.05
    else:
        # Gerstman이 u != "norm"인 경우(드문 케이스)에도 대비
        if normalization == "Gerstman":
            stepped = round(raw_data_value / 10.0) * 10.0
            tol = 5.0
        else:
            stepped = round(raw_data_value / 10.0) * 10.0
            tol = 5.0

    if extra_snap_values:
        valid_candidates = []
        for v in extra_snap_values:
            try:
                valid_candidates.append(float(v))
            except (ValueError, TypeError):
                continue
        if valid_candidates:
            nearest = min(valid_candidates, key=lambda v: abs(v - raw_data_value))
            if abs(nearest - raw_data_value) <= tol:
                if u == "norm" and "gerstman" in norm_str:
                    return float(int(round(float(nearest)))), True
                return nearest, True

    # 명시적 스냅 (그리드 스냅): stepped가 이미 반올림되었으므로 그냥 반환하면 된다.
    # is_snapped=True를 반환해야 라벨 포맷 등에서 이득을 볼 수 있음.
    # 단, norm이 아닌 일반 Hz 등에서는 10단위 반올림이 이미 snapped 상태라고 볼 수 있다.
    if u == "norm" and "gerstman" in norm_str:
        return float(int(round(float(stepped)))), True
    return stepped, True


class DrawReferenceTool:
    """참조선: 호버 시 연한 preview(그리드 색), 축 눈금과 동일 폰트/색·더 작은 크기, 클릭 시 확정."""

    def __init__(
        self,
        canvas,
        ax,
        horizontal: bool,
        snapping_data: list | None = None,
        x_unit: str = "Hz",
        y_unit: str = "Hz",
        x_scale: str = "linear",
        y_scale: str = "linear",
        x_name: str = "F2",
        y_name: str = "F1",
        on_complete: Callable[[ReferenceLineObject], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
        font_family: list | None = None,
        tick_color: str | None = None,
        normalization: str | None = None,
    ):
        self.canvas = canvas
        self.ax = ax
        self.horizontal = horizontal
        self.x_unit = (x_unit or "Hz").strip()
        self.y_unit = (y_unit or "Hz").strip()
        self.x_scale = (x_scale or "linear").strip().lower()
        self.y_scale = (y_scale or "linear").strip().lower()
        self.x_name = (x_name or "F2").strip()
        self.y_name = (y_name or "F1").strip()
        self.snapping_data = snapping_data or []
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self._font_family = font_family or ["DejaVu Sans", "Malgun Gothic"]
        self._tick_color = tick_color or "#303133"
        self.normalization = normalization

        self._preview_line = None
        self._preview_label = None
        self._cid_click = None
        self._cid_move = None
        self._cid_key = None
        self._snap_candidates_h: list[float] = []
        self._snap_candidates_v: list[float] = []
        self._prepare_snap_candidates()

    def activate(self):
        self._connect()

    def deactivate(self):
        self._disconnect()
        self._clear_preview()

    def cancel(self):
        """외부에서 호출: preview 제거."""
        self._clear_preview()

    def complete(self):
        """참조선은 클릭으로만 확정. Enter는 no-op."""
        pass

    def rollback(self):
        """참조선은 롤백 없음."""
        pass

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
                    try:
                        self.canvas.mpl_disconnect(cid)
                    except Exception:
                        pass
        self._cid_click = self._cid_move = self._cid_key = None

    def _clear_preview(self):
        self._remove_artist(self._preview_line)
        self._preview_line = None
        self._remove_artist(self._preview_label)
        self._preview_label = None
        if self.canvas:
            try:
                self.canvas.draw_idle()
            except Exception:
                pass

    @staticmethod
    def _remove_artist(artist):
        if artist is None:
            return
        try:
            if hasattr(artist, "axes") and artist.axes is not None:
                artist.remove()
        except Exception:
            pass

    def _on_key(self, event):
        if event.key == "escape":
            self._clear_preview()

    def _format_ref_label(self, value: float, is_snapped: bool = False) -> str:
        """value는 단위(Unit) 기준 순수 데이터 값. 그대로 포맷."""
        unit = self.y_unit if self.horizontal else self.x_unit
        return format_ref_label(
            value, unit, is_snapped, normalization=self.normalization
        )

    def _prepare_snap_candidates(self):
        """centroid(mean) 축 값을 단위 기준 데이터 값으로 변환해 스냅 후보로 준비."""
        h_vals: list[float] = []
        v_vals: list[float] = []
        for pt in self.snapping_data or []:
            if pt.get("type") != "mean":
                continue
            try:
                py = float(pt.get("y"))
                h_vals.append(_plot_coord_to_data_value(py, self.y_scale, self.y_unit))
            except Exception:
                pass
            try:
                px = float(pt.get("x"))
                v_vals.append(_plot_coord_to_data_value(px, self.x_scale, self.x_unit))
            except Exception:
                pass
        self._snap_candidates_h = h_vals
        self._snap_candidates_v = v_vals

    def _get_ax(self):
        """현재 그려진 축 사용. figure.clear() 후 재그리기 시 axes[0]이 바뀌므로 매번 캔버스에서 가져옴."""
        if (
            self.canvas
            and getattr(self.canvas, "figure", None)
            and getattr(self.canvas.figure, "axes", None)
            and len(self.canvas.figure.axes) > 0
        ):
            return self.canvas.figure.axes[0]
        return self.ax

    def _on_move(self, event):
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            self._clear_preview()
            return
        ax = event.inaxes
        if self.horizontal:
            value, is_snapped = round_ref_value(
                event.ydata,
                self.y_scale,
                self.y_unit,
                extra_snap_values=self._snap_candidates_h,
                normalization=self.normalization,
            )
            self._draw_preview(value, is_snapped=is_snapped, is_horizontal=True, ax=ax)
        else:
            value, is_snapped = round_ref_value(
                event.xdata,
                self.x_scale,
                self.x_unit,
                extra_snap_values=self._snap_candidates_v,
                normalization=self.normalization,
            )
            self._draw_preview(value, is_snapped=is_snapped, is_horizontal=False, ax=ax)
        if self.canvas:
            self.canvas.draw_idle()

    def _draw_preview(
        self, value: float, is_snapped: bool, is_horizontal: bool, ax=None
    ):
        """value: 단위(Unit) 기준 순수 데이터 값. 선은 축 스케일에 맞는 plot_val로 그림."""
        ax = ax or self._get_ax()
        if ax is None:
            return
        self._remove_artist(self._preview_line)
        self._remove_artist(self._preview_label)
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        if is_horizontal:
            scale, unit = self.y_scale, self.y_unit
        else:
            scale, unit = self.x_scale, self.x_unit
        if scale == "bark" and (unit or "").strip().lower() in ("hz",):
            plot_val = float(hz_to_bark(value))
        else:
            plot_val = value
        if is_horizontal:
            (self._preview_line,) = ax.plot(
                xlim,
                [plot_val, plot_val],
                color=REF_LINE_COLOR,
                linewidth=1,
                alpha=REF_LINE_ALPHA,
                zorder=1.5,
                clip_on=True,
            )
            self._preview_label = ax.text(
                xlim[0],
                plot_val,
                self._format_ref_label(value, is_snapped=is_snapped),
                fontsize=12,
                fontfamily=self._font_family,
                color=self._tick_color,
                va="center",
                zorder=2,
                clip_on=True,
            )
        else:
            (self._preview_line,) = ax.plot(
                [plot_val, plot_val],
                ylim,
                color=REF_LINE_COLOR,
                linewidth=1,
                alpha=REF_LINE_ALPHA,
                zorder=1.5,
                clip_on=True,
            )
            self._preview_label = ax.text(
                plot_val,
                ylim[0],
                self._format_ref_label(value, is_snapped=is_snapped),
                fontsize=12,
                fontfamily=self._font_family,
                color=self._tick_color,
                va="bottom",
                ha="center",
                zorder=2,
                clip_on=True,
            )

    def _on_click(self, event):
        if (
            event.inaxes is None
            or event.button != 1
            or event.xdata is None
            or event.ydata is None
        ):
            return
        if self.horizontal:
            value, is_snapped = round_ref_value(
                event.ydata,
                self.y_scale,
                self.y_unit,
                extra_snap_values=self._snap_candidates_h,
                normalization=self.normalization,
            )
            axis_units = self.y_unit
            axis_name = self.y_name
            axis_scale = self.y_scale
        else:
            value, is_snapped = round_ref_value(
                event.xdata,
                self.x_scale,
                self.x_unit,
                extra_snap_values=self._snap_candidates_v,
                normalization=self.normalization,
            )
            axis_units = self.x_unit
            axis_name = self.x_name
            axis_scale = self.x_scale
        obj = ReferenceLineObject(
            mode="horizontal" if self.horizontal else "vertical",
            value=float(value),
            axis_units=axis_units,
            axis_name=axis_name,
            axis_scale=axis_scale,
        )
        self._clear_preview()
        if self.on_complete:
            self.on_complete(obj)
