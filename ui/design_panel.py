# ui_design_panel.py

import os
import config
from PyQt6.QtWidgets import (
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
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import (
    QFont,
    QColor,
    QCursor,
    QPainter,
    QPainterPath,
    QPixmap,
)

from .icon_widgets import (
    create_font_style_icon,
    create_raw_marker_icon,
    create_legend_icon_design,
    LinePreviewButton,
    MarkerShapeButton,
    ColorCircleButton,
)
from .display_utils import (
    truncate_display_name,
    MAX_DISPLAY_NAME_LEN,
    strip_gichan_prefix,
)
from . import layout_constants as lc


class NoWheelComboBox(QComboBox):
    """마우스 휠로 값이 바뀌지 않도록 휠 이벤트를 무시하는 콤보박스."""

    def wheelEvent(self, event):
        event.ignore()


class ToggleSwitch(QWidget):
    """
    체크박스 대신 사용할 커스텀 ON/OFF 토글 스위치 위젯
    """

    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self._checked = checked
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.toggled.emit(self._checked)
            self.update()

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

        x_pos = self.width() - 20 if self._checked else 2
        painter.drawEllipse(x_pos, 2, 18, 18)
        painter.end()


class ColorPalette(QWidget):
    """
    디자인 설정용 색상 선택 컴포넌트
    """

    color_changed = pyqtSignal(str)

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
            "#000000": "Black",
            "#606060": "Dark Gray",
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
            "#000000",
            "#606060",
            "#AAAAAA",
            "#795548",
            "#009688",
            "#FF9800",
        ]
        # [기본색] + [투명(옵션)] + [프리셋]: default_color가 프리셋에 없어도 0번, allow_transparent면 기본색 바로 뒤에 투명 버튼
        if self.current_color and self.current_color not in ("transparent", "custom"):
            if self.current_color in preset_colors:
                preset_colors = [c for c in preset_colors if c != self.current_color]
            preset_colors = [self.current_color] + preset_colors
        for i, c in enumerate(preset_colors):
            c_name = self.color_names.get(c, "Color")
            btn = ColorCircleButton(c, tooltip=f"{c_name} ({c})")
            btn.clicked.connect(lambda checked, col=c: self.set_color(col))
            btn_list.append(btn)
            if i == 0 and self.allow_transparent:
                btn_none = ColorCircleButton(
                    "transparent", is_transparent=True, tooltip="Transparent"
                )
                btn_none.clicked.connect(lambda: self.set_color("transparent"))
                btn_list.append(btn_none)

        self.btn_custom = ColorCircleButton("custom", tooltip="Custom Color")
        self.btn_custom.clicked.connect(self.open_color_dialog)
        btn_list.append(self.btn_custom)

        grid = QGridLayout()
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

    settings_changed = pyqtSignal(dict)
    label_move_clicked = pyqtSignal()

    def __init__(self, parent=None, ui_font_name="Malgun Gothic"):
        super().__init__(parent)
        self.ui_font_name = ui_font_name
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
        group = QButtonGroup(self)

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
            group.addButton(btn, i)
            layout.addWidget(btn)

        group.button(default_idx).setChecked(True)
        return frame, group

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; }")

        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("QWidget { background-color: white; }")
        scroll_content.setMaximumWidth(260)
        scroll_content.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(12, 12, 12, 15)
        layout.setSpacing(14)

        font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        font_normal = QFont(self.ui_font_name, 9)

        # ==========================================
        # 1. 데이터 표시 (Data Display)
        # ==========================================
        data_group = QVBoxLayout()
        data_group.setSpacing(10)
        data_group.addWidget(QLabel("데이터 표시", font=font_bold))

        row1, self.sw_show_raw = self._create_toggle_row("데이터 포인트")
        row2, self.sw_show_centroid = self._create_toggle_row("모음 중심점(Centroid)")

        data_group.addLayout(row1)
        data_group.addLayout(row2)
        layout.addLayout(data_group)
        self._add_separator(layout)

        # ==========================================
        # 스타일 (폰트 스타일)
        # ==========================================
        style_group = QVBoxLayout()
        style_group.setSpacing(8)
        style_group.addWidget(QLabel("스타일", font=font_bold))
        font_style_row = QHBoxLayout()
        font_style_row.setSpacing(4)
        lbl_font_style = QLabel("폰트 스타일:", font=font_normal)
        lbl_font_style.setMinimumWidth(95)
        font_style_row.addWidget(lbl_font_style)
        btn_style = """
            QPushButton { background-color: transparent; border: 1px solid transparent; border-radius: 4px; }
            QPushButton:hover { background-color: #F5F7FA; }
            QPushButton:checked { background-color: #E4E7ED; border: 1px solid #C0C4CC; }
        """
        self.group_font_style = QButtonGroup(self)
        btn_serif = QPushButton("")
        btn_serif.setCheckable(True)
        btn_serif.setChecked(True)
        btn_serif.setFixedSize(40, 26)
        btn_serif.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_serif.setStyleSheet(btn_style)
        btn_serif.setIcon(create_font_style_icon(is_serif=True))
        btn_serif.setIconSize(QPixmap(40, 26).size())
        btn_serif.setToolTip("명조(세리프)")
        self.group_font_style.addButton(btn_serif, 0)
        btn_sans = QPushButton("")
        btn_sans.setCheckable(True)
        btn_sans.setFixedSize(40, 26)
        btn_sans.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_sans.setStyleSheet(btn_style)
        btn_sans.setIcon(create_font_style_icon(is_serif=False))
        btn_sans.setIconSize(QPixmap(40, 26).size())
        btn_sans.setToolTip("고딕(산세리프)")
        self.group_font_style.addButton(btn_sans, 1)
        font_style_row.addWidget(btn_serif)
        font_style_row.addWidget(btn_sans)
        font_style_row.addStretch()
        style_group.addLayout(font_style_row)

        # 데이터 포인트: o / x / 라벨문자
        dp_shape_row = QHBoxLayout()
        dp_shape_row.setSpacing(4)
        lbl_dp = QLabel("데이터 포인트:", font=font_normal)
        lbl_dp.setMinimumWidth(95)
        dp_shape_row.addWidget(lbl_dp)
        self.group_raw_marker = QButtonGroup(self)
        for i, (key, tip) in enumerate(
            [("o", "빈 원"), ("x", "x 모양"), ("a", "라벨 문자(모음 기호)")]
        ):
            btn = QPushButton("")
            btn.setCheckable(True)
            btn.setProperty("val", key)
            btn.setFixedSize(32, 26)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(btn_style)
            btn.setIcon(create_raw_marker_icon(key))
            btn.setIconSize(QPixmap(24, 24).size())
            btn.setToolTip(tip)
            if key == "o":
                btn.setChecked(True)
            self.group_raw_marker.addButton(btn, i)
            dp_shape_row.addWidget(btn)
        dp_shape_row.addStretch()
        style_group.addLayout(dp_shape_row)
        layout.addLayout(style_group)
        self._add_separator(layout)

        # ==========================================
        # 2. 라벨과 중심점 (그래프 배경과 동일: 클릭 가능 헤더 + 접기)
        # ==========================================
        label_group = QVBoxLayout()
        label_group.setSpacing(14)
        label_header_row = QWidget()
        label_header_row.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        label_header_layout = QHBoxLayout(label_header_row)
        label_header_layout.setContentsMargins(0, 0, 0, 0)
        label_header_layout.setSpacing(4)
        label_header_layout.addWidget(QLabel("라벨과 중심점", font=font_bold))
        self.label_toggle_btn = QPushButton("▼")
        self.label_toggle_btn.setFixedSize(28, 24)
        self.label_toggle_btn.setFlat(True)
        self.label_toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.label_toggle_btn.setStyleSheet(
            "QPushButton { color: #606266; font-size: 11px; }"
        )
        label_header_layout.addWidget(self.label_toggle_btn)
        label_header_layout.addStretch()
        label_group.addWidget(label_header_row)

        self.btn_label_move = QPushButton("라벨 위치 이동 (T)")
        self.btn_label_move.setObjectName("BtnLabelMove")
        self.btn_label_move.setCheckable(True)
        self.btn_label_move.setFixedHeight(32)
        self.btn_label_move.setFont(font_normal)
        self.btn_label_move.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_label_move.setStyleSheet("""
            QPushButton#BtnLabelMove { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #333;}
            QPushButton#BtnLabelMove:checked { background-color: #E6A23C; color: white; font-weight: bold; border: none; }
        """)
        self.btn_label_move.clicked.connect(self.label_move_clicked.emit)
        label_group.addWidget(self.btn_label_move)
        label_group.addSpacing(4)

        color_layout = QVBoxLayout()
        color_layout.setSpacing(6)
        color_layout.addWidget(QLabel("라벨 텍스트 색상:", font=font_normal))
        self.lbl_color_picker = ColorPalette(
            default_color="#E64A19", allow_transparent=True, parent=self
        )
        color_layout.addWidget(self.lbl_color_picker)
        label_group.addLayout(color_layout)
        label_group.addSpacing(4)

        font_style_layout = QHBoxLayout()
        font_style_layout.addWidget(QLabel("폰트:", font=font_normal))

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

        font_style_layout.addWidget(self.btn_bold)
        font_style_layout.addWidget(self.btn_italic)
        font_style_layout.addStretch()

        label_group.addLayout(font_style_layout)

        centroid_marker_layout = QVBoxLayout()
        centroid_marker_layout.setSpacing(4)
        lbl_centroid = QLabel("모음 중심점 모양:", font=font_normal)
        lbl_centroid.setMinimumWidth(140)
        centroid_marker_layout.addWidget(lbl_centroid)
        centroid_row = QHBoxLayout()
        centroid_row.setSpacing(0)
        centroid_row.addStretch()
        self.group_centroid_marker = QButtonGroup(self)
        for i, (mk, tip) in enumerate(
            [
                ("o", "동그라미"),
                ("s", "사각형"),
                ("^", "삼각형"),
                ("D", "다이아몬드"),
                ("wo", "동그라미(흰색)"),
                ("ws", "사각형(흰색)"),
                ("w^", "삼각형(흰색)"),
                ("wD", "다이아몬드(흰색)"),
            ]
        ):
            btn = MarkerShapeButton(mk, tooltip=tip)
            self.group_centroid_marker.addButton(btn, i)
            centroid_row.addWidget(btn)
        centroid_row.addStretch()
        centroid_marker_layout.addLayout(centroid_row)
        self.group_centroid_marker.button(0).setChecked(True)
        label_group.addLayout(centroid_marker_layout)

        # 접었을 때 숨겨지는 영역: // 기호 씌우기
        label_collapse_content = QWidget()
        label_collapse_content_layout = QVBoxLayout(label_collapse_content)
        label_collapse_content_layout.setContentsMargins(0, 0, 0, 0)
        label_collapse_content_layout.setSpacing(4)

        # 구분선을 content 안으로 삽입하여 불필요한 위아래 이중 여백 제거
        label_collapse_line = QFrame()
        label_collapse_line.setFrameShape(QFrame.Shape.HLine)
        label_collapse_line.setStyleSheet("color: #EBEEF5;")
        label_collapse_line.setFixedHeight(1)
        label_collapse_content_layout.addWidget(label_collapse_line)
        self.label_collapse_line = label_collapse_line

        row_slash, self.sw_label_slash_wrap = self._create_toggle_row(
            "// 기호 씌우기", default_checked=False
        )
        self.sw_label_slash_wrap.setToolTip("ON이면 라벨을 /a/ 형태로 표시합니다.")
        label_collapse_content_layout.addLayout(row_slash)
        self.label_collapse_content = label_collapse_content

        def toggle_label():
            visible = not self.label_collapse_content.isVisible()
            self.label_collapse_content.setVisible(visible)
            self.label_toggle_btn.setText("▶" if not visible else "▼")

        self.label_toggle_btn.clicked.connect(toggle_label)
        label_header_row.mousePressEvent = lambda e: toggle_label()
        self.label_collapse_content.setVisible(False)
        self.label_toggle_btn.setText("▶")
        label_group.addWidget(label_collapse_content)

        layout.addLayout(label_group)
        self._add_separator(layout)

        # ==========================================
        # 3. 신뢰 타원 (Confidence Ellipse)
        # ==========================================
        ell_group = QVBoxLayout()
        ell_group.setSpacing(12)
        ell_group.addWidget(QLabel("신뢰 타원", font=font_bold))

        ell_group.addWidget(QLabel("타원 선 타입:", font=font_normal))
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
        ell_type_row = QVBoxLayout()
        ell_type_row.setSpacing(4)
        ell_type_row.addWidget(thick_frame)
        ell_type_row.addWidget(style_frame)
        ell_group.addLayout(ell_type_row)

        ell_line_color_layout = QVBoxLayout()
        ell_line_color_layout.setSpacing(6)
        ell_line_color_layout.addWidget(QLabel("타원 선 색상:", font=font_normal))
        self.ell_line_picker = ColorPalette(
            default_color="#606060", allow_transparent=True, parent=self
        )
        ell_line_color_layout.addWidget(self.ell_line_picker)
        ell_group.addLayout(ell_line_color_layout)

        ell_fill_color_layout = QVBoxLayout()
        ell_fill_color_layout.setSpacing(6)
        ell_fill_color_layout.addWidget(QLabel("타원 내부 색상:", font=font_normal))
        self.ell_fill_picker = ColorPalette(
            default_color="transparent", allow_transparent=True, parent=self
        )
        ell_fill_color_layout.addWidget(self.ell_fill_picker)
        ell_group.addLayout(ell_fill_color_layout)

        layout.addLayout(ell_group)
        self._add_separator(layout)

        # ==========================================
        # 4. 그래프 배경 (Graph Background) — "그래프 배경" 옆에 ▼, 접는 영역 위에 구분선
        # ==========================================
        graph_group = QVBoxLayout()
        graph_group.setSpacing(10)
        # 제목 행: "그래프 배경" 텍스트 바로 옆에 ▼
        graph_header_row = QWidget()
        graph_header_row.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        graph_header_layout = QHBoxLayout(graph_header_row)
        graph_header_layout.setContentsMargins(0, 0, 0, 0)
        graph_header_layout.setSpacing(4)
        graph_title_lbl = QLabel("그래프 배경", font=font_bold)
        graph_header_layout.addWidget(graph_title_lbl)
        self.graph_bg_toggle_btn = QPushButton("▼")
        self.graph_bg_toggle_btn.setFixedSize(28, 24)
        self.graph_bg_toggle_btn.setFlat(True)
        self.graph_bg_toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.graph_bg_toggle_btn.setStyleSheet(
            "QPushButton { color: #606266; font-size: 11px; }"
        )
        graph_header_layout.addWidget(self.graph_bg_toggle_btn)
        graph_header_layout.addStretch()
        graph_group.addWidget(graph_header_row)

        # 항상 보이는 3개: 사방 테두리, 배경 실선(Grid), Y축 라벨 눕히기
        row5, self.sw_box_spines = self._create_toggle_row(
            "사방 테두리", default_checked=False
        )
        row6, self.sw_show_grid = self._create_toggle_row(
            "배경 실선(Grid)", default_checked=False
        )
        row_y_rot, self.sw_y_label_rotation = self._create_toggle_row(
            "Y축 라벨 눕히기", default_checked=False
        )
        self.sw_y_label_rotation.setToolTip(
            "Y축(F1 등) 글자를 90도 눕혀 표시합니다. 끄면 똑바로 세웁니다."
        )
        graph_group.addLayout(row5)
        graph_group.addLayout(row6)
        graph_group.addLayout(row_y_rot)

        # 접었을 때 숨겨지는 영역 위 얇은 구분선 + 펼치면 보이는 3개
        graph_collapse_line = QFrame()
        graph_collapse_line.setFrameShape(QFrame.Shape.HLine)
        graph_collapse_line.setStyleSheet("color: #EBEEF5;")
        graph_collapse_line.setFixedHeight(1)
        graph_group.addWidget(graph_collapse_line)
        self.graph_bg_collapse_line = graph_collapse_line

        graph_content = QWidget()
        graph_content_layout = QVBoxLayout(graph_content)
        graph_content_layout.setContentsMargins(0, 4, 0, 0)
        graph_content_layout.setSpacing(10)

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
            "축·눈금 위치 반전", default_checked=False
        )
        self.sw_axis_position_swap.setToolTip(
            "Praat에서 아래/왼쪽, 수학에서 위/오른쪽에 축과 눈금을 표시합니다."
        )
        graph_content_layout.addLayout(row_unit)
        graph_content_layout.addLayout(row_minor)
        graph_content_layout.addLayout(row_axis)
        self.graph_bg_content = graph_content

        def toggle_graph_bg():
            visible = not self.graph_bg_content.isVisible()
            self.graph_bg_content.setVisible(visible)
            self.graph_bg_collapse_line.setVisible(visible)
            self.graph_bg_toggle_btn.setText("▶" if not visible else "▼")

        self.graph_bg_toggle_btn.clicked.connect(toggle_graph_bg)
        graph_header_row.mousePressEvent = lambda e: toggle_graph_bg()

        self.graph_bg_content.setVisible(False)
        self.graph_bg_collapse_line.setVisible(False)
        self.graph_bg_toggle_btn.setText("▶")

        graph_group.addWidget(graph_content)
        layout.addLayout(graph_group)
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
            QPushButton {
                background-color: #F4F4F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #909399;
            }
            QPushButton:checked {
                background-color: #ECF5FF; border: 1px solid #409EFF; color: #409EFF;
            }
            QPushButton:hover:!checked { background-color: #E4E7ED; color: #606266; }
        """)

        self.btn_reset = QPushButton("초기화")
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
        self.ell_line_picker.color_changed.connect(self._on_setting_changed)
        self.ell_fill_picker.color_changed.connect(self._on_setting_changed)

    def _on_setting_changed(self, *args):
        if self._is_loading:
            return
        self.settings_changed.emit(self.get_current_settings())

    def _reset_to_defaults(self):
        self._is_loading = True

        self.sw_show_raw.setChecked(True)
        self.sw_show_centroid.setChecked(True)
        self.sw_show_axis_units.setChecked(False)

        self.lbl_color_picker.set_color("#E64A19")
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

        self.sw_axis_position_swap.setChecked(False)
        self.sw_y_label_rotation.setChecked(False)
        self.sw_box_spines.setChecked(False)
        self.sw_show_grid.setChecked(False)
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
            "font_style": font_style,
            "lbl_color": self.lbl_color_picker.current_color,
            "lbl_size": int(self.combo_lbl_size.currentText()),
            "lbl_bold": self.btn_bold.isChecked(),
            "lbl_italic": self.btn_italic.isChecked(),
            "ell_thick": thick_map.get(self.group_ell_thick.checkedId(), 1.0),
            "ell_style": style_map.get(self.group_ell_style.checkedId(), "--"),
            "ell_color": line_color if line_color != "transparent" else None,
            "ell_fill_color": fill_color if fill_color != "transparent" else None,
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

    settings_changed = pyqtSignal(dict)
    label_move_clicked = pyqtSignal(str)  # 'blue' | 'red'

    def __init__(
        self,
        name_blue="기준 데이터",
        name_red="비교 데이터",
        parent=None,
        ui_font_name="Malgun Gothic",
        is_normalized=False,
    ):
        super().__init__(parent)
        self.ui_font_name = ui_font_name
        self.name_blue = name_blue
        self.name_red = name_red
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
        group = QButtonGroup(self)
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
            group.addButton(btn, i)
            layout.addWidget(btn)

        group.button(default_idx).setChecked(True)
        return frame, group

    def _build_individual_tab(self, default_color, default_style_str, series):
        """서브 탭 내부에 들어갈 개별 디자인 요소 팩토리. series: 'blue' | 'red'. default_style_str: '-', '--', '---'."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(0, 15, 0, 10)
        layout.setSpacing(18)
        font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        font_normal = QFont(self.ui_font_name, 9)

        # 0. 데이터 범례 (현재 탭 파일명)
        file_name = self.name_blue if series == "blue" else self.name_red
        clean_name = os.path.splitext(file_name)[0]
        display_name = truncate_display_name(clean_name, MAX_DISPLAY_NAME_LEN)
        legend_row = QHBoxLayout()
        legend_row.setContentsMargins(0, 0, 0, 8)
        legend_row.setSpacing(6)
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(50, 16)
        icon_lbl.setPixmap(create_legend_icon_design(default_color, default_style_str))
        lbl_a = QLabel("a")
        lbl_a.setFont(font_bold)
        lbl_a.setStyleSheet(f"color: {default_color};")
        lbl_name = QLabel(display_name)
        lbl_name.setFont(font_normal)
        lbl_name.setStyleSheet("color: #333333;")
        lbl_name.setToolTip(clean_name)
        lbl_name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        legend_row.addWidget(icon_lbl)
        legend_row.addWidget(lbl_a)
        legend_row.addSpacing(8)
        legend_row.addWidget(lbl_name, stretch=1)
        layout.addLayout(legend_row)

        # 1. 라벨과 중심점 설정
        lbl_group = QVBoxLayout()
        lbl_group.setSpacing(14)
        lbl_group.addWidget(QLabel("라벨과 중심점", font=font_bold))

        btn_label_move = QPushButton("라벨 위치 이동 (T)")
        btn_label_move.setCheckable(True)
        btn_label_move.setFixedHeight(32)
        btn_label_move.setFont(font_normal)
        btn_label_move.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_label_move.setStyleSheet("""
            QPushButton { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #333; }
            QPushButton:checked { background-color: #E6A23C; color: white; font-weight: bold; border: none; }
        """)
        btn_label_move.clicked.connect(lambda: self.label_move_clicked.emit(series))
        lbl_group.addWidget(btn_label_move)
        lbl_group.addSpacing(4)

        color_layout = QVBoxLayout()
        color_layout.setSpacing(6)
        color_layout.addWidget(QLabel("라벨 텍스트 색상:", font=font_normal))
        lbl_color_picker = ColorPalette(
            default_color=default_color, allow_transparent=True, parent=self
        )
        color_layout.addWidget(lbl_color_picker)
        lbl_group.addLayout(color_layout)
        lbl_group.addSpacing(4)

        font_style_layout = QHBoxLayout()
        font_style_layout.addWidget(QLabel("폰트:", font=font_normal))

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

        font_style_layout.addWidget(btn_bold)
        font_style_layout.addWidget(btn_italic)
        font_style_layout.addStretch()

        lbl_group.addLayout(font_style_layout)

        centroid_marker_layout = QVBoxLayout()
        centroid_marker_layout.setSpacing(4)
        lbl_centroid = QLabel("모음 중심점 모양:", font=font_normal)
        lbl_centroid.setMinimumWidth(140)
        centroid_marker_layout.addWidget(lbl_centroid)
        centroid_row = QHBoxLayout()
        centroid_row.setSpacing(0)
        centroid_row.addStretch()
        group_centroid_marker = QButtonGroup(self)
        for i, (mk, tip) in enumerate(
            [
                ("o", "동그라미"),
                ("s", "사각형"),
                ("^", "삼각형"),
                ("D", "다이아몬드"),
                ("wo", "동그라미(흰색)"),
                ("ws", "사각형(흰색)"),
                ("w^", "삼각형(흰색)"),
                ("wD", "다이아몬드(흰색)"),
            ]
        ):
            btn = MarkerShapeButton(mk, tooltip=tip)
            group_centroid_marker.addButton(btn, i)
            centroid_row.addWidget(btn)
        centroid_row.addStretch()
        centroid_marker_layout.addLayout(centroid_row)
        group_centroid_marker.button(0).setChecked(True)
        lbl_group.addLayout(centroid_marker_layout)

        layout.addLayout(lbl_group)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #EBEEF5;")
        layout.addWidget(line)

        # 2. 신뢰 타원 설정
        ell_group = QVBoxLayout()
        ell_group.setSpacing(12)
        ell_group.addWidget(QLabel("신뢰 타원", font=font_bold))

        ell_group.addWidget(QLabel("타원 선 타입:", font=font_normal))
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
        ell_type_row = QVBoxLayout()
        ell_type_row.setSpacing(4)
        ell_type_row.addWidget(thick_frame)
        ell_type_row.addWidget(style_frame)
        ell_group.addLayout(ell_type_row)

        ell_line_color_layout = QVBoxLayout()
        ell_line_color_layout.setSpacing(6)
        ell_line_color_layout.addWidget(QLabel("타원 선 색상:", font=font_normal))
        ell_line_picker = ColorPalette(
            default_color=default_color, allow_transparent=True, parent=self
        )
        ell_line_color_layout.addWidget(ell_line_picker)
        ell_group.addLayout(ell_line_color_layout)

        ell_fill_color_layout = QVBoxLayout()
        ell_fill_color_layout.setSpacing(6)
        ell_fill_color_layout.addWidget(QLabel("타원 내부 색상:", font=font_normal))
        ell_fill_picker = ColorPalette(
            default_color="transparent", allow_transparent=True, parent=self
        )
        ell_fill_color_layout.addWidget(ell_fill_picker)
        ell_group.addLayout(ell_fill_color_layout)

        layout.addLayout(ell_group)
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
                "#1976D2" if series == "blue" else "#E64A19"
            )
            if ell_color == "transparent":
                ell_color = "#1976D2" if series == "blue" else "#E64A19"
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
        data_group = QVBoxLayout()
        data_group.setSpacing(10)
        data_group.addWidget(QLabel("데이터 표시", font=font_bold))
        row1, self.sw_show_raw = self._create_toggle_row("데이터 포인트")
        row2, self.sw_show_centroid = self._create_toggle_row("모음 중심점(Centroid)")
        row3, self.sw_label_slash_wrap_cmp = self._create_toggle_row(
            "라벨에 // 기호 씌우기", default_checked=False
        )
        self.sw_label_slash_wrap_cmp.setToolTip("ON이면 라벨을 /a/ 형태로 표시합니다.")
        data_group.addLayout(row1)
        data_group.addLayout(row2)
        data_group.addLayout(row3)
        layout.addLayout(data_group)
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color: #EBEEF5;")
        layout.addWidget(line1)

    def _setup_compare_style_section(self, layout, font_bold):
        """CompareDesignSettingsPanel: 스타일(폰트·데이터 포인트) 구역."""
        style_group = QVBoxLayout()
        style_group.setSpacing(8)
        style_group.addWidget(QLabel("스타일", font=font_bold))
        font_style_row = QHBoxLayout()
        font_style_row.setSpacing(4)
        lbl_font_style_c = QLabel(
            "폰트 스타일:", font=QFont(self.ui_font_name, config.FONT_SIZE_SMALL)
        )
        lbl_font_style_c.setMinimumWidth(95)
        font_style_row.addWidget(lbl_font_style_c)
        btn_style = """
            QPushButton { background-color: transparent; border: 1px solid transparent; border-radius: 4px; }
            QPushButton:hover { background-color: #F5F7FA; }
            QPushButton:checked { background-color: #E4E7ED; border: 1px solid #C0C4CC; }
        """
        self.group_font_style_common = QButtonGroup(self)
        btn_serif = QPushButton("")
        btn_serif.setCheckable(True)
        btn_serif.setChecked(True)
        btn_serif.setFixedSize(40, 26)
        btn_serif.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_serif.setStyleSheet(btn_style)
        btn_serif.setIcon(create_font_style_icon(is_serif=True))
        btn_serif.setIconSize(QPixmap(40, 26).size())
        btn_serif.setToolTip("명조(세리프)")
        self.group_font_style_common.addButton(btn_serif, 0)
        btn_sans = QPushButton("")
        btn_sans.setCheckable(True)
        btn_sans.setFixedSize(40, 26)
        btn_sans.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_sans.setStyleSheet(btn_style)
        btn_sans.setIcon(create_font_style_icon(is_serif=False))
        btn_sans.setIconSize(QPixmap(40, 26).size())
        btn_sans.setToolTip("고딕(산세리프)")
        self.group_font_style_common.addButton(btn_sans, 1)
        font_style_row.addWidget(btn_serif)
        font_style_row.addWidget(btn_sans)
        font_style_row.addStretch()
        style_group.addLayout(font_style_row)
        dp_shape_row = QHBoxLayout()
        dp_shape_row.setSpacing(4)
        lbl_dp_c = QLabel(
            "데이터 포인트:", font=QFont(self.ui_font_name, config.FONT_SIZE_SMALL)
        )
        lbl_dp_c.setMinimumWidth(95)
        dp_shape_row.addWidget(lbl_dp_c)
        self.group_raw_marker_common = QButtonGroup(self)
        for i, (key, tip) in enumerate(
            [("o", "빈 원"), ("x", "x 모양"), ("a", "라벨 문자(모음 기호)")]
        ):
            btn = QPushButton("")
            btn.setCheckable(True)
            btn.setProperty("val", key)
            btn.setFixedSize(32, 26)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(btn_style)
            btn.setIcon(create_raw_marker_icon(key))
            btn.setIconSize(QPixmap(24, 24).size())
            btn.setToolTip(tip)
            if key == "o":
                btn.setChecked(True)
            self.group_raw_marker_common.addButton(btn, i)
            dp_shape_row.addWidget(btn)
        dp_shape_row.addStretch()
        style_group.addLayout(dp_shape_row)
        layout.addLayout(style_group)
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #EBEEF5;")
        layout.addWidget(line2)

    def _setup_compare_graph_background_section(self, layout, font_bold):
        """CompareDesignSettingsPanel: 그래프 배경(접기·토글) 구역."""
        graph_group = QVBoxLayout()
        graph_group.setSpacing(10)
        graph_header_row = QWidget()
        graph_header_row.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        graph_header_layout = QHBoxLayout(graph_header_row)
        graph_header_layout.setContentsMargins(0, 0, 0, 0)
        graph_header_layout.setSpacing(4)
        graph_title_lbl = QLabel("그래프 배경", font=font_bold)
        graph_header_layout.addWidget(graph_title_lbl)
        self.graph_bg_toggle_btn = QPushButton("▼")
        self.graph_bg_toggle_btn.setFixedSize(28, 24)
        self.graph_bg_toggle_btn.setFlat(True)
        self.graph_bg_toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.graph_bg_toggle_btn.setStyleSheet(
            "QPushButton { color: #606266; font-size: 11px; }"
        )
        graph_header_layout.addWidget(self.graph_bg_toggle_btn)
        graph_header_layout.addStretch()
        graph_group.addWidget(graph_header_row)
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
        graph_group.addLayout(row3)
        graph_group.addLayout(row4)
        graph_group.addLayout(row_y_rot)
        graph_collapse_line = QFrame()
        graph_collapse_line.setFrameShape(QFrame.Shape.HLine)
        graph_collapse_line.setStyleSheet("color: #EBEEF5;")
        graph_collapse_line.setFixedHeight(1)
        graph_group.addWidget(graph_collapse_line)
        self.graph_bg_collapse_line = graph_collapse_line
        graph_content_cmp = QWidget()
        graph_content_cmp_layout = QVBoxLayout(graph_content_cmp)
        graph_content_cmp_layout.setContentsMargins(0, 4, 0, 0)
        graph_content_cmp_layout.setSpacing(10)
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
        graph_content_cmp_layout.addWidget(self.axis_units_row_widget)
        graph_content_cmp_layout.addLayout(row_minor)
        graph_content_cmp_layout.addWidget(self.axis_position_swap_row_widget)
        self.graph_bg_content = graph_content_cmp
        self.graph_bg_toggle_btn.clicked.connect(self._on_graph_bg_toggle_clicked)
        graph_header_row.mousePressEvent = lambda e: self._on_graph_header_pressed(e)
        self.graph_bg_content.setVisible(False)
        self.graph_bg_collapse_line.setVisible(False)
        self.graph_bg_toggle_btn.setText("▶")
        graph_group.addWidget(graph_content_cmp)
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
        layout.addLayout(graph_group)

    def _on_graph_bg_toggle_clicked(self):
        visible = not self.graph_bg_content.isVisible()
        self.graph_bg_content.setVisible(visible)
        self.graph_bg_collapse_line.setVisible(visible)
        self.graph_bg_toggle_btn.setText("▶" if not visible else "▼")

    def _on_graph_header_pressed(self, e):
        self._on_graph_bg_toggle_clicked()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; }")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("QWidget { background-color: white; }")
        scroll_content.setMaximumWidth(260)
        scroll_content.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(*lc.MARGIN_DOCK_CONTENTS)
        layout.setSpacing(14)
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

        # Blue (기준) 탭: 텍스트 및 선 디폴트 Blue(#1976D2), 실선('-')
        self.tab_blue, self.ctrl_blue = self._build_individual_tab(
            "#1976D2", "-", "blue"
        )
        # Red (비교) 탭: 텍스트 및 선 디폴트 Red(#E64A19), 긴 점선('---')
        self.tab_red, self.ctrl_red = self._build_individual_tab(
            "#E64A19", "---", "red"
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
            ctrl["ell_fill_picker"].color_changed.connect(self._on_setting_changed)
        self.ctrl_blue["ell_line_picker"].color_changed.connect(
            self._update_compare_tab_text_colors
        )
        self.ctrl_red["ell_line_picker"].color_changed.connect(
            self._update_compare_tab_text_colors
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
            0, to_qcolor(self.ctrl_blue["ell_line_picker"].current_color, "#1976D2")
        )
        bar.setTabTextColor(
            1, to_qcolor(self.ctrl_red["ell_line_picker"].current_color, "#E64A19")
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
        self.ctrl_blue["lbl_color_picker"].set_color("#1976D2")
        self.ctrl_blue["combo_lbl_size"].setCurrentText("20")
        self.ctrl_blue["btn_bold"].setChecked(True)
        self.ctrl_blue["btn_italic"].setChecked(False)
        self.ctrl_blue["group_centroid_marker"].button(0).setChecked(True)
        self.ctrl_blue["group_ell_thick"].button(1).setChecked(True)
        self.ctrl_blue["group_ell_style"].button(0).setChecked(True)  # 실선
        self.ctrl_blue["ell_line_picker"].set_color("#1976D2")
        self.ctrl_blue["ell_fill_picker"].set_color("transparent")

        # Red 초기화
        self.ctrl_red["lbl_color_picker"].set_color("#E64A19")
        self.ctrl_red["combo_lbl_size"].setCurrentText("20")
        self.ctrl_red["btn_bold"].setChecked(True)
        self.ctrl_red["btn_italic"].setChecked(False)
        self.ctrl_red["group_centroid_marker"].button(0).setChecked(True)
        self.ctrl_red["group_ell_thick"].button(1).setChecked(True)
        self.ctrl_red["group_ell_style"].button(1).setChecked(True)  # 긴 점선
        self.ctrl_red["ell_line_picker"].set_color("#E64A19")
        self.ctrl_red["ell_fill_picker"].set_color("transparent")

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
        }

    def get_current_settings(self):
        font_style = (
            "serif" if self.group_font_style_common.checkedId() == 0 else "sans"
        )
        raw_marker_id = self.group_raw_marker_common.checkedId()
        raw_marker = ["o", "x", "a"][raw_marker_id] if 0 <= raw_marker_id <= 2 else "o"
        return {
            "common": {
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
            "blue": self._parse_individual_settings(self.ctrl_blue),
            "red": self._parse_individual_settings(self.ctrl_red),
        }
