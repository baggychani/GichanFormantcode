# ui/layer_logic.py — 레이어 공통 로직 (Qt 비의존, 순수 함수·상수)
# layer_dock에서 import하여 사용. 상태 소유는 popup에 두고 계산만 여기서 수행.

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
from draw.draw_common import AreaLabelObject, polygon_area

# -----------------------------------------------------------------------------
# 상수 (layer_dock과 공유)
# -----------------------------------------------------------------------------
LAYER_ROW_MIME_TYPE = "application/x-gichan-layer-vowel"
DRAW_ROW_MIME_TYPE = "application/x-gichan-draw-layer"

# Filter state: "ON" | "OFF" | "SEMI"
FilterStateDict = Dict[str, str]


# -----------------------------------------------------------------------------
# 필터 상태 (가시성·반투명)
# -----------------------------------------------------------------------------
def apply_global_eye(
    state: FilterStateDict,
    keys: Sequence[str],
    turn_on: bool,
) -> FilterStateDict:
    """전체 눈 클릭: 모두 켜기(turn_on=True) 또는 모두 끄기(turn_on=False). 새 dict 반환."""
    result = dict(state)
    if not keys:
        return result
    value = "ON" if turn_on else "OFF"
    for k in keys:
        result[k] = value
    return result


def apply_global_semi(
    state: FilterStateDict,
    keys: Sequence[str],
    semi: bool,
) -> FilterStateDict:
    """전체 반투명 클릭: visible인 항목을 모두 SEMI(semi=True) 또는 ON(semi=False)으로. 새 dict 반환."""
    result = dict(state)
    if not keys:
        return result
    value = "SEMI" if semi else "ON"
    for k in keys:
        if result.get(k) != "OFF":
            result[k] = value
    return result


def toggle_item_visibility(
    eye_checked: bool,
    semi_checked: bool,
) -> str:
    """한 항목의 눈/반투명 토글 결과값. "ON" | "OFF" | "SEMI"."""
    if not eye_checked:
        return "OFF"
    return "SEMI" if semi_checked else "ON"


# -----------------------------------------------------------------------------
# 순서 (드래그 후 삽입 위치 계산)
# -----------------------------------------------------------------------------
def compute_order_after_drop(
    ordered_list: List[Any],
    dragged_list: List[Any],
    drop_target: Any,
    after: bool,
) -> Optional[List[Any]]:
    """
    드래그한 항목들을 drop_target 위(after=False) 또는 아래(after=True)에 삽입한 새 순서 반환.
    ordered_list: 현재 표시 순서. dragged_list: 드래그 중인 항목들(순서 유지). drop_target: 드롭 대상 항목.
    유효하지 않으면 None 반환. (그리기 객체 등 unhashable 항목도 리스트 멤버십으로 처리.)
    """
    if not dragged_list or drop_target not in ordered_list:
        return None
    if not all(d in ordered_list for d in dragged_list):
        return None
    new_order = [v for v in ordered_list if v not in dragged_list]
    if drop_target in dragged_list:
        target_pos = ordered_list.index(drop_target)
        insert_idx = len(
            [
                v
                for v in ordered_list[: target_pos + (1 if after else 0)]
                if v not in dragged_list
            ]
        )
    else:
        target_idx = new_order.index(drop_target)
        insert_idx = target_idx + (1 if after else 0)
    for v in dragged_list:
        new_order.insert(insert_idx, v)
        insert_idx += 1
    return new_order


# -----------------------------------------------------------------------------
# 그리기 디자인 설정 적용 (순수 데이터 매핑)
# -----------------------------------------------------------------------------
def apply_line_settings(obj: object, cfg: Dict[str, Any]) -> None:
    """선 객체에 cfg의 키만 반영. 없는 키는 기존 값 유지."""
    if "line_style" in cfg:
        setattr(obj, "line_style", (cfg.get("line_style") or "-"))
    if "line_color" in cfg:
        setattr(obj, "line_color", cfg.get("line_color") or "#000000")
    if "arrow_mode" in cfg:
        setattr(obj, "arrow_mode", cfg.get("arrow_mode") or "none")
    if "arrow_head" in cfg:
        setattr(obj, "arrow_head", cfg.get("arrow_head") or "stealth")


