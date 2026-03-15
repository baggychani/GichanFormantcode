# draw/draw_common.py — 그리기 공통: 스냅 재사용, 데이터 모델, 넓이 계산

from __future__ import annotations

from dataclasses import dataclass, field

# 기획: 기존 눈금자 툴에서 스냅·호버·툴팁 로직 import 재사용
from tools.ruler import snap_query

__all__ = [
    "DrawMode",
    "snap_query",
    "DrawObject",
    "LineObject",
    "PolygonObject",
    "ReferenceLineObject",
    "polygon_area",
]


# 모드 상수 (indicator와 일치)
class DrawMode:
    LINE = "line"
    POLYGON = "polygon"
    REF_H = "ref_h"
    REF_V = "ref_v"


@dataclass
class LineObject:
    """선(폴리라인) 객체. 데이터 좌표 점 리스트. point_labels: 꼭지점 스냅 라벨 (a-e-o 등)."""

    type: str = "line"
    name: str = ""
    visible: bool = True
    order: int = 0
    points: list[tuple[float, float]] = field(default_factory=list)
    point_labels: list[str] = field(default_factory=list)
    axis_units: str = "Hz"
    locked: bool = False
    semi: bool = False


@dataclass
class PolygonObject:
    """영역(폴리곤) 객체. 닫힌 점 리스트. point_labels: 꼭지점 스냅 라벨 (o-e-a 등, 닫힌 표시는 UI에서)."""

    type: str = "polygon"
    name: str = ""
    visible: bool = True
    order: int = 0
    points: list[tuple[float, float]] = field(default_factory=list)
    point_labels: list[str] = field(default_factory=list)
    axis_units: str = "Hz"
    locked: bool = False
    semi: bool = False


@dataclass
class ReferenceLineObject:
    """참조선 객체. 수평/수직, 값 하나. value는 축 스케일 좌표. axis_scale: 해당 축 스케일(bark/linear/log)."""

    type: str = "reference"
    name: str = ""
    visible: bool = True
    order: int = 0
    mode: str = "horizontal"
    value: float = 0.0
    axis_units: str = "Hz"
    axis_name: str = ""
    axis_scale: str = "linear"
    locked: bool = False
    semi: bool = False


DrawObject = LineObject | PolygonObject | ReferenceLineObject


def polygon_area(points: list[tuple[float, float]]) -> float:
    """데이터 좌표 기준 폴리곤 넓이 (Shoelace formula).
    points: [(x,y), ...] 닫힌 순서. 단위는 호출부 해석 (Hz² 등).
    """
    if len(points) < 3:
        return 0.0
    n = len(points)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0
