"""Compare combined 그룹에 포함된 파일 목록을 보여 주는 간단한 다이얼로그."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.display_utils import strip_gichan_prefix


def add_compare_legend_name_widgets(
    layout,
    *,
    display_name: str,
    tooltip: str,
    member_names: list[str] | None,
    font,
    dialog_parent,
    ui_font_name: str = "Malgun Gothic",
):
    from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy

    lbl_text = QLabel(display_name)
    lbl_text.setFont(font)
    lbl_text.setStyleSheet("color: #333333;")
    lbl_text.setToolTip(tooltip)
    lbl_text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    lbl_text.setMinimumWidth(0)
    layout.addWidget(lbl_text, stretch=1)
    if member_names:
        btn_detail = QPushButton("전체")
        btn_detail.setFlat(True)
        btn_detail.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_detail.setFont(QFont(ui_font_name, 9))
        btn_detail.setStyleSheet(
            "QPushButton { color: #909399; border: none; padding: 0 4px; }"
            "QPushButton:hover { color: #409EFF; }"
        )
        btn_detail.setFixedHeight(20)
        btn_detail.clicked.connect(
            lambda _checked=False, names=member_names, label=display_name: (
                show_combined_members_dialog(
                    dialog_parent,
                    group_label=label,
                    member_names=names,
                    ui_font_name=ui_font_name,
                )
            )
        )
        layout.addWidget(btn_detail)
    return lbl_text


def show_combined_members_dialog(
    parent,
    *,
    group_label: str,
    member_names: list[str],
    ui_font_name: str = "Malgun Gothic",
) -> None:
    """그룹 구성(포함 파일) 전체 목록."""
    cleaned = [os.path.splitext(strip_gichan_prefix(n))[0] for n in member_names if n]
    if not cleaned:
        return

    dlg = QDialog(parent)
    dlg.setWindowTitle("그룹 구성")
    dlg.setWindowModality(Qt.WindowModality.WindowModal)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(16, 14, 16, 12)
    root.setSpacing(10)

    title = QLabel(group_label)
    title.setFont(QFont(ui_font_name, 10, QFont.Weight.Bold))
    title.setWordWrap(True)
    root.addWidget(title)

    subtitle = QLabel(f"포함 {len(cleaned)}명")
    subtitle.setFont(QFont(ui_font_name, 9))
    subtitle.setStyleSheet("color: #909399;")
    root.addWidget(subtitle)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    body = QWidget()
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(0, 0, 4, 0)
    body_layout.setSpacing(6)
    for name in cleaned:
        row = QLabel(f"· {name}")
        row.setFont(QFont(ui_font_name, 10))
        row.setWordWrap(True)
        body_layout.addWidget(row)
    body_layout.addStretch()
    scroll.setWidget(body)
    root.addWidget(scroll, stretch=1)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    buttons.accepted.connect(dlg.accept)
    root.addWidget(buttons)

    dlg.setMinimumWidth(280)
    dlg.setMaximumWidth(420)
    dlg.setMaximumHeight(min(420, 120 + len(cleaned) * 28))
    dlg.exec()
