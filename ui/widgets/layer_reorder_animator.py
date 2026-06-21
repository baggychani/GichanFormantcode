"""레이어 행 위치 애니메이션 유틸."""

from __future__ import annotations

from typing import Iterable, Mapping

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer


def capture_visible_row_positions(
    rows_by_key: Mapping[object, object],
) -> dict[object, object]:
    """현재 보이는 행 위치를 key -> QPoint 형태로 저장."""
    positions = {}
    for key, row in rows_by_key.items():
        if row.isVisible():
            positions[key] = row.pos()
    return positions


def capture_visible_attr_positions(
    rows: Iterable[object], attr_name: str
) -> dict[object, object]:
    """행 객체의 속성값을 key로 사용해 현재 보이는 행 위치를 저장."""
    positions = {}
    for row in rows:
        key = getattr(row, attr_name, None)
        if key is not None and row.isVisible():
            positions[key] = row.pos()
    return positions


def row_pairs_for_order(
    rows_by_key: Mapping[object, object], ordered_keys
) -> list[tuple[object, object]]:
    """표시 순서 기준으로 애니메이션 대상 행 목록을 만든다."""
    row_pairs = []
    for key in ordered_keys:
        row = rows_by_key.get(key)
        if row is not None:
            row_pairs.append((row, key))
    return row_pairs


def row_pairs_for_attr(
    rows: Iterable[object], attr_name: str
) -> list[tuple[object, object]]:
    """행 객체의 속성값을 key로 사용해 애니메이션 대상 목록을 만든다."""
    row_pairs = []
    for row in rows:
        key = getattr(row, attr_name, None)
        if key is not None:
            row_pairs.append((row, key))
    return row_pairs


def animate_row_positions(
    *,
    owner,
    row_pairs: Iterable[tuple[object, object]],
    old_pos_map: dict[object, object],
    duration_ms: int = 300,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> None:
    """행들의 기존 위치 -> 새 위치 애니메이션."""
    if not hasattr(owner, "_active_animations"):
        owner._active_animations = []

    for row, key in row_pairs:
        if key not in old_pos_map:
            continue
        old_pos = old_pos_map[key]
        new_pos = row.pos()
        if old_pos == new_pos:
            continue
        anim = QPropertyAnimation(row, b"pos", owner)
        anim.setDuration(duration_ms)
        anim.setStartValue(old_pos)
        anim.setEndValue(new_pos)
        anim.setEasingCurve(easing)
        anim.start()
        owner._active_animations.append(anim)

    # finished 콜백이 한꺼번에 몰릴 때의 끊김을 피하기 위해 지연 정리
    if owner._active_animations:
        QTimer.singleShot(duration_ms + 80, lambda: _cleanup_finished(owner))


def _cleanup_finished(owner) -> None:
    active = getattr(owner, "_active_animations", [])
    kept = []
    for anim in active:
        try:
            if anim.state() != QPropertyAnimation.State.Stopped:
                kept.append(anim)
        except RuntimeError:
            continue
    owner._active_animations = kept