def apply_polygon_settings(obj: object, cfg: Dict[str, Any]) -> None:
    """폴리곤 객체에 cfg의 키만 반영. area_label_visible은 show_area_label로 매핑."""
    if "border_style" in cfg:
        setattr(obj, "border_style", (cfg.get("border_style") or "-"))
    if "border_color" in cfg:
        setattr(obj, "border_color", (cfg.get("border_color") or "#000000"))
    if "fill_color" in cfg:
        setattr(obj, "fill_color", cfg.get("fill_color"))
    if "area_label_visible" in cfg:
        setattr(obj, "show_area_label", cfg.get("area_label_visible", False))


def apply_reference_settings(obj: object, cfg: Dict[str, Any]) -> None:
    """참조선 객체에 cfg의 키만 반영. line_color는 None일 때 기본값 사용."""
    if "line_style" in cfg:
        setattr(obj, "line_style", (cfg.get("line_style") or "-"))
    if "line_color" in cfg:
        color = cfg.get("line_color")
        setattr(obj, "line_color", (color or "#AAAAAA"))


def rebuild_area_labels_for_polygons(all_objs: List[object]) -> List[object]:
    """polygon.show_area_label 상태를 기준으로 area_label 목록을 재구성한 새 리스트 반환."""
    if not all_objs:
        return []

    labels_by_parent: Dict[str, List[object]] = {}
    for obj in all_objs:
        if getattr(obj, "type", "") == "area_label":
            pid = getattr(obj, "parent_id", None)
            if pid:
                labels_by_parent.setdefault(pid, []).append(obj)

    desired_labels_by_parent: Dict[str, List[object]] = {}
    for obj in all_objs:
        if getattr(obj, "type", "") != "polygon":
            continue
        pid = getattr(obj, "id", None)
        if not pid:
            continue
        if not getattr(obj, "show_area_label", False):
            desired_labels_by_parent[pid] = []
            continue

        existing = labels_by_parent.get(pid, [])
        if existing:
            desired_labels_by_parent[pid] = list(existing)
            continue

        pts = getattr(obj, "points", None) or []
        if len(pts) < 3:
            desired_labels_by_parent[pid] = []
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        try:
            val = polygon_area(pts)
        except Exception:
            val = 0.0
        lbl = AreaLabelObject(
            parent_id=pid,
            value=val,
            x=cx,
            y=cy,
            axis_units=getattr(obj, "axis_units", "Hz"),
            visible=getattr(obj, "visible", True),
            locked=getattr(obj, "locked", False),
            semi=getattr(obj, "semi", False),
        )
        desired_labels_by_parent[pid] = [lbl]

    new_list: List[object] = []
    for obj in all_objs:
        if getattr(obj, "type", "") == "area_label":
            continue
        new_list.append(obj)
        if getattr(obj, "type", "") == "polygon":
            pid = getattr(obj, "id", None)
            if pid and pid in desired_labels_by_parent:
                new_list.extend(desired_labels_by_parent[pid])
    return new_list


# -----------------------------------------------------------------------------
# 잠금 (그리기: 부모→자식 동기화, 자식 인덱스 조회)
# -----------------------------------------------------------------------------
def get_children_indices(
    draw_objects: List[Any],
    parent_index: int,
    type_attr: str = "type",
    parent_id_attr: str = "parent_id",
    id_attr: str = "id",
) -> List[int]:
    """부모(보통 polygon)의 id와 같은 parent_id를 가진 자식(area_label 등)의 인덱스 목록 반환."""
    if parent_index < 0 or parent_index >= len(draw_objects):
        return []
    parent = draw_objects[parent_index]
    pid = getattr(parent, id_attr, None)
    if pid is None:
        return []
    return [
        i
        for i, obj in enumerate(draw_objects)
        if getattr(obj, parent_id_attr, None) == pid
    ]


def sync_parent_lock_to_children(
    draw_objects: List[Any],
    parent_index: int,
    checked: bool,
    locked_attr: str = "locked",
    type_attr: str = "type",
    parent_id_attr: str = "parent_id",
    id_attr: str = "id",
) -> None:
    """부모의 잠금 상태를 자식 객체들의 locked 속성에 반영. draw_objects를 in-place 수정."""
    children = get_children_indices(
        draw_objects, parent_index, type_attr, parent_id_attr, id_attr
    )
    for i in children:
        if 0 <= i < len(draw_objects):
            setattr(draw_objects[i], locked_attr, checked)
