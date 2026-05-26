"""그리기 레이어(선·영역·참조선·범례 등) Matplotlib 렌더 — 캔버스·일괄 저장 공용."""

from __future__ import annotations

import logging
from typing import Any

import matplotlib.colors as mcolors

_log = logging.getLogger(__name__)

from draw.draw_reference import REF_LINE_ALPHA, REF_LINE_COLOR, format_ref_label
from draw.legend_render import render_legend
from draw.text_render import render_text_object
from utils.math_utils import hz_to_bark


def _line_style_to_mpl(style: str):
    if style == "---":
        return (0, (6.0, 3.0))
    if style in ("-", "--", ":"):
        return style
    return "--"


def _log_render_skip(obj, phase: str, exc: BaseException) -> None:
    _log.debug(
        "draw render skip (%s): type=%s id=%s: %s",
        phase,
        getattr(obj, "type", "?"),
        getattr(obj, "id", ""),
        exc,
        exc_info=True,
    )


def _is_serif_font(ctx: Any) -> bool:
    ds = getattr(ctx, "design_settings", None) or {}
    if not isinstance(ds, dict):
        return False
    if ds.get("font_style") == "serif":
        return True
    common = ds.get("common", {})
    return isinstance(common, dict) and common.get("font_style") == "serif"


def render_draw_objects(
    ax,
    objects: list,
    ctx: Any,
    *,
    skip_types: frozenset[str] | None = None,
    show_editor_chrome: bool = False,
    selected_legend_id: str | None = None,
    selected_text_id: str | None = None,
    area_label_refs: list | None = None,
    text_layer_refs: list | None = None,
) -> list:
    """draw_objects를 ax에 그리고 생성된 artist 목록을 반환한다."""
    skip_types = skip_types or frozenset()
    artists: list = []
    label_refs = area_label_refs if area_label_refs is not None else []
    text_refs = text_layer_refs if text_layer_refs is not None else []

    for obj in objects or []:
        if not getattr(obj, "visible", True):
            continue
        obj_type = getattr(obj, "type", None)
        if obj_type in skip_types:
            continue

        is_semi = getattr(obj, "semi", False)
        line_alpha = 0.5 if is_semi else 0.9
        try:
            if obj_type == "line" and hasattr(obj, "points"):
                artists.extend(_render_line(ax, obj, line_alpha=line_alpha))
            elif obj_type == "polygon" and hasattr(obj, "points"):
                artists.append(_render_polygon(ax, obj, is_semi=is_semi))
            elif obj_type == "reference" and hasattr(obj, "mode"):
                pass
            elif obj_type == "legend":
                pass
            elif obj_type == "text":
                pass
            elif obj_type == "area_label":
                txt_artist = _render_area_label(ax, obj, ctx, is_semi=is_semi)
                if txt_artist is not None:
                    artists.append(txt_artist)
                    label_refs.append((txt_artist, obj))
        except Exception as exc:
            _log_render_skip(obj, "primary", exc)
            continue

    for obj in objects or []:
        if not getattr(obj, "visible", True):
            continue
        if getattr(obj, "type", None) != "reference" or not hasattr(obj, "mode"):
            continue
        if "reference" in skip_types:
            continue
        try:
            artists.extend(_render_reference(ax, obj, ctx, is_semi=is_semi))
        except Exception as exc:
            _log_render_skip(obj, "reference", exc)
            continue

    if "legend" not in skip_types:
        for obj in objects or []:
            if getattr(obj, "type", None) != "legend":
                continue
            selected = getattr(obj, "id", None) == selected_legend_id
            try:
                legend_artists = render_legend(
                    ax,
                    obj,
                    ctx,
                    selected=selected and not getattr(obj, "locked", False),
                    show_editor_chrome=show_editor_chrome,
                )
                artists.extend(legend_artists)
            except Exception as exc:
                _log_render_skip(obj, "legend", exc)
                continue

    if "text" not in skip_types:
        for obj in objects or []:
            if getattr(obj, "type", None) != "text":
                continue
            selected = getattr(obj, "id", None) == selected_text_id
            try:
                text_artists = render_text_object(
                    ax,
                    obj,
                    ctx,
                    selected=selected and not getattr(obj, "locked", False),
                    show_editor_chrome=show_editor_chrome,
                    text_refs=text_refs,
                )
                artists.extend(text_artists)
            except Exception as exc:
                _log_render_skip(obj, "text", exc)
                continue

    return artists


