"""draw_common — 데이터 모델·넓이 계산."""

from draw.draw_common import (
    LineObject,
    PolygonObject,
    TextObject,
    polygon_area,
)


def test_polygon_area_triangle():
    pts = [(0.0, 0.0), (4.0, 0.0), (0.0, 3.0)]
    assert polygon_area(pts) == 6.0


def test_polygon_area_too_few_points():
    assert polygon_area([]) == 0.0
    assert polygon_area([(1.0, 1.0), (2.0, 2.0)]) == 0.0


def test_text_object_defaults():
    obj = TextObject(text="hello", x=100.0, y=200.0)
    assert obj.type == "text"
    assert obj.font_size == 13.0
    assert obj.text_color == "#303133"
    assert obj.axis_units == "Hz"
    assert obj.visible is True
    assert obj.locked is False


def test_line_object_has_arrow_defaults():
    obj = LineObject(points=[(0.0, 0.0), (1.0, 1.0)])
    assert obj.arrow_mode == "none"
    assert obj.arrow_head == "stealth"


def test_polygon_object_fill_default():
    obj = PolygonObject(points=[(0, 0), (1, 0), (0, 1)])
    assert obj.fill_color == "#3366CC"
    assert obj.show_area_label is False
