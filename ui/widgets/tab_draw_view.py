from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from ui.widgets.layer_row_widgets import _DrawListDropArea


def create_draw_tab(dock) -> QWidget:
    """layer_dock에서 그리기 탭 영역만 물리 분리해 생성."""
    draw_tab = QWidget()
    draw_tab_layout = QVBoxLayout(draw_tab)
    draw_tab_layout.setContentsMargins(0, 0, 0, 0)
    draw_tab_layout.setSpacing(0)

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
