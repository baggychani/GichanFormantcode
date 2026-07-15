"""Framework-neutral LIVE preview rendering."""

from __future__ import annotations

from io import BytesIO
import math
from typing import Any

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

        # The ruler must snap to the same rendered points as PySide.  Capture
        # Matplotlib's post-transform pixel coordinates, rather than asking
        # the browser to recreate axis scaling/inversion rules.
        ruler_context = None
        if include_context:
            self.figure.canvas.draw()
            ruler_context = self._build_ruler_context(draw_result, params)
        buffer = BytesIO()
        self.figure.savefig(buffer, format="png", facecolor="white")
        png_data = buffer.getvalue()
        if include_context:
            return png_data, ruler_context or {}
        return png_data

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

        image_width, image_height = self.figure.canvas.get_width_height()
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
                "f2_scale": str(params.get("f2_scale", "linear")),
            },
        }
