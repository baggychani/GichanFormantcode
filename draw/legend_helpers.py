"""범례 객체 생성·조회 헬퍼."""

from __future__ import annotations

import os
from typing import Any

from draw.draw_common import LegendEntry, LegendObject

# 박스 내부 레이아웃 (박스 너비 대비 비율)
LEGEND_ICON_LEFT = 0.04
LEGEND_ICON_RIGHT = 0.30
LEGEND_TEXT_START = 0.44
LEGEND_RIGHT_PAD = 0.04
LEGEND_REF_ROW_H = 0.033
LEGEND_BOX_PAD_Y = 0.006
LEGEND_BOX_PAD_X_RATIO = 0.08


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


FIGURE_EDGE_MARGIN = 0.016


def legend_content_height(entry_count: int) -> float:
    """항목만 쌓은 높이(figure fraction). 행 간격 — 패딩 제외."""
    return LEGEND_REF_ROW_H * max(entry_count, 1)


def legend_height_frac(entry_count: int) -> float:
    """박스 전체 높이 = 내용 + 상하 패딩."""
    return max(
        0.034, min(0.26, legend_content_height(entry_count) + 2 * LEGEND_BOX_PAD_Y)
    )


def reconcile_legend_box_height(legend: LegendObject) -> None:
    """내용 높이(행 간격)만 맞추고, 상하 패딩은 항상 유지."""
    entries = list(getattr(legend, "entries", []) or [])
    n = max(len(entries), 1)
    expected = legend_height_frac(n)
    content_h = float(legend.height_frac) - 2 * LEGEND_BOX_PAD_Y
    ref_content = legend_content_height(n)
    if abs(content_h - ref_content) > ref_content * 0.04:
        legend.height_frac = expected
        clamp_legend_bounds(legend)


def default_legend_placement(
    popup: Any, entry_count: int, ax=None
) -> tuple[float, float, float, float]:
    """원점 반대편 모서리(axes 내부)에 범례 배치. (fx, fy, width_frac, height_frac) — figure fraction."""
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
        show_border=False,
        show_fill=False,
        fill_opacity=0.92,
        font_size=10.0,
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
    legend.font_size = max(7.0, min(float(legend.font_size), 28.0))


def _legend_font_family(popup: Any) -> list[str]:
    ds = getattr(popup, "design_settings", None) or {}
    common = ds.get("common", {}) if isinstance(ds, dict) else {}
    font_style = common.get("font_style") or ds.get("font_style", "serif")
    if font_style == "serif":
        return ["Times New Roman", "Noto Serif KR", "DejaVu Serif"]
    return ["DejaVu Sans", "Malgun Gothic"]


def _measure_text_width_frac(
    fig,
    text: str,
    font_size: float,
    font_family: list[str],
) -> float:
    """텍스트 너비를 figure fraction으로 반환."""
    if not text:
        return 0.0
    renderer = fig.canvas.get_renderer() if fig and fig.canvas else None
    temp = fig.text(
        0,
        0,
        text,
        transform=fig.transFigure,
        fontsize=font_size,
        fontfamily=font_family,
        visible=False,
    )
    try:
        if renderer is None:
            return len(text) * float(font_size) * 0.0065
        bbox = temp.get_window_extent(renderer=renderer)
        fig_bbox = fig.bbox
        fig_w = max(float(fig_bbox.width), 1.0)
        return float(bbox.width) / fig_w * 1.04
    finally:
        temp.remove()


def legend_box_content_bounds(
    legend: LegendObject,
) -> tuple[float, float, float, float]:
    """패딩을 뺀 내용 영역 (x0, y0, x1, y1) — figure fraction."""
    x0, y0, x1, y1 = legend_box_axes_bounds(legend)
    box_w = x1 - x0
    pad_x = box_w * LEGEND_BOX_PAD_X_RATIO
    pad_y = LEGEND_BOX_PAD_Y
    return x0 + pad_x, y0 + pad_y, x1 - pad_x, y1 - pad_y


def legend_row_pitch(legend: LegendObject, entry_count: int) -> float:
    """항목 한 줄 높이(figure fraction). 행 간 행 간격 — 패딩과 무관."""
    cx0, cy0, cx1, cy1 = legend_box_content_bounds(legend)
    n = max(entry_count, 1)
    pitch = (cy1 - cy0) / n
    return max(LEGEND_REF_ROW_H * 0.5, pitch)


def legend_content_scale(legend: LegendObject, entry_count: int) -> float:
    """내용 영역 높이에 비례한 스케일 (패딩 제외)."""
    pitch = legend_row_pitch(legend, entry_count)
    return max(0.95, min(2.8, pitch / LEGEND_REF_ROW_H))


def ensure_legend_content_fits(
    legend: LegendObject,
    fig,
    popup: Any,
    *,
    entries: list | None = None,
) -> None:
    """텍스트가 박스를 넘치면 width_frac를 키워 오른쪽으로 확장 (fx 고정)."""
    rows = list(entries or getattr(legend, "entries", []) or [])
    if not rows or fig is None:
        return

    font_family = _legend_font_family(popup)
    pad_ratio = LEGEND_BOX_PAD_X_RATIO
    inner_ratio = max(0.5, 1.0 - 2 * pad_ratio)
    margin = 1.06

    for _ in range(6):
        reconcile_legend_box_height(legend)
        scale = legend_content_scale(legend, len(rows))
        effective_font = float(getattr(legend, "font_size", 10.0)) * scale

        x0, _y0, x1, _y1 = legend_box_axes_bounds(legend)
        box_w = x1 - x0
        if box_w <= 1e-6:
            break

        cx0, _cy0, cx1, _cy1 = legend_box_content_bounds(legend)
        content_w = cx1 - cx0
        if content_w <= 1e-6:
            break

        text_start_x = cx0 + LEGEND_TEXT_START * content_w
        required_right = text_start_x
        for entry in rows:
            text = str(getattr(entry, "text", "") or "")
            text_w = _measure_text_width_frac(fig, text, effective_font, font_family)
            text_w *= margin
            required_right = max(required_right, text_start_x + text_w)

        required_cx1 = required_right + LEGEND_RIGHT_PAD * content_w
        if required_cx1 <= cx1 + 1e-5:
            break

        required_box_w = (required_cx1 - x0) / inner_ratio
        if required_box_w <= box_w + 1e-5:
            break

        legend.width_frac = float(legend.width_frac) * (required_box_w / box_w)
        clamp_legend_bounds(legend)
