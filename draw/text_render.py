"""그리기 텍스트 렌더."""

from __future__ import annotations

from typing import Any

import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from matplotlib.transforms import Affine2D

from draw.draw_common import TextObject
from draw.plot_fonts import font_properties_for_run, iter_text_runs, resolve_font_style

_ITALIC_SHEAR_DEG = 12.0


def _italic_transform_at(ax, x: float, y: float, angle_deg: float = _ITALIC_SHEAR_DEG):
    """display 공간 기준 앵커 (x,y) 주위 skew — 한글·라틴·기호 모두 동일하게 기울임."""
    shear = float(np.tan(np.deg2rad(angle_deg)))
    dx, dy = ax.transData.transform((x, y))
    return (
        Affine2D().translate(dx, dy).skew(shear, 0).translate(-dx, -dy) + ax.transData
    )


def _line_height_data(ax, fig, font_size: float, linespacing: float = 1.15) -> float:
    px = float(font_size) * linespacing * fig.dpi / 72.0
    _, y0 = ax.transData.inverted().transform((0.0, 0.0))
    _, y1 = ax.transData.inverted().transform((0.0, px))
    return abs(y1 - y0)


def _measure_run_width(
    ax,
    fig,
    renderer,
    x: float,
    y: float,
    run: str,
    fp,
    *,
    font_italic: bool,
) -> float:
    trans = _italic_transform_at(ax, x, y) if font_italic else ax.transData
    probe = Text(x=x, y=y, text=run, fontproperties=fp, transform=trans)
    probe.set_figure(fig)
    bb = probe.get_window_extent(renderer)
    p0 = ax.transData.inverted().transform((bb.x0, bb.y0))
    p1 = ax.transData.inverted().transform((bb.x1, bb.y0))
    return float(p1[0] - p0[0])


def _union_fig_bounds(
    fig, artists: list, renderer
) -> tuple[float, float, float, float] | None:
    if not artists or renderer is None:
        return None
    x0 = y0 = float("inf")
    x1 = y1 = float("-inf")
    inv = fig.transFigure.inverted()
    for art in artists:
        try:
            bb = art.get_window_extent(renderer).transformed(inv)
            x0 = min(x0, bb.x0)
            y0 = min(y0, bb.y0)
            x1 = max(x1, bb.x1)
            y1 = max(y1, bb.y1)
        except Exception:
            continue
    if x0 == float("inf"):
        return None
    return (float(x0), float(y0), float(x1), float(y1))


def text_fig_bounds_from_artist(txt, fig) -> tuple[float, float, float, float] | None:
    if txt is None or fig is None:
        return None
    try:
        renderer = fig.canvas.get_renderer() if fig.canvas else None
        if renderer is None:
            return None
        bbox = txt.get_window_extent(renderer)
        bbox_fig = bbox.transformed(fig.transFigure.inverted())
        return (
            float(bbox_fig.x0),
            float(bbox_fig.y0),
            float(bbox_fig.x1),
            float(bbox_fig.y1),
        )
    except Exception:
        return None


def clamp_text_font_size(font_size: float) -> float:
    return max(4.0, min(float(font_size), 200.0))


def render_text_object(
    ax,
    text_obj: TextObject,
    ctx: Any,
    *,
    selected: bool = False,
    show_editor_chrome: bool = True,
    text_refs: list | None = None,
) -> list:
    """텍스트를 ax에 그리고 artist 목록을 반환."""
    if not getattr(text_obj, "visible", True):
        return []

    content = str(getattr(text_obj, "text", "") or "")
    if not content.strip():
        return []

    alpha = 0.35 if getattr(text_obj, "semi", False) else 1.0
    font_size = clamp_text_font_size(getattr(text_obj, "font_size", 13.0))
    text_obj.font_size = font_size
    color = getattr(text_obj, "text_color", "#303133") or "#303133"
    font_bold = bool(getattr(text_obj, "font_bold", False))
    font_italic = bool(getattr(text_obj, "font_italic", False))
    x = float(getattr(text_obj, "x", 0.0))
    y = float(getattr(text_obj, "y", 0.0))
    font_style = resolve_font_style(ctx)

    fig = ax.figure
    renderer = fig.canvas.get_renderer() if fig.canvas else None
    line_h = _line_height_data(ax, fig, font_size)
    lines = content.split("\n")
    n_lines = len(lines)

    fragment_artists: list = []
    stroke = pe.withStroke(
        linewidth=max(1.0, font_size * 0.08),
        foreground="white",
        alpha=alpha,
    )

    for line_idx, line in enumerate(lines):
        y_line = y + (n_lines - 1 - line_idx) * line_h
        x_cursor = x
        for run, is_ko in iter_text_runs(line):
            if run == "\n":
                continue
            if not run:
                continue
            fp = font_properties_for_run(
                is_korean=is_ko,
                font_style=font_style,
                font_size=font_size,
                font_bold=font_bold,
            )
            trans = (
                _italic_transform_at(ax, x_cursor, y_line)
                if font_italic
                else ax.transData
            )
            txt = ax.text(
                x_cursor,
                y_line,
                run,
                transform=trans,
                fontproperties=fp,
                color=mcolors.to_rgba(color, alpha),
                ha="left",
                va="bottom",
                zorder=210,
                clip_on=False,
            )
            txt.set_path_effects([stroke])
            fragment_artists.append(txt)
            if renderer is not None:
                x_cursor += _measure_run_width(
                    ax,
                    fig,
                    renderer,
                    x_cursor,
                    y_line,
                    run,
                    fp,
                    font_italic=font_italic,
                )

    bounds = _union_fig_bounds(fig, fragment_artists, renderer)
    if text_refs is not None:
        text_refs.append((fragment_artists, text_obj, bounds))

    artists: list = list(fragment_artists)
    chrome = show_editor_chrome and selected and not getattr(text_obj, "locked", False)
    if chrome and bounds is not None:
        x0, y0, x1, y1 = bounds
        pad = 0.004
        outline = Rectangle(
            (x0 - pad, y0 - pad),
            max(x1 - x0, 1e-4) + 2 * pad,
            max(y1 - y0, 1e-4) + 2 * pad,
            transform=fig.transFigure,
            fill=False,
            edgecolor="#409EFF",
            linewidth=0.8,
            zorder=249,
            clip_on=False,
        )
        ax.add_patch(outline)
        artists.append(outline)

    return artists
