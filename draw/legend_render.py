"""Matplotlib figure fraction 범례 렌더."""

from __future__ import annotations

from typing import Any

import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle

from core.compare_settings import get_series_design_cfg
from draw.draw_common import LegendObject
from draw.legend_helpers import (
    LEGEND_ICON_LEFT,
    LEGEND_ICON_RIGHT,
    LEGEND_TEXT_START,
    ensure_legend_content_fits,
    legend_box_axes_bounds,
    legend_box_content_bounds,
    legend_content_scale,
    legend_row_pitch,
    _legend_font_family,
)
from engine.plot_engine import PlotEngine

_LEGEND_TEXT_COLOR = "#303133"


def _line_style_to_mpl(style: str):
    if style == "---":
        return (0, (6.0, 3.0))
    if style in ("--", ":"):
        return style
    return "-"


def _resolve_entry_style(
    popup: Any,
    series_id: int,
    is_compare: bool,
) -> dict:
    ds = getattr(popup, "design_settings", None) or {}
    if is_compare:
        cfg = get_series_design_cfg(ds, series_id)
    else:
        cfg = ds if isinstance(ds, dict) else {}

    pe = PlotEngine()
    ell_color = pe._resolve_plot_color(cfg.get("ell_color"), "#606060")
    ell_style = cfg.get("ell_style", "-") or "-"
    ell_thick = float(cfg.get("ell_thick", 2.0) or 2.0)
    centroid_marker = cfg.get("centroid_marker", "o") or "o"

    if is_compare:
        default_face = pe._resolve_plot_color(cfg.get("raw_color"), ell_color)
    else:
        default_face = "black"

    mpl_marker, face_c, edge_c, marker_lw, marker_size = pe._resolve_centroid_marker(
        centroid_marker,
        default_face=default_face,
        base_size=36,
    )

    return {
        "line_color": ell_color,
        "line_style": ell_style,
        "line_width": max(1.0, ell_thick * 0.75),
        "marker": mpl_marker,
        "marker_face": face_c,
        "marker_edge": edge_c,
        "marker_lw": marker_lw,
        "marker_size": marker_size,
    }


def render_legend(
    ax,
    legend: LegendObject,
    popup: Any,
    *,
    selected: bool = False,
    show_editor_chrome: bool = True,
) -> list:
    """범례를 figure 좌표에 그리고 artist 목록 반환."""
    artists: list = []
    if not getattr(legend, "visible", True):
        return artists

    fig = ax.figure
    entries = list(getattr(legend, "entries", []) or [])
    ensure_legend_content_fits(legend, fig, popup, entries=entries)

    x0, y0, x1, y1 = legend_box_axes_bounds(legend)
    alpha = 0.35 if getattr(legend, "semi", False) else 1.0
    trans = fig.transFigure
    show_border = bool(getattr(legend, "show_border", False))
    # 예전에는 show_border 하나로 테두리+흰 배경을 함께 켰음.
    if hasattr(legend, "show_fill"):
        show_fill = bool(getattr(legend, "show_fill", False))
    else:
        show_fill = show_border
    box_w = x1 - x0
    box_h = y1 - y0
    n_entries = max(len(entries), 1)
    row_pitch = legend_row_pitch(legend, n_entries)
    scale = legend_content_scale(legend, n_entries)
    font_size = float(getattr(legend, "font_size", 10.0)) * scale
    chrome = show_editor_chrome and selected

    if show_fill or show_border or chrome:
        fill_opacity = float(getattr(legend, "fill_opacity", 0.92))
        fill_opacity = max(0.0, min(1.0, fill_opacity))
        face = (1, 1, 1, fill_opacity * alpha) if show_fill else (1, 1, 1, 0)
        if show_border:
            edge = "#409EFF" if chrome else "#D0D3D9"
            lw = 0.8 if chrome else 0.5
        elif chrome:
            edge = "#409EFF"
            lw = 0.8
        else:
            edge = "none"
            lw = 0.0
        bg = Rectangle(
            (x0, y0),
            box_w,
            box_h,
            transform=trans,
            facecolor=face,
            edgecolor=edge,
            linewidth=lw,
            zorder=200,
            clip_on=False,
        )
        ax.add_patch(bg)
        artists.append(bg)

    if not entries:
        return artists

    font_family = _legend_font_family(popup)
    cx0, _cy0, cx1, cy1 = legend_box_content_bounds(legend)
    content_w = cx1 - cx0
    icon_left = cx0 + LEGEND_ICON_LEFT * content_w
    icon_right = cx0 + LEGEND_ICON_RIGHT * content_w
    icon_mid = (icon_left + icon_right) / 2
    gap = 0.015 * content_w
    text_x = cx0 + LEGEND_TEXT_START * content_w

    for i, entry in enumerate(entries):
        row_y = cy1 - row_pitch * (i + 0.5)
        style = _resolve_entry_style(
            popup,
            int(getattr(entry, "series_id", 0)),
            bool(getattr(legend, "is_compare", False)),
        )
        line_w = style["line_width"] * scale
        marker_size = style["marker_size"] * scale
        marker_lw = style["marker_lw"] * scale
        (line_left,) = ax.plot(
            [icon_left, icon_mid - gap],
            [row_y, row_y],
            transform=trans,
            color=mcolors.to_rgba(style["line_color"], alpha),
            linestyle=_line_style_to_mpl(style["line_style"]),
            linewidth=line_w,
            solid_capstyle="butt",
            zorder=201,
            clip_on=False,
        )
        (line_right,) = ax.plot(
            [icon_mid + gap, icon_right],
            [row_y, row_y],
            transform=trans,
            color=mcolors.to_rgba(style["line_color"], alpha),
            linestyle=_line_style_to_mpl(style["line_style"]),
            linewidth=line_w,
            solid_capstyle="butt",
            zorder=201,
            clip_on=False,
        )
        artists.extend([line_left, line_right])
        sc = ax.scatter(
            [icon_mid],
            [row_y],
            transform=trans,
            marker=style["marker"],
            s=marker_size,
            facecolors=mcolors.to_rgba(style["marker_face"], alpha),
            edgecolors=mcolors.to_rgba(style["marker_edge"], alpha),
            linewidths=marker_lw,
            zorder=202,
            clip_on=False,
        )
        artists.append(sc)

        txt = ax.text(
            text_x,
            row_y,
            str(getattr(entry, "text", "") or ""),
            transform=trans,
            fontsize=font_size,
            fontfamily=font_family,
            color=mcolors.to_rgba(_LEGEND_TEXT_COLOR, alpha),
            va="center",
            ha="left",
            zorder=203,
            clip_on=False,
        )
        txt.set_path_effects(
            [
                pe.withStroke(
                    linewidth=max(1.0, 1.5 * scale), foreground="white", alpha=alpha
                )
            ]
        )
        artists.append(txt)

    if chrome and not getattr(legend, "locked", False):
        handle_size = 0.010 * max(0.8, scale)
        corners = [
            (x0, y0),
            ((x0 + x1) / 2, y0),
            (x1, y0),
            (x1, (y0 + y1) / 2),
            (x1, y1),
            ((x0 + x1) / 2, y1),
            (x0, y1),
            (x0, (y0 + y1) / 2),
        ]
        for hx, hy in corners:
            h = Rectangle(
                (hx - handle_size / 2, hy - handle_size / 2),
                handle_size,
                handle_size,
                transform=trans,
                facecolor="white",
                edgecolor="#409EFF",
                linewidth=0.8,
                zorder=250,
                clip_on=False,
            )
            ax.add_patch(h)
            artists.append(h)

    return artists
