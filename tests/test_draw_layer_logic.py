"""layer_logic — 그리기 디자인 설정·area_label 재구성."""

from draw.draw_common import AreaLabelObject, LineObject, PolygonObject
from ui.widgets.layer_logic import (
    apply_line_settings,
    apply_polygon_settings,
    apply_reference_settings,
    rebuild_area_labels_for_polygons,
    sync_parent_lock_to_children,
)


def test_apply_line_settings():
    obj = LineObject(points=[(0, 0), (1, 1)])
    apply_line_settings(
        obj,
        {
            "line_style": "--",
            "line_color": "#AABBCC",
            "arrow_mode": "end",
            "arrow_head": "open",
        },
    )
    assert obj.line_style == "--"
    assert obj.line_color == "#AABBCC"
    assert obj.arrow_mode == "end"
    assert obj.arrow_head == "open"


def test_apply_line_settings_partial():
    obj = LineObject(points=[(0, 0)], arrow_mode="all")
    apply_line_settings(obj, {"line_style": "-", "line_color": "#000000"})
    apply_line_settings(obj, {"line_color": "#FFFFFF"})
    assert obj.line_style == "-"
    assert obj.line_color == "#FFFFFF"
    assert obj.arrow_mode == "all"


def test_apply_polygon_settings():
    obj = PolygonObject(points=[(0, 0), (1, 0), (0, 1)])
    apply_polygon_settings(
        obj,
        {
            "border_style": "---",
            "border_color": "#111111",
            "fill_color": "transparent",
            "area_label_visible": True,
        },
    )
    assert obj.border_style == "---"
    assert obj.border_color == "#111111"
    assert obj.fill_color == "transparent"
    assert obj.show_area_label is True


def test_apply_reference_settings():
    from draw.draw_common import ReferenceLineObject

    obj = ReferenceLineObject(mode="horizontal", value=500.0)
    apply_reference_settings(obj, {"line_style": "--", "line_color": "#999999"})
    assert obj.line_style == "--"
    assert obj.line_color == "#999999"


def test_rebuild_area_labels_creates_label_when_enabled():
    poly = PolygonObject(
        points=[(0.0, 0.0), (4.0, 0.0), (0.0, 3.0)],
        id="poly1",
        show_area_label=True,
    )
    result = rebuild_area_labels_for_polygons([poly])
    assert len(result) == 2
    assert result[0] is poly
    lbl = result[1]
    assert isinstance(lbl, AreaLabelObject)
    assert lbl.parent_id == "poly1"
    assert lbl.value == 6.0


def test_rebuild_area_labels_removes_when_disabled():
    poly = PolygonObject(
        points=[(0.0, 0.0), (4.0, 0.0), (0.0, 3.0)],
        id="poly1",
        show_area_label=False,
    )
    old_lbl = AreaLabelObject(parent_id="poly1", value=99.0, x=1.0, y=1.0)
    result = rebuild_area_labels_for_polygons([poly, old_lbl])
    assert result == [poly]


def test_sync_parent_lock_to_children():
    poly = PolygonObject(points=[(0, 0), (1, 0), (0, 1)], id="p1", locked=False)
    lbl = AreaLabelObject(parent_id="p1", value=1.0, x=0.5, y=0.5, locked=False)
    objs = [poly, lbl]
    sync_parent_lock_to_children(objs, 0, True)
    assert poly.locked is False
    assert lbl.locked is True
