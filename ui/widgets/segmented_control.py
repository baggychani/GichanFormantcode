"""세그먼트 버튼·선 타입 선택 바 레이아웃 헬퍼 (애니메이션 없음)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QEasingCurve
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from ui.widgets.icon_widgets import LinePreviewButton

# ToggleSwitch 전용
SLIDE_ANIM_MS = 260
_SLIDE_EASING = QEasingCurve(QEasingCurve.Type.OutQuart)


def wrap_segmented_buttons(
    buttons: list[QAbstractButton],
    parent: QWidget | None = None,
) -> QFrame:
    """가로 폭을 채우는 세그먼트형 버튼 줄."""
    frame = QFrame(parent)
    frame.setStyleSheet(
        "QFrame { background-color: #F5F7FA; border: 1px solid #EBEEF5; border-radius: 4px; }"
    )
    row = QHBoxLayout(frame)
    row.setContentsMargins(3, 3, 3, 3)
    row.setSpacing(3)
    for btn in buttons:
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row.addWidget(btn, 1)
    return frame


def create_line_preview_button_group(
    parent: QWidget,
    options: list,
    default_idx: int = 0,
) -> tuple[QFrame, QButtonGroup]:
    """타원 선 두께·스타일 등 LinePreviewButton 세그먼트 바."""
    group = QButtonGroup(parent)
    frame = QFrame()
    frame.setStyleSheet(
        "QFrame { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; }"
    )
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(2, 2, 2, 2)
    layout.setSpacing(0)

    for i, opt in enumerate(options):
        w, s, r, tooltip = opt[:4]
        dash = opt[4] if len(opt) > 4 else None
        btn = LinePreviewButton(
            line_width=w,
            line_style=s,
            radius_css=r,
            tooltip=tooltip,
            dash_pattern=dash,
        )
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        group.addButton(btn, i)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(btn, 1)

    if group.button(default_idx) is not None:
        group.button(default_idx).setChecked(True)
    return frame, group


def create_labeled_segmented_switch(
    left_label: str,
    right_label: str,
    *,
    default_index: int = 0,
    parent: QWidget | None = None,
) -> tuple[QFrame, QButtonGroup]:
    """두 옵션(Hz/Bark 등) 라벨이 붙은 세그먼트 토글."""
    frame = QFrame(parent)
    frame.setObjectName("labeledSegmentedSwitch")
    frame.setStyleSheet(
        """
        QFrame#labeledSegmentedSwitch {
            background-color: #F5F7FA;
            border: 1px solid #DCDFE6;
            border-radius: 6px;
        }
        QFrame#labeledSegmentedSwitch QPushButton {
            background: transparent;
            border: none;
            color: #909399;
            padding: 4px 14px;
            border-radius: 4px;
            font-size: 12px;
            min-width: 36px;
        }
        QFrame#labeledSegmentedSwitch QPushButton:hover:!checked {
            color: #606266;
            background-color: #EBEEF5;
        }
        QFrame#labeledSegmentedSwitch QPushButton:checked {
            background-color: white;
            color: #409EFF;
            font-weight: bold;
        }
        """
    )
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(2, 2, 2, 2)
    layout.setSpacing(2)

    group = QButtonGroup(frame)
    group.setExclusive(True)

    for i, label in enumerate((left_label, right_label)):
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setFixedHeight(28)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        group.addButton(btn, i)
        layout.addWidget(btn)

    if group.button(default_index) is not None:
        group.button(default_index).setChecked(True)
    return frame, group
