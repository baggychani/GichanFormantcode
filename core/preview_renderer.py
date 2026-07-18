"""Framework-neutral LIVE preview rendering."""

from __future__ import annotations

from io import BytesIO
import math
from types import SimpleNamespace
from typing import Any, Mapping

from core.normalization_service import normalize_dataframe


class PreviewRenderer:
    def __init__(self, plot_engine, figure):
        self.plot_engine = plot_engine
        self.figure = figure

    def render_png(
        self,
        current_data: dict[str, Any],
        params: dict[str, Any],
        ranges: dict[str, str],
        design_settings: dict[str, Any],
        *,
        filter_state: dict[str, str] | None = None,
        layer_overrides: dict[str, dict[str, Any]] | None = None,
        layer_order: list[str] | None = None,
        custom_label_offsets: dict[str, tuple[float, float]] | None = None,
        draw_objects: list[Mapping[str, Any]] | None = None,
        include_context: bool = False,
    ) -> bytes | tuple[bytes, dict[str, Any]]:
        self.figure.clear()
        normalization = params.get("normalization")
        if normalization:
            dataframe = normalize_dataframe(
                current_data["df"],
                normalization,
                data_item=current_data,
            )
            draw_result = self.plot_engine.draw_single_normalized(
                self.figure,
                dataframe,
                normalization,
                manual_ranges=ranges,
                filter_state=filter_state,
                design_settings=design_settings,
                sigma=float(params.get("sigma", 2.0)),
                custom_label_offsets=custom_label_offsets,
                layer_overrides=layer_overrides,
                plot_params=params,
                layer_order=layer_order,
            )
        else:
            draw_result = self.plot_engine.draw_plot(
                self.figure,
                current_data["df"],
                params,
                manual_ranges=ranges,
                filter_state=filter_state,
                design_settings=design_settings,
                layer_overrides=layer_overrides,
                layer_order=layer_order,
                custom_label_offsets=custom_label_offsets,
            )

        objects = []
        if draw_objects and self.figure.axes:
            from draw.draw_layer_render import render_draw_objects

            for raw in draw_objects:
                if not isinstance(raw, Mapping):
                    continue
                if raw.get("type", "line") == "legend":
                    entries = [SimpleNamespace(series_id=int(entry.get("series_id", 0)), text=str(entry.get("text", ""))) for entry in raw.get("entries", []) if isinstance(entry, Mapping)]
                    objects.append(SimpleNamespace(
                        type="legend",
                        id=str(raw.get("id", "")),
                        name=str(raw.get("name", "범례")),
                        entries=entries,
                        fx=float(raw.get("fx", 0.016)), fy=float(raw.get("fy", 0.20)),
                        width_frac=float(raw.get("width_frac", 0.30)), height_frac=float(raw.get("height_frac", 0.14)),
                        font_size=float(raw.get("font_size", 10)),
                        show_border=bool(raw.get("show_border", True)),
                        border_style=str(raw.get("border_style", "-")), border_color=str(raw.get("border_color", "#3f4650")),
                        show_fill=bool(raw.get("show_fill", True)), fill_color=str(raw.get("fill_color", "#ffffff")),
                        fill_opacity=float(raw.get("fill_opacity", 1)), font_family=str(raw.get("font_family", "Noto Sans KR")),
                        font_weight=str(raw.get("font_weight", "regular")), font_italic=bool(raw.get("font_italic", False)),
                        visible=bool(raw.get("visible", True)), locked=False, semi=bool(raw.get("semi", False)), is_compare=False,
                    ))
                    continue
                if raw.get("type", "line") == "reference":
                    objects.append(SimpleNamespace(
                        type="reference",
                        id=str(raw.get("id", "")),
                        mode=str(raw.get("mode", "horizontal")),
                        value=float(raw.get("value", 0)),
                        axis_units=str(raw.get("axis_units", "Hz")),
                        axis_name=str(raw.get("axis_name", "")),
                        axis_scale=str(raw.get("axis_scale", "linear")),
                        line_style=str(raw.get("line_style", "-")),
                        line_color=raw.get("line_color"),
                        visible=bool(raw.get("visible", True)),
                        semi=bool(raw.get("semi", False)),
                    ))
                    continue
                if raw.get("type", "line") != "line":
                    continue
                points = raw.get("points")
                if not isinstance(points, list) or len(points) < 2:
                    continue
                objects.append(SimpleNamespace(
                    type="line",
                    visible=bool(raw.get("visible", True)),
                    points=[tuple(point) for point in points],
                    line_color=raw.get("line_color", "#2563eb"),
                    line_style=raw.get("line_style", "-"),
                    line_width=float(raw.get("line_width", 2)),
                    arrow_mode=raw.get("arrow_mode", "none"),
                    arrow_head=raw.get("arrow_head", "stealth"),
                    semi=bool(raw.get("semi", False)),
                ))
            render_draw_objects(
                self.figure.axes[0],
                objects,
                SimpleNamespace(
                    design_settings=design_settings,
                    normalization=params.get("normalization"),
                    fixed_plot_params=params,
                ),
            )

        # draw 한 번으로 ruler 좌표 + PNG를 같이 뽑는다 (savefig 재렌더 방지)
        self.figure.canvas.draw()
        ruler_context = None
        if include_context:
            ruler_context = self._build_ruler_context(draw_result, params)
            ruler_context["legend_bounds"] = {
                str(getattr(obj, "id", "")): {
                    "fx": float(getattr(obj, "fx", 0.016)),
                    "fy": float(getattr(obj, "fy", 0.20)),
                    "width_frac": float(getattr(obj, "width_frac", 0.30)),
                    "height_frac": float(getattr(obj, "height_frac", 0.14)),
                }
                for obj in objects
                if getattr(obj, "type", None) == "legend" and getattr(obj, "id", "")
            }
        png_data = self._encode_drawn_png()
        if include_context:
            return png_data, ruler_context or {}
        return png_data

    def _encode_drawn_png(self) -> bytes:
        """이미 canvas.draw()된 figure를 재렌더 없이 PNG로 인코딩."""
        buffer = BytesIO()
        canvas = self.figure.canvas
        if hasattr(canvas, "buffer_rgba"):
            try:
                import numpy as np
                from PIL import Image

                rgba = np.asarray(canvas.buffer_rgba())
                Image.fromarray(rgba).save(buffer, format="PNG")
                return buffer.getvalue()
            except Exception:
                buffer = BytesIO()
        if hasattr(canvas, "print_png"):
            canvas.print_png(buffer)
            return buffer.getvalue()
        self.figure.savefig(buffer, format="png", facecolor="white")
        return buffer.getvalue()

    def _build_ruler_context(
        self, draw_result: Any, params: dict[str, Any]
    ) -> dict[str, Any]:
        ax = None
        snapping_data: list[dict[str, Any]] = []
        if isinstance(draw_result, tuple) and len(draw_result) >= 2:
            ax = draw_result[0]
            snapping_data = draw_result[1] or []
            label_data = draw_result[2] or [] if len(draw_result) >= 3 else []
        else:
            label_data = []

        # PNG(buffer_rgba)와 동일한 픽셀 크기 — get_width_height와 어긋나면 호버 좌표가 전부 틀림
        image_width, image_height = self.figure.canvas.get_width_height()
        try:
            rgba = getattr(self.figure.canvas, "buffer_rgba", None)
            if rgba is not None:
                arr = rgba()
                image_height = int(arr.shape[0])
                image_width = int(arr.shape[1])
        except Exception:
            pass
        points: list[dict[str, Any]] = []
        if ax is not None:
            renderer = self.figure.canvas.get_renderer()
            bbox = ax.get_window_extent(renderer)
            axes_bbox = {
                "left": float(bbox.x0),
                "bottom": float(bbox.y0),
                "width": float(bbox.width),
                "height": float(bbox.height),
            }
            for source in snapping_data:
                try:
                    x = float(source["x"])
                    y = float(source["y"])
                    px, py = ax.transData.transform((x, y))
                except (KeyError, TypeError, ValueError):
                    continue
                if not all(math.isfinite(value) for value in (x, y, px, py)):
                    continue
                point = {
                    "x": x,
                    "y": y,
                    "px": float(px),
                    "py": float(py),
                    "type": str(source.get("type", "raw")),
                    "label": str(source.get("label", "")),
                    "color": str(source.get("color", "#168f8b")),
                }
                for key in ("raw_f1", "raw_f2"):
                    value = source.get(key)
                    if value is not None:
                        try:
                            number = float(value)
                        except (TypeError, ValueError):
                            continue
                        if math.isfinite(number):
                            point[key] = number
                points.append(point)
            labels = []
            x_min, x_max = ax.get_xlim()
            y_min, y_max = ax.get_ylim()
            label_artists = []
            if isinstance(draw_result, tuple) and len(draw_result) >= 4:
                label_artists = draw_result[3] or []
            renderer = self.figure.canvas.get_renderer()
            for index, source in enumerate(label_data):
                try:
                    cx, cy = float(source["cx"]), float(source["cy"])
                    lx, ly = float(source["lx"]), float(source["ly"])
                    cpx, cpy = ax.transData.transform((cx, cy))
                    lpx, lpy = ax.transData.transform((lx, ly))
                except (KeyError, TypeError, ValueError):
                    continue
                if not all(math.isfinite(value) for value in (cx, cy, lx, ly, cpx, cpy, lpx, lpy)):
                    continue
                bbox = None
                if index < len(label_artists):
                    try:
                        artist_bbox = label_artists[index].get_window_extent(renderer)
                        bbox = {
                            "left": float(artist_bbox.x0),
                            "top": float(image_height - artist_bbox.y1),
                            "width": float(artist_bbox.width),
                            "height": float(artist_bbox.height),
                        }
                    except (AttributeError, TypeError, ValueError):
                        bbox = None
                labels.append({
                    "vowel": str(source.get("vowel", "")),
                    "display_vowel": str(source.get("display_vowel", source.get("vowel", ""))),
                    "cx": cx,
                    "cy": cy,
                    "lx": lx,
                    "ly": ly,
                    "px": float(cpx),
                    "py": float(cpy),
                    "lpx": float(lpx),
                    "lpy": float(lpy),
                    "bbox": bbox,
                    "fontsize": source.get("fontsize"),
                    "ha": source.get("ha", "left"),
                    "va": source.get("va", "bottom"),
                    "lbl_color": source.get("lbl_color"),
                    "lbl_bold": source.get("lbl_bold"),
                    "lbl_italic": source.get("lbl_italic"),
                })
        else:
            axes_bbox = {"left": 0.0, "bottom": 0.0, "width": 0.0, "height": 0.0}
            labels = []
            x_min = x_max = y_min = y_max = 0.0

        return {
            "image_width": int(image_width),
            "image_height": int(image_height),
            "axes_bbox": axes_bbox,
            "points": points,
            "labels": labels,
            "xlim": [float(x_min), float(x_max)],
            "ylim": [float(y_min), float(y_max)],
            "params": {
                "normalization": params.get("normalization"),
                "use_bark_units": bool(params.get("use_bark_units", False)),
                "f1_scale": str(params.get("f1_scale", "linear")),
                "f2_scale": str(params.get("f2_scale", "linear")),
            },
        }
