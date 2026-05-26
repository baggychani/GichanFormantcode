# ui_design_panel.py

import os
import config
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QScrollArea,
    QFrame,
    QColorDialog,
    QButtonGroup,
    QSizePolicy,
    QTabWidget,
    QGridLayout,
)
from PySide6.QtCore import Qt, Signal, QRect, QRectF, Property, QPropertyAnimation
from PySide6.QtGui import (
    QFont,
    QColor,
    QCursor,
    QPainter,
    QPainterPath,
    QPixmap,
)

from ui.widgets.icon_widgets import (
    create_font_style_icon,
    create_raw_marker_icon,
    create_legend_icon_design,
    MarkerShapeButton,
    ColorCircleButton,
    ShortcutButton,
)
from ui.widgets.display_utils import (
    truncate_display_name,
    MAX_DISPLAY_NAME_LEN,
    strip_gichan_prefix,
)
from ui.dialogs.combined_members_dialog import add_compare_legend_name_widgets
import ui.widgets.layout_constants as lc
from ui.widgets.collapsible_section import CollapsibleSection, AdvancedOptionsBlock
from ui.widgets.opacity_slider import DEFAULT_ELL_FILL_OPACITY, OpacitySliderRow, opacity_to_slider
from core.compare_settings import pack_compare_design_settings
from ui.widgets.segmented_control import (
    wrap_segmented_buttons,
    create_line_preview_button_group,
    SLIDE_ANIM_MS,
    _SLIDE_EASING,
)


def _field_caption(text: str, font: QFont) -> QLabel:
    """폼 필드 캡션(콜론 없음, 위·아래 스택 레이아웃용)."""
    lbl = QLabel(text, font=font)
    lbl.setStyleSheet("color: #606266;")
    return lbl


def _field_group(caption: str, font: QFont) -> QVBoxLayout:
    """필드 캡션 + 컨트롤 묶음. 캡션-컨트롤·그룹 간 간격은 레이아웃 상수로 통일."""
    group = QVBoxLayout()
    group.setContentsMargins(0, 0, 0, 0)
    group.setSpacing(lc.SPACING_CAPTION_TO_CONTROL_PX)
    group.addWidget(_field_caption(caption, font))
    return group


def _ell_fill_has_color(color) -> bool:
    return color not in (None, "transparent", "") and str(color).lower() != "transparent"


def _wrap_marker_shape_bar(buttons, parent=None, *, columns: int = 4) -> QFrame:
    """모음 중심점 마커(고정 28px)를 4×2 그리드로 배치. 배경색 단일 톤(#F5F7FA)."""
    frame = QFrame(parent)
    frame.setStyleSheet(
        "QFrame#marker_shape_bar { background-color: #F5F7FA; border: 1px solid #EBEEF5; border-radius: 4px; }"
        "QFrame#marker_shape_bar QPushButton { background-color: transparent; }"
    )
    frame.setObjectName("marker_shape_bar")
    grid = QGridLayout(frame)
    grid.setContentsMargins(3, 3, 3, 3)
    grid.setSpacing(2)
    for i, btn in enumerate(buttons):
        btn.setFixedSize(28, 28)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        grid.addWidget(btn, i // columns, i % columns, Qt.AlignmentFlag.AlignCenter)
    return frame


class NoWheelComboBox(QComboBox):
    """마우스 휠로 값이 바뀌지 않도록 휠 이벤트를 무시하는 콤보박스."""

    def wheelEvent(self, event):
        event.ignore()


def apply_combo_center_align(combo: QComboBox) -> None:
    """콤보박스 표시 텍스트를 가운데 정렬 (읽기 전용 lineEdit 사용)."""
    combo.setEditable(True)
    editor = combo.lineEdit()
    if editor is None:
        return
    editor.setReadOnly(True)
    editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
    editor.setFrame(False)


class ToggleSwitch(QWidget):
    """
    체크박스 대신 사용할 커스텀 ON/OFF 토글 스위치 위젯
    """

    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self._checked = checked
        self._handle_x = float(self._target_handle_x())
        self._handle_anim = QPropertyAnimation(self, b"handle_x", self)
        self._handle_anim.setDuration(SLIDE_ANIM_MS)
        self._handle_anim.setEasingCurve(_SLIDE_EASING)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _target_handle_x(self) -> float:
        return float(self.width() - 20 if self._checked else 2)

    def get_handle_x(self) -> float:
        return self._handle_x

    def set_handle_x(self, value: float) -> None:
        old = int(self._handle_x)
        new = int(value)
        if old == new and abs(self._handle_x - value) < 0.01:
            return
        self._handle_x = value
        # 핸들 영역만 갱신 (전체 위젯 리페인트 방지)
        self.update(QRect(min(old, new), 0, abs(new - old) + 20, self.height()))

    handle_x = Property(float, get_handle_x, set_handle_x)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked, *, animate: bool = True):
        if self._checked == checked:
            return
        self._checked = checked
        target = self._target_handle_x()
        if animate and self.isVisible():
            self.update()  # 배경색 전환은 한 번만 전체 갱신
            if self._handle_anim.state() == QPropertyAnimation.State.Running:
                self._handle_anim.stop()
            self._handle_anim.setStartValue(self._handle_x)
            self._handle_anim.setEndValue(target)
            self._handle_anim.start()
        else:
            if self._handle_anim.state() == QPropertyAnimation.State.Running:
                self._handle_anim.stop()
            self.set_handle_x(target)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            self.toggled.emit(self._checked)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._handle_anim.state() == QPropertyAnimation.State.Running:
            self._handle_anim.stop()
        self.set_handle_x(self._target_handle_x())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_color = QColor("#67C23A") if self._checked else QColor("#DCDFE6")
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 11, 11)
        painter.fillPath(path, bg_color)

        handle_color = QColor("#FFFFFF")
        painter.setBrush(handle_color)
        painter.setPen(Qt.PenStyle.NoPen)

        painter.drawEllipse(int(self._handle_x), 2, 18, 18)
        painter.end()


