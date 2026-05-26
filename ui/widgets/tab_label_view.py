from __future__ import annotations

import os
import config

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.display_utils import (
    strip_gichan_prefix,
    truncate_display_name,
    MAX_LAYER_FILE_BTN_LEN,
)
from ui.widgets.layer_row_widgets import _LayerListDropArea


def create_label_tab(dock) -> QWidget:
    """layer_dock에서 라벨 탭 영역만 물리 분리해 생성."""
    layer_tab = QWidget()
    data_layout = QVBoxLayout(layer_tab)
    data_layout.setContentsMargins(0, 0, 0, 0)

    tab_underline = QFrame()
    tab_underline.setFrameShape(QFrame.Shape.HLine)
    tab_underline.setFixedHeight(1)
    tab_underline.setStyleSheet("background-color: #E4E7ED; margin: 0; border: none;")
    data_layout.addWidget(tab_underline)
    data_layout.setSpacing(0)

    dock._compare_file_switch_row = None
    dock._compare_file_btn_a = None
    dock._compare_file_btn_b = None
    dock._compare_file_group = None
    if dock._compare_mode:

        def _btn_label(raw: str, display: str | None) -> str:
            if display:
                return truncate_display_name(display, MAX_LAYER_FILE_BTN_LEN)
            base = os.path.splitext(raw)[0]
            return truncate_display_name(
                strip_gichan_prefix(base), MAX_LAYER_FILE_BTN_LEN
            )

        btn_label_a = _btn_label(
            dock._file_a_name, getattr(dock, "_file_a_label", None)
        )
        btn_label_b = _btn_label(
            dock._file_b_name, getattr(dock, "_file_b_label", None)
        )
        tip_a = (
            getattr(dock, "_file_a_tooltip", "")
            or os.path.splitext(strip_gichan_prefix(dock._file_a_name))[0]
        )
        tip_b = (
            getattr(dock, "_file_b_tooltip", "")
            or os.path.splitext(strip_gichan_prefix(dock._file_b_name))[0]
        )
        dock._compare_file_switch_row = QFrame()
        dock._compare_file_switch_row.setFixedHeight(32)
        dock._compare_file_switch_row.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        dock._compare_file_switch_row.setStyleSheet(
            "background-color: #F5F7FA; border-bottom: 1px solid #EBEEF5;"
        )
        switch_layout = QHBoxLayout(dock._compare_file_switch_row)
        switch_layout.setContentsMargins(0, 0, 0, 0)
        switch_layout.setSpacing(0)
        dock._compare_file_btn_a = QPushButton(btn_label_a)
        dock._compare_file_btn_b = QPushButton(btn_label_b)
        dock._compare_file_btn_a.setToolTip(tip_a)
        dock._compare_file_btn_b.setToolTip(tip_b)
        dock._compare_file_btn_a.setCheckable(True)
        dock._compare_file_btn_b.setCheckable(True)
        dock._compare_file_group = QButtonGroup(dock)
        dock._compare_file_group.addButton(dock._compare_file_btn_a, 0)
        dock._compare_file_group.addButton(dock._compare_file_btn_b, 1)
        dock._compare_file_btn_a.setChecked(True)
        for btn in (dock._compare_file_btn_a, dock._compare_file_btn_b):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setFixedHeight(32)
            btn.setMaximumHeight(32)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; color: {config.COLOR_TEXT_SECONDARY}; font-size: 11px; padding: 0 4px; }}"
                f"QPushButton:checked {{ background: {config.COLOR_ACTION_HOVER_BG}; color: {config.COLOR_ACTION_BLUE}; }}"
                f"QPushButton:hover:!checked {{ background: {config.COLOR_TAB_HOVER}; }}"
            )
        switch_layout.addWidget(dock._compare_file_btn_a, 1)
        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.Shape.VLine)
        sep_v.setFixedWidth(1)
        sep_v.setStyleSheet("background-color: #E4E7ED; margin: 0; border: none;")
        switch_layout.addWidget(sep_v)
        switch_layout.addWidget(dock._compare_file_btn_b, 1)
        dock._compare_file_group.buttonClicked.connect(
            lambda b: dock.compare_switch_requested.emit(dock._compare_file_group.id(b))
        )
        data_layout.addWidget(dock._compare_file_switch_row)

    dock.layer_scroll = QScrollArea()
    dock.layer_scroll.setWidgetResizable(True)
    dock.layer_scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    dock.layer_scroll.setStyleSheet(
        "QScrollArea { border: none; background: #FFFFFF; }"
    )

    dock._layer_list_widget = _LayerListDropArea(dock)
    dock._layer_list_layout = QVBoxLayout(dock._layer_list_widget)
    dock._layer_list_layout.setContentsMargins(0, 0, 0, 0)
    dock._layer_list_layout.setSpacing(0)
    dock._layer_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    dock.layer_scroll.setWidget(dock._layer_list_widget)
    dock._global_row = None
    dock._drop_target = None
    data_layout.addWidget(dock.layer_scroll)
    return layer_tab
