# ui/layer_dock.py — 레이어 설정 도크 내부 위젯 (단일 플롯 전용)
#
# compare_plot 이식 시 재사용할 로직 정리:
# - 상태 접근: _get_current_filter_state() / _set_filter_state(state) 로만 읽기·쓰기.
# - 표시 순서: _get_ordered_vowels_for_display(vowels) 에서 popup.layer_order 사용. compare 시 탭별로 동일 구조 확장 가능.
# - 전체 한 줄: _build_global_row() 는 눈/반투명만 사용, 동일 규칙(눈=전체 끄기/켜기, 반투명=전체 반투명/해제).
# - 순서 변경: _on_layer_reorder(dragged, target, after) 로 저장 후 set_vowels(ordered). 삽입 위치 미리 보기는 _set_drop_indicator_between / _hide_drop_indicator.

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QTabWidget,
    QButtonGroup,
    QSizePolicy,
    QApplication,
    QSplitter,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QEvent,
    QObject,
)
from PySide6.QtGui import QFont, QFontMetrics

import config
import app_logger
from ui.widgets.layer_logic import (
    apply_global_eye,
    apply_global_semi,
    apply_line_settings,
    apply_polygon_settings,
    apply_reference_settings,
    rebuild_area_labels_for_polygons,
    toggle_item_visibility,
    compute_order_after_drop,
    get_children_indices,
)
from ui.widgets.design_panel import ColorPalette
from ui.widgets.draw_design_panel import DrawDesignPanel
from ui.widgets.layer_data_model import LayerDataModel
from ui.widgets.label_manager import LabelManager
from ui.widgets.draw_manager import DrawManager
from ui.widgets.layer_row_widgets import (
    _RowClickForwarder,
    _LayerRowFrame,
    _DrawLayerRowFrame,
)
from ui.widgets.tab_label_view import create_label_tab
from ui.widgets.tab_draw_view import create_draw_tab
from ui.widgets.icon_widgets import (
    LinePreviewButton,
    MarkerShapeButton,
    LayerEyeButton,
    LayerLockButton,
)
from utils.vowel_sorting import get_vowel_sort_key
import ui.widgets.layout_constants as lc
from draw.draw_common import polygon_area


# design_panel과 동일 매핑. 검은색 4종 + 흰색 채움·검은 외곽선 4종
MARKER_IDS = {"o": 0, "s": 1, "^": 2, "D": 3, "wo": 4, "ws": 5, "w^": 6, "wD": 7}
MARKER_VALS = ["o", "s", "^", "D", "wo", "ws", "w^", "wD"]
MARKER_LABELS = {
    "o": "원",
    "s": "사각형",
    "^": "삼각형",
    "D": "다이아몬드",
    "wo": "원(흰색)",
    "ws": "사각형(흰색)",
    "w^": "삼각형(흰색)",
    "wD": "다이아몬드(흰색)",
}
# 디자인 설정과 동일: 얇게=0.5, 보통=1.0, 두껍게=2.0
THICK_VALS = [0.5, 1.0, 2.0]
THICK_LABELS = {0.5: "얇게", 1.0: "보통", 2.0: "두껍게"}
# 실선 '-', 긴 점선 '---'(긴 대시), 짧은 점선 '--'(중간 대시, 기존 긴 점선에 나오던 모양)
STYLE_IDS = {"-": 0, "---": 1, "--": 2}
STYLE_VALS = ["-", "---", "--"]
STYLE_LABELS = {"-": "실선", "---": "긴 점선", "--": "짧은 점선"}

