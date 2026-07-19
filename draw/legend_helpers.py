"""범례 객체 생성·조회·픽셀 고정 레이아웃 헬퍼."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from draw.draw_common import LegendEntry, LegendObject

# 디스플레이 픽셀 기준 레이아웃 (좌우·상하 패딩 동일·고정)
LEGEND_PAD_X_PX = 20.0
LEGEND_PAD_Y_PX = 16.0
LEGEND_ICON_W_PX = 36.0
LEGEND_GAP_PX = 8.0
LEGEND_ROW_H_AT_10PT_PX = 22.0
LEGEND_MIN_BOX_W_PX = 72.0
# % 여유 금지 — 글자가 길수록 오른쪽이 비어 보였음. 고정 px만.
LEGEND_TEXT_SLACK_PX = 3.0

FIGURE_EDGE_MARGIN = 0.016

# 하위호환 (예전 비율 상수 — 외부 import 깨짐 방지)
LEGEND_ICON_LEFT = 0.03
LEGEND_ICON_RIGHT = 0.26
LEGEND_TEXT_START = 0.36
LEGEND_RIGHT_PAD = 0.08
LEGEND_REF_ROW_H = 0.036
LEGEND_BOX_PAD_Y = 0.012
LEGEND_BOX_PAD_X_LEFT_RATIO = 0.034
LEGEND_BOX_PAD_X_RIGHT_RATIO = 0.07
LEGEND_BOX_PAD_X_RATIO = LEGEND_BOX_PAD_X_LEFT_RATIO


def find_legend_object(draw_objects: list) -> LegendObject | None:
    for obj in draw_objects or []:
        if getattr(obj, "type", "") == "legend":
            return obj
    return None


def has_legend_object(draw_objects: list) -> bool:
    return find_legend_object(draw_objects) is not None


def _default_entry_text(popup: Any, series_id: int, is_compare: bool) -> str:
    controller = getattr(popup, "controller", None)
    if is_compare and controller is not None:
        session = getattr(popup, "compare_session", None)
        if session is not None and series_id < session.count:
            idx = session.data_index(series_id)
            item = controller.get_data_item_at(idx)
            if item:
                return os.path.splitext(item.get("name", ""))[0]
        if series_id == 0:
            idx = getattr(popup, "idx_blue", None)
        elif series_id == 1:
            idx = getattr(popup, "idx_red", None)
        else:
            idx = None
        if idx is not None and controller is not None:
            item = controller.get_data_item_at(idx)
            if item:
                return os.path.splitext(item.get("name", ""))[0]
    if controller is not None:
        idx = getattr(popup, "current_idx", None)
        if idx is None:
            idx = controller.get_current_index()
        item = controller.get_data_item_at(idx)
        if item:
            return os.path.splitext(item.get("name", ""))[0]
    return "데이터"


def _plot_uses_top_right_origin(popup: Any) -> bool:
    """플롯 원점이 우상단(Praat)인지 — axis_position_swap 반영."""
    params = getattr(popup, "fixed_plot_params", None) or {}
    origin = params.get("origin", "top_right")
    ds = getattr(popup, "design_settings", None) or {}
    axis_swap = False
    if isinstance(ds, dict):
        common = ds.get("common", {})
        if isinstance(common, dict) and "axis_position_swap" in common:
            axis_swap = bool(common.get("axis_position_swap"))
        else:
            axis_swap = bool(ds.get("axis_position_swap", False))
    return (origin == "top_right") != axis_swap


def legend_height_frac(entry_count: int) -> float:
    """초기 배치용 대략 높이 (렌더 시 픽셀 레이아웃이 덮어씀)."""
    n = max(entry_count, 1)
    return max(0.034, min(0.26, 0.012 * 2 + 0.036 * n))


def default_legend_placement(
    popup: Any, entry_count: int, ax=None
) -> tuple[float, float, float, float]:
    """원점 반대편 모서리(axes 내부)에 범례 배치. (fx, fy, width_frac, height_frac)."""
    height_frac = legend_height_frac(entry_count)

    if ax is not None:
        pos = ax.get_position()
        width_frac = max(0.12, min(0.38, float(pos.width) * 0.36))
        if _plot_uses_top_right_origin(popup):
            fx = float(pos.x0)
            fy = float(pos.y0) + height_frac
        else:
            fx = float(pos.x0) + float(pos.width) - width_frac
            fy = float(pos.y0) + float(pos.height)
        return fx, fy, width_frac, height_frac

    margin = FIGURE_EDGE_MARGIN
    width_frac = 0.26
    if _plot_uses_top_right_origin(popup):
        fx = margin
        fy = margin + height_frac
    else:
        fx = 1.0 - width_frac - margin
        fy = 1.0 - margin
    return fx, fy, width_frac, height_frac


def build_legend_entries(popup: Any, *, is_compare: bool) -> list[LegendEntry]:
    if is_compare:
        session = getattr(popup, "compare_session", None)
        count = session.count if session is not None else 2
        return [
            LegendEntry(
                series_id=i,
                text=_default_entry_text(popup, i, True),
            )
            for i in range(count)
        ]
    return [LegendEntry(series_id=0, text=_default_entry_text(popup, 0, False))]


def create_legend_object(popup: Any, *, is_compare: bool) -> LegendObject:
    entries = build_legend_entries(popup, is_compare=is_compare)
    ax = None
    figure = getattr(popup, "figure", None)
    if figure is not None and figure.axes:
        ax = figure.axes[0]
    fx, fy, width_frac, height_frac = default_legend_placement(
        popup, len(entries), ax=ax
    )
    return LegendObject(
        name="범례",
        entries=entries,
        is_compare=is_compare,
        fx=fx,
        fy=fy,
        width_frac=width_frac,
        height_frac=height_frac,
        show_border=True,
        border_style="-",
        border_color="#3f4650",
        show_fill=True,
        fill_color="#ffffff",
        fill_opacity=1.0,
        font_size=9.0,
        font_family="Noto Sans KR",
        font_weight="regular",
        font_italic=False,
    )


def legend_box_axes_bounds(legend: LegendObject) -> tuple[float, float, float, float]:
    """(x0, y0, x1, y1) in figure fraction. fy = top edge."""
    x0 = float(legend.fx)
    y1 = float(legend.fy)
    x1 = x0 + float(legend.width_frac)
    y0 = y1 - float(legend.height_frac)
    return x0, y0, x1, y1


def clamp_legend_bounds(legend: LegendObject) -> None:
    m = FIGURE_EDGE_MARGIN
    legend.width_frac = max(0.05, min(float(legend.width_frac), 0.92))
    legend.height_frac = max(0.028, min(float(legend.height_frac), 0.92))
    legend.fx = max(m, min(float(legend.fx), 1.0 - legend.width_frac - m))
    legend.fy = max(legend.height_frac + m, min(float(legend.fy), 1.0 - m))
    legend.font_size = max(6.0, min(float(legend.font_size), 20.0))


def _legend_font_family(popup: Any, legend: LegendObject | None = None) -> list[str]:
    requested = getattr(legend, "font_family", None) if legend is not None else None
    if requested == "Noto Sans KR":
        return ["Noto Sans KR", "Malgun Gothic", "DejaVu Sans"]
    if requested == "Noto Serif KR":
        return ["Noto Serif KR", "Times New Roman", "DejaVu Serif"]
    if requested == "Charis SIL":
        return ["Charis SIL", "DejaVu Serif"]
    if requested == "Andika":
        return ["Andika", "DejaVu Sans"]
    ds = getattr(popup, "design_settings", None) or {}
    common = ds.get("common", {}) if isinstance(ds, dict) else {}
    font_style = common.get("font_style") or ds.get("font_style", "serif")
    if font_style == "serif":
        return ["Times New Roman", "Noto Serif KR", "DejaVu Serif"]
    return ["DejaVu Sans", "Malgun Gothic"]


def _fig_pixel_size(fig) -> tuple[float, float, float]:
    """(width_px, height_px, dpi)."""
    dpi = float(getattr(fig, "dpi", 100.0) or 100.0)
    try:
        w = float(fig.bbox.width)
        h = float(fig.bbox.height)
        if w > 8 and h > 8:
            return w, h, dpi
    except Exception:
        pass
    try:
        w_in, h_in = fig.get_size_inches()
        return float(w_in) * dpi, float(h_in) * dpi, dpi
    except Exception:
        return 800.0, 600.0, dpi


def _estimate_text_width_px(text: str, font_size_pt: float, dpi: float) -> float:
    """폭 추정 (한글·기호). 비율 여유 없이 points→px만 변환."""
    if not text:
        return 0.0
    width_pt = 0.0
    for ch in text:
        code = ord(ch)
        if code > 0x2E80 or ("\uac00" <= ch <= "\ud7a3"):
            width_pt += font_size_pt * 1.0
        elif ch.isupper() or ch.isdigit():
            width_pt += font_size_pt * 0.66
        elif ch in "_-./ ":
            width_pt += font_size_pt * 0.42
        else:
            width_pt += font_size_pt * 0.56
    return width_pt * (dpi / 72.0)


def _measure_text_width_px(
    fig,
    text: str,
    font_size_pt: float,
    font_family: list[str],
    *,
    font_weight: str = "normal",
    font_style: str = "normal",
) -> float:
    """텍스트 너비(디스플레이 px). TextPath 우선, 실패 시 추정. 끝단에 고정 slack만 가산."""
    if not text:
        return LEGEND_TEXT_SLACK_PX
    _fig_w, _fig_h, dpi = _fig_pixel_size(fig)
    estimate = _estimate_text_width_px(text, font_size_pt, dpi)
    measured = None

    try:
        from matplotlib.font_manager import FontProperties
        from matplotlib.textpath import TextPath

        prop = FontProperties(
            family=list(font_family),
            size=font_size_pt,
            weight=font_weight,
            style=font_style,
        )
        path = TextPath((0, 0), text, size=font_size_pt, prop=prop)
        width_pt = float(path.get_extents().width)
        candidate = width_pt * (dpi / 72.0)
        if candidate >= estimate * 0.45:
            measured = candidate
    except Exception:
        pass

    if measured is None and fig is not None and getattr(fig, "canvas", None) is not None:
        try:
            renderer = fig.canvas.get_renderer()
        except Exception:
            renderer = None
        if renderer is not None:
            temp = fig.text(
                0,
                0,
                text,
                transform=fig.transFigure,
                fontsize=font_size_pt,
                fontfamily=font_family,
                fontweight=font_weight,
                fontstyle=font_style,
                visible=False,
            )
            try:
                bbox = temp.get_window_extent(renderer=renderer)
                candidate = float(bbox.width)
                if candidate >= estimate * 0.45:
                    measured = candidate
            finally:
                temp.remove()

    return (measured if measured is not None else estimate) + LEGEND_TEXT_SLACK_PX


@dataclass(frozen=True)
class LegendPixelLayout:
    """픽셀 고정 레이아웃 → figure fraction 배치용."""

    fig_w: float
    fig_h: float
    pad_l: float
    pad_r: float
    pad_y: float
    icon_w: float
    gap: float
    row_h: float
    font_size: float
    max_text_w: float
    box_w_px: float
    box_h_px: float
    width_frac: float
    height_frac: float

    def icon_left_frac(self, fx: float) -> float:
        return fx + self.pad_l / self.fig_w

    def icon_right_frac(self, fx: float) -> float:
        return fx + (self.pad_l + self.icon_w) / self.fig_w

    def text_x_frac(self, fx: float) -> float:
        return fx + (self.pad_l + self.icon_w + self.gap) / self.fig_w

    def row_y_frac(self, fy: float, index: int) -> float:
        # fy = top; first row centered in first row band below top pad
        top = fy - self.pad_y / self.fig_h
        return top - (index + 0.5) * (self.row_h / self.fig_h)


def build_legend_pixel_layout(
    legend: LegendObject,
    fig,
    popup: Any,
    *,
    entries: list | None = None,
) -> LegendPixelLayout:
    """텍스트 실측(px)으로 박스 크기·배치를 계산하고 legend.width/height_frac를 갱신."""
    rows = list(entries or getattr(legend, "entries", []) or [])
    n = max(len(rows), 1)
    fig_w, fig_h, dpi = _fig_pixel_size(fig)
    fig_w = max(fig_w, 1.0)
    fig_h = max(fig_h, 1.0)

    font_size = float(getattr(legend, "font_size", 10.0) or 10.0)
    font_size = max(6.0, min(font_size, 20.0))
    font_family = _legend_font_family(popup, legend)
    font_weight = str(getattr(legend, "font_weight", "regular") or "regular")
    mpl_weight = "bold" if font_weight in {"bold", "semibold"} else "normal"
    mpl_style = "italic" if bool(getattr(legend, "font_italic", False)) else "normal"

    max_text_w = 0.0
    for entry in rows:
        text = str(getattr(entry, "text", "") or "")
        max_text_w = max(
            max_text_w,
            _measure_text_width_px(
                fig,
                text,
                font_size,
                font_family,
                font_weight=mpl_weight,
                font_style=mpl_style,
            ),
        )

    pad_x = LEGEND_PAD_X_PX
    pad_y = LEGEND_PAD_Y_PX
    icon_w = LEGEND_ICON_W_PX
    gap = LEGEND_GAP_PX
    row_h = max(
        LEGEND_ROW_H_AT_10PT_PX * (font_size / 10.0),
        font_size * (dpi / 72.0) * 1.55,
    )

    # 전체 폭 = 좌패딩 + 아이콘(선) + 간격 + 텍스트 + 우패딩 (패딩은 길이와 무관)
    box_w_px = max(LEGEND_MIN_BOX_W_PX, pad_x + icon_w + gap + max_text_w + pad_x)
    box_h_px = 2.0 * pad_y + n * row_h

    width_frac = max(0.05, min(0.92, box_w_px / fig_w))
    height_frac = max(0.028, min(0.92, box_h_px / fig_h))

    legend.width_frac = width_frac
    legend.height_frac = height_frac
    legend.font_size = font_size
    clamp_legend_bounds(legend)

    return LegendPixelLayout(
        fig_w=fig_w,
        fig_h=fig_h,
        pad_l=pad_x,
        pad_r=pad_x,
        pad_y=pad_y,
        icon_w=icon_w,
        gap=gap,
        row_h=row_h,
        font_size=font_size,
        max_text_w=max_text_w,
        box_w_px=box_w_px,
        box_h_px=box_h_px,
        width_frac=float(legend.width_frac),
        height_frac=float(legend.height_frac),
    )


def ensure_legend_content_fits(
    legend: LegendObject,
    fig,
    popup: Any,
    *,
    entries: list | None = None,
) -> LegendPixelLayout | None:
    """텍스트에 맞게 width/height 맞춤. 레이아웃 객체를 반환."""
    if fig is None:
        return None
    return build_legend_pixel_layout(legend, fig, popup, entries=entries)


# 하위호환 스텁 — 예전 호출부가 깨지지 않게
def reconcile_legend_box_height(legend: LegendObject) -> None:
    entries = list(getattr(legend, "entries", []) or [])
    legend.height_frac = legend_height_frac(max(len(entries), 1))
    clamp_legend_bounds(legend)


def legend_box_content_bounds(legend: LegendObject) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = legend_box_axes_bounds(legend)
    # 대략적 패딩 (픽셀 레이아웃 없을 때)
    return x0 + 0.01, y0 + 0.008, x1 - 0.012, y1 - 0.008


def legend_row_pitch(legend: LegendObject, entry_count: int) -> float:
    n = max(entry_count, 1)
    return max(0.02, float(legend.height_frac) / n)


def legend_content_scale(legend: LegendObject, entry_count: int) -> float:
    return 1.0