def _render_line(ax, obj, *, line_alpha: float) -> list:
    from matplotlib.patches import Polygon as MplPolygon

    artists: list = []
    xs = [p[0] for p in obj.points]
    ys = [p[1] for p in obj.points]
    style = getattr(obj, "line_style", "-") or "-"
    color_hex = getattr(obj, "line_color", "#000000") or "#000000"
    rgba_color = mcolors.to_rgba(color_hex, float(line_alpha))
    linewidth = 1.0
    (line,) = ax.plot(
        xs,
        ys,
        linestyle=_line_style_to_mpl(style),
        color=rgba_color,
        linewidth=linewidth,
        zorder=1,
        clip_on=False,
    )
    artists.append(line)

    arrow_mode = getattr(obj, "arrow_mode", "none") or "none"
    arrow_head = getattr(obj, "arrow_head", "stealth") or "stealth"
    if arrow_mode == "none" or len(obj.points) < 2:
        return artists

    arrow_z = 4.0

    def _add_arrow(p_start, p_end):
        x0, y0 = float(p_start[0]), float(p_start[1])
        x1, y1 = float(p_end[0]), float(p_end[1])
        disp0 = ax.transData.transform((x0, y0))
        disp1 = ax.transData.transform((x1, y1))
        dx, dy = float(disp1[0] - disp0[0]), float(disp1[1] - disp0[1])
        seg_len_px = (dx * dx + dy * dy) ** 0.5
        if seg_len_px <= 1e-6:
            return

        ux, uy = dx / seg_len_px, dy / seg_len_px
        px, py = -uy, ux

        head_len = max(12.0, 8.0 * max(linewidth, 1.0))
        head_len = min(head_len, seg_len_px * 0.7)
        head_w = head_len * 0.78

        tx, ty = float(disp1[0]), float(disp1[1])
        bx, by = tx - ux * head_len, ty - uy * head_len
        lx, ly = bx + px * head_w * 0.5, by + py * head_w * 0.5
        rx, ry = bx - px * head_w * 0.5, by - py * head_w * 0.5

        inv = ax.transData.inverted().transform
        tip_d = tuple(inv((tx, ty)))
        left_d = tuple(inv((lx, ly)))
        right_d = tuple(inv((rx, ry)))

        if arrow_head == "open":
            (l1,) = ax.plot(
                [tip_d[0], left_d[0]],
                [tip_d[1], left_d[1]],
                color=rgba_color,
                linewidth=max(0.9, linewidth * 0.9),
                zorder=arrow_z,
                clip_on=False,
            )
            (l2,) = ax.plot(
                [tip_d[0], right_d[0]],
                [tip_d[1], right_d[1]],
                color=rgba_color,
                linewidth=max(0.9, linewidth * 0.9),
                zorder=arrow_z,
                clip_on=False,
            )
            artists.extend([l1, l2])
        elif arrow_head == "latex":
            poly = MplPolygon(
                [tip_d, left_d, right_d],
                closed=True,
                facecolor=rgba_color,
                edgecolor=rgba_color,
                linewidth=max(0.5, linewidth * 0.5),
                zorder=arrow_z,
                clip_on=False,
            )
            ax.add_patch(poly)
            artists.append(poly)
        else:
            indent = head_len * (3.6 / 8.5)
            mx, my = bx + ux * indent, by + uy * indent
            mid_d = tuple(inv((mx, my)))
            poly = MplPolygon(
                [tip_d, left_d, mid_d, right_d],
                closed=True,
                facecolor=rgba_color,
                edgecolor=rgba_color,
                linewidth=max(0.5, linewidth * 0.5),
                zorder=arrow_z,
                clip_on=False,
            )
            ax.add_patch(poly)
            artists.append(poly)

    pts = obj.points
    if arrow_mode == "end":
        _add_arrow(pts[-2], pts[-1])
    elif arrow_mode == "all":
        for j in range(len(pts) - 1):
            _add_arrow(pts[j], pts[j + 1])

    return artists


