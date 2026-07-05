"""플롯 창 공통: 좌표축 범위 입력 + Hz/Bark 변환기."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import config
from ui.widgets.design_panel import NoWheelComboBox, apply_combo_center_align
from ui.widgets.icon_widgets import BidirectionalArrowButton
from ui.widgets.plot_event_filters import RangeInputFilter
from ui.widgets.style_tokens import (
    PLOT_RANGE_APPLY_BUTTON_STYLE,
    PLOT_RANGE_RESET_BUTTON_STYLE,
)
from utils.math_utils import bark_to_hz, hz_to_bark

_CLEAN_LINE_EDIT_STYLE = """
    QLineEdit { border: 1px solid #DCDFE6; border-radius: 3px; background-color: transparent; padding: 2px; font-size: 12px;}
    QLineEdit:focus { border: 1px solid #409EFF; }
"""
_AXIS_LABEL_WIDTH = 58


class AxisRangePanel(QWidget):
    """좌표축 범위 설정 패널 (popup/compare 공통)."""

    apply_clicked = Signal()
    reset_clicked = Signal()

    def __init__(
        self,
        parent=None,
        *,
        x_axis_label: str = "F2",
        font_normal: QFont | None = None,
        font_bold: QFont | None = None,
        focus_policy: Qt.FocusPolicy = Qt.FocusPolicy.StrongFocus,
    ):
        super().__init__(parent)
        font_normal = font_normal or QFont()
        font_bold = font_bold or QFont()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        range_header = QWidget()
        range_header.setCursor(Qt.CursorShape.PointingHandCursor)
        range_header_layout = QHBoxLayout(range_header)
        range_header_layout.setContentsMargins(0, 0, 0, 0)
        title_lbl = QLabel("좌표축 범위 설정", font=font_bold)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._range_toggle_btn = QPushButton("▶")
        self._range_toggle_btn.setFixedSize(22, 22)
        self._range_toggle_btn.setFlat(True)
        self._range_toggle_btn.setStyleSheet(
            "background: transparent; border: none; font-size: 11px;"
        )
        self._range_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._range_toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        range_header_layout.addWidget(title_lbl)
        range_header_layout.addWidget(self._range_toggle_btn)
        root.addWidget(range_header)

        self._converter_container = QWidget()
        converter_layout = QVBoxLayout(self._converter_container)
        converter_layout.setContentsMargins(0, 0, 0, 0)
        line_conv = QFrame()
        line_conv.setFrameShape(QFrame.Shape.HLine)
        line_conv.setStyleSheet("color: #E4E7ED;")
        converter_layout.addWidget(line_conv)
        conv_row = QHBoxLayout()
        conv_row.setSpacing(6)
        self._hz_edit = QLineEdit()
        self._bark_edit = QLineEdit()
        for le in (self._hz_edit, self._bark_edit):
            le.setFixedWidth(52)
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            le.setStyleSheet(_CLEAN_LINE_EDIT_STYLE)
            le.setFocusPolicy(focus_policy)
            le.setPlaceholderText("—")
        self._conv_btn = BidirectionalArrowButton(self)
        self._last_conv_focus = "hz"

        def _hz_focus_in(event):
            self._last_conv_focus = "hz"
            QLineEdit.focusInEvent(self._hz_edit, event)

        def _bark_focus_in(event):
            self._last_conv_focus = "bark"
            QLineEdit.focusInEvent(self._bark_edit, event)

        self._hz_edit.focusInEvent = _hz_focus_in
        self._bark_edit.focusInEvent = _bark_focus_in
        conv_row.addStretch()
        conv_row.addWidget(QLabel("Hz", font=font_normal))
        conv_row.addWidget(self._hz_edit)
        conv_row.addWidget(self._conv_btn)
        conv_row.addWidget(self._bark_edit)
        conv_row.addWidget(QLabel("Bark", font=font_normal))
        conv_row.addStretch()
        converter_layout.addLayout(conv_row)
        self._converter_container.setVisible(False)

        def _toggle_converter():
            vis = self._converter_container.isVisible()
            self._converter_container.setVisible(not vis)
            self._range_toggle_btn.setText("▼" if not vis else "▶")

        def _on_conv_clicked():
            try:
                hz_text = self._hz_edit.text().strip()
                bark_text = self._bark_edit.text().strip()
                if self._last_conv_focus == "bark" and bark_text:
                    val = float(bark_text)
                    self._hz_edit.setText(f"{float(bark_to_hz(val)):.1f}")
                elif hz_text:
                    val = float(hz_text)
                    self._bark_edit.setText(f"{float(hz_to_bark(val)):.2f}")
                elif bark_text:
                    val = float(bark_text)
                    self._hz_edit.setText(f"{float(bark_to_hz(val)):.1f}")
            except ValueError:
                pass

        self._range_toggle_btn.clicked.connect(_toggle_converter)
        self._conv_btn.clicked.connect(_on_conv_clicked)

        def _header_clicked(event):
            if event.button() == Qt.MouseButton.LeftButton:
                _toggle_converter()

        range_header.mousePressEvent = _header_clicked

        self.range_widgets: dict[str, QLineEdit] = {}
        self.lbl_f1_axis = QLabel("F1:", font=font_normal)
        self.lbl_f1_axis.setFixedWidth(_AXIS_LABEL_WIDTH)
        self.range_widgets["y_min"] = QLineEdit()
        self.range_widgets["y_max"] = QLineEdit()
        f1_row = QHBoxLayout()
        for le in (self.range_widgets["y_min"], self.range_widgets["y_max"]):
            le.setFixedWidth(48)
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            le.setStyleSheet(_CLEAN_LINE_EDIT_STYLE)
            le.setFocusPolicy(focus_policy)
        f1_row.addWidget(self.lbl_f1_axis)
        f1_row.addWidget(self.range_widgets["y_min"])
        f1_row.addWidget(QLabel("~", font=font_normal))
        f1_row.addWidget(self.range_widgets["y_max"])
        f1_row.addSpacing(8)
        self.lbl_f1_unit = QLabel("(Hz)", font=font_normal)
        f1_row.addWidget(self.lbl_f1_unit)
        f1_row.addStretch()
        root.addLayout(f1_row)

        self.x_axis_label = x_axis_label
        self.lbl_x_axis = QLabel(f"{x_axis_label}:", font=font_normal)
        self.lbl_x_axis.setFixedWidth(_AXIS_LABEL_WIDTH)
        self.range_widgets["x_min"] = QLineEdit()
        self.range_widgets["x_max"] = QLineEdit()
        f2_row = QHBoxLayout()
        for le in (self.range_widgets["x_min"], self.range_widgets["x_max"]):
            le.setFixedWidth(48)
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            le.setStyleSheet(_CLEAN_LINE_EDIT_STYLE)
            le.setFocusPolicy(focus_policy)
        f2_row.addWidget(self.lbl_x_axis)
        f2_row.addWidget(self.range_widgets["x_min"])
        f2_row.addWidget(QLabel("~", font=font_normal))
        f2_row.addWidget(self.range_widgets["x_max"])
        f2_row.addSpacing(8)
        self.lbl_f2_unit = QLabel("(Hz)", font=font_normal)
        f2_row.addWidget(self.lbl_f2_unit)
        f2_row.addStretch()
        root.addLayout(f2_row)

        self.range_tab_order = [
            self.range_widgets["y_min"],
            self.range_widgets["y_max"],
            self.range_widgets["x_min"],
            self.range_widgets["x_max"],
        ]

        sig_h = QHBoxLayout()
        sig_h.addWidget(QLabel("신뢰 타원:", font=font_normal))
        self.cb_sigma = NoWheelComboBox()
        self.cb_sigma.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.cb_sigma.addItems(config.SIGMA_VALS)
        self.cb_sigma.setCurrentText(
            config.SIGMA_VALS[-1] if config.SIGMA_VALS else "2.0"
        )
        apply_combo_center_align(self.cb_sigma)
        sig_h.addWidget(self.cb_sigma)
        sig_h.addWidget(QLabel("σ", font=font_normal))
        sig_h.addStretch()
        root.addLayout(sig_h)

        apply_h = QHBoxLayout()
        btn_reset = QPushButton("초기화")
        btn_apply = QPushButton("적용")
        for btn in (btn_reset, btn_apply):
            btn.setFixedHeight(28)
            btn.setFont(font_normal)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setAutoDefault(False)
            btn.setDefault(False)
        btn_apply.setStyleSheet(PLOT_RANGE_APPLY_BUTTON_STYLE)
        btn_reset.setStyleSheet(PLOT_RANGE_RESET_BUTTON_STYLE)
        btn_apply.clicked.connect(self.apply_clicked.emit)
        btn_reset.clicked.connect(self.reset_clicked.emit)
        apply_h.addWidget(btn_reset)
        apply_h.addWidget(btn_apply)
        root.addLayout(apply_h)
        root.addWidget(self._converter_container)

    def range_edits(self) -> list[QLineEdit]:
        return [
            self.range_widgets["y_min"],
            self.range_widgets["y_max"],
            self.range_widgets["x_min"],
            self.range_widgets["x_max"],
            self._hz_edit,
            self._bark_edit,
        ]

    def install_input_filter(self, owner_window) -> RangeInputFilter:
        owner_window._range_tab_order = self.range_tab_order
        filt = RangeInputFilter(owner_window)
        for le in self.range_edits():
            le.installEventFilter(filt)
        return filt

    def analysis_edits(self) -> set[QLineEdit]:
        return set(self.range_widgets.values()) | {self._hz_edit, self._bark_edit}
