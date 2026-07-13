"""Drawing package with lazy presentation-module imports."""

from importlib import import_module

from .draw_common import (
    AreaLabelObject,
    DrawMode,
    DrawObject,
    LegendEntry,
    LegendObject,
    LineObject,
    PolygonObject,
    ReferenceLineObject,
    TextObject,
    polygon_area,
    snap_query,
)

__all__ = [
    "DrawModeIndicator",
    "DrawMode",
    "snap_query",
    "DrawObject",
    "LineObject",
    "PolygonObject",
    "ReferenceLineObject",
    "AreaLabelObject",
    "LegendEntry",
    "LegendObject",
    "TextObject",
    "polygon_area",
    "draw_line",
    "draw_polygon",
    "draw_reference",
    "draw_text",
]

_LAZY_MODULES = {"draw_line", "draw_polygon", "draw_reference", "draw_text"}


def __getattr__(name):
    if name == "DrawModeIndicator":
        from .indicator import DrawModeIndicator

        return DrawModeIndicator
    if name in _LAZY_MODULES:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(name)