class ColorPalette(QWidget):
    """
    디자인 설정용 색상 선택 컴포넌트
    """

    color_changed = Signal(str)

    def __init__(self, default_color="#000000", allow_transparent=False, parent=None):
        super().__init__(parent)
        self.current_color = default_color
        self.allow_transparent = allow_transparent

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(4)

        self.color_names = {
            "#E64A19": "Red",
            "#F57C00": "Orange",
            "#FFEB3B": "Yellow",
            "#388E3C": "Green",
            "#00BCD4": "Cyan",
            "#1976D2": "Blue",
            "#7B1FA2": "Purple",
            "#E91E63": "Pink",
            "#606060": "Dark Gray",
            "#000000": "Black",
            "#AAAAAA": "Light Gray",
            "#795548": "Brown",
            "#009688": "Teal",
            "#FF9800": "Amber",
            "transparent": "Transparent",
            "custom": "Custom Color",
        }

        palette_row = QHBoxLayout()
        palette_row.setSpacing(4)
        btn_list = []

        preset_colors = [
            "#E64A19",
            "#F57C00",
            "#FFEB3B",
            "#388E3C",
            "#00BCD4",
            "#1976D2",
            "#7B1FA2",
            "#E91E63",
            "#606060",
            "#000000",
            "#AAAAAA",
            "#795548",
            "#009688",
            "#FF9800",
        ]
        # [기본색] + [투명(옵션)] + [프리셋]
        # - 기본색이 transparent이고 allow_transparent=True면 transparent를 맨 앞에 둔다.
        transparent_first = (
            self.allow_transparent and self.current_color == "transparent"
        )
        if self.current_color and self.current_color not in ("transparent", "custom"):
            if self.current_color in preset_colors:
                preset_colors = [c for c in preset_colors if c != self.current_color]
            preset_colors = [self.current_color] + preset_colors
        for i, c in enumerate(preset_colors):
            c_name = self.color_names.get(c, "Color")
            btn = ColorCircleButton(c, tooltip=f"{c_name} ({c})", palette_swatch=True)
            btn.clicked.connect(lambda checked, col=c: self.set_color(col))
            if i == 0 and transparent_first:
                btn_none = ColorCircleButton(
                    "transparent",
                    is_transparent=True,
                    tooltip="Transparent",
                    palette_swatch=True,
                )
                btn_none.clicked.connect(lambda: self.set_color("transparent"))
                btn_list.append(btn_none)
            btn_list.append(btn)
            if i == 0 and self.allow_transparent and not transparent_first:
                btn_none = ColorCircleButton(
                    "transparent",
                    is_transparent=True,
                    tooltip="Transparent",
                    palette_swatch=True,
                )
                btn_none.clicked.connect(lambda: self.set_color("transparent"))
                btn_list.append(btn_none)

        self.btn_custom = ColorCircleButton(
            "custom", tooltip="Custom Color", palette_swatch=True
        )
        self.btn_custom.clicked.connect(self.open_color_dialog)
        btn_list.append(self.btn_custom)

        grid = QGridLayout()
        grid.setSpacing(4)
        cols = 8
        for i, btn in enumerate(btn_list):
            grid.addWidget(btn, i // cols, i % cols)

        palette_row.addLayout(grid)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #DCDFE6; margin: 2px 4px;")
        palette_row.addWidget(sep)

        self.preview = ColorCircleButton(
            self.current_color,
            is_transparent=(self.current_color == "transparent"),
            tooltip=f"Current Color : {self._get_tooltip_string(self.current_color)}",
            preview=True,
        )
        self.preview.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        palette_row.addWidget(self.preview)
        self.main_layout.addLayout(palette_row)

    def _get_tooltip_string(self, color_hex):
        if color_hex == "transparent":
            return "Transparent"
        key = color_hex if color_hex in self.color_names else color_hex.upper()
        name = self.color_names.get(key, "Custom Color")
        if name == "Custom Color":
            return f"Custom ({color_hex})"
        return f"{name} ({color_hex})"

    def set_color(self, color):
        if self.current_color != color:
            self.current_color = color
            self.preview.set_color(color, is_transparent=(color == "transparent"))

            tooltip_str = self._get_tooltip_string(color)
            self.preview.setToolTip(f"Current Color : {tooltip_str}")

            self.color_changed.emit(self.current_color)

    def open_color_dialog(self):
        initial_color = (
            QColor(self.current_color)
            if self.current_color != "transparent"
            else QColor("#FFFFFF")
        )
        color = QColorDialog.getColor(initial_color, self, "색상 선택")
        if color.isValid():
            self.set_color(color.name())


class DesignSettingsPanel(QWidget):
    """
    단일 플롯 전용 디자인 설정 패널입니다.
    """

    settings_changed = Signal(dict)
    label_move_clicked = Signal()

    def __init__(self, parent=None, ui_font_name="Malgun Gothic", is_normalized=False):
        super().__init__(parent)
        self.ui_font_name = ui_font_name
        self._is_normalized = is_normalized
        self._is_loading = True

        self._setup_ui()
        self._connect_signals()

        self._is_loading = False

    def _create_toggle_row(self, label_text, default_checked=True):
        row = QHBoxLayout()
        lbl = QLabel(label_text, font=QFont(self.ui_font_name, 9))
        switch = ToggleSwitch(checked=default_checked)
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(switch)
        return row, switch

    def _create_visual_button_group(self, options, default_idx):
        return create_line_preview_button_group(self, options, default_idx)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; }")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("QWidget { background-color: white; }")
        scroll_content.setMaximumWidth(260)
        scroll_content.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(12, 12, 12, 15)
        layout.setSpacing(lc.SPACING_DOCK_SECTIONS_PX)

        font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        font_normal = QFont(self.ui_font_name, 9)

        # ==========================================
        # 1. 데이터 표시 (Data Display)
        # ==========================================
        sec_data = CollapsibleSection(
            "데이터 표시",
            font_bold,
            panel_id="design",
            settings_key="data_display",
            default_collapsed=False,
        )
        data_body = sec_data.body_layout()
        row1, self.sw_show_raw = self._create_toggle_row("데이터 포인트")
        row2, self.sw_show_centroid = self._create_toggle_row("모음 중심점(Centroid)")
        data_body.addLayout(row1)
        data_body.addLayout(row2)
        layout.addWidget(sec_data)
        self._add_separator(layout)

        # ==========================================
        # 스타일 (폰트 스타일)
        # ==========================================
        sec_style = CollapsibleSection(
            "스타일",
            font_bold,
            panel_id="design",
            settings_key="style",
            default_collapsed=False,
        )
        style_body = sec_style.body_layout()
        btn_style = """
            QPushButton { background-color: transparent; border: 1px solid transparent; border-radius: 4px; }
            QPushButton:hover { background-color: #F5F7FA; }
            QPushButton:checked { background-color: #E4E7ED; border: 1px solid #C0C4CC; }
        """
        font_style_block = _field_group("폰트 스타일", font_normal)
        self.group_font_style = QButtonGroup(self)
        btn_serif = QPushButton("")
        btn_serif.setCheckable(True)
        btn_serif.setChecked(True)
        btn_serif.setMinimumHeight(26)
        btn_serif.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_serif.setStyleSheet(btn_style)
        btn_serif.setIcon(create_font_style_icon(is_serif=True))
        btn_serif.setIconSize(QPixmap(34, 22).size())
        btn_serif.setToolTip("명조(세리프)")
        self.group_font_style.addButton(btn_serif, 0)
        btn_sans = QPushButton("")
        btn_sans.setCheckable(True)
        btn_sans.setMinimumHeight(26)
        btn_sans.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_sans.setStyleSheet(btn_style)
        btn_sans.setIcon(create_font_style_icon(is_serif=False))
        btn_sans.setIconSize(QPixmap(34, 22).size())
        btn_sans.setToolTip("고딕(산세리프)")
        self.group_font_style.addButton(btn_sans, 1)
        font_style_block.addWidget(wrap_segmented_buttons([btn_serif, btn_sans], self))
        style_body.addLayout(font_style_block)

        dp_shape_block = _field_group("데이터 포인트", font_normal)
        self.group_raw_marker = QButtonGroup(self)
        dp_btns = []
        for i, (key, tip) in enumerate(
            [("o", "빈 원"), ("x", "X 모양"), ("a", "라벨 문자(모음 기호)")]
        ):
            btn = QPushButton("")
            btn.setCheckable(True)
            btn.setProperty("val", key)
            btn.setMinimumHeight(26)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(btn_style)
            btn.setIcon(create_raw_marker_icon(key))
            btn.setIconSize(QPixmap(24, 24).size())
            btn.setToolTip(tip)
            if key == "o":
                btn.setChecked(True)
            self.group_raw_marker.addButton(btn, i)
            dp_btns.append(btn)
        dp_shape_block.addWidget(wrap_segmented_buttons(dp_btns, self))
        style_body.addLayout(dp_shape_block)
        raw_color_layout = _field_group("데이터 포인트 색상", font_normal)
        self.raw_color_picker = ColorPalette(
            default_color="#606060", allow_transparent=False, parent=self
        )
        raw_color_layout.addWidget(self.raw_color_picker)
        style_body.addLayout(raw_color_layout)
        layout.addWidget(sec_style)
        self._add_separator(layout)

        # ==========================================
        # 2. 라벨과 중심점
        # ==========================================
        sec_label = CollapsibleSection(
            "라벨과 중심점",
            font_bold,
            panel_id="design",
            settings_key="label_centroid",
            default_collapsed=False,
        )
        label_body = sec_label.body_layout()
        self.btn_label_move = ShortcutButton("assets/shortcuts/T.png", "라벨 위치 이동")
        self.btn_label_move.setObjectName("BtnLabelMove")
        self.btn_label_move.setCheckable(True)
        self.btn_label_move.setFixedHeight(32)
        self.btn_label_move.setFont(font_normal)
        self.btn_label_move.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_label_move.setStyleSheet("""
            QPushButton { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #333;}
            QPushButton:hover:!checked { background-color: #E4E7ED; border: 1px solid #C0C4CC; color: #409EFF; }
            QPushButton:checked { background-color: #E6A23C; color: white; font-weight: bold; border: none; }
        """)

        self.btn_label_move.clicked.connect(self.label_move_clicked.emit)
        label_body.addWidget(self.btn_label_move)

        color_layout = _field_group("라벨 텍스트 색상", font_normal)
        self.lbl_color_picker = ColorPalette(
            default_color=config.COLOR_PRIMARY_RED, allow_transparent=True, parent=self
        )
        color_layout.addWidget(self.lbl_color_picker)
        label_body.addLayout(color_layout)

        font_block = _field_group("폰트", font_normal)
        font_style_layout = QHBoxLayout()
        font_style_layout.setSpacing(6)

        self.combo_lbl_size = NoWheelComboBox()
        self.combo_lbl_size.setStyleSheet(
            "QComboBox { padding: 2px 4px; border: 1px solid #DCDFE6; border-radius: 3px; }"
        )
        self.combo_lbl_size.addItems(["14", "16", "18", "20", "22", "24"])
        self.combo_lbl_size.setCurrentText("20")
        self.combo_lbl_size.setFixedWidth(55)
        self.combo_lbl_size.setMaxVisibleItems(8)
        font_style_layout.addWidget(self.combo_lbl_size)
        font_style_layout.addWidget(QLabel("pt", font=font_normal))

        font_style_layout.addSpacing(10)

        toolbar_style = """
            QPushButton {
                background-color: transparent; border: 1px solid transparent; border-radius: 4px; color: #333333;
            }
            QPushButton:hover { background-color: #E4E7ED; }
            QPushButton:checked { background-color: #DCDFE6; border: 1px solid #C0C4CC; }
        """
        self.btn_bold = QPushButton("B")
        self.btn_bold.setCheckable(True)
        self.btn_bold.setChecked(True)
        self.btn_bold.setFixedSize(26, 26)
        self.btn_bold.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_bold.setStyleSheet(toolbar_style)
        self.btn_bold.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_bold.setToolTip("굵게 (Bold)")

        self.btn_italic = QPushButton("I")
        self.btn_italic.setCheckable(True)
        self.btn_italic.setFixedSize(26, 26)
        font_i = QFont("Times New Roman", 10)
        font_i.setItalic(True)
        self.btn_italic.setFont(font_i)
        self.btn_italic.setStyleSheet(toolbar_style)
        self.btn_italic.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_italic.setToolTip("기울임 (Italic)")

        font_style_layout.addWidget(self.btn_bold, 1)
        font_style_layout.addWidget(self.btn_italic, 1)
        font_toolbar = QFrame()
        font_toolbar.setStyleSheet(
            "QFrame { background-color: #F5F7FA; border: 1px solid #EBEEF5; border-radius: 4px; }"
        )
        font_toolbar.setLayout(font_style_layout)
        font_block.addWidget(font_toolbar)
        label_body.addLayout(font_block)

        centroid_marker_layout = _field_group("모음 중심점 모양", font_normal)
        self.group_centroid_marker = QButtonGroup(self)
        centroid_btns = []
        for i, (mk, tip) in enumerate(
            [
                ("o", "원"),
                ("s", "사각형"),
                ("^", "삼각형"),
                ("D", "다이아몬드"),
                ("wo", "원(흰색)"),
                ("ws", "사각형(흰색)"),
                ("w^", "삼각형(흰색)"),
                ("wD", "다이아몬드(흰색)"),
            ]
        ):
            btn = MarkerShapeButton(mk, tooltip=tip)
            self.group_centroid_marker.addButton(btn, i)
            centroid_btns.append(btn)
        centroid_marker_layout.addWidget(_wrap_marker_shape_bar(centroid_btns, self))
        self.group_centroid_marker.button(0).setChecked(True)
        label_body.addLayout(centroid_marker_layout)

        label_advanced = AdvancedOptionsBlock(
            panel_id="design",
            settings_key="label_slash",
            default_collapsed=True,
            ui_font_name=self.ui_font_name,
        )
        row_slash, self.sw_label_slash_wrap = self._create_toggle_row(
            "// 기호 씌우기", default_checked=False
        )
        self.sw_label_slash_wrap.setToolTip("ON이면 라벨을 /a/ 형태로 표시합니다.")
        label_advanced.body_layout().addLayout(row_slash)
        label_body.addWidget(label_advanced)

        layout.addWidget(sec_label)
        self._add_separator(layout)

        # ==========================================
        # 3. 신뢰 타원 (Confidence Ellipse)
        # ==========================================
        sec_ellipse = CollapsibleSection(
            "신뢰 타원",
            font_bold,
            panel_id="design",
            settings_key="confidence_ellipse",
            default_collapsed=False,
        )
        ell_body = sec_ellipse.body_layout()

        ell_type_block = _field_group("타원 선 타입", font_normal)
        thicks = [
            (1.0, Qt.PenStyle.SolidLine, "4px 0 0 4px", "얇게"),
            (2.0, Qt.PenStyle.SolidLine, "0px", "보통"),
            (3.5, Qt.PenStyle.SolidLine, "0 4px 4px 0", "두껍게"),
        ]
        thick_frame, self.group_ell_thick = self._create_visual_button_group(thicks, 1)
        # 실선/긴 점선/짧은 점선. 버튼 아이콘은 레이어 도크와 동일하게 DashLine/DotLine 사용
        styles = [
            (2.0, Qt.PenStyle.SolidLine, "4px 0 0 4px", "실선"),
            (2.0, Qt.PenStyle.DashLine, "0px", "긴 점선"),
            (2.0, Qt.PenStyle.DotLine, "0 4px 4px 0", "짧은 점선"),
        ]
        style_frame, self.group_ell_style = self._create_visual_button_group(styles, 2)
        ell_type_block.addWidget(thick_frame)
        ell_type_block.addWidget(style_frame)
        ell_body.addLayout(ell_type_block)

        ell_line_color_layout = _field_group("타원 선 색상", font_normal)
        self.ell_line_picker = ColorPalette(
            default_color="#606060", allow_transparent=True, parent=self
        )
        ell_line_color_layout.addWidget(self.ell_line_picker)
        ell_body.addLayout(ell_line_color_layout)

        ell_fill_color_layout = _field_group("타원 내부 색상", font_normal)
        self.ell_fill_picker = ColorPalette(
            default_color="transparent", allow_transparent=True, parent=self
        )
        ell_fill_color_layout.addWidget(self.ell_fill_picker)
        self.ell_fill_opacity_row = OpacitySliderRow(
            "내부 색상 불투명도",
            font_normal,
            default_percent=opacity_to_slider(DEFAULT_ELL_FILL_OPACITY),
            enabled=False,
            parent=self,
        )
        ell_fill_color_layout.addWidget(self.ell_fill_opacity_row)
        ell_body.addLayout(ell_fill_color_layout)

        layout.addWidget(sec_ellipse)
        self._add_separator(layout)

        # ==========================================
        # 4. 그래프 배경 (Graph Background)
        # ==========================================
        sec_graph = CollapsibleSection(
            "그래프 배경",
            font_bold,
            panel_id="design",
            settings_key="graph_background",
            default_collapsed=False,
        )
        graph_body = sec_graph.body_layout()

        row5, self.sw_box_spines = self._create_toggle_row(
            "사방 테두리", default_checked=self._is_normalized
        )
        row6, self.sw_show_grid = self._create_toggle_row(
            "배경 실선(Grid)", default_checked=self._is_normalized
        )
        row_y_rot, self.sw_y_label_rotation = self._create_toggle_row(
            "Y축 라벨 눕히기", default_checked=self._is_normalized
        )
        self.sw_y_label_rotation.setToolTip(
            "Y축(F1 등) 글자를 90도 눕혀 표시합니다. 끄면 똑바로 세웁니다."
        )
        graph_body.addLayout(row5)
        graph_body.addLayout(row6)
        graph_body.addLayout(row_y_rot)

        graph_advanced = AdvancedOptionsBlock(
            panel_id="design",
            settings_key="graph_background_extra",
            default_collapsed=True,
            ui_font_name=self.ui_font_name,
        )
        adv_body = graph_advanced.body_layout()

        row_unit, self.sw_show_axis_units = self._create_toggle_row(
            "눈금 단위", default_checked=False
        )
        self.sw_show_axis_units.setToolTip(
            "ON 시 X·Y축 이름 뒤에 (Hz) 등 눈금 단위 표시"
        )
        row_minor, self.sw_show_minor_ticks = self._create_toggle_row(
            "세부 눈금 표시", default_checked=True
        )
        self.sw_show_minor_ticks.setToolTip(
            "ON 시 주 눈금 사이에 세부 눈금을 표시합니다."
        )
        row_axis, self.sw_axis_position_swap = self._create_toggle_row(
            "축·눈금 위치 반전", default_checked=self._is_normalized
        )
        self.sw_axis_position_swap.setToolTip(
            "Praat에서 아래/왼쪽, 수학에서 위/오른쪽에 축과 눈금을 표시합니다."
        )
        adv_body.addLayout(row_unit)
        adv_body.addLayout(row_minor)
        adv_body.addLayout(row_axis)
        graph_body.addWidget(graph_advanced)

        layout.addWidget(sec_graph)
        layout.addStretch()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # ==========================================
        # 5. 하단 액션 버튼 (설정 유지 / 초기화 분할)
        # ==========================================
        bottom_container = QWidget()
        bottom_container.setStyleSheet(
            "background-color: white; border-top: 1px solid #E4E7ED;"
        )
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(12, 10, 12, 10)
        bottom_layout.setSpacing(8)

        self.btn_lock = QPushButton("🔒 설정 유지")
        self.btn_lock.setCheckable(True)
        # 기본값: 설정 유지 ON (전역 디자인 설정 기본값을 유지하도록)
        self.btn_lock.setChecked(True)
        self.btn_lock.setFixedHeight(35)
        self.btn_lock.setFont(font_bold)
        self.btn_lock.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_lock.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_lock.setStyleSheet("""
            QPushButton { background-color: #F4F4F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #909399; }
            QPushButton:checked { background-color: #ECF5FF; border: 1px solid #409EFF; color: #409EFF; }
            QPushButton:hover:!checked { background-color: #E4E7ED; color: #606266; }
        """)

        self.btn_reset = QPushButton("초기화")
        self.btn_reset.setFixedHeight(35)
        self.btn_reset.setFont(font_bold)
        self.btn_reset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_reset.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_reset.setStyleSheet("""
            QPushButton { background-color: #F4F4F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #F56C6C; }
            QPushButton:hover { background-color: #FEF0F0; border-color: #FBC4C4; }
        """)
        self.btn_reset.clicked.connect(self._reset_to_defaults)

        bottom_layout.addWidget(self.btn_lock, stretch=1)
        bottom_layout.addWidget(self.btn_reset, stretch=1)

        main_layout.addWidget(bottom_container)

    def _add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #EBEEF5;")
        layout.addWidget(line)

    def _connect_signals(self):
        for sw in [
            self.sw_show_raw,
            self.sw_show_centroid,
            self.sw_show_axis_units,
            self.sw_axis_position_swap,
            self.sw_y_label_rotation,
            self.sw_box_spines,
            self.sw_show_grid,
            self.sw_show_minor_ticks,
            self.sw_label_slash_wrap,
        ]:
            sw.toggled.connect(self._on_setting_changed)

        self.combo_lbl_size.currentTextChanged.connect(self._on_setting_changed)
        self.btn_bold.toggled.connect(self._on_setting_changed)
        self.btn_italic.toggled.connect(self._on_setting_changed)

        self.btn_lock.toggled.connect(self._on_setting_changed)

        self.group_ell_thick.buttonToggled.connect(self._on_setting_changed)
        self.group_ell_style.buttonToggled.connect(self._on_setting_changed)
        self.group_centroid_marker.buttonToggled.connect(self._on_setting_changed)
        self.group_font_style.buttonToggled.connect(self._on_setting_changed)
        self.group_raw_marker.buttonToggled.connect(self._on_setting_changed)

        self.lbl_color_picker.color_changed.connect(self._on_setting_changed)
        self.raw_color_picker.color_changed.connect(self._on_setting_changed)
        self.ell_line_picker.color_changed.connect(self._on_setting_changed)
        self.ell_fill_picker.color_changed.connect(self._sync_ell_fill_opacity_enabled)
        self.ell_fill_picker.color_changed.connect(self._on_setting_changed)
        self.ell_fill_opacity_row.slider.valueChanged.connect(self._on_setting_changed)

    def _sync_ell_fill_opacity_enabled(self, *_args):
        self.ell_fill_opacity_row.set_enabled(
            _ell_fill_has_color(self.ell_fill_picker.current_color)
        )

    def _on_setting_changed(self, *args):
        if self._is_loading:
            return
        self.settings_changed.emit(self.get_current_settings())

    def _reset_to_defaults(self):
        self._is_loading = True

        self.sw_show_raw.setChecked(True)
        self.sw_show_centroid.setChecked(True)
        self.sw_show_axis_units.setChecked(False)

        self.lbl_color_picker.set_color(config.COLOR_PRIMARY_RED)
        self.raw_color_picker.set_color("#606060")
        self.combo_lbl_size.setCurrentText("20")
        self.btn_bold.setChecked(True)
        self.btn_italic.setChecked(False)

        self.group_ell_thick.button(1).setChecked(True)
        self.group_ell_style.button(2).setChecked(True)  # 짧은 점선
        self.group_centroid_marker.button(0).setChecked(True)
        self.group_font_style.button(0).setChecked(True)  # serif(명조) 기본
        self.group_raw_marker.button(0).setChecked(True)
        self.sw_label_slash_wrap.setChecked(False)

        self.ell_line_picker.set_color("#606060")
        self.ell_fill_picker.set_color("transparent")
        self.ell_fill_opacity_row.set_opacity(DEFAULT_ELL_FILL_OPACITY)
        self._sync_ell_fill_opacity_enabled()

        self.sw_axis_position_swap.setChecked(False)
        self.sw_y_label_rotation.setChecked(False)
        self.sw_box_spines.setChecked(False)
        self.sw_show_grid.setChecked(False)
        if self._is_normalized:
            self.sw_y_label_rotation.setChecked(True)
            self.sw_box_spines.setChecked(True)
            self.sw_show_grid.setChecked(True)
            self.sw_axis_position_swap.setChecked(True)
        self.sw_show_minor_ticks.setChecked(True)

        # 초기화 시 설정 유지도 OFF (로그 없이)
        self.btn_lock.blockSignals(True)
        self.btn_lock.setChecked(False)
        self.btn_lock.blockSignals(False)

        self._is_loading = False
        self._on_setting_changed()

    def get_current_settings(self):
        thick_map = {0: 0.5, 1: 1.0, 2: 2.0}
        style_map = {0: "-", 1: "---", 2: "--"}  # 실선, 긴 점선, 짧은 점선
        marker_map = {
            0: "o",
            1: "s",
            2: "^",
            3: "D",
            4: "wo",
            5: "ws",
            6: "w^",
            7: "wD",
        }

        line_color = self.ell_line_picker.current_color
        fill_color = self.ell_fill_picker.current_color

        font_style = "serif" if self.group_font_style.checkedId() == 0 else "sans"
        raw_marker_id = self.group_raw_marker.checkedId()
        raw_marker = ["o", "x", "a"][raw_marker_id] if 0 <= raw_marker_id <= 2 else "o"
        return {
            "show_raw": self.sw_show_raw.isChecked(),
            "show_centroid": self.sw_show_centroid.isChecked(),
            "show_axis_units": self.sw_show_axis_units.isChecked(),
            "centroid_marker": marker_map.get(
                self.group_centroid_marker.checkedId(), "o"
            ),
            "raw_marker": raw_marker,
            "raw_color": self.raw_color_picker.current_color,
            "font_style": font_style,
            "lbl_color": self.lbl_color_picker.current_color,
            "lbl_size": int(self.combo_lbl_size.currentText()),
            "lbl_bold": self.btn_bold.isChecked(),
            "lbl_italic": self.btn_italic.isChecked(),
            "ell_thick": thick_map.get(self.group_ell_thick.checkedId(), 1.0),
            "ell_style": style_map.get(self.group_ell_style.checkedId(), "--"),
            "ell_color": line_color if line_color != "transparent" else None,
            "ell_fill_color": fill_color if fill_color != "transparent" else None,
            "ell_fill_opacity": self.ell_fill_opacity_row.get_opacity(),
            "axis_position_swap": self.sw_axis_position_swap.isChecked(),
            "y_label_rotation": self.sw_y_label_rotation.isChecked(),
            "box_spines": self.sw_box_spines.isChecked(),
            "show_grid": self.sw_show_grid.isChecked(),
            "show_minor_ticks": self.sw_show_minor_ticks.isChecked(),
            "label_slash_wrap": self.sw_label_slash_wrap.isChecked(),
            "is_locked": self.btn_lock.isChecked(),
        }


