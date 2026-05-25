from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.layer_row_widgets import _DrawListDropArea


def create_draw_tab(dock) -> QWidget:
    """layer_dock에서 그리기 탭 영역만 물리 분리해 생성."""
    draw_tab = QWidget()
    draw_tab_layout = QVBoxLayout(draw_tab)
    draw_tab_layout.setContentsMargins(0, 0, 0, 0)
    draw_tab_layout.setSpacing(0)

    add_row = QFrame()
    add_row.setStyleSheet(
        "background-color: #F5F7FA; border-bottom: 1px solid #EBEEF5;"
    )
    add_layout = QHBoxLayout(add_row)
    add_layout.setContentsMargins(8, 6, 8, 6)
    dock.btn_add_legend = QPushButton("범례 추가")
    dock.btn_add_legend.setCursor(Qt.CursorShape.PointingHandCursor)
    dock.btn_add_legend.setFont(
        QFont(getattr(dock, "ui_font_name", "Malgun Gothic"), 9)
    )
    dock.btn_add_legend.setStyleSheet(
        "QPushButton { background-color: #FFFFFF; border: 1px solid #DCDFE6; "
        "border-radius: 4px; color: #303133; padding: 4px 10px; }"
        "QPushButton:hover { border-color: #409EFF; color: #409EFF; }"
        "QPushButton:disabled { color: #C0C4CC; border-color: #EBEEF5; }"
    )
    dock.btn_add_legend.clicked.connect(dock._on_add_legend_clicked)
    add_layout.addWidget(dock.btn_add_legend)
    add_layout.addStretch()
    draw_tab_layout.addWidget(add_row)
    dock._legend_add_row = add_row

    draw_tab_underline = QFrame()
    draw_tab_underline.setFrameShape(QFrame.Shape.HLine)
    draw_tab_underline.setFixedHeight(1)
    draw_tab_underline.setStyleSheet(
        "background-color: #E4E7ED; margin: 0; border: none;"
    )
    draw_tab_layout.addWidget(draw_tab_underline)

    dock._draw_layer_scroll = QScrollArea()
    dock._draw_layer_scroll.setWidgetResizable(True)
    dock._draw_layer_scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    dock._draw_layer_scroll.setStyleSheet(
        "QScrollArea { border: none; background: #FFFFFF; }"
    )
    dock._draw_list_placeholder = _DrawListDropArea(dock)
    dock._draw_list_placeholder.setStyleSheet("background: #FFFFFF;")
    dock._draw_list_placeholder.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    dock._draw_drop_target = None
    dock._draw_layer_rows = []
    dock._selected_draw_indices = set()
    dock._draw_list_layout = QVBoxLayout(dock._draw_list_placeholder)
    dock._draw_list_layout.setContentsMargins(0, 0, 0, 0)
    dock._draw_list_layout.setSpacing(0)
    dock._draw_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    draw_tab_layout.addWidget(dock._draw_layer_scroll, 1)
    dock._draw_layer_scroll.setWidget(dock._draw_list_placeholder)
    dock._draw_list_placeholder.installEventFilter(dock)
    draw_tab.installEventFilter(dock)
    return draw_tab