COLOR_NAMES = {
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


class TabBarWheelBlocker(QObject):
    """탭 위에서 마우스 휠로 탭이 바뀌지 않도록 휠 이벤트를 흡수합니다."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            return True
        return False


def _draw_object_display_name(draw_objects, index, normalization=None):
    """그리기 객체의 레이어 목록 표시명. 선 N : a-e-o, 영역 N : o-e-a-o, 참조선 X/Y=..."""
    if not draw_objects or index < 0 or index >= len(draw_objects):
        return ""
    obj = draw_objects[index]
    t = getattr(obj, "type", "")
    if t == "line":
        n = 1 + sum(
            1 for i in range(index) if getattr(draw_objects[i], "type", "") == "line"
        )
        labels = getattr(obj, "point_labels", None) or []
        s = getattr(obj, "series", None)
        if s in ("blue", "red"):
            suffix = "1" if s == "blue" else "2"
            norm_labels = []
            for lb in labels:
                t_lb = str(lb).strip()
                if t_lb in ("", "?"):
                    norm_labels.append(t_lb)
                elif t_lb.endswith("1") or t_lb.endswith("2"):
                    norm_labels.append(t_lb)
                else:
                    norm_labels.append(f"{t_lb}{suffix}")
            labels = norm_labels
        suffix = " : " + "-".join(labels) if labels else ""
        return f"선 {n}{suffix}"
    if t == "polygon":
        n = 1 + sum(
            1 for i in range(index) if getattr(draw_objects[i], "type", "") == "polygon"
        )
        labels = getattr(obj, "point_labels", None) or []
        s = getattr(obj, "series", None)
        if s in ("blue", "red"):
            suffix = "1" if s == "blue" else "2"
            norm_labels = []
            for lb in labels:
                t_lb = str(lb).strip()
                if t_lb in ("", "?"):
                    norm_labels.append(t_lb)
                elif t_lb.endswith("1") or t_lb.endswith("2"):
                    norm_labels.append(t_lb)
                else:
                    norm_labels.append(f"{t_lb}{suffix}")
            labels = norm_labels
        if labels:
            suffix = " : " + "-".join(labels) + "-" + labels[0]
        else:
            suffix = ""
        return f"영역 {n}{suffix}"
    if t == "reference":
        v = getattr(obj, "value", 0)  # 단위(Unit) 기준 순수 데이터 값
        axis_name = getattr(obj, "axis_name", None) or ""
        unit = (getattr(obj, "axis_units", "Hz") or "Hz").strip().lower()
        is_norm = unit == "norm" or "norm" in unit
        if not axis_name and getattr(obj, "mode", "") == "horizontal":
            axis_name = "nF1" if is_norm else "F1"
        if not axis_name:
            axis_name = "nF2" if is_norm else "F2"
        unit = (getattr(obj, "axis_units", "Hz") or "Hz").strip().lower()
        if unit == "norm" or "norm" in unit:
            if "gerstman" in str(normalization or "").strip().lower():
                s = f"{int(round(float(v)))}"
            else:
                s = f"{v:.2f}"
        elif unit in ("bk", "bark"):
            s = f"{v:.1f}"
        else:
            s = str(int(v))
        return f"참조선 : {axis_name}={s}"
    if t == "area_label":
        v = getattr(obj, "value", 0)
        unit = (getattr(obj, "axis_units", "Hz") or "Hz").strip().lower()
        if unit == "norm" or "norm" in unit:
            s = f"{v:.2f}"
        else:
            s = str(int(round(v)))
        return f"넓이 : {s}"
    return f"그리기 {index + 1}"


def _format_color_display(color_hex):
    if not color_hex or color_hex == "transparent":
        return "Transparent"
    key = color_hex if color_hex in COLOR_NAMES else color_hex.upper()
    name = COLOR_NAMES.get(key, "Custom Color")
    if name == "Custom Color":
        return f"Custom ({color_hex})"
    return f"{name} ({color_hex})"


def _create_visual_button_group(parent, options, default_idx):
    group = QButtonGroup(parent)
    frame = QFrame()
    frame.setStyleSheet(
        "QFrame { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; }"
    )
    row_layout = QHBoxLayout(frame)
    row_layout.setContentsMargins(2, 2, 2, 2)
    row_layout.setSpacing(0)
    for i, opt in enumerate(options):
        w, s, r, tooltip = opt[:4]
        dash = opt[4] if len(opt) > 4 else None
        btn = LinePreviewButton(
            line_width=w, line_style=s, radius_css=r, tooltip=tooltip, dash_pattern=dash
        )
        group.addButton(btn, i)
        row_layout.addWidget(btn)
    group.button(default_idx).setChecked(True)
    return frame, group


class LayerDockWidget(QWidget):
    filter_state_changed = Signal(dict)
    overrides_changed = Signal(dict)
    label_filter_item_changed = Signal(str, str)
    draw_item_state_changed = Signal(int, str, object)
    compare_switch_requested = Signal(
        int
    )  # compare 모드에서 파일 A(0)/B(1) 전환 요청
    splitter_sizes_changed = Signal(
        list
    )  # 다중플롯에서 두 도크 스플리터 비율 공유용
    order_changed = Signal(list)

    def __init__(
        self,
        parent_popup,
        ui_font_name="Malgun Gothic",
        state_key=None,
        compare_mode=False,
        file_a_name="",
        file_b_name="",
        get_default_design=None,
    ):
        """state_key: None=단일 플롯, 'blue'/'red'=compare_plot 쪽 탭별 상태. compare_mode 시 레이어 탭 내에 파일 선택 행 표시.
        get_default_design: compare_plot용. None이면 popup.design_settings 사용, callable이면 호출해 해당 시리즈(Blue/Red) 기본값 사용."""
        super().__init__(parent_popup)
        self.popup = parent_popup
        self.ui_font_name = ui_font_name
        self._state_key = state_key  # None | 'blue' | 'red'
        self._compare_mode = compare_mode
        self._file_a_name = file_a_name
        self._file_b_name = file_b_name
        self._get_default_design = get_default_design  # callable() -> dict | None
        self.label_manager = LabelManager(self.popup, state_key=self._state_key)
        self.draw_manager = DrawManager(self.popup)
        self.data_model = LayerDataModel(self.label_manager, self.draw_manager, self)

        # Connect internal signal to data_model (for backward compatibility if needed)
        self.data_model.filter_state_changed.connect(self.filter_state_changed.emit)
        self.data_model.layer_overrides_changed.connect(self.overrides_changed.emit)
        self.data_model.layer_order_changed.connect(self.order_changed.emit)
        self._selected_vowels = set()
        self._layer_rows = {}
        self._updating = False
        self._semi_memory = {}
        self._draw_design_settings = {}
        self._setup_ui()
        self.label_filter_item_changed.connect(self._on_label_filter_item_changed)
        self.draw_item_state_changed.connect(self._on_draw_item_state_changed)
        self._setup_drop_indicators()

    def _get_modifiers_from_arg(self, arg):
        """이벤트 포워더(arg=KeyboardModifier) 또는 직접 클릭(arg=bool/None)에서 모디파이어를 추출합니다."""
        if isinstance(arg, Qt.KeyboardModifier) or (isinstance(arg, int) and arg > 0):
            return arg
        return QApplication.keyboardModifiers()

    def _create_column_frame(self, width, height=32, has_border=True):
        """정해진 너비와 스타일을 가진 표 형식의 칸(Column) 프레임을 생성합니다."""
        col = QFrame()
        col.setFixedSize(width, height)
        if has_border:
            style = "background: transparent; border-right: 1px solid #E4E7ED; border-bottom: none; border-top: none; border-left: none;"
        else:
            style = "border: none; background: transparent;"
        col.setStyleSheet(style)
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        return col, layout

    def _setup_drop_indicators(self):
        """드래그 앤 드롭 시 삽입 위치를 표시할 오버레이 위젯 초기화."""
        # 1. 라벨 탭용 인디케이터
        if hasattr(self, "_layer_list_widget"):
            self._label_drop_indicator = QFrame(self._layer_list_widget)
            self._label_drop_indicator.setFixedHeight(2)
            self._label_drop_indicator.setStyleSheet(
                "background-color: #409EFF; border: none;"
            )
            self._label_drop_indicator.hide()
            self._label_drop_indicator.raise_()

        # 2. 그리기 탭용 인디케이터
        if hasattr(self, "_draw_list_placeholder"):
            self._draw_drop_indicator = QFrame(self._draw_list_placeholder)
            self._draw_drop_indicator.setFixedHeight(2)
            self._draw_drop_indicator.setStyleSheet(
                "background-color: #409EFF; border: none;"
            )
            self._draw_drop_indicator.hide()
            self._draw_drop_indicator.raise_()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        font_normal = QFont(self.ui_font_name, 9)
        font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)

        # 상단: 모음 레이어 디자인용 단일 컨테이너 (삭제/clear 없이 show/hide만 사용)
        self._design_scroll = QScrollArea()
        top_scroll = self._design_scroll
        top_scroll.setWidgetResizable(True)
        top_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        top_scroll.setFrameShape(QFrame.Shape.NoFrame)
        top_scroll.setStyleSheet("QScrollArea { background-color: #FFFFFF; }")
        self.vowel_design_container = QWidget()
        self.vowel_design_container.setStyleSheet(
            "QWidget { background-color: #FFFFFF; }"
        )
        top_layout = QVBoxLayout(self.vowel_design_container)
        top_layout.setContentsMargins(12, 12, 12, 12)
        top_layout.setSpacing(14)

        top_layout.addWidget(QLabel("라벨과 중심점", font=font_bold))
        color_layout = QVBoxLayout()
        color_layout.setSpacing(6)
        color_layout.addWidget(QLabel("라벨 텍스트 색상:", font=font_normal))
        self.lbl_color_picker = ColorPalette(
            default_color=config.COLOR_PRIMARY_RED,
            allow_transparent=True,
            parent=self.vowel_design_container,
        )
        color_layout.addWidget(self.lbl_color_picker)
        top_layout.addLayout(color_layout)
        centroid_layout = QVBoxLayout()
        centroid_layout.setSpacing(4)
        lbl_centroid = QLabel("모음 중심점 모양:", font=font_normal)
        lbl_centroid.setMinimumWidth(120)
        centroid_layout.addWidget(lbl_centroid)
        centroid_row = QHBoxLayout()
        centroid_row.setSpacing(0)
        centroid_row.addStretch()
        self.group_centroid_marker = QButtonGroup(self.vowel_design_container)
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
            centroid_row.addWidget(btn)
        centroid_row.addStretch()
        centroid_layout.addLayout(centroid_row)
        self.group_centroid_marker.button(0).setChecked(True)
        top_layout.addLayout(centroid_layout)

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color: #EBEEF5;")
        top_layout.addWidget(line1)

        top_layout.addWidget(QLabel("신뢰 타원", font=font_bold))
        thicks = [
            (1.0, Qt.PenStyle.SolidLine, "4px 0 0 4px", "얇게"),
            (2.0, Qt.PenStyle.SolidLine, "0px", "보통"),
            (3.5, Qt.PenStyle.SolidLine, "0 4px 4px 0", "두껍게"),
        ]
        thick_frame, self.group_ell_thick = _create_visual_button_group(
            self.vowel_design_container, thicks, 1
        )
        styles = [
            (2.0, Qt.PenStyle.SolidLine, "4px 0 0 4px", "실선"),
            (2.0, Qt.PenStyle.DashLine, "0px", "긴 점선"),
            (2.0, Qt.PenStyle.DotLine, "0 4px 4px 0", "짧은 점선"),
        ]
        style_frame, self.group_ell_style = _create_visual_button_group(
            self.vowel_design_container, styles, 2
        )
        ell_type_row = QVBoxLayout()
        ell_type_row.setSpacing(4)
        ell_type_row.addWidget(QLabel("타원 선 타입:", font=font_normal))
        ell_type_row.addWidget(thick_frame)
        ell_type_row.addWidget(style_frame)
        top_layout.addLayout(ell_type_row)
        ell_line_color_layout = QVBoxLayout()
        ell_line_color_layout.setSpacing(6)
        ell_line_color_layout.addWidget(QLabel("타원 선 색상:", font=font_normal))
        self.ell_color_picker = ColorPalette(
            default_color="#606060",
            allow_transparent=True,
            parent=self.vowel_design_container,
        )
        ell_line_color_layout.addWidget(self.ell_color_picker)
        top_layout.addLayout(ell_line_color_layout)
        ell_fill_layout = QVBoxLayout()
        ell_fill_layout.setSpacing(6)
        ell_fill_layout.addWidget(QLabel("타원 내부 색상:", font=font_normal))
        self.ell_fill_picker = ColorPalette(
            default_color="transparent",
            allow_transparent=True,
            parent=self.vowel_design_container,
        )
        ell_fill_layout.addWidget(self.ell_fill_picker)
        top_layout.addLayout(ell_fill_layout)

        top_layout.addStretch()

        # 상단 디자인 래퍼: 라벨/그리기 두 패널을 모두 포함
        self.top_design_wrapper = QWidget()
        self.top_design_wrapper.setStyleSheet("background-color: #FFFFFF;")
        top_wrapper_layout = QVBoxLayout(self.top_design_wrapper)
        top_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        top_wrapper_layout.setSpacing(0)

        # 래퍼에 라벨 디자인 패널 추가
        top_wrapper_layout.addWidget(self.vowel_design_container)

        # 래퍼에 그리기 디자인 패널 추가 (초기에는 숨김)
        self._draw_design_panel = DrawDesignPanel(
            parent=self, ui_font_name=self.ui_font_name
        )
        self._draw_design_panel.settings_changed.connect(
            self._on_draw_design_settings_changed
        )
        self._draw_design_panel.clear_selection()
        self._draw_design_panel.hide()
        top_wrapper_layout.addWidget(self._draw_design_panel)

        top_scroll.setWidget(self.top_design_wrapper)
        top_scroll.setMinimumHeight(80)

        self.tab_widget = QTabWidget()
        self.tab_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border-top: 1px solid #E4E7ED;
                background: #FFFFFF;
            }
            QTabBar::tab {
                background: #E4E7ED;
                border: 1px solid #DCDFE6;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: %dpx;
                padding: 6px 0px;
                color: #606266;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #303133;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #EBEEF5;
                color: #409EFF;
            }
        """
            % config.TAB_BAR_MIN_WIDTH_PX
        )
        layer_tab = create_label_tab(self)
        self.tab_widget.addTab(layer_tab, "라벨")
        self._tab_wheel_blocker = TabBarWheelBlocker(self)
        self.tab_widget.tabBar().installEventFilter(self._tab_wheel_blocker)

        draw_tab = create_draw_tab(self)
        self.tab_widget.addTab(draw_tab, "그리기")
        self.tab_widget.currentChanged.connect(self._on_layer_tab_index_changed)

        bottom_sep = QFrame()
        bottom_sep.setFrameShape(QFrame.Shape.HLine)
        bottom_sep.setFixedHeight(1)
        bottom_sep.setStyleSheet("background-color: #E4E7ED; margin: 0; border: none;")

        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(8, 4, 8, 4)
        reset_row.setSpacing(12)
        reset_row.addStretch()

        # 레이어 순서 초기화 버튼 (파일을 넘겨도 유지되는 전역 순서를 기본값으로 되돌림)
        self.btn_reset_order = QPushButton("순서 초기화")
        self.btn_reset_order.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_order.setStyleSheet(
            "QPushButton { background-color: #F5F7FA; border: 1px solid #DCDFE6; border-radius: 4px; color: #606266; padding: 4px 10px; }"
            "QPushButton:hover { background-color: #EBEEF5; }"
        )
        self.btn_reset_order.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_reset_order.clicked.connect(self._on_reset_order_clicked)
        reset_row.addWidget(self.btn_reset_order)

        self.btn_reset_layers = QPushButton("레이어 설정 초기화")
        self.btn_reset_layers.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_layers.setStyleSheet(
            "QPushButton { background-color: #F5F7FA; border: 1px solid #DCDFE6; border-radius: 4px; color: #606266; padding: 4px 10px; }"
            "QPushButton:hover { background-color: #EBEEF5; }"
        )
        self.btn_reset_layers.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_reset_layers.clicked.connect(self._on_reset_layers_clicked)
        reset_row.addWidget(self.btn_reset_layers)

        self.btn_batch_delete_draw = QPushButton("일괄 삭제")
        self.btn_batch_delete_draw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_delete_draw.setStyleSheet(
            "QPushButton { background-color: #F5F7FA; border: 1px solid #DCDFE6; border-radius: 4px; color: #606266; padding: 4px 10px; }"
            "QPushButton:hover { background-color: #FDE2E2; color: #E64A19; }"
        )
        self.btn_batch_delete_draw.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_batch_delete_draw.clicked.connect(self._on_batch_delete_draw_clicked)
        reset_row.addWidget(self.btn_batch_delete_draw)
        self.btn_batch_delete_draw.hide()

        lower_widget = QWidget()
        lower_layout = QVBoxLayout(lower_widget)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(0)
        lower_layout.addWidget(self.tab_widget, 1)
        lower_layout.addWidget(bottom_sep)
        lower_layout.addLayout(reset_row)
        lower_widget.setMinimumHeight(80)

        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.addWidget(top_scroll)
        self._splitter.addWidget(lower_widget)
        saved = getattr(self.popup, "layer_dock_splitter_sizes", None)
        if saved and len(saved) == 2 and all(s > 0 for s in saved):
            self._splitter.setSizes(list(saved))
        else:
            self._splitter.setSizes([lc.DOCK_WIDTH_PX, 400])

        def _on_splitter_moved():
            self.splitter_sizes_changed.emit(self._splitter.sizes())

        self._splitter.splitterMoved.connect(_on_splitter_moved)
        root_layout.addWidget(self._splitter)

        def make_apply(key, get_value):
            def apply():
                if self.tab_widget.currentIndex() != 0:
                    return
                if self._updating or not self._selected_vowels:
                    return
                overrides = self._get_layer_overrides()
                if not isinstance(overrides, dict):
                    overrides = {}
                val = get_value()
                for v in self._selected_vowels:
                    overrides.setdefault(v, {})
                    overrides[v][key] = val
                self._set_layer_overrides(overrides)
                self.overrides_changed.emit(overrides)
                self._rebuild_effects()

            return apply

        self.lbl_color_picker.color_changed.connect(
            make_apply("lbl_color", lambda: self.lbl_color_picker.current_color)
        )
        self.ell_color_picker.color_changed.connect(
            make_apply(
                "ell_color",
                lambda: (
                    self.ell_color_picker.current_color
                    if self.ell_color_picker.current_color != "transparent"
                    else None
                ),
            )
        )
        self.ell_fill_picker.color_changed.connect(
            make_apply(
                "ell_fill_color",
                lambda: (
                    self.ell_fill_picker.current_color
                    if self.ell_fill_picker.current_color != "transparent"
                    else None
                ),
            )
        )

        def on_centroid_toggled():
            if self._updating:
                return
            bid = self.group_centroid_marker.checkedId()
            if bid >= 0:
                make_apply("centroid_marker", lambda: MARKER_VALS[bid])()

        def on_ell_thick_toggled():
            if self._updating:
                return
            bid = self.group_ell_thick.checkedId()
            if bid >= 0:
                make_apply("ell_thick", lambda: THICK_VALS[bid])()

        def on_ell_style_toggled():
            if self._updating:
                return
            bid = self.group_ell_style.checkedId()
            if bid >= 0:
                make_apply("ell_style", lambda: STYLE_VALS[bid])()

        self.group_centroid_marker.buttonToggled.connect(on_centroid_toggled)
        self.group_ell_thick.buttonToggled.connect(on_ell_thick_toggled)
        self.group_ell_style.buttonToggled.connect(on_ell_style_toggled)

    def _get_current_filter_state(self):
        return self.data_model.get_filter_state()

    def _set_filter_state(self, state):
        self.data_model.set_filter_state(state)
        self._update_global_row_state()

    def _get_layer_overrides(self):
        return self.data_model.get_layer_overrides()

    def _set_layer_overrides(self, overrides):
        self.data_model.set_layer_overrides(overrides)

    def _on_label_filter_item_changed(self, vowel: str, new_state: str):
        """라벨 필터 델타 갱신: 단일 row 상태만 변경."""
        st = self._get_current_filter_state()
        st[vowel] = new_state
        self._set_filter_state(st)
        row = self._layer_rows.get(vowel)
        if row is not None:
            row.eye_btn.blockSignals(True)
            row.semi_btn.blockSignals(True)
            row.eye_btn.setChecked(new_state != "OFF")
            row.semi_btn.setChecked(new_state == "SEMI")
            row.eye_btn.blockSignals(False)
            row.semi_btn.blockSignals(False)

    def _get_draw_row_by_index(self, draw_index: int):
        rows = getattr(self, "_draw_layer_rows", None) or []
        for r in rows:
            if getattr(r, "draw_index", None) == draw_index:
                return r
        return None

    def _sync_draw_row_controls(self, draw_index: int, obj: object):
        row = self._get_draw_row_by_index(draw_index)
        if row is None:
            return
        if hasattr(row, "eye_btn"):
            row.eye_btn.blockSignals(True)
            row.eye_btn.setChecked(getattr(obj, "visible", True))
            row.eye_btn.blockSignals(False)
        if hasattr(row, "semi_btn"):
            row.semi_btn.blockSignals(True)
            row.semi_btn.setChecked(getattr(obj, "semi", False))
            row.semi_btn.blockSignals(False)
        if hasattr(row, "lock_btn"):
            row.lock_btn.blockSignals(True)
            row.lock_btn.setChecked(getattr(obj, "locked", False))
            row.lock_btn.blockSignals(False)

    def _on_draw_item_state_changed(self, draw_index: int, key: str, value: object):
        """그리기 단일 항목 델타 갱신: 전체 리스트 재구성 없이 row 단위로 동기화."""
        objs = self.draw_manager.get_draw_objects()
        if not (0 <= draw_index < len(objs)):
            return
        obj = objs[draw_index]
        if key not in ("visible", "semi", "locked"):
            return

        setattr(obj, key, value)

        # polygon의 area_label 자식은 부모 visible/semi/locked를 동기화한다.
        if getattr(obj, "type", "") == "polygon" and key in (
            "visible",
            "semi",
            "locked",
        ):
            for child_idx in get_children_indices(objs, draw_index):
                if 0 <= child_idx < len(objs):
                    setattr(objs[child_idx], key, value)
                    self._sync_draw_row_controls(child_idx, objs[child_idx])

        self.draw_manager.set_draw_objects(objs)
        self.draw_manager.redraw()
        self._sync_draw_row_controls(draw_index, obj)
        self._update_draw_global_row_state()

    def _build_global_row(self):
        """레이어 목록 위 한 줄: 전체 눈(가시성) + 전체 반투명만. 높이를 약간 낮게.
        - 눈: 클릭 시 모두 끄기. 모든 레이어가 꺼져 있으면 클릭 시 모두 켜기.
        - 반투명: 클릭 시 모두 반투명. 모두 반투명이면 클릭 시 반투명 해제.
        compare_plot 이식 시 동일 로직을 탭별로 재사용할 수 있도록 상태는 _get_current_filter_state/_set_filter_state로만 접근.
        """
        row = QFrame()
        row.setFixedHeight(26)
        # 아래쪽 1px 경계선만 사용해 다른 구분선과 동일한 두께로 보이도록 함
        row.setStyleSheet(
            "background-color: #F5F7FA; border-top: none; border-left: none; border-right: none; border-bottom: 1px solid #EBEEF5;"
        )
        main_h = QHBoxLayout(row)
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        col_eye = QFrame()
        col_eye.setFixedSize(32, 26)
        col_eye.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED;"
        )
        eye_layout = QVBoxLayout(col_eye)
        eye_layout.setContentsMargins(0, 0, 0, 0)
        eye_btn = LayerEyeButton()
        eye_btn.setFixedSize(32, 26)
        eye_layout.addWidget(eye_btn)
        main_h.addWidget(col_eye)

        col_semi = QFrame()
        col_semi.setFixedSize(54, 26)
        col_semi.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED;"
        )
        semi_layout = QVBoxLayout(col_semi)
        semi_layout.setContentsMargins(0, 0, 0, 0)
        semi_btn = QPushButton("반투명")
        semi_btn.setCheckable(True)
        semi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        semi_btn.setFixedHeight(22)
        semi_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; color: #C0C4CC; font-size: 11px; }
            QPushButton:checked { color: #409EFF; font-weight: bold; }
            QPushButton:hover { color: #66B1FF; }
        """)
        semi_layout.addWidget(semi_btn)
        main_h.addWidget(col_semi)

        main_h.addStretch()

        def on_global_eye_clicked():
            st = self._get_current_filter_state()
            vowels = list(self._layer_rows.keys())
            if not vowels:
                return
            all_off = all(st.get(v) == "OFF" for v in vowels)
            new_st = apply_global_eye(st, vowels, turn_on=all_off)
            self._updating = True
            try:
                self._set_filter_state(new_st)
                for v in vowels:
                    self._layer_rows[v].eye_btn.blockSignals(True)
                    self._layer_rows[v].eye_btn.setChecked(new_st.get(v) != "OFF")
                    self._layer_rows[v].eye_btn.blockSignals(False)
            finally:
                self._updating = False
            self._update_global_row_state()

        def on_global_semi_clicked():
            st = self._get_current_filter_state()
            vowels = list(self._layer_rows.keys())
            if not vowels:
                return
            all_semi = all(
                self._layer_rows[v].semi_btn.isChecked() and st.get(v) != "OFF"
                for v in vowels
            )
            new_st = apply_global_semi(st, vowels, semi=not all_semi)
            self._updating = True
            try:
                for v in vowels:
                    self._layer_rows[v].semi_btn.blockSignals(True)
                    self._layer_rows[v].semi_btn.setChecked(new_st.get(v) == "SEMI")
                    self._layer_rows[v].semi_btn.blockSignals(False)
                    self._semi_memory[v] = new_st.get(v) == "SEMI"
                self._set_filter_state(new_st)
            finally:
                self._updating = False
            self._update_global_row_state()

        eye_btn.clicked.connect(on_global_eye_clicked)
        semi_btn.clicked.connect(on_global_semi_clicked)
        row.eye_btn = eye_btn
        row.semi_btn = semi_btn
        return row

    def _build_draw_global_row(self):
        """그리기 탭용 일괄 눈/반투명 행. 레이어 탭과 동일한 외형, 목록 비어 있으면 no-op."""
        row = QFrame()
        row.setFixedHeight(26)
        row.setStyleSheet(
            "background-color: #F5F7FA; border-top: none; border-left: none; border-right: none; border-bottom: 1px solid #EBEEF5;"
        )
        main_h = QHBoxLayout(row)
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        col_eye = QFrame()
        col_eye.setFixedSize(32, 26)
        col_eye.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED;"
        )
        eye_layout = QVBoxLayout(col_eye)
        eye_layout.setContentsMargins(0, 0, 0, 0)
        eye_btn = LayerEyeButton()
        eye_btn.setFixedSize(32, 26)
        eye_btn.setChecked(True)
        eye_layout.addWidget(eye_btn)
        main_h.addWidget(col_eye)

        col_semi = QFrame()
        col_semi.setFixedSize(54, 26)
        col_semi.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED;"
        )
        semi_layout = QVBoxLayout(col_semi)
        semi_layout.setContentsMargins(0, 0, 0, 0)
        semi_btn = QPushButton("반투명")
        semi_btn.setCheckable(True)
        semi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        semi_btn.setFixedHeight(22)
        semi_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; color: #C0C4CC; font-size: 11px; }
            QPushButton:checked { color: #409EFF; font-weight: bold; }
            QPushButton:hover { color: #66B1FF; }
        """)
        semi_layout.addWidget(semi_btn)
        main_h.addWidget(col_semi)

        main_h.addStretch()

        def on_eye():
            rows = getattr(self, "_draw_layer_rows", None) or []
            objs = self.draw_manager.get_draw_objects()
            if not rows or not objs:
                return
            n = min(len(objs), len(rows))
            all_off = all(not getattr(objs[i], "visible", True) for i in range(n))
            # all_off == True  → 모두 꺼져 있었으므로 이번엔 모두 켜기(True)
            # all_off == False → 하나라도 켜져 있었으므로 이번엔 모두 끄기(False)
            for i in range(n):
                objs[i].visible = all_off
            for i in range(n):
                r = rows[i]
                if hasattr(r, "eye_btn"):
                    r.eye_btn.blockSignals(True)
                    r.eye_btn.setChecked(objs[i].visible)
                    r.eye_btn.blockSignals(False)
            self.draw_manager.set_draw_objects(objs)
            self.draw_manager.redraw()
            self._update_draw_global_row_state()

        def on_semi():
            rows = getattr(self, "_draw_layer_rows", None) or []
            objs = self.draw_manager.get_draw_objects()
            if not rows or not objs:
                return
            n = min(len(objs), len(rows))
            all_semi = all(getattr(objs[i], "semi", False) for i in range(n))
            for i in range(n):
                objs[i].semi = not all_semi
            for i in range(n):
                r = rows[i]
                if hasattr(r, "semi_btn"):
                    r.semi_btn.blockSignals(True)
                    r.semi_btn.setChecked(objs[i].semi)
                    r.semi_btn.blockSignals(False)
            self.draw_manager.set_draw_objects(objs)
            self.draw_manager.redraw()
            self._update_draw_global_row_state()

        eye_btn.clicked.connect(on_eye)
        semi_btn.clicked.connect(on_semi)
        row.eye_btn = eye_btn
        row.semi_btn = semi_btn
        return row

    def _build_draw_layer_row(self, draw_index, obj, draw_objects):
        """그리기 레이어 한 행. 라벨 행과 동일 구조: 눈(32), 반투명(54), 이름, X(삭제)(32), 잠금(32).
        draw_index: draw_objects 상의 인덱스. area_label도 행으로 만들고, 이름에 ↳를 붙이고 expand_btn을 숨김."""
        row = _DrawLayerRowFrame(self, draw_index)
        row.setProperty("drawRow", True)
        row.setProperty("drawIndex", draw_index)
        row.setProperty(
            "selected", draw_index in getattr(self, "_selected_draw_indices", set())
        )
        row.setStyleSheet("""
            QFrame[drawRow="true"] {
                background-color: transparent;
                border-bottom: 1px solid #EBEEF5;
            }
            QFrame[drawRow="true"]:hover { background-color: #F5F7FA; }
            QFrame[drawRow="true"][selected="true"] {
                background-color: #E6F0F9;
            }
        """)
        row_vbox = QVBoxLayout(row)
        row_vbox.setContentsMargins(0, 0, 0, 0)
        row_vbox.setSpacing(0)
        main_h = QHBoxLayout()
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        # 1. 눈 (Eye) 열
        col_eye, eye_layout = self._create_column_frame(32)
        eye_btn = LayerEyeButton()
        eye_btn.setChecked(getattr(obj, "visible", True))
        eye_layout.addWidget(eye_btn)
        main_h.addWidget(col_eye)

        # 2. 반투명 (Semi) 열
        col_semi, semi_layout = self._create_column_frame(54)
        semi_btn = QPushButton("반투명")
        semi_btn.setCheckable(True)
        semi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        semi_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; color: #C0C4CC; font-size: 11px; }
            QPushButton:checked { color: #409EFF; font-weight: bold; }
            QPushButton:hover { color: #66B1FF; }
        """)
        semi_btn.setChecked(getattr(obj, "semi", False))
        semi_layout.addWidget(semi_btn)
        main_h.addWidget(col_semi)

        col_name = QFrame()
        col_name.setStyleSheet("border: none; background: transparent;")
        name_layout = QHBoxLayout(col_name)
        name_layout.setContentsMargins(8, 0, 4, 0)
        name_layout.setSpacing(4)
        font_name = QFont(self.ui_font_name)
        font_name.setPointSizeF(8)
        full_name = _draw_object_display_name(
            draw_objects,
            draw_index,
            normalization=getattr(self.popup, "normalization", None)
            or (getattr(self.popup, "fixed_plot_params", None) or {}).get(
                "normalization"
            ),
        )
        name_btn = QPushButton()
        name_btn.setFont(font_name)
        _elide_width = 200
        name_btn.setText(
            QFontMetrics(font_name).elidedText(
                full_name, Qt.TextElideMode.ElideRight, _elide_width
            )
        )
        name_btn.setToolTip("")
        name_btn.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed
        )
        name_btn.setMinimumWidth(30)
        name_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        name_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; text-align: left; color: #303133; }"
        )
        name_btn.setCheckable(False)
        name_btn.setChecked(
            draw_index in getattr(self, "_selected_draw_indices", set())
        )

        is_area_label = getattr(obj, "type", "") == "area_label"
        expand_btn = QPushButton("▶")
        expand_btn.setFixedSize(22, 22)
        expand_btn.setCheckable(True)
        expand_btn.setChecked(False)  # 처음에는 접힌 상태
        expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        expand_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; color: #909399; font-size: 10px; } "
            "QPushButton:hover { color: #409EFF; }"
        )
        if is_area_label:
            expand_btn.setVisible(False)
        else:
            # 세부 설정 유무에 따라 _rebuild_draw_effects에서 결정될 것이므로 일단 숨김
            expand_btn.setVisible(False)

        name_layout.addWidget(name_btn, 1)
        name_layout.addWidget(expand_btn)
        main_h.addWidget(col_name, 1)

        col_x = QFrame()
        col_x.setFixedSize(32, 32)
        col_x.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED; border-bottom: none; border-top: none; border-left: none;"
        )
        x_layout = QVBoxLayout(col_x)
        x_layout.setContentsMargins(0, 0, 0, 0)
        x_btn = QPushButton("✕")
        x_btn.setFixedSize(28, 28)
        x_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        x_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; color: #909399; font-size: 12px; }"
            "QPushButton:hover { color: #E64A19; }"
        )
        x_layout.addWidget(x_btn)
        main_h.addWidget(col_x)

        col_lock = QFrame()
        col_lock.setFixedSize(32, 32)
        col_lock.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED; border-bottom: none; border-top: none; border-left: none;"
        )
        lock_layout = QVBoxLayout(col_lock)
        lock_layout.setContentsMargins(0, 0, 0, 0)
        lock_btn = LayerLockButton()
        lock_btn.setToolTip("")
        lock_btn.setChecked(getattr(obj, "locked", False))
        lock_btn.setToolTip("")
        lock_layout.addWidget(lock_btn)
        main_h.addWidget(col_lock)

        row_vbox.addLayout(main_h)

        effects_container = QWidget()
        effects_container.setStyleSheet("background-color: transparent;")
        effects_layout = QVBoxLayout(effects_container)
        effects_layout.setContentsMargins(40, 2, 8, 2)
        effects_layout.setSpacing(0)
        row_vbox.addWidget(effects_container)

        idx = draw_index

        def on_eye_toggled(checked):
            self.draw_item_state_changed.emit(idx, "visible", bool(checked))

        def on_semi_toggled(checked):
            self.draw_item_state_changed.emit(idx, "semi", bool(checked))

        def on_name_clicked(arg=None):
            self._last_modifier = self._get_modifiers_from_arg(arg)
            self._selected_vowels = set()
            for r in self._layer_rows.values():
                r.setProperty("selected", False)
                if hasattr(r, "name_btn"):
                    r.name_btn.setChecked(False)
                r.style().unpolish(r)
                r.style().polish(r)
            self._toggle_select_draw_index(draw_index, name_btn)
            self._sync_draw_design_panel_to_selection()

        def on_x_clicked():
            self._selected_draw_indices = {idx}
            self._on_draw_delete()

        def on_lock_toggled(checked):
            self.draw_item_state_changed.emit(idx, "locked", bool(checked))

        row._click_forwarder = _RowClickForwarder(on_name_clicked, col_name)
        col_name.installEventFilter(row._click_forwarder)

        eye_btn.toggled.connect(on_eye_toggled)
        semi_btn.toggled.connect(on_semi_toggled)
        name_btn.clicked.connect(on_name_clicked)
        x_btn.clicked.connect(on_x_clicked)
        lock_btn.toggled.connect(on_lock_toggled)

        def on_expand_toggled(checked):
            effects_container.setVisible(checked)
            expand_btn.setText("▼" if checked else "▶")

        expand_btn.toggled.connect(on_expand_toggled)

        row.register_drag_child(row)
        row.register_drag_child(col_name)
        row.register_drag_child(effects_container)
        row.register_drag_child(eye_btn)
        row.register_drag_child(semi_btn)
        row.register_drag_child(name_btn)
        row.register_drag_child(expand_btn)
        row.register_drag_child(x_btn)
        row.register_drag_child(lock_btn)

        row.eye_btn = eye_btn
        row.semi_btn = semi_btn
        row.name_btn = name_btn
        row.x_btn = x_btn
        row.lock_btn = lock_btn
        row.expand_btn = expand_btn
        row.effects_container = effects_container
        row.effects_layout = effects_layout
        row.draw_index = draw_index
        return row

    def _update_global_row_state(self):
        """전체 눈/반투명 행의 체크 상태를 현재 레이어 상태에 맞춤."""
        if self._global_row is None or not self._layer_rows:
            return
        st = self._get_current_filter_state()
        vowels = list(self._layer_rows.keys())
        any_visible = any(st.get(v) != "OFF" for v in vowels)
        all_semi = all(
            st.get(v) == "SEMI" for v in vowels if st.get(v) != "OFF"
        ) and any(st.get(v) != "OFF" for v in vowels)
        self._global_row.eye_btn.blockSignals(True)
        self._global_row.semi_btn.blockSignals(True)
        self._global_row.eye_btn.setChecked(any_visible)
        self._global_row.semi_btn.setChecked(bool(all_semi))
        self._global_row.eye_btn.blockSignals(False)
        self._global_row.semi_btn.blockSignals(False)

    def _get_ordered_vowels_for_display(self, vowels):
        """표시 순서용 모음 리스트. 저장된 순서가 있으면 사용하고, 없으면 정렬 순.
        compare_plot 이식 시에는 popup 대신 탭별 layer_order를 사용할 수 있도록 확장 가능.
        """
        vowels_set = set(vowels)
        ordered = self.label_manager.get_layer_order()
        # 저장된 순서 중 현재 모음 집합에 포함되는 것만 유지
        stored = [v for v in ordered if v in vowels_set]
        if stored and set(stored) == vowels_set:
            return list(stored)
        return sorted(vowels, key=get_vowel_sort_key)

    def _set_drop_indicator_between(self, vowel, after):
        """그려야 할 목표 위치만 저장하고 화면(DropArea)을 다시 그리도록 요청합니다."""
        ordered = self._get_ordered_vowels_for_display(list(self._layer_rows.keys()))
        if vowel not in ordered:
            self._hide_drop_indicator()
            return
        self._drop_target = (vowel, after)
        row = self._layer_rows.get(vowel)
        if row and hasattr(self, "_label_drop_indicator"):
            rect = row.geometry()
            y = rect.bottom() if after else rect.top()
            # 인디케이터 위치 및 크기 설정 후 노출
            self._label_drop_indicator.setGeometry(rect.left(), y - 1, rect.width(), 2)
            self._label_drop_indicator.show()
            self._label_drop_indicator.raise_()

    def _hide_drop_indicator(self):
        """파란 선을 숨깁니다."""
        self._drop_target = None
        if hasattr(self, "_label_drop_indicator"):
            self._label_drop_indicator.hide()

    def _get_drop_target_at_pos(self, pos):
        """레이어 목록 위젯 내 pos(좌표)에 대응하는 (vowel, after) 반환.
        'A 아래'와 'B 위'가 사실상 같은 간격임을 고려하여, 하나의 간격에는 하나의 상태만 대응되도록 정규화합니다.
        """
        ordered = self._get_ordered_vowels_for_display(list(self._layer_rows.keys()))
        if not ordered:
            return (None, False)

        y = pos.y()
        rows = [self._layer_rows[v] for v in ordered]

        # 각 행의 중심점을 기준으로 영역을 나눕니다. (N개 행 -> N+1개 슬롯)
        # 슬롯 i는 'i번째 행의 위'를 의미하며, 마지막 슬롯은 '마지막 행의 아래'를 의미합니다.
        for i, row in enumerate(rows):
            geom = row.geometry()
            mid = geom.center().y()

            if y <= mid:
                # 현재 행의 중심점보다 위면 무조건 '현재 행의 위'로 취급
                return (ordered[i], False)

            # 현재 행의 중심점보다 아래인 경우
            if i < len(rows) - 1:
                # 다음 행이 있다면, 다음 행의 중심점까지의 영역을 모두 '다음 행의 위'로 통합
                next_mid = rows[i + 1].geometry().center().y()
                if y <= next_mid:
                    return (ordered[i + 1], False)
            else:
                # 마지막 행의 중심점보다 아래면 '마지막 행의 아래'
                return (ordered[i], True)

        return (ordered[-1], True)

    def _on_layer_reorder(self, dragged_list, drop_target_vowel, after=False):
        """드래그한 레이어(단일 또는 다중 선택)를 드롭 대상 행 위/아래로 이동"""
        if not isinstance(dragged_list, list):
            dragged_list = [dragged_list]
        ordered = self._get_ordered_vowels_for_display(list(self._layer_rows.keys()))
        new_order = compute_order_after_drop(
            ordered, dragged_list, drop_target_vowel, after
        )
        if new_order is None:
            return

        self.label_manager.set_layer_order(list(new_order))
        self._hide_drop_indicator()

        # 1. 화면 새로고침 (에러나던 유령 함수를 지우고 정상 함수 사용)
        self.set_vowels(new_order)

        # 2. 이동한 레이어 파란색 선택 효과 확실하게 칠하기
        self._selected_vowels = set(dragged_list)
        for v, r in self._layer_rows.items():
            r.setProperty("selected", v in self._selected_vowels)
            r.name_btn.setChecked(v in self._selected_vowels)
            r.style().unpolish(r)
            r.style().polish(r)

        # 3. 하단 디자인 패널 동기화
        self._sync_design_controls_to_selection()

        # 4. 다중 플롯 시그널 동기화 및 그래프 갱신
        if hasattr(self, "order_changed"):
            self.order_changed.emit(new_order)
        self.label_manager.notify_apply()

    def _hide_draw_drop_indicator(self):
        self._draw_drop_target = None
        if hasattr(self, "_draw_drop_indicator"):
            self._draw_drop_indicator.hide()

    def _set_draw_drop_indicator_between(self, draw_index, after):
        objs = self.draw_manager.get_draw_objects()
        if 0 <= draw_index < len(objs):
            self._draw_drop_target = (draw_index, after)
            rows = getattr(self, "_draw_layer_rows", None) or []
            if 0 <= draw_index < len(rows) and hasattr(self, "_draw_drop_indicator"):
                row = rows[draw_index]
                rect = row.geometry()
                y = rect.bottom() if after else rect.top()
                self._draw_drop_indicator.setGeometry(
                    rect.left(), y - 1, rect.width(), 2
                )
                self._draw_drop_indicator.show()
                self._draw_drop_indicator.raise_()

    def _get_draw_drop_target_at_pos(self, pos):
        """그리기 탭용 드롭 대상 계산. 동일하게 슬롯 로직을 적용하여 매끄럽게 처리합니다."""
        rows = getattr(self, "_draw_layer_rows", None) or []
        if not rows:
            return (None, False)

        y = pos.y()
        for i, row in enumerate(rows):
            geom = row.geometry()
            mid = geom.center().y()

            if y <= mid:
                return (getattr(row, "draw_index", i), False)

            if i < len(rows) - 1:
                next_mid = rows[i + 1].geometry().center().y()
                if y <= next_mid:
                    return (getattr(rows[i + 1], "draw_index", i + 1), False)
            else:
                idx = getattr(row, "draw_index", len(rows) - 1)
                return (idx, True)

        last_idx = getattr(rows[-1], "draw_index", len(rows) - 1)
        return (last_idx, True)

    def _on_draw_reorder(self, dragged_indices, target_index, after=False):
        objs = self.draw_manager.get_draw_objects()
        if not objs or target_index is None:
            return
        selected_obj_ids = {
            id(objs[i])
            for i in getattr(self, "_selected_draw_indices", set())
            if 0 <= i < len(objs)
        }
        anchor_idx = getattr(self, "_anchor_draw_index", None)
        anchor_obj_id = (
            id(objs[anchor_idx])
            if anchor_idx is not None and 0 <= anchor_idx < len(objs)
            else None
        )
        dragged_list = [objs[i] for i in sorted(dragged_indices) if 0 <= i < len(objs)]
        drop_target = objs[target_index]
        new_order = compute_order_after_drop(objs, dragged_list, drop_target, after)
        if new_order is None:
            return

        # 부모-자식(PolygonObject - AreaLabelObject) 인접 유지: 부모 이동 시 자식도 바로 뒤에 붙여서 함께 이동
        # 1) 부모 폴리곤 id → [자식 area_label 리스트] 맵 구성
        polygon_ids = {
            getattr(o, "id", None)
            for o in new_order
            if getattr(o, "type", "") == "polygon"
        }
        child_by_parent = {}
        for o in new_order:
            if getattr(o, "type", "") == "area_label":
                pid = getattr(o, "parent_id", None)
                if pid in polygon_ids:
                    child_by_parent.setdefault(pid, []).append(o)
        # 2) 부모를 순회하면서 부모 바로 뒤에 자식을 붙이는 새 리스트 구성
        reordered: list = []
        for o in new_order:
            if getattr(o, "type", "") == "area_label":
                # 부모에서 이미 붙일 것이므로 여기서는 건너뜀
                continue
            reordered.append(o)
            if getattr(o, "type", "") == "polygon":
                pid = getattr(o, "id", None)
                if pid in child_by_parent:
                    reordered.extend(child_by_parent[pid])

        # 선택/앵커를 "인덱스"가 아닌 "객체" 기준으로 재매핑하여 재정렬 후에도 유지한다.
        if selected_obj_ids:
            self._selected_draw_indices = {
                i for i, o in enumerate(reordered) if id(o) in selected_obj_ids
            }
        else:
            self._selected_draw_indices = set()
        if anchor_obj_id is not None:
            self._anchor_draw_index = next(
                (i for i, o in enumerate(reordered) if id(o) == anchor_obj_id), None
            )

        self.draw_manager.set_draw_objects(reordered)
        self._hide_draw_drop_indicator()
        self.draw_manager.redraw()
        self.update_draw_layer_list(reordered)

    def _toggle_select_draw_index(self, draw_index, name_btn):
        mod = getattr(self, "_last_modifier", None)
        if mod == Qt.KeyboardModifier.ControlModifier:
            if draw_index in self._selected_draw_indices:
                self._selected_draw_indices.discard(draw_index)
            else:
                self._selected_draw_indices.add(draw_index)
        elif mod == Qt.KeyboardModifier.ShiftModifier:
            anchor = getattr(self, "_anchor_draw_index", None)
            if anchor is None:
                anchor = draw_index
            start, end = min(anchor, draw_index), max(anchor, draw_index)
            self._selected_draw_indices = set(range(start, end + 1))
        else:
            if self._selected_draw_indices == {draw_index}:
                self._selected_draw_indices = set()
            else:
                self._selected_draw_indices = {draw_index}
                self._anchor_draw_index = draw_index
        self._last_modifier = None
        rows = getattr(self, "_draw_layer_rows", None) or []
        for r in rows:
            idx = getattr(r, "draw_index", None)
            sel = idx in self._selected_draw_indices if idx is not None else False
            r.setProperty("selected", sel)
            if hasattr(r, "name_btn"):
                r.name_btn.setChecked(sel)
            r.style().unpolish(r)
            r.style().polish(r)

        # 타입이 달라져서 디자인 패널 내용이 바뀔 수 있으므로, 항상 스크롤을 맨 위로 올린 뒤 동기화
        if hasattr(self, "_design_scroll") and getattr(self, "_design_scroll", None):
            vbar = self._design_scroll.verticalScrollBar()
            if vbar is not None:
                vbar.setValue(0)
        self._sync_draw_design_panel_to_selection()

    def _on_draw_delete(self):
        objs = self.draw_manager.get_draw_objects()
        if not objs:
            return
        to_remove = sorted(self._selected_draw_indices, reverse=True)
        if not to_remove:
            return
        removed_parent_ids = {
            getattr(objs[i], "id", None)
            for i in to_remove
            if 0 <= i < len(objs) and getattr(objs[i], "type", "") == "polygon"
        }
        removed_parent_ids.discard(None)
        min_idx = min(to_remove)
        for i in to_remove:
            if 0 <= i < len(objs):
                objs.pop(i)
        new_list = [
            o
            for o in objs
            if not (
                getattr(o, "type", "") == "area_label"
                and getattr(o, "parent_id", None) in removed_parent_ids
            )
        ]
        self.draw_manager.set_draw_objects(new_list)
        if new_list:
            new_idx = min(min_idx, len(new_list) - 1)
            self._selected_draw_indices = {new_idx}
        else:
            self._selected_draw_indices = set()
        self.draw_manager.redraw()
        self.update_draw_layer_list(new_list)
        self._draw_list_placeholder.setFocus(Qt.FocusReason.OtherFocusReason)

    def _update_draw_global_row_state(self):
        objs = self.draw_manager.get_draw_objects()
        row = getattr(self, "_draw_global_row", None)
        if row is None or not objs:
            return
        any_visible = any(getattr(o, "visible", True) for o in objs)
        all_semi = all(getattr(o, "semi", False) for o in objs)
        row.eye_btn.blockSignals(True)
        row.semi_btn.blockSignals(True)
        row.eye_btn.setChecked(any_visible)
        row.semi_btn.setChecked(bool(all_semi))
        row.eye_btn.blockSignals(False)
        row.semi_btn.blockSignals(False)

    def set_vowels(self, vowels):
        """현재 파일의 모음 레이어 목록을 표시.
        최적화: 위젯 재사용 및 불필요한 레이아웃 갱신(구분선 위젯 생성 등)을 제거하여 드롭 시 렉을 없앱니다.
        """
        ordered_vowels = self._get_ordered_vowels_for_display(vowels)
        self.setUpdatesEnabled(False)
        try:
            # 1. 기존 레이아웃에서 위젯들을 분리 (파괴하지 않음)
            while self._layer_list_layout.count():
                item = self._layer_list_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.hide()
                    # 행 위젯이 아닌 것(기존 구분선 등)은 삭제
                    if not (w == self._global_row or w.property("layerRow")):
                        w.deleteLater()

            if not ordered_vowels:
                self._global_row = None
                self._layer_rows.clear()
                return

            filter_state = self._get_current_filter_state()

            # 2. 전역 행 재사용
            if self._global_row is None:
                self._global_row = self._build_global_row()
            self._layer_list_layout.addWidget(self._global_row)
            self._global_row.show()

            # 3. 레이어 행 순서대로 재삽입 (생성 대신 재사용 우선)
            new_rows = {}
            for v in ordered_vowels:
                row = self._layer_rows.get(v)
                if row is None:
                    row = self._build_layer_row(str(v), filter_state.get(v, "ON"))
                    row.setProperty("vowel", v)
                else:
                    # 선택 상태 동기화
                    is_sel = v in self._selected_vowels
                    row.setProperty("selected", is_sel)
                    if hasattr(row, "name_btn"):
                        row.name_btn.setChecked(is_sel)
                    row.style().unpolish(row)
                    row.style().polish(row)

                self._layer_list_layout.addWidget(row)
                row.show()
                new_rows[v] = row

            self._layer_rows = new_rows
            self._update_global_row_state()
            self._rebuild_effects()
        finally:
            self.setUpdatesEnabled(True)

    def set_compare_file_index(self, index):
        """compare 모드에서 어느 파일이 선택됐는지 동기화 (0=파일A, 1=파일B)."""
        if not self._compare_mode or self._compare_file_group is None:
            return
        btn = self._compare_file_group.button(index)
        if btn and not btn.isChecked():
            btn.setChecked(True)

    def set_splitter_sizes(self, sizes):
        """다중플롯에서 다른 도크와 스플리터 비율 동기화. sizes: [상단, 하단] 픽셀."""
        if getattr(self, "_splitter", None) is not None and sizes and len(sizes) == 2:
            self._splitter.setSizes(list(sizes))

    def _build_layer_row(self, vowel, state):
        row = _LayerRowFrame(self, vowel)
        row.setProperty("layerRow", True)
        row.setProperty("vowel", vowel)

        # 행 전체에 hover 및 선택 효과 적용 (구분선 위젯 대신 border-bottom 사용)
        row.setStyleSheet("""
            QFrame[layerRow="true"] {
                background-color: transparent;
                border-bottom: 1px solid #EBEEF5;
            }
            QFrame[layerRow="true"]:hover {
                background-color: #F5F7FA;
            }
            QFrame[layerRow="true"][selected="true"] {
                background-color: #E6F0F9;
            }
        """)

        row_vbox = QVBoxLayout(row)
        row_vbox.setContentsMargins(0, 0, 0, 0)
        row_vbox.setSpacing(0)

        # 메인 가로 레이아웃 (테이블 구조: 여백과 간격을 0으로)
        main_h = QHBoxLayout()
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        # 1. 눈 (Eye) 열
        col_eye, eye_layout = self._create_column_frame(32)
        eye_btn = LayerEyeButton()
        eye_layout.addWidget(eye_btn)

        # 2. 반투명 (Semi) 열
        col_semi, semi_layout = self._create_column_frame(54)
        semi_btn = QPushButton("반투명")
        semi_btn.setCheckable(True)
        semi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        semi_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; color: #C0C4CC; font-size: 11px; }
            QPushButton:checked { color: #409EFF; font-weight: bold; }
            QPushButton:hover { color: #66B1FF; }
        """)
        semi_layout.addWidget(semi_btn)

        # 상태 연동 로직 (가장 중요한 독립성 보장 영역)
        was_semi = self._semi_memory.get(vowel, False)
        if state == "SEMI":
            was_semi = True
            self._semi_memory[vowel] = True

        eye_btn.setChecked(state != "OFF")
        semi_btn.setChecked(was_semi)

        # 3. 레이어 이름 & 확장 (Name) 열
        col_name = QFrame()
        col_name.setStyleSheet("border: none; background: transparent;")
        name_layout = QHBoxLayout(col_name)
        name_layout.setContentsMargins(8, 0, 4, 0)
        name_layout.setSpacing(4)

        font_name = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        name_btn = QPushButton(vowel)
        name_btn.setFont(font_name)
        name_btn.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed
        )
        name_btn.setMinimumWidth(30)
        name_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        name_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; text-align: left; color: #303133; }"
        )

        expand_btn = QPushButton("▶")
        expand_btn.setFixedSize(22, 22)
        expand_btn.setCheckable(True)
        expand_btn.setChecked(False)  # 처음부터 펼쳐지지 않도록 접힌 상태(▶)로 초기화
        expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        expand_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; color: #909399; font-size: 10px; } QPushButton:hover { color: #409EFF; }"
        )
        # 세부 정보 유무 확인 전까지는 숨김 처리
        expand_btn.setVisible(False)

        name_layout.addWidget(name_btn, 1)
        name_layout.addWidget(expand_btn)

        # 4. 자물쇠(잠금) 열 — 잠금 시 레이어 설정 초기화에서 제외
        col_lock, lock_layout = self._create_column_frame(32)
        lock_btn = LayerLockButton()
        lock_layout.addWidget(lock_btn)

        locked_set = self.label_manager.get_locked_vowels_set()
        lock_btn.setChecked(vowel in locked_set)

        def on_lock_toggled(checked):
            self.label_manager.set_locked_vowel(vowel, checked)

        lock_btn.toggled.connect(on_lock_toggled)

        # 행에 각 열 합체
        main_h.addWidget(col_eye)
        main_h.addWidget(col_semi)
        main_h.addWidget(col_name, 1)
        main_h.addWidget(col_lock)
        row_vbox.addLayout(main_h)

        # 4. 효과 레이어 표시 컨테이너 (여백 최소화로 "두툼한 공백" 감소)
        row.effects_container = QWidget()
        row.effects_container.setStyleSheet("background-color: transparent;")
        row.effects_layout = QVBoxLayout(row.effects_container)
        row.effects_layout.setContentsMargins(40, 2, 8, 2)
        row.effects_layout.setSpacing(0)
        row_vbox.addWidget(row.effects_container)

        # 드래그 시작 영역 확장: 행 전체와 주요 클릭 영역(이름/토글 버튼들/효과 영역)에서 드래그 가능
        row.register_drag_child(row)
        row.register_drag_child(col_name)
        row.register_drag_child(row.effects_container)
        row.register_drag_child(eye_btn)
        row.register_drag_child(semi_btn)
        row.register_drag_child(name_btn)
        row.register_drag_child(expand_btn)
        row.register_drag_child(lock_btn)

        # --- 시그널 함수 정의 ---
        def on_eye_toggled(checked):
            new_state = toggle_item_visibility(checked, semi_btn.isChecked())
            self.label_filter_item_changed.emit(vowel, new_state)

        def on_semi_toggled(checked):
            self._semi_memory[vowel] = checked
            if eye_btn.isChecked():
                self.label_filter_item_changed.emit(
                    vowel, toggle_item_visibility(True, checked)
                )

        def on_name_clicked(arg=None):
            self._last_modifier = self._get_modifiers_from_arg(arg)
            self._toggle_select_vowel(vowel, name_btn)
            self._sync_design_controls_to_selection()

        # 이름 열 빈 영역 클릭 시에도 선택 토글 (두툼한 공백 대응: 클릭 가능 영역 확대)
        row._click_forwarder = _RowClickForwarder(on_name_clicked, col_name)
        col_name.installEventFilter(row._click_forwarder)

        def on_expand_toggled(checked):
            row.effects_container.setVisible(checked)
            expand_btn.setText("▼" if checked else "▶")

        eye_btn.toggled.connect(on_eye_toggled)
        semi_btn.toggled.connect(on_semi_toggled)
        name_btn.clicked.connect(on_name_clicked)
        expand_btn.toggled.connect(on_expand_toggled)

        row.eye_btn = eye_btn
        row.semi_btn = semi_btn
        row.name_btn = name_btn
        row.expand_btn = expand_btn

        return row

    def _toggle_select_vowel(self, vowel, name_btn):
        mod = getattr(self, "_last_modifier", None)
        if mod == Qt.KeyboardModifier.ControlModifier:
            if vowel in self._selected_vowels:
                self._selected_vowels.discard(vowel)
            else:
                self._selected_vowels.add(vowel)
        elif mod == Qt.KeyboardModifier.ShiftModifier:
            vowels = self._get_ordered_vowels_for_display(list(self._layer_rows.keys()))
            if vowel in vowels:
                anchor = getattr(self, "_anchor_vowel", None) or vowel
                if anchor in vowels:
                    i1 = vowels.index(anchor)
                    i2 = vowels.index(vowel)
                    start, end = (i1, i2) if i1 <= i2 else (i2, i1)
                    self._selected_vowels = set(vowels[start : end + 1])
        else:
            # 수정키 없이 클릭: 이미 이 모음만 선택된 상태면 선택 해제, 아니면 이 모음만 선택
            if self._selected_vowels == {vowel}:
                self._selected_vowels = set()
            else:
                self._selected_vowels = {vowel}
                self._anchor_vowel = vowel

        self._last_modifier = None

        for v, r in self._layer_rows.items():
            r.setProperty("selected", v in self._selected_vowels)
            if hasattr(r, "name_btn"):
                r.name_btn.setChecked(v in self._selected_vowels)
            r.style().unpolish(r)
            r.style().polish(r)
        self._sync_design_controls_to_selection()

    def refresh_design_ui(self):
        """좌측 디자인 설정(기본값)이 바뀌었을 때 호출. 개별 오버라이드 없는 컨트롤을 새 기본값에 맞춰 갱신."""
        self._sync_design_controls_to_selection()

    def keyPressEvent(self, event):
        self._last_modifier = event.modifiers()
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and event.key() in (
            Qt.Key.Key_Delete,
            Qt.Key.Key_Backspace,
        ):
            if self.tab_widget.currentIndex() == 1:
                w = obj
                while w is not None:
                    if w == self._draw_list_placeholder:
                        self._on_draw_delete()
                        return True
                    try:
                        w = w.parent()
                    except Exception:
                        break
        return super().eventFilter(obj, event)

    def _on_layer_tab_index_changed(self, index: int):
        """탭 전환 시 라벨 탭의 레이어 선택 해제. 그리기 탭일 때 순서/레이어 초기화 버튼 숨김."""
        self._selected_vowels = set()
        for r in self._layer_rows.values():
            r.setProperty("selected", False)
            if hasattr(r, "name_btn"):
                r.name_btn.setChecked(False)
            r.style().unpolish(r)
            r.style().polish(r)
        if index == 1:
            self.btn_reset_order.hide()
            self.btn_reset_layers.hide()
            self.btn_batch_delete_draw.show()
            self._draw_list_placeholder.setFocus(Qt.FocusReason.OtherFocusReason)
            self._selected_vowels = set()
            for r in self._layer_rows.values():
                r.setProperty("selected", False)
                if hasattr(r, "name_btn"):
                    r.name_btn.setChecked(False)
                r.style().unpolish(r)
                r.style().polish(r)
            # 상단 디자인 영역: 라벨 패널 숨기고 그리기 패널 표시
            self.vowel_design_container.hide()
            self._draw_design_panel.show()
            self._sync_draw_design_panel_to_selection()
        else:
            self.btn_reset_order.show()
            self.btn_reset_layers.show()
            self.btn_batch_delete_draw.hide()
            # 상단 디자인 영역: 그리기 패널 숨기고 라벨 패널 표시
            self._draw_design_panel.hide()
            self.vowel_design_container.show()
            self._draw_design_panel.clear_selection()
            self._sync_design_controls_to_selection()

    def update_draw_layer_list(self, draw_objects):
        """그리기 탭 목록 최적화: 위젯 재사용 및 레이아웃 갱신 최소화."""
        self.setUpdatesEnabled(False)
        try:
            old_rows = getattr(self, "_draw_layer_rows", [])
            # 레이아웃에서 분리
            while self._draw_list_layout.count():
                item = self._draw_list_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.hide()
                    if not (
                        w == getattr(self, "_draw_global_row", None) or w in old_rows
                    ):
                        w.deleteLater()

            if not draw_objects:
                if getattr(self, "_draw_global_row", None) is not None:
                    self._draw_global_row.hide()
                    self._draw_global_row.deleteLater()
                    self._draw_global_row = None
                self._draw_layer_rows = []
                return

            if getattr(self, "_draw_global_row", None) is None:
                self._draw_global_row = self._build_draw_global_row()
            self._draw_list_layout.addWidget(self._draw_global_row)
            self._draw_global_row.show()

            self._draw_layer_rows = []
            for i, obj in enumerate(draw_objects):
                # 기존 위젯이 있다면 재사용 (단순 인덱스 기반 매칭)
                if i < len(old_rows):
                    row = old_rows[i]
                    row.setProperty("drawIndex", i)
                    row.draw_index = i
                    is_selected = i in getattr(self, "_selected_draw_indices", set())
                    row.setProperty("selected", is_selected)
                    # 이름 등 최소한의 정보만 업데이트
                    if hasattr(row, "name_btn"):
                        full_name = _draw_object_display_name(
                            draw_objects,
                            i,
                            normalization=getattr(self.popup, "normalization", None)
                            or (
                                getattr(self.popup, "fixed_plot_params", None) or {}
                            ).get("normalization"),
                        )
                        prefix = (
                            "  ↳ " if getattr(obj, "type", "") == "area_label" else ""
                        )
                        row.name_btn.setText(
                            QFontMetrics(row.name_btn.font()).elidedText(
                                prefix + full_name, Qt.TextElideMode.ElideRight, 200
                            )
                        )
                        row.name_btn.setChecked(is_selected)
                    if hasattr(row, "eye_btn"):
                        row.eye_btn.blockSignals(True)
                        row.eye_btn.setChecked(getattr(obj, "visible", True))
                        row.eye_btn.blockSignals(False)
                    if hasattr(row, "semi_btn"):
                        row.semi_btn.blockSignals(True)
                        row.semi_btn.setChecked(getattr(obj, "semi", False))
                        row.semi_btn.blockSignals(False)
                    if hasattr(row, "lock_btn"):
                        row.lock_btn.blockSignals(True)
                        row.lock_btn.setChecked(getattr(obj, "locked", False))
                        row.lock_btn.blockSignals(False)
                    row.style().unpolish(row)
                    row.style().polish(row)
                else:
                    row = self._build_draw_layer_row(i, obj, draw_objects)

                self._draw_list_layout.addWidget(row)
                row.show()
                self._draw_layer_rows.append(row)

            self._rebuild_draw_effects()
        finally:
            self.setUpdatesEnabled(True)

    def _sync_draw_design_panel_to_selection(self):
        """현재 그리기 탭에서 선택된 객체에 맞춰 그리기 디자인 패널을 갱신."""
        if not hasattr(self, "_draw_design_panel"):
            return
        if self.tab_widget.currentIndex() != 1:
            self._draw_design_panel.clear_selection()
            return

        # 다중 플롯(compare) 팝업 등, 아직 그리기 모드를 지원하지 않는 경우는 조용히 무시
        if not hasattr(self.popup, "_get_current_draw_objects"):
            self._draw_design_panel.clear_selection()
            return

        objs = self.draw_manager.get_draw_objects()
        if not objs:
            self._draw_design_panel.clear_selection()
            return

        sel_set = getattr(self, "_selected_draw_indices", set())
        if not sel_set:
            self._draw_design_panel.clear_selection()
            return

        # 기준이 되는 인덱스: 앵커(Shift 기준) 또는 가장 마지막 클릭, 없으면 첫 번째
        anchor = getattr(self, "_anchor_draw_index", None)
        idx = None
        if anchor is not None and anchor in sel_set:
            idx = anchor
        else:
            idx = sorted(sel_set)[0]

        if idx < 0 or idx >= len(objs):
            self._draw_design_panel.clear_selection()
            return

        obj = objs[idx]
        t = getattr(obj, "type", "")
        if t == "line":
            layer_type = "line"
        elif t == "polygon":
            layer_type = "area"
        elif t == "reference":
            layer_type = "reference"
        else:
            self._draw_design_panel.clear_selection()
            return

        layer_id = getattr(obj, "id", None)
        if not layer_id:
            # UUID 기반 ID 정책: id가 비어 있으면 디자인 패널과의 연동을 건너뛴다.
            self._draw_design_panel.clear_selection()
            return

        # 실제 객체의 속성에서 직접 settings를 구성한다.
        settings: dict[str, object] = {}
        if layer_type == "line":
            settings["line_style"] = getattr(obj, "line_style", "-") or "-"
            settings["line_color"] = getattr(obj, "line_color", "#000000") or "#000000"
            settings["arrow_mode"] = getattr(obj, "arrow_mode", "none") or "none"
            settings["arrow_head"] = getattr(obj, "arrow_head", "stealth") or "stealth"
        elif layer_type == "area":
            if getattr(obj, "points", None):
                try:
                    settings["area_value"] = polygon_area(obj.points)
                except Exception:
                    pass
            settings["area_label_visible"] = getattr(obj, "show_area_label", False)
            settings["border_style"] = getattr(obj, "border_style", "-") or "-"
            settings["border_color"] = (
                getattr(obj, "border_color", "#000000") or "#000000"
            )
            settings["fill_color"] = getattr(obj, "fill_color", "#3366CC")
        elif layer_type == "reference":
            settings["line_style"] = getattr(obj, "line_style", "-") or "-"
            settings["line_color"] = getattr(obj, "line_color", "#AAAAAA") or "#AAAAAA"

        # UI 갱신 중 역참조 방지
        self._draw_design_panel.blockSignals(True)
        try:
            self._draw_design_panel.set_current_layer(layer_id, layer_type, settings)
        finally:
            self._draw_design_panel.blockSignals(False)

    def _apply_draw_settings_to_objects(
        self, layer_id: str, settings_for_apply: dict
    ) -> tuple[str, dict, list[str]]:
        """settings_for_apply를 실제 Draw Object들에 적용하고,
        base_type, summary용 settings, 실제로 변경된 레이어 ID 목록을 반환."""
        objs = self.draw_manager.get_draw_objects()
        if not objs:
            return "", {}, []

        # 기준 객체(type)를 찾는다.
        base_idx = None
        base_obj = None
        for i, o in enumerate(objs):
            base_layer_id = getattr(o, "id", None)
            if (
                getattr(o, "type", "") in ("line", "polygon", "reference")
                and base_layer_id == layer_id
            ):
                base_idx = i
                base_obj = o
                break
        if base_obj is None:
            return "", {}, []
        base_type = getattr(base_obj, "type", "")

        # 효과 요약 줄에 사용할 설정은 넓이 텍스트 토글 등을 제외
        settings_for_summary = dict(settings_for_apply)
        settings_for_summary.pop("area_label_visible", None)

        # 다중 선택 시: 기준 타입과 동일한 객체에만 일괄 적용
        selected = getattr(self, "_selected_draw_indices", set()) or {base_idx}
        target_indices = [
            i
            for i in selected
            if 0 <= i < len(objs) and getattr(objs[i], "type", "") == base_type
        ]
        if not target_indices:
            target_indices = [base_idx]

        # 실제 변경 대상 레이어 ID 목록 (요약/override에도 동일하게 반영하기 위함)
        target_layer_ids: list[str] = []
        for i in target_indices:
            lid = getattr(objs[i], "id", None)
            if lid:
                target_layer_ids.append(lid)

        for i in target_indices:
            o = objs[i]
            t = getattr(o, "type", "")
            if t == "line":
                apply_line_settings(o, settings_for_apply)
            elif t == "polygon":
                apply_polygon_settings(o, settings_for_apply)
            elif t == "reference":
                apply_reference_settings(o, settings_for_apply)

        # 폴리곤의 넓이 텍스트 레이어는 모든 폴리곤을 한 번에 훑으면서 AreaLabelObject를 재구성한다.
        if base_type == "polygon":
            rebuilt = rebuild_area_labels_for_polygons(objs)
            objs.clear()
            objs.extend(rebuilt)

        self.draw_manager.set_draw_objects(objs)
        self.draw_manager.redraw()
        self.update_draw_layer_list(objs)
        return base_type, settings_for_summary, target_layer_ids

    def _update_draw_overrides_for_summary(
        self,
        layer_id: str,
        base_type: str,
        settings_for_summary: dict,
        target_layer_ids: list[str] | None = None,
    ):
        """기본값과 비교하여 override dict를 갱신하고 효과 요약 줄을 재구성한다.
        다중 선택 시 기준 레이어와 동일 타입인 모든 대상 레이어에 동일한 요약을 반영한다."""
        popup = self.popup
        # 기본 디자인 값과 동일한 항목을 제거한 뒤 효과 요약에 사용할 설정을 저장
        if (
            hasattr(self, "_get_default_design")
            and self._get_default_design is not None
        ):
            defaults = self._get_default_design() or {}
        else:
            defaults = getattr(popup, "design_settings", {}) or {}

        clean_cfg: dict[str, object] = {}
        if base_type == "line":
            # 선 레이어: line_style, line_color만 비교
            base_style = defaults.get("draw_line_style", "-") or "-"
            base_color = defaults.get("draw_line_color", "#000000") or "#000000"
            base_arrow_mode = "none"
            base_arrow_head = "stealth"
            for k, v in settings_for_summary.items():
                if k == "line_style" and (v or "-") == base_style:
                    continue
                if (
                    k == "line_color"
                    and (v or "#000000").lower() == str(base_color).lower()
                ):
                    continue
                if k == "arrow_mode" and (v or "none") == base_arrow_mode:
                    continue
                if k == "arrow_head" and (v or "stealth") == base_arrow_head:
                    continue
                clean_cfg[k] = v
            # mode가 none이면 요약/오버라이드에서 arrow_head는 항상 제거
            if str(clean_cfg.get("arrow_mode", "none")) == "none":
                clean_cfg.pop("arrow_head", None)
        elif base_type == "polygon":
            # 영역 레이어: border_style, border_color, fill_color 비교. 넓이 텍스트 ON/OFF는 데이터 모델에서 관리해 여기엔 넣지 않음
            base_border_style = defaults.get("draw_area_border_style", "-") or "-"
            base_border_color = (
                defaults.get("draw_area_border_color", "#000000") or "#000000"
            )
            # 영역 내부 색 기본값은 항상 파랑(#3366CC)로 고정. None/transparent는 기본값으로 보지 않는다.
            raw_fill = defaults.get("draw_area_fill_color", "#3366CC")
            if not raw_fill or str(raw_fill).lower() == "transparent":
                base_fill = "#3366CC"
            else:
                base_fill = raw_fill
            for k, v in settings_for_summary.items():
                if k == "area_label_visible":
                    continue
                if k == "border_style" and (v or "-") == base_border_style:
                    continue
                if (
                    k == "border_color"
                    and (v or "#000000").lower() == str(base_border_color).lower()
                ):
                    continue
                if k == "fill_color":
                    if str(v or "#3366CC").lower() == str(base_fill).lower():
                        continue
                clean_cfg[k] = v
        elif base_type == "reference":
            # 참조선: 스타일은 기본값과 비교, 색상은 패널 기본값(#AAAAAA)과 비교하여 필터링
            base_style = defaults.get("draw_ref_line_style", "-") or "-"
            base_color = defaults.get("draw_ref_line_color", "#AAAAAA") or "#AAAAAA"
            for k, v in settings_for_summary.items():
                if k == "line_style" and (v or "-") == base_style:
                    continue
                if k == "line_color":
                    if str(v or "#AAAAAA").lower() == str(base_color).lower():
                        continue
                clean_cfg[k] = v
        else:
            clean_cfg = settings_for_summary

        if target_layer_ids is None or not target_layer_ids:
            target_layer_ids = [layer_id]

        for lid in target_layer_ids:
            if clean_cfg:
                self._draw_design_settings[lid] = dict(clean_cfg)
            elif lid in self._draw_design_settings:
                # 모든 항목이 기본값이면 오버라이드를 삭제해 효과 요약 줄을 숨김
                self._draw_design_settings.pop(lid, None)

        self._rebuild_draw_effects()

    def _on_draw_design_settings_changed(self, layer_id: str, settings: dict):
        """그리기 디자인 패널에서 설정이 변경됐을 때 내부 상태를 저장하고 객체에 반영한다."""
        if not layer_id or not isinstance(settings, dict):
            return

        # 1단계: 실제 Draw Object에 설정 적용
        settings_for_apply = dict(settings)
        (
            base_type,
            settings_for_summary,
            target_layer_ids,
        ) = self._apply_draw_settings_to_objects(layer_id, settings_for_apply)
        if not base_type:
            return

        # 2단계: override/요약 정보 갱신 (다중 선택 시에도 모든 대상 레이어에 적용)
        self._update_draw_overrides_for_summary(
            layer_id, base_type, settings_for_summary, target_layer_ids
        )

    def _sync_design_controls_to_selection(self):
        if self.tab_widget.currentIndex() != 0:
            return
        self._updating = True
        try:
            overrides = self._get_layer_overrides()
            if self._get_default_design is not None:
                ds = self._get_default_design() or {}
            else:
                ds = getattr(self.popup, "design_settings", {}) or {}
            if len(self._selected_vowels) == 1:
                v = next(iter(self._selected_vowels))
                o = overrides.get(v, {})
                self.lbl_color_picker.set_color(
                    o.get("lbl_color", ds.get("lbl_color", config.COLOR_PRIMARY_RED))
                )
                idx = MARKER_IDS.get(
                    o.get("centroid_marker", ds.get("centroid_marker", "o")), 0
                )
                btn_c = self.group_centroid_marker.button(idx)
                if btn_c:
                    btn_c.setChecked(True)
                thick_val = o.get("ell_thick") or ds.get("ell_thick", 2.0)
                tid = next(
                    (
                        i
                        for i, t in enumerate(THICK_VALS)
                        if abs(t - float(thick_val)) < 0.01
                    ),
                    1,
                )
                btn_thick = self.group_ell_thick.button(tid)
                if btn_thick:
                    btn_thick.setChecked(True)
                sid = STYLE_IDS.get(o.get("ell_style", ds.get("ell_style", ":")), 2)
                btn_style = self.group_ell_style.button(sid)
                if btn_style:
                    btn_style.setChecked(True)
                self.ell_color_picker.set_color(
                    o.get("ell_color") or ds.get("ell_color") or "#606060"
                )
                self.ell_fill_picker.set_color(
                    o.get("ell_fill_color") or ds.get("ell_fill_color") or "transparent"
                )
            else:
                self.lbl_color_picker.set_color(
                    ds.get("lbl_color", config.COLOR_PRIMARY_RED)
                )
                self.group_centroid_marker.button(0).setChecked(True)
                self.group_ell_thick.button(1).setChecked(True)
                self.group_ell_style.button(2).setChecked(True)
                self.ell_color_picker.set_color(ds.get("ell_color") or "#606060")
                self.ell_fill_picker.set_color(
                    ds.get("ell_fill_color") or "transparent"
                )
        finally:
            self._updating = False

    def _effect_display_text(self, key, value):
        if value is None:
            return ""
        if key == "lbl_color":
            return _format_color_display(value)
        if key == "centroid_marker":
            return MARKER_LABELS.get(value, str(value))
        if key == "ell_thick":
            return THICK_LABELS.get(value, str(value))
        if key == "ell_style":
            return STYLE_LABELS.get(value, str(value))
        if key in ["ell_color", "ell_fill_color"]:
            return _format_color_display(value)
        return str(value)[:20]

    def _effect_label(self, key):
        labels = {
            "lbl_color": "라벨 색",
            "centroid_marker": "중심점 모양",
            "ell_thick": "타원 선 두께",
            "ell_style": "타원 선 모양",
            "ell_color": "타원 선 색",
            "ell_fill_color": "타원 내부 색",
        }
        return labels.get(key, key)

    def _rebuild_effects(self):
        overrides = self._get_layer_overrides()
        font_effect = QFont(self.ui_font_name, 8)
        for vowel, row in self._layer_rows.items():
            while row.effects_layout.count():
                item = row.effects_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            o = overrides.get(vowel, {})
            if not o:
                if hasattr(row, "expand_btn"):
                    row.expand_btn.setVisible(False)
                    row.expand_btn.setChecked(
                        False
                    )  # 세부 정보가 없으면 로직상으로도 접힘 처리
                continue

            if hasattr(row, "expand_btn"):
                # 세부 정보가 생기면 버튼을 보여주고 기본적으로 펼침 상태(▼)가 되도록 함
                if not row.expand_btn.isVisible():
                    row.expand_btn.setChecked(True)
                row.expand_btn.setVisible(True)
            first = True
            for key in [
                "lbl_color",
                "centroid_marker",
                "ell_thick",
                "ell_style",
                "ell_color",
                "ell_fill_color",
            ]:
                if key not in o:
                    continue
                if not first:
                    sep = QFrame()
                    sep.setFrameShape(QFrame.Shape.HLine)
                    sep.setStyleSheet(
                        "color: #F0F2F5; margin-left: 4px; margin-right: 4px; margin-top: 1px; margin-bottom: 1px;"
                    )
                    row.effects_layout.addWidget(sep)
                first = False
                eff_row = QHBoxLayout()
                eff_row.setContentsMargins(0, 0, 0, 0)
                eff_row.setSpacing(4)
                lbl = QLabel(
                    f"  {self._effect_label(key)}: {self._effect_display_text(key, o[key])}",
                    font=font_effect,
                )
                lbl.setStyleSheet("color: #606266;")
                eff_row.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
                eff_row.addStretch()
                x_btn = QPushButton("✕")
                x_btn.setFixedSize(18, 18)
                x_btn.setStyleSheet(
                    "QPushButton { border: none; color: #909399; font-size: 11px; } QPushButton:hover { color: #E64A19; }"
                )
                x_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                k, v = key, vowel

                # 버그 수정 반영: (checked=False 추가)
                def remove_key(checked=False, kk=k, vv=v):
                    if self.tab_widget.currentIndex() != 0:
                        return
                    ov = self._get_layer_overrides()
                    if not isinstance(ov, dict):
                        return
                    if vv not in ov or kk not in ov[vv]:
                        return
                    new_overrides = {}
                    for v_key, o_dict in ov.items():
                        if v_key != vv:
                            new_overrides[v_key] = dict(o_dict)
                        else:
                            no = {
                                k_sub: val
                                for k_sub, val in o_dict.items()
                                if k_sub != kk
                            }
                            if no:
                                new_overrides[v_key] = no
                    self._set_layer_overrides(new_overrides)
                    self.label_manager.sync_overrides_by_current_file(new_overrides)
                    self.overrides_changed.emit(new_overrides)
                    self._rebuild_effects()
                    self.label_manager.notify_apply()

                x_btn.clicked.connect(remove_key)
                eff_row.addWidget(x_btn)
                w = QWidget()
                w.setFixedHeight(24)
                w.setLayout(eff_row)
                row.effects_layout.addWidget(w)

    def _rebuild_draw_effects(self):
        """그리기 레이어용 효과 요약 줄 (선/영역/참조선 디자인 설정)."""
        rows = getattr(self, "_draw_layer_rows", None) or []
        if not rows:
            return
        objs = self.draw_manager.get_draw_objects()
        if not objs:
            return
        font_effect = QFont(self.ui_font_name, 8)

        def effect_label(key):
            labels = {
                "line_style": "선 타입",
                "line_color": "선 색",
                "arrow_mode": "화살표 타입",
                "arrow_head": "화살표 모양",
                "border_style": "외곽선 타입",
                "border_color": "외곽선 색",
                "fill_color": "내부 색",
            }
            return labels.get(key, key)

        def effect_text(key, value):
            if value is None:
                return ""
            if key in ("line_color", "border_color", "fill_color"):
                return _format_color_display(value)
            if key == "line_style" or key == "border_style":
                return STYLE_LABELS.get(value, str(value))
            if key == "arrow_mode":
                return {"none": "없음", "end": "끝점", "all": "점마다"}.get(
                    str(value), str(value)
                )
            if key == "arrow_head":
                return {"stealth": "stealth", "open": "open", "latex": "latex"}.get(
                    str(value), str(value)
                )
            return str(value)[:20]

        for row in rows:
            idx = getattr(row, "draw_index", None)
            if idx is None or idx < 0 or idx >= len(objs):
                continue
            while row.effects_layout.count():
                item = row.effects_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            obj = objs[idx]
            t = getattr(obj, "type", "")
            layer_id = getattr(obj, "id", None)
            if not layer_id:
                # UUID 기반 ID가 없는 객체는 디자인 요약에서 제외
                continue
            cfg = self._draw_design_settings.get(layer_id, {}) or {}
            display_cfg = dict(cfg)

            # 타입별로 의미 있는 키만 표시
            if t == "line":
                keys = ["line_style", "line_color", "arrow_mode", "arrow_head"]
                # 화살표 타입이 end/all로 설정됐고 head가 미지정이면,
                # 기본값(stealth)을 세부 레이어에만 표시한다.
                mode_val = str(display_cfg.get("arrow_mode", "none"))
                if mode_val in ("end", "all") and "arrow_head" not in display_cfg:
                    display_cfg["arrow_head"] = "stealth"
            elif t == "polygon":
                keys = ["border_style", "border_color", "fill_color"]
            elif t == "reference":
                keys = ["line_style", "line_color"]
            else:
                keys = []

            # 저장된 설정 중 이 타입에 해당하는 키만 남긴다.
            keys = [k for k in keys if k in display_cfg]
            # 화살표가 none이면 화살표 모양 줄은 요약에서 숨긴다.
            if (
                "arrow_mode" in keys
                and str(display_cfg.get("arrow_mode", "none")) == "none"
            ):
                keys = [k for k in keys if k != "arrow_head"]
            if not keys or t == "area_label":
                if hasattr(row, "expand_btn"):
                    row.expand_btn.setVisible(False)
                    row.expand_btn.setChecked(False)  # 로직상 접힘 상태 유지
                continue

            if hasattr(row, "expand_btn"):
                # 세부 정보가 처음 생길 때 자동으로 펼침(▼) 상태가 되도록 처리
                if not row.expand_btn.isVisible():
                    row.expand_btn.setChecked(True)
                row.expand_btn.setVisible(True)

            first = True
            for key in keys:
                if not first:
                    sep = QFrame()
                    sep.setFrameShape(QFrame.Shape.HLine)
                    sep.setStyleSheet(
                        "color: #F0F2F5; margin-left: 4px; margin-right: 4px; margin-top: 1px; margin-bottom: 1px;"
                    )
                    row.effects_layout.addWidget(sep)
                first = False

                eff_row = QHBoxLayout()
                eff_row.setContentsMargins(0, 0, 0, 0)
                eff_row.setSpacing(4)
                lbl = QLabel(
                    f"  {effect_label(key)}: {effect_text(key, display_cfg[key])}",
                    font=font_effect,
                )
                lbl.setStyleSheet("color: #606266;")
                eff_row.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
                eff_row.addStretch()

                # 그리기 레이어의 세부 레이어(요약 줄)는 레이어 목록에서 X 버튼으로 직접 삭제할 수 없게 한다.
                # (디폴트 디자인 초기화나 상단 패널에서만 기본값 복원이 가능)
                w = QWidget()
                w.setFixedHeight(24)
                w.setLayout(eff_row)
                row.effects_layout.addWidget(w)

    def _reset_layers_for_current_file(self):
        locked_set = self.label_manager.prune_to_locked_only_for_current_file()

        for v in list(self._semi_memory.keys()):
            if v not in locked_set:
                del self._semi_memory[v]

        vowel_names = list(self._layer_rows.keys())
        self._rebuild_effects()
        self.set_vowels(vowel_names)
        app_logger.info(config.LOG_MSG["LAYER_SETTINGS_RESET"])
        self.label_manager.notify_apply()

    def _on_reset_order_clicked(self):
        """순서 초기화 버튼: 현재 탭에 따라 레이어/그리기 순서 초기화."""
        if self.tab_widget.currentIndex() == 0:
            self._reset_layer_order()
        else:
            self._reset_draw_order()

    def _on_reset_layers_clicked(self):
        """레이어 설정 초기화 버튼: 현재 탭에 따라 레이어/그리기 설정 초기화."""
        if self.tab_widget.currentIndex() == 0:
            self._reset_layers_for_current_file()
        else:
            self._reset_draw_layers()

    def _on_batch_delete_draw_clicked(self):
        """일괄 삭제: locked가 False인 그리기 객체만 제거. 잠금된 객체와 그 자식(area_label 등)은 유지."""
        objs = self.draw_manager.get_draw_objects()
        if not objs:
            return
        keep_ids = {
            getattr(o, "id", None)
            for o in objs
            if getattr(o, "locked", False) and getattr(o, "type", "") == "polygon"
        }
        keep_ids.discard(None)
        new_list = [
            o
            for o in objs
            if getattr(o, "locked", False)
            or (
                getattr(o, "type", "") == "area_label"
                and getattr(o, "parent_id", None) in keep_ids
            )
        ]
        self.draw_manager.set_draw_objects(new_list)
        self._selected_draw_indices = set()
        self.draw_manager.redraw()
        self.update_draw_layer_list(new_list)
        self._draw_list_placeholder.setFocus(Qt.FocusReason.OtherFocusReason)

    def _reset_draw_order(self):
        """그리기 탭 순서 초기화. 추후 _draw_layer_rows 등 연동 시 구현."""
        pass

    def _reset_draw_layers(self):
        """그리기 탭 레이어 설정 초기화. 추후 그리기 전용 overrides 연동 시 구현."""
        pass

    def _reset_layer_order(self):
        """레이어 표시 순서를 기본값(정렬)으로 초기화. 필터/디자인 설정은 그대로 유지."""
        # 전역 순서 저장소만 비우고, 현재 모음 목록을 다시 그리면 _get_ordered_vowels_for_display가 정렬 순서를 사용.
        self.label_manager.set_layer_order([])
        vowels = list(self._layer_rows.keys())
        self.set_vowels(vowels)
        if hasattr(self, "order_changed"):
            self.order_changed.emit(self._get_ordered_vowels_for_display(vowels))
        app_logger.info(config.LOG_MSG["LAYER_ORDER_RESET"])