class CompareDesignSettingsPanel(QWidget):
    """
    다중 비교 플롯 전용 디자인 설정 패널입니다.
    """

    settings_changed = Signal(dict)
    label_move_clicked = Signal(str)  # 'blue' | 'red'

    def __init__(
        self,
        name_blue="기준 데이터",
        name_red="비교 데이터",
        parent=None,
        ui_font_name="Malgun Gothic",
        is_normalized=False,
        legend_meta_blue=None,
        legend_meta_red=None,
    ):
        super().__init__(parent)
        self.ui_font_name = ui_font_name
        self.name_blue = name_blue
        self.name_red = name_red
        self._legend_meta = {
            "blue": legend_meta_blue,
            "red": legend_meta_red,
        }
        self._is_loading = True
        self._is_normalized = is_normalized

        self._setup_ui()
        self._connect_signals()

        self._is_loading = False

    def _create_toggle_row(self, label_text, default_checked=True):
        row = QHBoxLayout()
        lbl = QLabel(label_text, font=QFont(self.ui_font_name, 9))
        switch = ToggleSwitch(checked=default_checked)
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(switch)
        return row, switch

    def _create_visual_button_group(self, options, default_idx):
        return create_line_preview_button_group(self, options, default_idx)

    def _add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #EBEEF5;")
        layout.addWidget(line)

    def _build_individual_tab(self, default_color, default_style_str, series):
        """서브 탭 내부에 들어갈 개별 디자인 요소 팩토리. series: 'blue' | 'red'. default_style_str: '-', '--', '---'."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(0, 15, 0, 10)
        layout.setSpacing(18)
        font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        font_normal = QFont(self.ui_font_name, 9)

        # 0. 데이터 범례 (현재 탭 파일명)
        meta = self._legend_meta.get(series)
        if meta:
            display_name, tooltip, members = meta
        else:
            file_name = self.name_blue if series == "blue" else self.name_red
            clean_name = os.path.splitext(strip_gichan_prefix(file_name))[0]
            display_name = truncate_display_name(clean_name, MAX_DISPLAY_NAME_LEN)
            tooltip = clean_name
            members = None
        legend_row = QHBoxLayout()
        legend_row.setContentsMargins(0, 0, 0, 8)
        legend_row.setSpacing(6)
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(50, 16)
        icon_lbl.setPixmap(create_legend_icon_design(default_color, default_style_str))
        lbl_a = QLabel("a")
        lbl_a.setFont(font_bold)
        lbl_a.setStyleSheet(f"color: {default_color};")
        legend_row.addWidget(icon_lbl)
        legend_row.addWidget(lbl_a)
        legend_row.addSpacing(8)
        add_compare_legend_name_widgets(
            legend_row,
            display_name=display_name,
            tooltip=tooltip,
            member_names=members,
            font=font_normal,
            dialog_parent=self.window(),
            ui_font_name=self.ui_font_name,
        )
        layout.addLayout(legend_row)

        # 1. 라벨과 중심점 설정
        sec_label = CollapsibleSection(
            "라벨과 중심점",
            font_bold,
            panel_id="compare_design",
            settings_key=f"label_{series}",
            default_collapsed=False,
        )
        label_body = sec_label.body_layout()

        btn_label_move = ShortcutButton("assets/shortcuts/T.png", "라벨 위치 이동")
        btn_label_move.setObjectName("BtnLabelMove")
        btn_label_move.setCheckable(True)
        btn_label_move.setFixedHeight(32)
        btn_label_move.setFont(font_normal)
        btn_label_move.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_label_move.setStyleSheet("""
            QPushButton { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #333; }
            QPushButton:hover:!checked { background-color: #E4E7ED; border: 1px solid #C0C4CC; color: #409EFF; }
            QPushButton:checked { background-color: #E6A23C; color: white; font-weight: bold; border: none; }
        """)

        btn_label_move.clicked.connect(lambda: self.label_move_clicked.emit(series))
        label_body.addWidget(btn_label_move)

        color_layout = _field_group("라벨 텍스트 색상", font_normal)
        lbl_color_picker = ColorPalette(
            default_color=default_color, allow_transparent=True, parent=self
        )
        color_layout.addWidget(lbl_color_picker)
        label_body.addLayout(color_layout)

        font_block = _field_group("폰트", font_normal)
        font_style_layout = QHBoxLayout()
        font_style_layout.setSpacing(6)

        combo_lbl_size = NoWheelComboBox()
        combo_lbl_size.setStyleSheet(
            "QComboBox { padding: 2px 4px; border: 1px solid #DCDFE6; border-radius: 3px; }"
        )
        combo_lbl_size.addItems(["12", "14", "16", "18", "20", "22", "24"])
        combo_lbl_size.setCurrentText("20")
        combo_lbl_size.setFixedWidth(55)
        combo_lbl_size.setMaxVisibleItems(8)
        font_style_layout.addWidget(combo_lbl_size)
        font_style_layout.addWidget(QLabel("pt", font=font_normal))
        font_style_layout.addSpacing(10)

        toolbar_style = """
            QPushButton { background-color: transparent; border: 1px solid transparent; border-radius: 4px; color: #333333; }
            QPushButton:hover { background-color: #E4E7ED; }
            QPushButton:checked { background-color: #DCDFE6; border: 1px solid #C0C4CC; }
        """
        btn_bold = QPushButton("B")
        btn_bold.setCheckable(True)
        btn_bold.setChecked(True)
        btn_bold.setFixedSize(26, 26)
        btn_bold.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        btn_bold.setStyleSheet(toolbar_style)
        btn_bold.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_bold.setToolTip("굵게 (Bold)")

        btn_italic = QPushButton("I")
        btn_italic.setCheckable(True)
        btn_italic.setFixedSize(26, 26)
        font_i = QFont("Times New Roman", 10)
        font_i.setItalic(True)
        btn_italic.setFont(font_i)
        btn_italic.setStyleSheet(toolbar_style)
        btn_italic.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_italic.setToolTip("기울임 (Italic)")

        font_style_layout.addWidget(btn_bold, 1)
        font_style_layout.addWidget(btn_italic, 1)
        font_toolbar = QFrame()
        font_toolbar.setStyleSheet(
            "QFrame { background-color: #F5F7FA; border: 1px solid #EBEEF5; border-radius: 4px; }"
        )
        font_toolbar.setLayout(font_style_layout)
        font_block.addWidget(font_toolbar)
        label_body.addLayout(font_block)

        centroid_marker_layout = _field_group("모음 중심점 모양", font_normal)
        group_centroid_marker = QButtonGroup(self)
        centroid_btns = []
        for i, (mk, tip) in enumerate(
            [
                ("o", "원"),
                ("s", "사각형"),
                ("^", "삼각형"),
                ("D", "다이아몬드"),
                ("wo", "원(흰색)"),
                ("ws", "사각형(흰색)"),
                ("w^", "삼각형(흰색)"),
                ("wD", "다이아몬드(흰색)"),
            ]
        ):
            btn = MarkerShapeButton(mk, tooltip=tip)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            group_centroid_marker.addButton(btn, i)
            centroid_btns.append(btn)
        centroid_marker_layout.addWidget(_wrap_marker_shape_bar(centroid_btns, self))
        group_centroid_marker.button(0).setChecked(True)
        label_body.addLayout(centroid_marker_layout)

        raw_color_layout = _field_group("데이터 포인트 색상", font_normal)
        raw_color_picker = ColorPalette(
            default_color="#606060", allow_transparent=False, parent=self
        )
        raw_color_layout.addWidget(raw_color_picker)
        label_body.addLayout(raw_color_layout)

        layout.addWidget(sec_label)
        self._add_separator(layout)

        # 2. 신뢰 타원 설정
        sec_ellipse = CollapsibleSection(
            "신뢰 타원",
            font_bold,
            panel_id="compare_design",
            settings_key=f"confidence_ellipse_{series}",
            default_collapsed=False,
        )
        ell_body = sec_ellipse.body_layout()

        ell_type_block = _field_group("타원 선 타입", font_normal)
        thicks = [
            (1.0, Qt.PenStyle.SolidLine, "4px 0 0 4px", "얇게"),
            (2.0, Qt.PenStyle.SolidLine, "0px", "보통"),
            (3.5, Qt.PenStyle.SolidLine, "0 4px 4px 0", "두껍게"),
        ]
        thick_frame, group_ell_thick = self._create_visual_button_group(thicks, 1)
        # 버튼 아이콘은 레이어 도크와 동일하게 DashLine/DotLine 사용. default_style_str -> 인덱스: '-'=0, '---'=1, '--'=2
        style_str_to_idx = {"-": 0, "---": 1, "--": 2}
        default_style_idx = style_str_to_idx.get(default_style_str, 0)
        styles = [
            (2.0, Qt.PenStyle.SolidLine, "4px 0 0 4px", "실선"),
            (2.0, Qt.PenStyle.DashLine, "0px", "긴 점선"),
            (2.0, Qt.PenStyle.DotLine, "0 4px 4px 0", "짧은 점선"),
        ]
        style_frame, group_ell_style = self._create_visual_button_group(
            styles, default_style_idx
        )
        ell_type_block.addWidget(thick_frame)
        ell_type_block.addWidget(style_frame)
        ell_body.addLayout(ell_type_block)

        ell_line_color_layout = _field_group("타원 선 색상", font_normal)
        ell_line_picker = ColorPalette(
            default_color=default_color, allow_transparent=True, parent=self
        )
        ell_line_color_layout.addWidget(ell_line_picker)
        ell_body.addLayout(ell_line_color_layout)

        ell_fill_color_layout = _field_group("타원 내부 색상", font_normal)
        ell_fill_picker = ColorPalette(
            default_color="transparent", allow_transparent=True, parent=self
        )
        ell_fill_color_layout.addWidget(ell_fill_picker)
        ell_fill_opacity_row = OpacitySliderRow(
            "내부 색상 불투명도",
            font_normal,
            default_percent=opacity_to_slider(DEFAULT_ELL_FILL_OPACITY),
            enabled=False,
            parent=self,
        )
        ell_fill_color_layout.addWidget(ell_fill_opacity_row)
        ell_body.addLayout(ell_fill_color_layout)

        layout.addWidget(sec_ellipse)
        layout.addStretch()

        controls = {
            "btn_label_move": btn_label_move,
            "legend_icon": icon_lbl,
            "legend_a": lbl_a,
            "lbl_color_picker": lbl_color_picker,
            "combo_lbl_size": combo_lbl_size,
            "btn_bold": btn_bold,
            "btn_italic": btn_italic,
            "group_centroid_marker": group_centroid_marker,
            "group_ell_thick": group_ell_thick,
            "group_ell_style": group_ell_style,
            "ell_line_picker": ell_line_picker,
            "ell_fill_picker": ell_fill_picker,
            "ell_fill_opacity_row": ell_fill_opacity_row,
            "raw_color_picker": raw_color_picker,
        }
        return tab_widget, controls

    def update_legend_indicators(self, settings):
        """디자인 설정 변경 시 각 탭(Blue/Red) 상단 범례 아이콘·텍스트 색상을 실시간 반영. 점 모양은 모음 중심점 모양을 따름."""
        if not settings:
            return
        marker_map = ["o", "s", "^", "D", "wo", "ws", "w^", "wD"]
        for series, ctrl in [("blue", self.ctrl_blue), ("red", self.ctrl_red)]:
            cfg = settings.get(series, {})
            ell_color = cfg.get("ell_color") or (
                config.COLOR_PRIMARY_BLUE
                if series == "blue"
                else config.COLOR_PRIMARY_RED
            )
            if ell_color == "transparent":
                ell_color = (
                    config.COLOR_PRIMARY_BLUE
                    if series == "blue"
                    else config.COLOR_PRIMARY_RED
                )
            ell_style = cfg.get("ell_style", "-" if series == "blue" else "--")
            centroid_marker = cfg.get("centroid_marker", "o")
            if centroid_marker not in marker_map:
                centroid_marker = "o"
            # 범례 아이콘용: 흰색 세트(wo,ws,w^,wD)는 같은 형태의 검은 버전으로 표시
            legend_marker = (
                centroid_marker[1]
                if centroid_marker in ("wo", "ws", "w^", "wD")
                else centroid_marker
            )
            if "legend_icon" in ctrl:
                ctrl["legend_icon"].setPixmap(
                    create_legend_icon_design(ell_color, ell_style, legend_marker)
                )
            lbl_color = cfg.get("lbl_color") or ell_color
            if lbl_color == "transparent":
                lbl_color = ell_color
            if "legend_a" in ctrl:
                ctrl["legend_a"].setStyleSheet(f"color: {lbl_color};")

    def _setup_compare_data_section(self, layout, font_bold):
        """CompareDesignSettingsPanel: 데이터 표시 구역."""
        sec_data = CollapsibleSection(
            "데이터 표시",
            font_bold,
            panel_id="compare_design",
            settings_key="data_display",
            default_collapsed=False,
        )
        body = sec_data.body_layout()
        row1, self.sw_show_raw = self._create_toggle_row("데이터 포인트")
        row2, self.sw_show_centroid = self._create_toggle_row("모음 중심점(Centroid)")
        row3, self.sw_label_slash_wrap_cmp = self._create_toggle_row(
            "라벨에 // 기호 씌우기", default_checked=False
        )
        self.sw_label_slash_wrap_cmp.setToolTip("ON이면 라벨을 /a/ 형태로 표시합니다.")
        body.addLayout(row1)
        body.addLayout(row2)
        body.addLayout(row3)
        layout.addWidget(sec_data)
        self._add_separator(layout)

    def _setup_compare_style_section(self, layout, font_bold):
        """CompareDesignSettingsPanel: 스타일(폰트·데이터 포인트) 구역."""
        sec_style = CollapsibleSection(
            "스타일",
            font_bold,
            panel_id="compare_design",
            settings_key="style",
            default_collapsed=False,
        )
        style_body = sec_style.body_layout()
        font_caption = QFont(self.ui_font_name, config.FONT_SIZE_SMALL)
        btn_style = """
            QPushButton { background-color: transparent; border: 1px solid transparent; border-radius: 4px; }
            QPushButton:hover { background-color: #F5F7FA; }
            QPushButton:checked { background-color: #E4E7ED; border: 1px solid #C0C4CC; }
        """
        font_style_block = _field_group("폰트 스타일", font_caption)
        self.group_font_style_common = QButtonGroup(self)
        btn_serif = QPushButton("")
        btn_serif.setCheckable(True)
        btn_serif.setChecked(True)
        btn_serif.setMinimumHeight(26)
        btn_serif.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_serif.setStyleSheet(btn_style)
        btn_serif.setIcon(create_font_style_icon(is_serif=True))
        btn_serif.setIconSize(QPixmap(40, 26).size())
        btn_serif.setToolTip("명조(세리프)")
        self.group_font_style_common.addButton(btn_serif, 0)
        btn_sans = QPushButton("")
        btn_sans.setCheckable(True)
        btn_sans.setMinimumHeight(26)
        btn_sans.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_sans.setStyleSheet(btn_style)
        btn_sans.setIcon(create_font_style_icon(is_serif=False))
        btn_sans.setIconSize(QPixmap(40, 26).size())
        btn_sans.setToolTip("고딕(산세리프)")
        self.group_font_style_common.addButton(btn_sans, 1)
        font_style_block.addWidget(wrap_segmented_buttons([btn_serif, btn_sans], self))
        style_body.addLayout(font_style_block)

        dp_shape_block = _field_group("데이터 포인트", font_caption)
        self.group_raw_marker_common = QButtonGroup(self)
        dp_btns = []
        for i, (key, tip) in enumerate(
            [("o", "빈 원"), ("x", "X 모양"), ("a", "라벨 문자(모음 기호)")]
        ):
            btn = QPushButton("")
            btn.setCheckable(True)
            btn.setProperty("val", key)
            btn.setMinimumHeight(26)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(btn_style)
            btn.setIcon(create_raw_marker_icon(key))
            btn.setIconSize(QPixmap(24, 24).size())
            btn.setToolTip(tip)
            if key == "o":
                btn.setChecked(True)
            self.group_raw_marker_common.addButton(btn, i)
            dp_btns.append(btn)
        dp_shape_block.addWidget(wrap_segmented_buttons(dp_btns, self))
        style_body.addLayout(dp_shape_block)
        layout.addWidget(sec_style)
        self._add_separator(layout)

    def _setup_compare_graph_background_section(self, layout, font_bold):
        """CompareDesignSettingsPanel: 그래프 배경 구역."""
        sec_graph = CollapsibleSection(
            "그래프 배경",
            font_bold,
            panel_id="compare_design",
            settings_key="graph_background",
            default_collapsed=False,
        )
        graph_body = sec_graph.body_layout()

        row3, self.sw_box_spines = self._create_toggle_row(
            "사방 테두리", default_checked=self._is_normalized
        )
        row4, self.sw_show_grid = self._create_toggle_row(
            "배경 실선(Grid)", default_checked=self._is_normalized
        )
        row_y_rot, self.sw_y_label_rotation = self._create_toggle_row(
            "Y축 라벨 눕히기", default_checked=False
        )
        self.sw_y_label_rotation.setToolTip(
            "Y축 글자를 90도 눕혀 표시합니다. 끄면 똑바로 세웁니다."
        )
        graph_body.addLayout(row3)
        graph_body.addLayout(row4)
        graph_body.addLayout(row_y_rot)

        graph_advanced = AdvancedOptionsBlock(
            panel_id="compare_design",
            settings_key="graph_background_extra",
            default_collapsed=True,
            ui_font_name=self.ui_font_name,
        )
        adv_body = graph_advanced.body_layout()

        row_unit, self.sw_show_axis_units = self._create_toggle_row(
            "눈금 단위", default_checked=False
        )
        self.sw_show_axis_units.setToolTip(
            "ON 시 X·Y축 이름 뒤에 (Hz) 등 눈금 단위 표시"
        )
        self.axis_units_row_widget = QWidget()
        self.axis_units_row_widget.setLayout(row_unit)
        self.axis_units_row_widget.setContentsMargins(0, 0, 0, 0)
        row_unit.setContentsMargins(0, 0, 0, 0)

        row_minor, self.sw_show_minor_ticks = self._create_toggle_row(
            "세부 눈금 표시", default_checked=True
        )
        self.sw_show_minor_ticks.setToolTip(
            "ON 시 주 눈금 사이에 세부 눈금을 표시합니다."
        )

        row_axis, self.sw_axis_position_swap = self._create_toggle_row(
            "축·눈금 위치 반전", default_checked=False
        )
        self.sw_axis_position_swap.setToolTip(
            "Praat에서 아래/왼쪽, 수학에서 위/오른쪽에 축과 눈금을 표시합니다."
        )
        row_axis.setContentsMargins(0, 0, 0, 0)
        self.axis_position_swap_row_widget = QWidget()
        self.axis_position_swap_row_widget.setContentsMargins(0, 0, 0, 0)
        self.axis_position_swap_row_widget.setLayout(row_axis)

        adv_body.addWidget(self.axis_units_row_widget)
        adv_body.addLayout(row_minor)
        adv_body.addWidget(self.axis_position_swap_row_widget)
        graph_body.addWidget(graph_advanced)

        if self._is_normalized:
            self.axis_units_row_widget.setVisible(False)
            self.axis_position_swap_row_widget.setVisible(False)
            self.sw_y_label_rotation.setChecked(True)
            self.sw_box_spines.setChecked(True)
            self.sw_show_grid.setChecked(True)
        else:
            self.sw_axis_position_swap.setChecked(False)
            self.sw_y_label_rotation.setChecked(False)
            self.sw_box_spines.setChecked(False)
            self.sw_show_grid.setChecked(False)
        self.sw_show_minor_ticks.setChecked(True)

        layout.addWidget(sec_graph)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; }")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("QWidget { background-color: white; }")
        scroll_content.setMaximumWidth(260)
        scroll_content.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(*lc.MARGIN_DOCK_CONTENTS)
        layout.setSpacing(lc.SPACING_DOCK_SECTIONS_PX)
        font_bold = QFont(self.ui_font_name, config.FONT_SIZE_NORMAL, QFont.Weight.Bold)
        self._setup_compare_data_section(layout, font_bold)
        self._setup_compare_style_section(layout, font_bold)
        self._setup_compare_graph_background_section(layout, font_bold)

        # ------------------------------------------------
        # [ 개별 설정 구역 (서브 탭) ]
        # ------------------------------------------------
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.sub_tabs.setUsesScrollButtons(False)
        self.sub_tabs.tabBar().setElideMode(Qt.TextElideMode.ElideRight)

        # 도크 폭 내 수용: 탭 너비 고정(두 탭 합쳐 도크를 넘지 않도록), 말줄임·툴팁으로 전체 이름 표시
        _tab_width_px = (
            100  # 탭 하나당 고정 너비; 2탭 합 200px로 마진 내 가용 폭에 맞춤
        )
        self.sub_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border-top: 2px solid #E4E7ED; background: white; }}
            QTabBar::tab {{
                background: #F5F7FA; border: 1px solid #DCDFE6; border-bottom: none;
                border-top-left-radius: 4px; border-top-right-radius: 4px;
                min-width: {_tab_width_px}px; max-width: {_tab_width_px}px; padding: 6px 5px; color: #606266; font-size: 11px;
            }}
            QTabBar::tab:selected {{ background: #FFFFFF; color: #303133; font-weight: bold; }}
        """)

        # Blue (기준) 탭: 텍스트 및 선 디폴트 Blue, 실선('-')
        self.tab_blue, self.ctrl_blue = self._build_individual_tab(
            config.COLOR_PRIMARY_BLUE, "-", "blue"
        )
        # Red (비교) 탭: 텍스트 및 선 디폴트 Red, 긴 점선('---')
        self.tab_red, self.ctrl_red = self._build_individual_tab(
            config.COLOR_PRIMARY_RED, "---", "red"
        )

        idx_blue = self.sub_tabs.addTab(
            self.tab_blue, strip_gichan_prefix(self.name_blue)
        )
        self.sub_tabs.setTabToolTip(idx_blue, self.name_blue)

        idx_red = self.sub_tabs.addTab(self.tab_red, strip_gichan_prefix(self.name_red))
        self.sub_tabs.setTabToolTip(idx_red, self.name_red)

        self._update_compare_tab_text_colors()
        layout.addSpacing(10)
        layout.addWidget(self.sub_tabs)
        layout.addStretch()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # ------------------------------------------------
        # [ 하단 초기화 버튼 ]
        # ------------------------------------------------
        bottom_container = QWidget()
        bottom_container.setStyleSheet(
            "background-color: white; border-top: 1px solid #E4E7ED;"
        )
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(12, 10, 12, 10)

        self.btn_reset = QPushButton("전체 초기화")
        self.btn_reset.setFixedHeight(35)
        self.btn_reset.setFont(font_bold)
        self.btn_reset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_reset.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #F4F4F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #F56C6C;
            }
            QPushButton:hover { background-color: #FEF0F0; border-color: #FBC4C4; }
        """)
        self.btn_reset.clicked.connect(self._reset_to_defaults)

        bottom_layout.addWidget(self.btn_reset)
        main_layout.addWidget(bottom_container)

    def _connect_signals(self):
        for sw in [
            self.sw_show_raw,
            self.sw_show_centroid,
            self.sw_label_slash_wrap_cmp,
            self.sw_show_axis_units,
            self.sw_axis_position_swap,
            self.sw_y_label_rotation,
            self.sw_box_spines,
            self.sw_show_grid,
            self.sw_show_minor_ticks,
        ]:
            sw.toggled.connect(self._on_setting_changed)
        self.group_font_style_common.buttonToggled.connect(self._on_setting_changed)
        self.group_raw_marker_common.buttonToggled.connect(self._on_setting_changed)

        for ctrl in [self.ctrl_blue, self.ctrl_red]:
            ctrl["combo_lbl_size"].currentTextChanged.connect(self._on_setting_changed)
            ctrl["btn_bold"].toggled.connect(self._on_setting_changed)
            ctrl["btn_italic"].toggled.connect(self._on_setting_changed)
            ctrl["group_centroid_marker"].buttonToggled.connect(
                self._on_setting_changed
            )
            ctrl["group_ell_thick"].buttonToggled.connect(self._on_setting_changed)
            ctrl["group_ell_style"].buttonToggled.connect(self._on_setting_changed)
            ctrl["lbl_color_picker"].color_changed.connect(self._on_setting_changed)
            ctrl["ell_line_picker"].color_changed.connect(self._on_setting_changed)
            ctrl["ell_fill_picker"].color_changed.connect(
                lambda *_a, c=ctrl: self._sync_compare_ell_fill_opacity(c)
            )
            ctrl["ell_fill_picker"].color_changed.connect(self._on_setting_changed)
            ctrl["ell_fill_opacity_row"].slider.valueChanged.connect(
                self._on_setting_changed
            )
            ctrl["raw_color_picker"].color_changed.connect(self._on_setting_changed)
        self.ctrl_blue["ell_line_picker"].color_changed.connect(
            self._update_compare_tab_text_colors
        )
        self.ctrl_red["ell_line_picker"].color_changed.connect(
            self._update_compare_tab_text_colors
        )

    def _sync_compare_ell_fill_opacity(self, ctrl):
        ctrl["ell_fill_opacity_row"].set_enabled(
            _ell_fill_has_color(ctrl["ell_fill_picker"].current_color)
        )

    def _update_compare_tab_text_colors(self):
        """파일 탭 파일명 텍스트 색을 각 시리즈의 신뢰타원 선 색과 맞춤."""
        bar = self.sub_tabs.tabBar()

        def to_qcolor(raw, fallback):
            if not raw or str(raw).lower() == "transparent":
                return QColor(fallback)
            c = QColor(raw)
            return c if c.isValid() else QColor(fallback)

        bar.setTabTextColor(
            0,
            to_qcolor(
                self.ctrl_blue["ell_line_picker"].current_color,
                config.COLOR_PRIMARY_BLUE,
            ),
        )
        bar.setTabTextColor(
            1,
            to_qcolor(
                self.ctrl_red["ell_line_picker"].current_color, config.COLOR_PRIMARY_RED
            ),
        )

    def _on_setting_changed(self, *args):
        if self._is_loading:
            return
        self.settings_changed.emit(self.get_current_settings())

    def _reset_to_defaults(self):
        self._is_loading = True

        self.sw_show_raw.setChecked(True)
        self.sw_show_centroid.setChecked(True)
        self.sw_show_axis_units.setChecked(False)
        # 정규화 여부에 따라 공통 스위치 디폴트 분기
        if self._is_normalized:
            # Case B: 정규화 모드 – Y라벨/테두리/그리드 ON, 축 위치 스위치는 기존 기본값 유지(ON)
            self.sw_axis_position_swap.setChecked(True)
            self.sw_y_label_rotation.setChecked(True)
            self.sw_box_spines.setChecked(True)
            self.sw_show_grid.setChecked(True)
        else:
            # Case A: 비정규화 모드 – 네 옵션 모두 OFF
            self.sw_axis_position_swap.setChecked(False)
            self.sw_y_label_rotation.setChecked(False)
            self.sw_box_spines.setChecked(False)
            self.sw_show_grid.setChecked(False)
        self.sw_show_minor_ticks.setChecked(True)
        self.sw_label_slash_wrap_cmp.setChecked(False)

        self.group_font_style_common.button(0).setChecked(True)  # serif(명조) 기본
        self.group_raw_marker_common.button(0).setChecked(True)

        # Blue 초기화
        self.ctrl_blue["lbl_color_picker"].set_color(config.COLOR_PRIMARY_BLUE)
        self.ctrl_blue["combo_lbl_size"].setCurrentText("20")
        self.ctrl_blue["btn_bold"].setChecked(True)
        self.ctrl_blue["btn_italic"].setChecked(False)
        self.ctrl_blue["group_centroid_marker"].button(0).setChecked(True)
        self.ctrl_blue["group_ell_thick"].button(1).setChecked(True)
        self.ctrl_blue["group_ell_style"].button(0).setChecked(True)  # 실선
        self.ctrl_blue["ell_line_picker"].set_color(config.COLOR_PRIMARY_BLUE)
        self.ctrl_blue["ell_fill_picker"].set_color("transparent")
        self.ctrl_blue["ell_fill_opacity_row"].set_opacity(DEFAULT_ELL_FILL_OPACITY)
        self.ctrl_blue["raw_color_picker"].set_color("#606060")
        self._sync_compare_ell_fill_opacity(self.ctrl_blue)

        # Red 초기화
        self.ctrl_red["lbl_color_picker"].set_color(config.COLOR_PRIMARY_RED)
        self.ctrl_red["combo_lbl_size"].setCurrentText("20")
        self.ctrl_red["btn_bold"].setChecked(True)
        self.ctrl_red["btn_italic"].setChecked(False)
        self.ctrl_red["group_centroid_marker"].button(0).setChecked(True)
        self.ctrl_red["group_ell_thick"].button(1).setChecked(True)
        self.ctrl_red["group_ell_style"].button(1).setChecked(True)  # 긴 점선
        self.ctrl_red["ell_line_picker"].set_color(config.COLOR_PRIMARY_RED)
        self.ctrl_red["ell_fill_picker"].set_color("transparent")
        self.ctrl_red["ell_fill_opacity_row"].set_opacity(DEFAULT_ELL_FILL_OPACITY)
        self.ctrl_red["raw_color_picker"].set_color("#606060")
        self._sync_compare_ell_fill_opacity(self.ctrl_red)

        self._is_loading = False
        self._on_setting_changed()

    def _parse_individual_settings(self, ctrl):
        thick_map = {0: 0.5, 1: 1.0, 2: 2.0}
        style_map = {0: "-", 1: "---", 2: "--"}  # 실선, 긴 점선, 짧은 점선
        marker_map = {
            0: "o",
            1: "s",
            2: "^",
            3: "D",
            4: "wo",
            5: "ws",
            6: "w^",
            7: "wD",
        }

        line_color = ctrl["ell_line_picker"].current_color
        fill_color = ctrl["ell_fill_picker"].current_color

        # ell_style: checkedId()가 -1이면(토글 순간 등) checkedButton()으로 보정
        g_ell = ctrl["group_ell_style"]
        style_id = g_ell.checkedId()
        if style_id < 0:
            btn = g_ell.checkedButton()
            style_id = g_ell.id(btn) if btn else 0
        ell_style = style_map.get(style_id, "-")

        return {
            "lbl_color": ctrl["lbl_color_picker"].current_color,
            "lbl_size": int(ctrl["combo_lbl_size"].currentText()),
            "lbl_bold": ctrl["btn_bold"].isChecked(),
            "lbl_italic": ctrl["btn_italic"].isChecked(),
            "centroid_marker": marker_map.get(
                ctrl["group_centroid_marker"].checkedId(), "o"
            ),
            "ell_thick": thick_map.get(ctrl["group_ell_thick"].checkedId(), 1.0),
            "ell_style": ell_style,
            "ell_color": line_color if line_color != "transparent" else None,
            "ell_fill_color": fill_color if fill_color != "transparent" else None,
            "ell_fill_opacity": ctrl["ell_fill_opacity_row"].get_opacity(),
            "raw_color": ctrl["raw_color_picker"].current_color,
        }

    def get_current_settings(self):
        font_style = (
            "serif" if self.group_font_style_common.checkedId() == 0 else "sans"
        )
        raw_marker_id = self.group_raw_marker_common.checkedId()
        raw_marker = ["o", "x", "a"][raw_marker_id] if 0 <= raw_marker_id <= 2 else "o"
        return pack_compare_design_settings(
            common={
                "show_raw": self.sw_show_raw.isChecked(),
                "show_centroid": self.sw_show_centroid.isChecked(),
                "raw_marker": raw_marker,
                "label_slash_wrap": self.sw_label_slash_wrap_cmp.isChecked(),
                "show_axis_units": self.sw_show_axis_units.isChecked()
                if not self._is_normalized
                else False,
                "axis_position_swap": self.sw_axis_position_swap.isChecked(),
                "y_label_rotation": self.sw_y_label_rotation.isChecked(),
                "box_spines": self.sw_box_spines.isChecked(),
                "show_grid": self.sw_show_grid.isChecked(),
                "show_minor_ticks": self.sw_show_minor_ticks.isChecked(),
                "font_style": font_style,
            },
            series_cfgs=[
                self._parse_individual_settings(self.ctrl_blue),
                self._parse_individual_settings(self.ctrl_red),
            ],
        )