def _render_polygon(ax, obj, *, is_semi: bool):
    from matplotlib.patches import Polygon as MplPolygon

    face_alpha = 0.15 if not is_semi else 0.06
    edge_alpha = 1.0 if not is_semi else 0.4

    border_style = getattr(obj, "border_style", "-") or "-"
    border_hex = getattr(obj, "border_color", "#000000") or "#000000"
    fill_hex = getattr(obj, "fill_color", "#3366CC") or "#3366CC"

    if str(fill_hex).lower() == "transparent":
        face_rgba = (0.0, 0.0, 0.0, 0.0)
    else:
        face_rgba = mcolors.to_rgba(fill_hex, float(face_alpha))
    edge_rgba = mcolors.to_rgba(border_hex, float(edge_alpha))

    poly = MplPolygon(
        obj.points,
        facecolor=face_rgba,
        edgecolor=edge_rgba,
        linestyle=_line_style_to_mpl(border_style),
        linewidth=1.0,
        zorder=1,
    )
    ax.add_patch(poly)
    return poly


def _render_area_label(ax, obj, ctx: Any, *, is_semi: bool):
    v = getattr(obj, "value", 0)
    u = (getattr(obj, "axis_units", "Hz") or "Hz").strip().lower()
    if u == "norm" or "norm" in u:
        txt = f"{v:.2f}"
    else:
        txt = str(int(round(v)))

    font_family = ["DejaVu Sans", "Malgun Gothic"]
    if _is_serif_font(ctx):
        font_family = ["Times New Roman", "Noto Serif KR", "DejaVu Serif"]
    text_alpha = 0.3 if is_semi else 1.0
    return ax.text(
        getattr(obj, "x", 0),
        getattr(obj, "y", 0),
        txt,
        fontsize=12,
        fontfamily=font_family,
        color="#303133",
        alpha=text_alpha,
        va="center",
        ha="center",
        zorder=100,
        clip_on=True,
    )


def _render_reference(ax, obj, ctx: Any, *, is_semi: bool) -> list:
    artists: list = []
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    v = getattr(obj, "value", 0.0)
    mode = getattr(obj, "mode", "horizontal") or "horizontal"
    axis_units = getattr(obj, "axis_units", "") or "Hz"
    axis_scale = getattr(obj, "axis_scale", "linear")
    if axis_scale == "bark" and (axis_units or "").strip().lower() == "hz":
        plot_v = float(hz_to_bark(v))
    else:
        plot_v = v
    ref_norm = getattr(ctx, "normalization", None) or (
        getattr(ctx, "fixed_plot_params", None) or {}
    ).get("normalization")
    lbl = format_ref_label(v, axis_units, normalization=ref_norm)
    font_family = ["DejaVu Sans", "Malgun Gothic"]
    if _is_serif_font(ctx):
        font_family = ["Times New Roman", "Noto Serif KR", "DejaVu Serif"]
    style = getattr(obj, "line_style", "-") or "-"
    color_override = getattr(obj, "line_color", None)
    base_color = color_override or REF_LINE_COLOR
    ref_alpha = 0.3 if is_semi else REF_LINE_ALPHA
    rgba_line = mcolors.to_rgba(base_color, float(ref_alpha))
    text_alpha = 0.3 if is_semi else 1.0

    if mode == "horizontal":
        (ref_line,) = ax.plot(
            xlim,
            [plot_v, plot_v],
            color=rgba_line,
            linestyle=_line_style_to_mpl(style),
            linewidth=1,
            zorder=1.5,
            clip_on=True,
        )
        ref_txt = ax.text(
            xlim[0],
            plot_v,
            lbl,
            fontsize=12,
            fontfamily=font_family,
            color="#303133",
            alpha=text_alpha,
            va="center",
            zorder=2,
            clip_on=False,
        )
        artists.extend([ref_line, ref_txt])
    else:
        (ref_line,) = ax.plot(
            [plot_v, plot_v],
            ylim,
            color=rgba_line,
            linestyle=_line_style_to_mpl(style),
            linewidth=1,
            zorder=1.5,
            clip_on=True,
        )
        ref_txt = ax.text(
            plot_v,
            ylim[0],
            lbl,
            fontsize=12,
            fontfamily=font_family,
            color="#303133",
            alpha=text_alpha,
            va="bottom",
            ha="center",
            zorder=2,
            clip_on=False,
        )
        artists.extend([ref_line, ref_txt])

    return artists
