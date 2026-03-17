# ui_popup.py

import inspect
import platform
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QDialog,
    QButtonGroup,
    QMessageBox,
    QDockWidget,
    QApplication,
    QFrame,
    QSizePolicy,
    QFormLayout,
    QTabWidget,
)
from PyQt6.QtCore import Qt, QObject, QEvent


class TabBarWheelBlocker(QObject):
    """탭 위에서 마우스 휠로 탭이 바뀌지 않도록 휠 이벤트를 흡수합니다."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            return True
        return False


from PyQt6.QtGui import (
    QFont,
    QIcon,
    QShortcut,
    QKeySequence,
    QRegularExpressionValidator,
)
from PyQt6.QtCore import QRegularExpression
from .canvas_fixed import FixedFigureCanvas

from utils import icon_utils
import config
import app_logger
from .filter_panel import LiveVowelFilterPanel
from .design_panel import DesignSettingsPanel, NoWheelComboBox
from .icon_widgets import BidirectionalArrowButton
from .tool_indicator import ToolStatusIndicator
from .layer_dock import LayerDockWidget
from draw import DrawModeIndicator, DrawMode, draw_line, draw_polygon, draw_reference
from draw.draw_common import polygon_area, AreaLabelObject
from . import layout_constants as layout
from .display_utils import format_file_label
from utils.math_utils import hz_to_bark, bark_to_hz
import matplotlib.colors as mcolors


class ClickClearFocusFilter(QObject):
    """다른 위젯 클릭 시 지정한 LineEdit들에서 포커스를 빼서 분석 탭으로 넘깁니다."""

    def __init__(self, window, analysis_tab, edits, parent=None):
        super().__init__(parent)
        self._window = window
        self._analysis_tab = analysis_tab
        self._edits = set(edits)

    def eventFilter(self, obj, event):
        if (
            event.type() != QEvent.Type.MouseButtonPress
            or event.button() != Qt.MouseButton.LeftButton
        ):
            return False
        f = QApplication.focusWidget()
        if not f or f not in self._edits:
            return False
        try:
            # obj가 QWindow일 수 있음 → isAncestorOf는 QWidget에만 사용
            clicked_inside_edit = obj is f
            if (
                not clicked_inside_edit
                and isinstance(obj, QWidget)
                and hasattr(f, "isAncestorOf")
            ):
                clicked_inside_edit = f.isAncestorOf(obj)
            if clicked_inside_edit:
                return False
            same_window = False
            if isinstance(obj, QWidget) and hasattr(obj, "window"):
                same_window = obj.window() is self._window
            else:
                tw = f.window() if hasattr(f, "window") else None
                if tw and hasattr(tw, "windowHandle") and tw.windowHandle() is obj:
                    same_window = True
            if same_window:
                f.clearFocus()
                self._analysis_tab.setFocus()
        except (RuntimeError, TypeError):
            pass
        return False


class RangeInputFilter(QObject):
    """좌표축 범위 입력란: 숫자·소수점·마이너스 외 키는 입력되지 않게 막고 포커스 해제."""

    ALLOWED_KEYS = frozenset(
        {
            Qt.Key.Key_0,
            Qt.Key.Key_1,
            Qt.Key.Key_2,
            Qt.Key.Key_3,
            Qt.Key.Key_4,
            Qt.Key.Key_5,
            Qt.Key.Key_6,
            Qt.Key.Key_7,
            Qt.Key.Key_8,
            Qt.Key.Key_9,
            Qt.Key.Key_Period,
            Qt.Key.Key_Minus,
            Qt.Key.Key_Backspace,
            Qt.Key.Key_Delete,
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
            Qt.Key.Key_Home,
            Qt.Key.Key_End,
            Qt.Key.Key_Tab,
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        }
    )

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            mods = event.modifiers()
            if mods & Qt.KeyboardModifier.ControlModifier and key in (
                Qt.Key.Key_A,
                Qt.Key.Key_C,
                Qt.Key.Key_V,
                Qt.Key.Key_X,
            ):
                return False
            if key in self.ALLOWED_KEYS:
                return False
            obj.clearFocus()
            return True
        return False


class SmartDockWidget(QDockWidget):
    """도크가 닫힐 때 처리를 위한 커스텀 도크 위젯"""

    def __init__(self, title, parent, on_close_callback):
        super().__init__(title, parent)
        self.on_close_callback = on_close_callback

    def closeEvent(self, event):
        if self.on_close_callback:
            self.on_close_callback()
        super().closeEvent(event)


class BatchSaveDialog(QDialog):
    """일괄 저장 설정 다이얼로그"""

    def __init__(
        self,
        parent,
        controller,
        current_ranges,
        f1_unit,
        f2_unit,
        x_axis_label,
        current_sigma,
    ):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("일괄 저장 설정")
        self.setFixedSize(
            config.DIALOG_BATCH_SAVE_WIDTH_PX, config.DIALOG_BATCH_SAVE_HEIGHT_PX
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.ui_font_name = parent.ui_font_name
        self._apply_pyqt6_icon()
        self._setup_ui(current_ranges, f1_unit, f2_unit, x_axis_label, current_sigma)

    def _apply_pyqt6_icon(self):
        try:
            icon_path = icon_utils.get_icon_path()
            if icon_path:
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

    def _setup_ui(self, ranges, f1_unit, f2_unit, x_label, sigma):
        self.setStyleSheet("""
            QDialog { background-color: white; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 26, 28, 22)
        main_layout.setSpacing(18)

        title = QLabel("일괄 저장 옵션을 확인하고 설정하세요.")
        title.setFont(QFont(self.ui_font_name, 12, QFont.Weight.Bold))
        main_layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        num_validator = QRegularExpressionValidator(
            QRegularExpression(r"^-?\d*\.?\d*$")
        )
        f1_frame = QHBoxLayout()
        self.ent_y_min = QLineEdit(ranges["y_min"])
        self.ent_y_max = QLineEdit(ranges["y_max"])
        for le in (self.ent_y_min, self.ent_y_max):
            le.setFixedWidth(config.RANGE_EDIT_FIXED_WIDTH_PX)
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            le.setValidator(num_validator)
        f1_frame.addWidget(self.ent_y_min)
        f1_frame.addWidget(QLabel("~"))
        f1_frame.addWidget(self.ent_y_max)
        f1_frame.addStretch()
        form.addRow(f"F1 ({f1_unit}):", f1_frame)

        f2_frame = QHBoxLayout()
        self.ent_x_min = QLineEdit(ranges["x_min"])
        self.ent_x_max = QLineEdit(ranges["x_max"])
        for le in (self.ent_x_min, self.ent_x_max):
            le.setFixedWidth(config.RANGE_EDIT_FIXED_WIDTH_PX)
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            le.setValidator(num_validator)
        f2_frame.addWidget(self.ent_x_min)
        f2_frame.addWidget(QLabel("~"))
        f2_frame.addWidget(self.ent_x_max)
        f2_frame.addStretch()
        form.addRow(f"{x_label} ({f2_unit}):", f2_frame)

        seg_btn_style = """
            QPushButton { background-color: #f5f7fa; border: 1px solid #dcdfe6; color: #606266; padding: 6px 14px; }
            QPushButton:hover { background-color: #ecf5ff; color: #409eff; border-color: #c6e2ff; }
            QPushButton:checked { background-color: #409eff; color: white; border-color: #409eff; font-weight: bold; }
        """
        sig_container = QWidget()
        sig_container.setObjectName("SigSegContainer")
        sig_h = QHBoxLayout(sig_container)
        sig_h.setContentsMargins(0, 5, 0, 5)
        sig_h.setSpacing(0)
        self.sig_group = QButtonGroup(self)
        self.sig_group.setExclusive(True)
        _seg_btn_radius = [
            "QPushButton { border-top-left-radius: 4px; border-bottom-left-radius: 4px; border-right: none; }",
            "QPushButton { border-top-right-radius: 4px; border-bottom-right-radius: 4px; border-left: none; }",
        ]
        for i, (text, val) in enumerate([("1σ (68%)", "1.0"), ("2σ (95%)", "2.0")]):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("val", val)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(seg_btn_style + _seg_btn_radius[i])
            self.sig_group.addButton(btn, i)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            sig_h.addWidget(btn, stretch=1)
        if sigma == "1.0":
            self.sig_group.buttons()[0].setChecked(True)
        else:
            self.sig_group.buttons()[1].setChecked(True)
        form.addRow("신뢰 타원 크기:", sig_container)

        fmt_container = QWidget()
        fmt_h = QHBoxLayout(fmt_container)
        fmt_h.setContentsMargins(0, 5, 0, 5)
        fmt_h.setSpacing(0)
        self.fmt_group = QButtonGroup(self)
        self.fmt_group.setExclusive(True)
        _fmt_btn_radius = [
            "QPushButton { border-top-left-radius: 4px; border-bottom-left-radius: 4px; border-right: none; }",
            "QPushButton { border-left: none; border-right: none; }",
            "QPushButton { border-top-right-radius: 4px; border-bottom-right-radius: 4px; border-left: none; }",
        ]
        for i, (text, val) in enumerate(
            [("JPG", "jpg"), ("PNG", "png"), ("EPS", "eps")]
        ):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("val", val)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(seg_btn_style + _fmt_btn_radius[i])
            self.fmt_group.addButton(btn, i)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            fmt_h.addWidget(btn, stretch=1)
        self.fmt_group.buttons()[0].setChecked(True)
        form.addRow("저장 형식:", fmt_container)

        # 폼 전체를 가운데 정렬하기 위해 컨테이너 위젯에 담아서 추가
        form_container = QWidget()
        form_container.setLayout(form)
        form_container.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        main_layout.addWidget(form_container, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("취소")
        btn_cancel.setFixedSize(100, 38)
        btn_cancel.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        btn_cancel.clicked.connect(self.reject)

        btn_next = QPushButton("저장 실행")
        btn_next.setFixedSize(140, 38)
        btn_next.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px;"
        )
        btn_next.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        btn_next.setDefault(True)
        btn_next.clicked.connect(self.on_next)

        btn_layout.addWidget(btn_cancel)
        btn_layout.setSpacing(15)
        btn_layout.addWidget(btn_next)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def on_next(self):
        ranges = {
            "y_min": self.ent_y_min.text(),
            "y_max": self.ent_y_max.text(),
            "x_min": self.ent_x_min.text(),
            "x_max": self.ent_x_max.text(),
        }
        sig_btn = self.sig_group.checkedButton()
        sigma = sig_btn.property("val") if sig_btn else "2.0"
        fmt_btn = self.fmt_group.checkedButton()
        img_format = fmt_btn.property("val") if fmt_btn else "jpg"

        self.accept()

        parent_popup = self.parent()
        design_settings = (
            parent_popup.design_settings
            if hasattr(parent_popup, "design_settings")
            else None
        )

        # main.py가 업데이트되기 전에도 튕기지 않도록 파라미터 유무를 안전하게 검사합니다.
        sig_params = inspect.signature(
            self.controller.batch_download_with_options
        ).parameters
        if "design_settings" in sig_params:
            self.controller.batch_download_with_options(
                ranges, sigma, img_format, design_settings=design_settings
            )
        else:
            self.controller.batch_download_with_options(ranges, sigma, img_format)


class PlotPopup(QMainWindow):
    """메인 결과 시각화 창 (단일 도크 통합 탭 버전)"""

    def __init__(
        self, parent, controller, figure, x_axis_label="F2", title="Plot Result"
    ):
        super().__init__()

        self.controller = controller
        self.figure = figure
        self.x_axis_label = x_axis_label
        # 이 창 인스턴스 전용 라벨 오프셋 캐시 (필요 시 사용)
        self.custom_offsets = {}

        self.was_dock_visible = True
        self.dock_floating_state = False

        self.vowel_filter_state = {}
        self.vowel_filter_state_by_file = {}  # idx -> { vowel: 'ON'|'OFF'|'SEMI' }
        self.layer_design_overrides = {}  # vowel -> {lbl_color, centroid_marker, ell_style, ...} (레이어 설정 도크)
        self.layer_design_overrides_by_file = {}  # idx -> { vowel: {} } (파일 전환 시 복원용)
        # 레이어 순서는 파일 간 공통으로 사용 (모든 파일에서 동일 모음 세트를 쓴다는 전제)
        self.layer_order = []  # [vowel, ...] (레이어 표시 순서, 드래그로 변경)
        self.layer_locked_vowels_by_file = {}  # idx -> set(vowel): 레이어 잠금(초기화 제외). 파일별로 별도 유지.
        self.design_settings = {}
        self.filter_panel = None
        self._layer_dock_was_docked_before_hide = False  # 창 크기 연동용

        # 컨트롤러가 set_initial_plot_state / set_draw_result 로 주입 (직접 대입 대신 명시적 API)
        self.fixed_plot_params = {}
        self.plot_data_snapshot = None
        self.current_idx = 0
        self.snapping_data = []
        self.label_data = []
        self.label_text_artists = []
        self._plot_key = None

        data_list = self.plot_data_snapshot or self.controller.get_plot_data_list()
        idx = (
            self.current_idx
            if self.plot_data_snapshot is not None
            else self.controller.get_current_index()
        )
        current_data = data_list[idx]
        self._update_window_title(current_data["name"])

        self.resize(layout.PLOT_WINDOW_WIDTH_PX, config.PLOT_WINDOW_HEIGHT_PX)
        self.ui_font_name = (
            config.UI_FONT_WINDOWS
            if platform.system() == "Windows"
            else config.UI_FONT_MAC
        )

        self.setCorner(Qt.Corner.TopLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.TopRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.setCorner(
            Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea
        )

        self.setDockOptions(QMainWindow.DockOption.AnimatedDocks)
        self.setDockNestingEnabled(False)

        self._apply_pyqt6_icon()

        self.setStyleSheet(
            """
            QMainWindow { background-color: #F5F7FA; }
            QWidget#CentralWidget { background-color: transparent; }

            QMainWindow::separator {
                width: 0px;
                height: 0px;
                margin: 0px;
                padding: 0px;
                border: none;
                background: transparent;
            }

            QDockWidget::title {
                text-align: left;
                background: #FFFFFF;
                padding-left: 10px;
                padding-top: 6px;
                padding-bottom: 6px;
                font-size: 11px;
                font-weight: bold;
                color: #555555;
            }

            QTabWidget::pane {
                border-top: 1px solid #E4E7ED;
                background: white;
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

        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)

        self.central_outer_layout = QHBoxLayout(self.central_widget)
        self.central_outer_layout.setContentsMargins(0, 0, 0, 0)
        self.central_outer_layout.setSpacing(0)

        self.sep_left = QFrame()
        self.sep_left.setFixedWidth(layout.SEPARATOR_WIDTH_PX)
        self.sep_left.setStyleSheet(
            "background-color: %s; border: none;" % config.SEPARATOR_BG_COLOR
        )

        self.sep_right = QFrame()
        self.sep_right.setFixedWidth(layout.SEPARATOR_WIDTH_PX)
        self.sep_right.setStyleSheet(
            "background-color: %s; border: none;" % config.SEPARATOR_BG_COLOR
        )

        canvas_container = QWidget()
        canvas_container.setStyleSheet("background-color: white;")
        central_layout = QVBoxLayout(canvas_container)
        central_layout.setContentsMargins(
            config.CENTRAL_LAYOUT_MARGIN_PX,
            config.CENTRAL_LAYOUT_MARGIN_PX,
            config.CENTRAL_LAYOUT_MARGIN_PX,
            config.CENTRAL_LAYOUT_MARGIN_PX,
        )
        central_layout.setSpacing(4)

        # 상단 우측에 눈금자/라벨 이동 상태 인디케이터 박스 배치
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(0)
        top_row.addStretch()
        self.tool_indicator = ToolStatusIndicator(
            canvas_container, ui_font_name=self.ui_font_name
        )
        top_row.addWidget(self.tool_indicator, alignment=Qt.AlignmentFlag.AlignRight)
        central_layout.addLayout(top_row)

        # 캔버스 고정 크기 + 좌측 하단 그리기 모드 인디케이터 오버레이 (기존 영역 길이 변경 없음)
        central_layout.addStretch(1)
        canvas_wrapper = QWidget()
        canvas_wrapper.setFixedSize(
            config.PLOT_CANVAS_SIZE_PX, config.PLOT_CANVAS_SIZE_PX
        )
        self.canvas = FixedFigureCanvas(self.figure)
        self.canvas.setParent(canvas_wrapper)
        self.canvas.setGeometry(
            0, 0, config.PLOT_CANVAS_SIZE_PX, config.PLOT_CANVAS_SIZE_PX
        )
        self.canvas.setFixedSize(config.PLOT_CANVAS_SIZE_PX, config.PLOT_CANVAS_SIZE_PX)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.draw_indicator = DrawModeIndicator(canvas_wrapper)
        self.draw_indicator.setParent(canvas_wrapper)
        self._draw_indicator_height = 34
        self.draw_indicator.move(
            8, config.PLOT_CANVAS_SIZE_PX - 8 - self._draw_indicator_height
        )
        self.draw_indicator.mode_changed.connect(self._on_draw_mode_changed)
        self._draw_tool = None
        self._draw_objects_by_file = {}  # current_idx -> list of draw objects (파일별 분리)
        self._draw_layer_artists = []  # 그리기 레이어로 추가한 아티스트 (재그리기 전 제거용)
        self.draw_indicator.hide()
        central_layout.addWidget(canvas_wrapper, alignment=Qt.AlignmentFlag.AlignCenter)
        central_layout.addStretch(1)

        self.central_outer_layout.addWidget(self.sep_left)
        self.central_outer_layout.addWidget(canvas_container)
        self.central_outer_layout.addWidget(self.sep_right)

        self._build_unified_dock()
        self._bind_shortcuts()
        self._update_nav_buttons()

    def _apply_pyqt6_icon(self):
        try:
            icon_path = icon_utils.get_icon_path()
            if icon_path:
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

    def set_initial_plot_state(
        self, fixed_plot_params, plot_data_snapshot, current_idx
    ):
        """컨트롤러가 팝업을 연 직후 호출. 상태를 명시적으로 주입 (몽키 패칭 대신)."""
        self.fixed_plot_params = fixed_plot_params
        self.plot_data_snapshot = plot_data_snapshot
        self.current_idx = current_idx
        if (
            hasattr(self, "btn_vowel_analysis")
            and plot_data_snapshot
            and len(plot_data_snapshot) >= 1
        ):
            self.btn_vowel_analysis.setEnabled(True)

    def set_draw_result(self, snapping_data, label_data, label_text_artists, plot_key):
        """draw_plot 직후 호출. 스냅/라벨/플롯키를 명시적으로 주입."""
        self.snapping_data = snapping_data
        self.label_data = label_data
        self.label_text_artists = label_text_artists
        self._plot_key = plot_key
        self._redraw_draw_layer()
        if (
            hasattr(self, "_layer_dock_content")
            and self._layer_dock_content is not None
        ):
            self._layer_dock_content.update_draw_layer_list(
                self._get_current_draw_objects()
            )

    def get_filter_state(self):
        return self.vowel_filter_state

    def get_design_settings(self):
        return self.design_settings

    def get_layer_design_overrides(self):
        return self.layer_design_overrides

    def _build_unified_dock(self):
        self.dock_widget = QDockWidget("도구 및 설정", self)
        self.dock_widget.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        self.dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        self.dock_container = QWidget()
        self.dock_container.setObjectName("DockContainer")
        self.dock_container.setStyleSheet(
            "#DockContainer { background-color: #FFFFFF; }"
        )

        self.dock_container.setMinimumWidth(layout.DOCK_WIDTH_PX)
        self.dock_container.setMaximumWidth(layout.DOCK_WIDTH_PX)
        self.dock_container.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )

        dock_layout = QVBoxLayout(self.dock_container)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._tab_wheel_blocker = TabBarWheelBlocker(self)
        self.tab_widget.tabBar().installEventFilter(self._tab_wheel_blocker)

        self.analysis_tab = QWidget()
        self._setup_analysis_ui(self.analysis_tab)
        self.tab_widget.addTab(self.analysis_tab, "분석 도구")

        # 디자인 탭을 분리된 패널 모듈로 교체 및 초기화
        self.design_tab = DesignSettingsPanel(
            parent=self, ui_font_name=self.ui_font_name
        )
        self.design_settings = self.design_tab.get_current_settings()
        self.design_tab.settings_changed.connect(self._on_design_settings_changed)
        self.design_tab.btn_lock.toggled.connect(self._log_design_lock)
        # 설정 유지 기본 ON과 인디케이터 동기화: 처음부터 자물쇠 불 켜진 상태
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_lock_on(self.design_tab.btn_lock.isChecked())

        # --- [수정된 부분] 시그널 실행 순서 강제 재배치 ---
        try:
            self.design_tab.btn_reset.clicked.disconnect(
                self.design_tab._reset_to_defaults
            )  # 1. 잘못된 순서로 연결된 기존 시그널 끊기
        except TypeError:
            pass

        self.design_tab.btn_reset.clicked.connect(
            self._log_design_reset
        )  # 2. 로그 기록 (먼저 실행)
        self.design_tab.btn_reset.clicked.connect(
            lambda: self.controller.clear_label_offsets_for_popup(self)
        )  # 3. 데이터 삭제 (먼저 실행)
        self.design_tab.btn_reset.clicked.connect(
            self.design_tab._reset_to_defaults
        )  # 4. 화면 다시 그리기 (가장 마지막에 실행)
        # ---------------------------------------------------

        self.design_tab.label_move_clicked.connect(self.on_toggle_label_move)
        self.tab_widget.addTab(self.design_tab, "디자인 설정")

        dock_layout.addWidget(self.tab_widget)
        self.dock_widget.setWidget(self.dock_container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_widget)

        self.dock_widget.dockLocationChanged.connect(self._on_dock_state_changed)
        self.dock_widget.topLevelChanged.connect(self._on_dock_state_changed)
        self._on_dock_state_changed()

        # 레이어 설정 도크 (도구 도크가 좌측, 레이어는 우측 기본 / 닫기는 불가, 떼기는 허용)
        self.layer_dock_widget = QDockWidget("레이어 설정", self)
        self.layer_dock_widget.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.layer_dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.layer_dock_widget.setMinimumWidth(layout.DOCK_WIDTH_PX)
        self.layer_dock_widget.setMaximumWidth(layout.DOCK_WIDTH_PX)
        self._layer_dock_container = QWidget()
        self._layer_dock_container.setObjectName("LayerDockContainer")
        self._layer_dock_container.setStyleSheet(
            "#LayerDockContainer { background-color: #FFFFFF; }"
        )
        self._layer_dock_container.setMinimumWidth(layout.DOCK_WIDTH_PX)
        self._layer_dock_container.setMaximumWidth(layout.DOCK_WIDTH_PX)
        self._layer_dock_container.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        layer_dock_inner = QVBoxLayout(self._layer_dock_container)
        layer_dock_inner.setContentsMargins(0, 0, 0, 0)
        layer_dock_inner.setSpacing(0)
        self._layer_dock_content = LayerDockWidget(self, ui_font_name=self.ui_font_name)
        # 레이어 도크는 상태 변경을 시그널로만 알리고, 실제 플롯 갱신은 팝업에서 관리
        self._layer_dock_content.filter_state_changed.connect(
            self._on_layer_filter_state_changed
        )
        self._layer_dock_content.overrides_changed.connect(
            self._on_layer_overrides_changed
        )
        layer_dock_inner.addWidget(self._layer_dock_content)
        self.layer_dock_widget.setWidget(self._layer_dock_container)
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.layer_dock_widget
        )
        self.layer_dock_widget.dockLocationChanged.connect(
            self._on_layer_dock_location_changed
        )
        self.layer_dock_widget.topLevelChanged.connect(
            self._on_layer_dock_location_changed
        )
        self.layer_dock_widget.visibilityChanged.connect(
            self._on_layer_dock_visibility_changed
        )
        self._layer_dock_visible = True
        self._layer_dock_floating = False
        self._layer_dock_geometry = None
        self._layer_dock_saved_area = Qt.DockWidgetArea.RightDockWidgetArea
        self._layer_dock_saved_floating = False
        self._layer_dock_saved_geometry = None
        self._layer_dock_docked_visible = True  # 폭 조정 중복 방지용
        self._update_dock_separators()
        self._resize_for_dock_state()

    def _on_layer_dock_location_changed(self, *args):
        if self.layer_dock_widget.isFloating():
            self._layer_dock_floating = True
            self._layer_dock_geometry = self.layer_dock_widget.geometry()
        else:
            self._layer_dock_floating = False
            # 한 쪽 한 도크: 레이어가 막 붙었을 때 같은 쪽이면 레이어를 반대쪽으로 이동 (먼저 붙은 쪽이 임자)
            layer_area = self.dockWidgetArea(self.layer_dock_widget)
            if not self.dock_widget.isFloating() and self.dock_widget.isVisible():
                tools_area = self.dockWidgetArea(self.dock_widget)
                if layer_area == tools_area:
                    opposite = (
                        Qt.DockWidgetArea.RightDockWidgetArea
                        if tools_area == Qt.DockWidgetArea.LeftDockWidgetArea
                        else Qt.DockWidgetArea.LeftDockWidgetArea
                    )
                    self.addDockWidget(opposite, self.layer_dock_widget)
        self._resize_for_dock_state()
        self._update_dock_separators()

    def _on_layer_dock_visibility_changed(self, visible):
        self._layer_dock_visible = visible
        self._update_dock_separators()
        self._update_layer_button_style()

    def _on_dock_state_changed(self, *args):
        # 한 쪽 한 도크: 도구 도크가 막 붙었을 때 같은 쪽이면 도구를 반대쪽으로 이동 (먼저 붙은 쪽이 임자)
        layer = getattr(self, "layer_dock_widget", None)
        if layer and not self.dock_widget.isFloating() and not layer.isFloating():
            tools_area = self.dockWidgetArea(self.dock_widget)
            layer_area = self.dockWidgetArea(layer)
            if tools_area == layer_area:
                opposite = (
                    Qt.DockWidgetArea.RightDockWidgetArea
                    if tools_area == Qt.DockWidgetArea.LeftDockWidgetArea
                    else Qt.DockWidgetArea.LeftDockWidgetArea
                )
                self.addDockWidget(opposite, self.dock_widget)
        self._resize_for_dock_state()
        self._update_dock_separators()

    def _resize_for_dock_state(self):
        """창 가로는 항상 도크 둘 다 붙었을 때 너비(PLOT_WINDOW_WIDTH_PX)로 유지. (플로팅 시 줄이지 않음)"""
        w = layout.PLOT_WINDOW_WIDTH_PX
        self.resize(w, self.height())

    def _update_dock_separators(self):
        """도구 도크·레이어 도크 위치에 따라 central 좌우 얇은 선(sep) 표시."""
        if getattr(self, "dock_widget", None) is None:
            return
        show_left = False
        show_right = False
        if not self.dock_widget.isFloating() and self.dock_widget.isVisible():
            area = self.dockWidgetArea(self.dock_widget)
            if area == Qt.DockWidgetArea.LeftDockWidgetArea:
                show_left = True
            elif area == Qt.DockWidgetArea.RightDockWidgetArea:
                show_right = True
        if (
            getattr(self, "layer_dock_widget", None)
            and not self.layer_dock_widget.isFloating()
            and self.layer_dock_widget.isVisible()
        ):
            area = self.dockWidgetArea(self.layer_dock_widget)
            if area == Qt.DockWidgetArea.LeftDockWidgetArea:
                show_left = True
            elif area == Qt.DockWidgetArea.RightDockWidgetArea:
                show_right = True
        self.sep_left.setVisible(show_left)
        self.sep_right.setVisible(show_right)

    def _setup_analysis_ui(self, parent_widget):
        parent_widget.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(12, 15, 12, 15)
        layout.setSpacing(12)

        font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        font_normal = QFont(self.ui_font_name, 9)

        nav_group = QVBoxLayout()
        self.lbl_info = QLabel("Loading...")
        self.lbl_info.setFont(font_bold)
        self.lbl_info.setStyleSheet("color: #1976D2; border: none;")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_group.addWidget(self.lbl_info)

        btn_h = QHBoxLayout()
        self.btn_prev = QPushButton("◀ 이전")
        self.btn_next = QPushButton("다음 ▶")

        self.nav_btn_style = """
            QPushButton { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; color: #333333; }
            QPushButton:hover { background-color: #F5F7FA; color: #409EFF; border-color: #C0C4CC; }
            QPushButton:disabled { background-color: #F5F7FA; color: #C0C4CC; border-color: #E4E7ED; }
        """
        for btn in (self.btn_prev, self.btn_next):
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self.nav_btn_style)
            btn.setFont(font_normal)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.btn_prev.clicked.connect(self.on_nav_prev_clicked)
        self.btn_next.clicked.connect(self.on_nav_next_clicked)

        btn_h.addWidget(self.btn_prev)
        btn_h.addWidget(self.btn_next)
        nav_group.addLayout(btn_h)
        layout.addLayout(nav_group)

        self.line1 = QFrame()
        self.line1.setFrameShape(QFrame.Shape.HLine)
        self.line1.setStyleSheet("color: #E4E7ED;")
        layout.addWidget(self.line1)

        clean_line_edit_style = """
            QLineEdit { border: 1px solid #DCDFE6; border-radius: 3px; background-color: transparent; padding: 2px; font-size: 12px;}
            QLineEdit:focus { border: 1px solid #409EFF; }
        """
        range_group = QVBoxLayout()
        range_group.setSpacing(8)
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
            le.setStyleSheet(clean_line_edit_style)
            le.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
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
                    out = float(bark_to_hz(val))
                    self._hz_edit.setText(f"{out:.1f}")
                elif hz_text:
                    val = float(hz_text)
                    out = float(hz_to_bark(val))
                    self._bark_edit.setText(f"{out:.2f}")
                elif bark_text:
                    val = float(bark_text)
                    out = float(bark_to_hz(val))
                    self._hz_edit.setText(f"{out:.1f}")
            except ValueError:
                pass

        self._range_toggle_btn.clicked.connect(_toggle_converter)
        self._conv_btn.clicked.connect(_on_conv_clicked)

        def _header_clicked(event):
            if event.button() == Qt.MouseButton.LeftButton:
                _toggle_converter()

        range_header.mousePressEvent = _header_clicked

        range_group.addWidget(range_header)

        self.range_widgets = {}

        AXIS_LABEL_WIDTH = 58
        f1_row = QHBoxLayout()
        self.lbl_f1_axis = QLabel("F1:", font=font_normal)
        self.lbl_f1_axis.setFixedWidth(AXIS_LABEL_WIDTH)
        self.range_widgets["y_min"] = QLineEdit()
        self.range_widgets["y_max"] = QLineEdit()
        for le in (self.range_widgets["y_min"], self.range_widgets["y_max"]):
            le.setFixedWidth(48)
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            le.setStyleSheet(clean_line_edit_style)
            le.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        f1_row.addWidget(self.lbl_f1_axis)
        f1_row.addWidget(self.range_widgets["y_min"])
        f1_row.addWidget(QLabel("~", font=font_normal))
        f1_row.addWidget(self.range_widgets["y_max"])
        f1_row.addSpacing(8)
        self.lbl_f1_unit = QLabel("(Hz)", font=font_normal)
        f1_row.addWidget(self.lbl_f1_unit)
        f1_row.addStretch()
        range_group.addLayout(f1_row)

        f2_row = QHBoxLayout()
        self.lbl_x_axis = QLabel(f"{self.x_axis_label}:", font=font_normal)
        self.lbl_x_axis.setFixedWidth(AXIS_LABEL_WIDTH)
        self.range_widgets["x_min"] = QLineEdit()
        self.range_widgets["x_max"] = QLineEdit()
        for le in (self.range_widgets["x_min"], self.range_widgets["x_max"]):
            le.setFixedWidth(48)
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            le.setStyleSheet(clean_line_edit_style)
            le.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        f2_row.addWidget(self.lbl_x_axis)
        f2_row.addWidget(self.range_widgets["x_min"])
        f2_row.addWidget(QLabel("~", font=font_normal))
        f2_row.addWidget(self.range_widgets["x_max"])
        f2_row.addSpacing(8)
        self.lbl_f2_unit = QLabel("(Hz)", font=font_normal)
        f2_row.addWidget(self.lbl_f2_unit)
        f2_row.addStretch()
        range_group.addLayout(f2_row)

        range_edits = [
            self.range_widgets["y_min"],
            self.range_widgets["y_max"],
            self.range_widgets["x_min"],
            self.range_widgets["x_max"],
            self._hz_edit,
            self._bark_edit,
        ]
        self._range_input_filter = RangeInputFilter(self)
        for le in range_edits:
            le.installEventFilter(self._range_input_filter)

        sig_h = QHBoxLayout()
        sig_h.addWidget(QLabel("신뢰 타원:", font=font_normal))
        self.cb_sigma = NoWheelComboBox()
        self.cb_sigma.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.cb_sigma.addItems(["1.0", "2.0"])
        self.cb_sigma.setCurrentText("2.0")
        sig_h.addWidget(self.cb_sigma)
        sig_h.addWidget(QLabel("σ", font=font_normal))
        sig_h.addStretch()
        range_group.addLayout(sig_h)

        apply_h = QHBoxLayout()
        btn_reset = QPushButton("초기화")
        btn_apply = QPushButton("적용")
        for btn in (btn_reset, btn_apply):
            btn.setFixedHeight(28)
            btn.setFont(font_normal)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        btn_apply.setStyleSheet(
            "background-color: #E6A23C; color: white; font-weight: bold; border-radius: 4px;"
        )
        btn_reset.setStyleSheet(
            "background-color: #909399; color: white; font-weight: bold; border-radius: 4px;"
        )

        btn_apply.clicked.connect(self._on_range_apply_clicked)
        btn_reset.clicked.connect(self.on_reset_clicked)

        apply_h.addWidget(btn_reset)
        apply_h.addWidget(btn_apply)
        range_group.addLayout(apply_h)
        range_group.addWidget(self._converter_container)
        layout.addLayout(range_group)

        analysis_edits = set(self.range_widgets.values()) | {
            self._hz_edit,
            self._bark_edit,
        }
        self._click_clear_focus_filter = ClickClearFocusFilter(
            self, parent_widget, analysis_edits
        )
        QApplication.instance().installEventFilter(self._click_clear_focus_filter)

        self.line2 = QFrame()
        self.line2.setFrameShape(QFrame.Shape.HLine)
        self.line2.setStyleSheet("color: #E4E7ED;")
        layout.addWidget(self.line2)

        tool_group = QVBoxLayout()
        tool_group.setSpacing(8)
        t_lbl = QLabel("분석 도구", font=font_bold)
        t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tool_group.addWidget(t_lbl)

        self.btn_vowel_analysis = QPushButton("모음 상세 분석")
        self.btn_vowel_analysis.setFixedHeight(35)
        self.btn_vowel_analysis.setFont(font_normal)
        self.btn_vowel_analysis.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_vowel_analysis.setEnabled(False)
        self.btn_vowel_analysis.setStyleSheet(self.nav_btn_style)
        self.btn_vowel_analysis.clicked.connect(self._on_vowel_analysis_clicked)
        tool_group.addWidget(self.btn_vowel_analysis)

        self.btn_compare = QPushButton("다중 플롯 모드 (M)")
        self.btn_compare.setFixedHeight(35)
        self.btn_compare.setFont(font_normal)
        self.btn_compare.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_compare.setStyleSheet(self.nav_btn_style)
        data_list = (
            getattr(self, "plot_data_snapshot", None)
            or self.controller.get_plot_data_list()
        )
        self.btn_compare.setEnabled(len(data_list) >= 2)
        self.btn_compare.clicked.connect(self.on_btn_compare_click)
        tool_group.addWidget(self.btn_compare)

        self.btn_ruler = QPushButton("눈금자 툴 (R)")
        self.btn_ruler.setObjectName("BtnRuler")
        self.btn_ruler.setCheckable(True)
        self.btn_ruler.setFixedHeight(35)
        self.btn_ruler.setFont(font_normal)
        self.btn_ruler.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_ruler.setStyleSheet("""
            QPushButton#BtnRuler { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #333;}
            QPushButton#BtnRuler:hover:!checked { background-color: #E4E7ED; border: 1px solid #C0C4CC; }
            QPushButton#BtnRuler:checked { background-color: #67C23A; color: white; font-weight: bold; border: none; }
        """)
        self.btn_ruler.clicked.connect(self.on_toggle_ruler)
        tool_group.addWidget(self.btn_ruler)

        self.btn_draw = QPushButton("그리기 (P)")
        self.btn_draw.setToolTip("")
        self.btn_draw.setCheckable(True)
        self.btn_draw.setFixedHeight(35)
        self.btn_draw.setFont(font_normal)
        self.btn_draw.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_draw.setEnabled(True)
        self.btn_draw.setStyleSheet("""
            QPushButton { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #333; }
            QPushButton:checked { background-color: #409EFF; color: white; font-weight: bold; border: none; }
            QPushButton:hover:!checked { background-color: #E4E7ED; }
        """)
        self.btn_draw.clicked.connect(self._on_toggle_draw)
        tool_group.addWidget(self.btn_draw)

        layout.addLayout(tool_group)
        layout.addStretch()

        export_group = QVBoxLayout()
        export_group.setSpacing(6)

        save_h = QHBoxLayout()
        save_h.setSpacing(4)
        btn_jpg = QPushButton("JPG 저장")
        btn_png = QPushButton("PNG 저장")
        btn_eps = QPushButton("EPS 저장")

        for btn, fmt in zip([btn_jpg, btn_png, btn_eps], ["jpg", "png", "eps"]):
            btn.setFixedHeight(34)
            btn.setFont(QFont(self.ui_font_name, 8))
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(
                "background-color: white; border: 1px solid #C0C4CC; border-radius: 4px;"
            )
            btn.clicked.connect(
                lambda checked, f=fmt: self.controller.download_plot(
                    self.figure, f, parent_window=self
                )
            )
            save_h.addWidget(btn)
        export_group.addLayout(save_h)

        btn_batch = QPushButton("일괄 자동 저장")
        btn_batch.setFixedHeight(38)
        btn_batch.setFont(font_normal)
        btn_batch.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_batch.setStyleSheet(
            "background-color: #409EFF; color: white; font-weight: bold; border-radius: 4px;"
        )
        btn_batch.clicked.connect(self.on_batch_save)
        export_group.addWidget(btn_batch)

        layout.addLayout(export_group)

    def _on_design_settings_changed(self, settings):
        """디자인 패널의 설정이 변경되었을 때 실시간 반영을 위한 콜백"""
        self.design_settings = settings
        if (
            hasattr(self, "_layer_dock_content")
            and self._layer_dock_content is not None
        ):
            self._layer_dock_content._sync_design_controls_to_selection()
        self.on_apply()

    def _update_window_title(self, file_name):
        base = f"Plot Result - {file_name}"
        mode = self.controller.get_outlier_mode()
        if mode == "1sigma":
            base += " (이상치 제거 : 1σ)"
        elif mode == "2sigma":
            base += " (이상치 제거 : 2σ)"
        self.setWindowTitle(base)

    def closeEvent(self, event):
        if (
            hasattr(self, "_click_clear_focus_filter")
            and self._click_clear_focus_filter is not None
        ):
            try:
                QApplication.instance().removeEventFilter(
                    self._click_clear_focus_filter
                )
            except Exception:
                pass
            self._click_clear_focus_filter = None
        try:
            # 창이 닫힐 때 이 팝업과 연결된 모든 라벨 오프셋을 완전히 제거
            if hasattr(self.controller, "clear_label_offsets_for_popup"):
                self.controller.clear_label_offsets_for_popup(self)

            if self.filter_panel is not None and self.filter_panel.isVisible():
                self.filter_panel.close()

            if hasattr(self, "dock_widget") and self.dock_widget:
                self.dock_widget.close()
                self.dock_widget.deleteLater()
                self.dock_widget = None
            if hasattr(self, "layer_dock_widget") and self.layer_dock_widget:
                # 플로팅 여부와 관계없이 메인 창과 함께 정리되도록 보장
                try:
                    self.layer_dock_widget.setParent(self)
                except Exception:
                    pass
                self.layer_dock_widget.close()
                self.layer_dock_widget.deleteLater()
                self.layer_dock_widget = None

            if hasattr(self.controller, "remove_popup"):
                self.controller.remove_popup(self)

            # Matplotlib Figure/Canvas 명시적 해제로 메모리 누수 방지
            if hasattr(self, "figure") and self.figure is not None:
                self.figure.clear()
                self.figure = None
            if hasattr(self, "canvas") and self.canvas is not None:
                self.canvas.deleteLater()
                self.canvas = None
        except Exception:
            pass

        event.accept()

    def _is_input_focused(self):
        return isinstance(QApplication.focusWidget(), QLineEdit)

    def _bind_shortcuts(self):
        QShortcut(
            QKeySequence(Qt.Key.Key_A), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_switch_to_tab(0))
        QShortcut(
            QKeySequence(Qt.Key.Key_D), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_switch_to_tab(1))
        QShortcut(QKeySequence(Qt.Key.Key_Tab), self).activated.connect(
            self._toggle_panels_visibility
        )

        QShortcut(QKeySequence("Left"), self).activated.connect(self._safe_nav_prev)
        QShortcut(QKeySequence("Right"), self).activated.connect(self._safe_nav_next)

        QShortcut(
            QKeySequence(Qt.Key.Key_R), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_ruler)
        QShortcut(
            QKeySequence(Qt.Key.Key_T), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_label_move)
        QShortcut(
            QKeySequence(Qt.Key.Key_M), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_compare_click)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._safe_save_jpg)

        QShortcut(
            QKeySequence("Esc"), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_cancel_ruler_or_draw)
        QShortcut(
            QKeySequence(Qt.Key.Key_Return),
            self,
            context=Qt.ShortcutContext.ApplicationShortcut,
        ).activated.connect(self._safe_draw_complete)
        QShortcut(
            QKeySequence(Qt.Key.Key_Enter),
            self,
            context=Qt.ShortcutContext.ApplicationShortcut,
        ).activated.connect(self._safe_draw_complete)
        QShortcut(
            QKeySequence(QKeySequence.StandardKey.Undo),
            self,
            context=Qt.ShortcutContext.ApplicationShortcut,
        ).activated.connect(self._safe_draw_rollback)
        QShortcut(
            QKeySequence(Qt.Key.Key_P), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_draw)
        # 그리기 모드에서 도구 선택: 1=선, 2=영역, 3=수평 참조선, 4=수직 참조선
        QShortcut(
            QKeySequence(Qt.Key.Key_1), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.LINE))
        QShortcut(
            QKeySequence(Qt.Key.Key_2), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.POLYGON))
        QShortcut(
            QKeySequence(Qt.Key.Key_3), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.REF_H))
        QShortcut(
            QKeySequence(Qt.Key.Key_4), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.REF_V))
        # L: 설정 유지 토글
        QShortcut(
            QKeySequence(Qt.Key.Key_L), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_design_lock)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(
            self._safe_batch_save
        )
        QShortcut(
            QKeySequence("Ctrl+B"), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_bold)
        QShortcut(
            QKeySequence("Ctrl+I"), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_italic)

    def _safe_cancel_ruler_or_draw(self):
        if self._is_input_focused():
            return
        if getattr(self, "btn_draw", None) and self.btn_draw.isChecked():
            # 그리기 모드는 유지하고, 현재 그리던 오브젝트만 취소 (도구/인디케이터는 그대로)
            if getattr(self, "_draw_tool", None) is not None:
                self._draw_tool.cancel()
            return
        if self.controller.ruler_tool.active:
            self.controller.ruler_tool._cancel_current_drawing()

    def _safe_draw_complete(self):
        if self._is_input_focused():
            return
        if (
            getattr(self, "btn_draw", None)
            and self.btn_draw.isChecked()
            and getattr(self, "_draw_tool", None)
        ):
            self._draw_tool.complete()

    def _safe_draw_rollback(self):
        if self._is_input_focused():
            return
        if (
            getattr(self, "btn_draw", None)
            and self.btn_draw.isChecked()
            and getattr(self, "_draw_tool", None)
        ):
            self._draw_tool.rollback()

    def _safe_set_draw_mode(self, mode):
        """숫자 키(1~4)로 그리기 도구를 선택. 그리기 모드가 꺼져 있으면 무시."""
        if self._is_input_focused():
            return
        if not (getattr(self, "btn_draw", None) and self.btn_draw.isChecked()):
            return
        if hasattr(self, "draw_indicator") and self.draw_indicator is not None:
            # 인디케이터 버튼 체크 상태를 바꾸고, 실제 도구도 즉시 교체
            self.draw_indicator.set_mode(mode)
        # DrawModeIndicator.set_mode는 mode_changed를 emit하지 않으므로, 직접 도구를 교체해 준다.
        self._on_draw_mode_changed(mode)

    def _safe_toggle_draw(self):
        if self._is_input_focused():
            return
        if getattr(self, "btn_draw", None):
            # 눈금자 또는 라벨 이동 모드가 켜져 있으면 그리기 모드를 켤 수 없다 (배타 모드)
            if not self.btn_draw.isChecked() and (
                self._is_ruler_active() or self._is_label_move_active()
            ):
                return
            self.btn_draw.setChecked(not self.btn_draw.isChecked())
            self._on_toggle_draw()

    def _safe_toggle_design_lock(self):
        if self._is_input_focused():
            return
        if (
            hasattr(self, "design_tab")
            and self.design_tab is not None
            and hasattr(self.design_tab, "btn_lock")
        ):
            self.design_tab.btn_lock.setChecked(
                not self.design_tab.btn_lock.isChecked()
            )

    def _safe_batch_save(self):
        if self._is_input_focused():
            return
        self.on_batch_save()

    def _safe_toggle_bold(self):
        if self._is_input_focused():
            return
        if (
            hasattr(self, "design_tab")
            and self.design_tab is not None
            and hasattr(self.design_tab, "btn_bold")
        ):
            self.design_tab.btn_bold.setChecked(
                not self.design_tab.btn_bold.isChecked()
            )

    def _safe_toggle_italic(self):
        if self._is_input_focused():
            return
        if (
            hasattr(self, "design_tab")
            and self.design_tab is not None
            and hasattr(self.design_tab, "btn_italic")
        ):
            self.design_tab.btn_italic.setChecked(
                not self.design_tab.btn_italic.isChecked()
            )

    def _safe_switch_to_tab(self, index):
        if self._is_input_focused():
            return
        if self.tab_widget.currentIndex() != index:
            self.tab_widget.setCurrentIndex(index)

    def _toggle_panels_visibility(self):
        """
        Tab 키로 도구 도크와 레이어 도크를 함께 임시 숨김/복원합니다.
        두 도크의 가시성/플로팅 상태/geometry를 기억해 두었다가 되돌립니다.
        """
        if not hasattr(self, "dock_widget") or not hasattr(self, "layer_dock_widget"):
            return

        if getattr(self, "_panels_hidden_by_tab", False) is False:
            # 현재: 패널이 보이는 상태 → 숨김
            self._panels_hidden_by_tab = True

            # 메인 도크 상태 저장
            self.was_main_dock_visible = self.dock_widget.isVisible()
            self.main_dock_floating_state = self.dock_widget.isFloating()

            # 레이어 도크 상태 저장
            self.was_layer_dock_visible = self.layer_dock_widget.isVisible()
            self.layer_dock_floating_state = self.layer_dock_widget.isFloating()
            self.layer_dock_geometry = (
                self.layer_dock_widget.geometry()
                if self.layer_dock_widget.isFloating()
                else None
            )

            if self.was_main_dock_visible:
                self.dock_widget.hide()
            if self.was_layer_dock_visible:
                self.layer_dock_widget.hide()
        else:
            # 현재: Tab으로 숨긴 상태 → 복원
            self._panels_hidden_by_tab = False

            if getattr(self, "was_main_dock_visible", True):
                if getattr(self, "main_dock_floating_state", False):
                    self.dock_widget.setFloating(True)
                self.dock_widget.show()

            if getattr(self, "was_layer_dock_visible", True):
                if getattr(self, "layer_dock_floating_state", False):
                    self.layer_dock_widget.setFloating(True)
                    if getattr(self, "layer_dock_geometry", None) is not None:
                        self.layer_dock_widget.setGeometry(self.layer_dock_geometry)
                self.layer_dock_widget.show()

        self._update_dock_separators()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_update_dock_separators"):
            self._update_dock_separators()

    def _update_nav_buttons(self):
        data_list = (
            getattr(self, "plot_data_snapshot", None)
            or self.controller.get_plot_data_list()
        )
        idx = getattr(self, "current_idx", self.controller.get_current_index())
        total = len(data_list)
        self.btn_prev.setEnabled(idx > 0)
        self.btn_next.setEnabled(idx < total - 1)

    def _safe_nav_prev(self):
        if self._is_input_focused():
            return
        self.on_nav_prev_clicked()

    def _safe_nav_next(self):
        if self._is_input_focused():
            return
        self.on_nav_next_clicked()

    def on_nav_prev_clicked(self):
        if not self.btn_prev.isEnabled():
            return
        self.setFocus()
        self._save_filter_state_for_current_file()
        self._save_layer_overrides_for_current_file()
        data_list = (
            getattr(self, "plot_data_snapshot", None)
            or self.controller.get_plot_data_list()
        )
        self.current_idx = (
            getattr(self, "current_idx", self.controller.get_current_index()) - 1
        ) % len(data_list)
        self.controller.set_current_index(self.current_idx)
        self._on_navigate_update()

    def on_nav_next_clicked(self):
        if not self.btn_next.isEnabled():
            return
        self.setFocus()
        self._save_filter_state_for_current_file()
        self._save_layer_overrides_for_current_file()
        data_list = (
            getattr(self, "plot_data_snapshot", None)
            or self.controller.get_plot_data_list()
        )
        self.current_idx = (
            getattr(self, "current_idx", self.controller.get_current_index()) + 1
        ) % len(data_list)
        self.controller.set_current_index(self.current_idx)
        self._on_navigate_update()

    def _save_layer_overrides_for_current_file(self):
        """현재 파일 인덱스에 대한 레이어 오버라이드를 저장."""
        idx = getattr(self, "current_idx", self.controller.get_current_index())
        overrides = getattr(self, "layer_design_overrides", {})
        self.layer_design_overrides_by_file[idx] = {
            v: dict(o) for v, o in overrides.items()
        }

    def _load_layer_overrides_for_file(self, idx):
        """해당 파일 인덱스의 레이어 오버라이드를 복원."""
        self.layer_design_overrides = {}
        if idx in self.layer_design_overrides_by_file:
            self.layer_design_overrides = {
                v: dict(o) for v, o in self.layer_design_overrides_by_file[idx].items()
            }
        if hasattr(self, "_layer_dock_content") and self._layer_dock_content:
            self._layer_dock_content._rebuild_effects()

    def _save_filter_state_for_current_file(self):
        """현재 파일 인덱스에 대한 모음 필터 상태를 저장."""
        idx = getattr(self, "current_idx", self.controller.get_current_index())
        state = getattr(self, "vowel_filter_state", {})
        self.vowel_filter_state_by_file[idx] = dict(state)

    def _load_filter_state_for_file(self, idx):
        """해당 파일 인덱스의 모음 필터 상태를 복원."""
        if idx in self.vowel_filter_state_by_file:
            self.vowel_filter_state = dict(self.vowel_filter_state_by_file[idx])
        else:
            self.vowel_filter_state = {}

    def _on_navigate_update(self):
        # 파일 전환 시 플롯이 clear되기 전에 그리기 도구 및 UI 완벽 비활성화
        if getattr(self, "btn_draw", None) and self.btn_draw.isChecked():
            self.btn_draw.setChecked(False)
            self._on_toggle_draw()
        else:
            self._draw_tool_deactivate()

        self._update_nav_buttons()
        data_list = (
            getattr(self, "plot_data_snapshot", None)
            or self.controller.get_plot_data_list()
        )
        idx = getattr(self, "current_idx", self.controller.get_current_index())
        self._load_layer_overrides_for_file(idx)
        self._load_filter_state_for_file(idx)
        current_data = data_list[idx]
        self._update_window_title(current_data["name"])
        self.lbl_info.setText(
            format_file_label(idx + 1, len(data_list), current_data["name"])
        )

        if self.filter_panel is not None and self.filter_panel.isVisible():
            self.filter_panel.close()

        # 광역 디자인 설정: 설정 유지(lock)가 꺼져 있으면 파일 전환 시 디자인을 기본값으로 리셋. 라벨 위치 이동은 lock 여부와 관계없이 유지.
        if (
            hasattr(self, "design_tab")
            and self.design_tab is not None
            and hasattr(self.design_tab, "btn_lock")
            and not self.design_tab.btn_lock.isChecked()
        ):
            self.design_tab._reset_to_defaults()
        else:
            self.controller.refresh_plot(
                self.figure, self.canvas, self.range_widgets, self.lbl_info, self
            )
        self._refresh_layer_dock_vowels()
        # 파일 전환 시 해당 파일의 그리기 객체만 표시
        self._redraw_draw_layer()
        if (
            hasattr(self, "_layer_dock_content")
            and self._layer_dock_content is not None
        ):
            self._layer_dock_content.update_draw_layer_list(
                self._get_current_draw_objects()
            )
        if self.canvas:
            self.canvas.draw_idle()

    def on_reset_clicked(self):
        self.setFocus()
        self._reset_ranges_to_default(apply_plot=True)
        app_logger.info(config.LOG_MSG["PLOT_RANGE_INIT"])

    def _log_design_lock(self, checked):
        app_logger.info(
            config.LOG_MSG["DESIGN_KEPT"]
            if checked
            else config.LOG_MSG["DESIGN_UNKEPT"]
        )
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_lock_on(checked)

    def _log_design_reset(self):
        app_logger.info(config.LOG_MSG["DESIGN_RESET"])

    def _reset_ranges_to_default(self, apply_plot=True):
        if hasattr(self, "fixed_plot_params"):
            ptype = self.fixed_plot_params.get("type", "f1_f2")
            use_bark = self.fixed_plot_params.get("use_bark_units", False)
            smart_ranges = self.controller.get_smart_ranges_for_params(ptype, use_bark)
            self.cb_sigma.setCurrentText(str(config.DEFAULT_SIGMA))

            for k in ["y_min", "y_max", "x_min", "x_max"]:
                self.range_widgets[k].setText(smart_ranges[k])

            if apply_plot is True:
                self.on_apply()

    def _safe_toggle_ruler(self):
        if self._is_input_focused():
            return
        next_state = not self.btn_ruler.isChecked()
        # 배타 모드: 눈금자를 켜려면 draw/label_move가 모두 꺼져 있어야 한다.
        if next_state and (
            (getattr(self, "btn_draw", None) and self.btn_draw.isChecked())
            or self._is_label_move_active()
        ):
            return
        self.btn_ruler.setChecked(next_state)
        self.on_toggle_ruler()

    def on_toggle_ruler(self):
        # 버튼 직접 클릭으로 진입했을 때도 배타 모드를 강제한다.
        if self.btn_ruler.isChecked() and (
            (getattr(self, "btn_draw", None) and self.btn_draw.isChecked())
            or self._is_label_move_active()
        ):
            self.btn_ruler.setChecked(False)
            self.update_ruler_style(False)
            return
        self.setFocus()
        self.controller.toggle_ruler(self)
        self.btn_ruler.setChecked(self.controller.ruler_tool.active)

    def _safe_toggle_label_move(self):
        if self._is_input_focused():
            return
        next_state = not self.design_tab.btn_label_move.isChecked()
        # 배타 모드: 라벨 이동을 켜려면 draw/ruler가 모두 꺼져 있어야 한다.
        if next_state and (
            (getattr(self, "btn_draw", None) and self.btn_draw.isChecked())
            or self._is_ruler_active()
        ):
            return
        self.design_tab.btn_label_move.setChecked(next_state)
        self.on_toggle_label_move()

    def on_toggle_label_move(self):
        # 버튼 직접 클릭으로 진입했을 때도 배타 모드를 강제한다.
        if self.design_tab.btn_label_move.isChecked() and (
            (getattr(self, "btn_draw", None) and self.btn_draw.isChecked())
            or self._is_ruler_active()
        ):
            self.design_tab.btn_label_move.setChecked(False)
            self.update_label_move_style(False)
            return
        self.setFocus()
        self.controller.toggle_label_move(self)
        if self.controller.label_move_tool:
            self.design_tab.btn_label_move.setChecked(
                self.controller.label_move_tool.active
            )

    def _is_ruler_active(self):
        btn_on = bool(getattr(self, "btn_ruler", None) and self.btn_ruler.isChecked())
        tool_on = bool(
            getattr(getattr(self, "controller", None), "ruler_tool", None)
            and self.controller.ruler_tool.active
        )
        return btn_on or tool_on

    def _is_label_move_active(self):
        btn_on = bool(
            hasattr(self, "design_tab")
            and hasattr(self.design_tab, "btn_label_move")
            and self.design_tab.btn_label_move.isChecked()
        )
        tool_on = bool(
            getattr(getattr(self, "controller", None), "label_move_tool", None)
            and self.controller.label_move_tool.active
        )
        return btn_on or tool_on

    def update_label_move_style(self, is_on):
        self.design_tab.btn_label_move.setChecked(is_on)
        self.design_tab.btn_label_move.setStyleSheet(
            "QPushButton#BtnLabelMove { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #333;} "
            "QPushButton#BtnLabelMove:checked { background-color: #E6A23C; color: white; font-weight: bold; border: none; }"
        )
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_label_move_on(is_on)

    def _draw_tool_deactivate(self):
        if getattr(self, "_draw_tool", None) is not None:
            try:
                self._draw_tool.deactivate()
            except Exception:
                pass
            self._draw_tool = None
        if getattr(self, "canvas", None) is not None:
            self.canvas.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _on_toggle_draw(self):
        # 버튼 직접 클릭으로 진입했을 때도 배타 모드를 강제한다.
        if self.btn_draw.isChecked() and (
            self._is_ruler_active() or self._is_label_move_active()
        ):
            self.btn_draw.setChecked(False)
            if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
                self.tool_indicator.set_draw_mode_on(False)
            return
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_draw_mode_on(self.btn_draw.isChecked())
        if self.btn_draw.isChecked():
            self.draw_indicator.show()
            self.draw_indicator.set_mode(None)
            # 인디케이터가 키보드 포커스를 갖지 않도록 캔버스 또는 메인 창으로 포커스 이동
            if getattr(self, "canvas", None) is not None:
                self.canvas.setFocus()
            else:
                self.setFocus()
            app_logger.info(config.LOG_MSG["DRAW_ON"])
        else:
            self._draw_tool_deactivate()
            self.draw_indicator.hide()
            app_logger.info(config.LOG_MSG["DRAW_OFF_INFO"])

    def _get_current_draw_objects(self):
        """현재 파일 인덱스에 해당하는 그리기 객체 리스트 (파일별 분리)."""
        idx = getattr(self, "current_idx", None)
        if (
            idx is None
            and hasattr(self, "controller")
            and hasattr(self.controller, "get_current_index")
        ):
            idx = self.controller.get_current_index()
        if idx is None:
            idx = 0
        return getattr(self, "_draw_objects_by_file", {}).setdefault(idx, [])

    def _set_current_draw_objects(self, lst):
        """현재 파일의 그리기 객체 리스트를 교체."""
        idx = getattr(self, "current_idx", None)
        if (
            idx is None
            and hasattr(self, "controller")
            and hasattr(self.controller, "get_current_index")
        ):
            idx = self.controller.get_current_index()
        if idx is None:
            idx = 0
        if not hasattr(self, "_draw_objects_by_file"):
            self._draw_objects_by_file = {}
        self._draw_objects_by_file[idx] = list(lst)

    def _on_draw_object_complete(self, obj):
        objs = self._get_current_draw_objects()
        objs.append(obj)
        if (
            getattr(obj, "type", "") == "polygon"
            and getattr(obj, "points", None)
            and len(obj.points) >= 3
            and getattr(obj, "id", "")
            and getattr(obj, "show_area_label", False)
        ):
            area = polygon_area(obj.points)
            xs = [p[0] for p in obj.points]
            ys = [p[1] for p in obj.points]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            area_label = AreaLabelObject(
                parent_id=obj.id,
                value=area,
                x=cx,
                y=cy,
                axis_units=getattr(obj, "axis_units", "Hz"),
                visible=obj.visible,
                locked=obj.locked,
                semi=obj.semi,
            )
            objs.append(area_label)
        self._redraw_draw_layer()
        if (
            hasattr(self, "_layer_dock_content")
            and self._layer_dock_content is not None
        ):
            self._layer_dock_content.update_draw_layer_list(
                self._get_current_draw_objects()
            )
        if self.canvas:
            self.canvas.draw_idle()

    def _redraw_draw_layer(self):
        if not self.figure.axes:
            return
        ax = self.figure.axes[0]
        # 이전 그리기 레이어 아티스트 제거 (삭제/파일 전환 시 화면에서 사라지도록)
        for a in getattr(self, "_draw_layer_artists", []):
            try:
                a.remove()
            except Exception:
                pass
        self._draw_layer_artists = []
        self._draw_layer_area_label_refs = []

        def _line_style_to_mpl(s):
            """'-' | '---' | '--' -> matplotlib linestyle.

            신뢰타원(engine.plot_engine._to_mpl_linestyle)과 동일한 철학:
            - '---' : 긴 대시 (6pt dash, 3pt gap)
            - '--'  : Matplotlib 기본 dashed
            - '-'   : 실선
            """
            if s == "---":
                # 긴 점선: 신뢰타원과 동일하게 커스텀 긴 대시 패턴
                return (0, (6.0, 3.0))
            # 나머지는 Matplotlib 표준 스타일에 그대로 위임
            if s in ("-", "--", ":"):
                return s
            # 알 수 없는 값이면 짧은 점선과 동일하게 처리
            return "--"

        for obj in self._get_current_draw_objects():
            if not getattr(obj, "visible", True):
                continue
            # semi: 확정 객체도 반투명 표시 (선/외곽선만 알파 조정)
            is_semi = getattr(obj, "semi", False)
            line_alpha = 0.5 if is_semi else 0.9
            try:
                if getattr(obj, "type", None) == "line" and hasattr(obj, "points"):
                    xs = [p[0] for p in obj.points]
                    ys = [p[1] for p in obj.points]
                    style = getattr(obj, "line_style", "-") or "-"
                    color_hex = getattr(obj, "line_color", "#000000") or "#000000"
                    rgba_color = mcolors.to_rgba(color_hex, float(line_alpha))
                    linewidth = 1.0
                    (line,) = ax.plot(
                        xs,
                        ys,
                        linestyle=_line_style_to_mpl(style),
                        color=rgba_color,
                        linewidth=linewidth,
                        zorder=1,
                        clip_on=False,
                    )
                    self._draw_layer_artists.append(line)

                    # 화살표 그리기 (arrow_mode, arrow_head에 따라)
                    arrow_mode = getattr(obj, "arrow_mode", "none") or "none"
                    arrow_head = getattr(obj, "arrow_head", "stealth") or "stealth"
                    if arrow_mode != "none" and len(obj.points) >= 2:
                        from matplotlib.patches import Polygon as MplPolygon

                        arrow_z = 4.0  # 선(z=1)은 아래 유지, centroid(z=3) 위 / 라벨(z=100) 아래

                        def _add_arrow(p_start, p_end):
                            # 기존 선 스타일(실선/점선)을 보존하기 위해 shaft를 덧그리지 않고,
                            # 끝점 근처에 head만 별도 렌더링한다.
                            # 화살촉 왜곡을 막기 위해 화면(px) 좌표에서 head를 만든 뒤 data 좌표로 역변환한다.
                            x0, y0 = float(p_start[0]), float(p_start[1])
                            x1, y1 = float(p_end[0]), float(p_end[1])
                            disp0 = ax.transData.transform((x0, y0))
                            disp1 = ax.transData.transform((x1, y1))
                            dx, dy = (
                                float(disp1[0] - disp0[0]),
                                float(disp1[1] - disp0[1]),
                            )
                            seg_len_px = (dx * dx + dy * dy) ** 0.5
                            if seg_len_px <= 1e-6:
                                return

                            ux, uy = dx / seg_len_px, dy / seg_len_px
                            px, py = -uy, ux  # 수직 단위벡터

                            # px 단위 head 크기: 선 두께 비례 + 최소 보장
                            head_len = max(12.0, 8.0 * max(linewidth, 1.0))
                            head_len = min(head_len, seg_len_px * 0.7)
                            head_w = head_len * 0.78

                            tx, ty = float(disp1[0]), float(disp1[1])
                            bx, by = tx - ux * head_len, ty - uy * head_len
                            lx, ly = bx + px * head_w * 0.5, by + py * head_w * 0.5
                            rx, ry = bx - px * head_w * 0.5, by - py * head_w * 0.5

                            inv = ax.transData.inverted().transform
                            tip_d = tuple(inv((tx, ty)))
                            left_d = tuple(inv((lx, ly)))
                            right_d = tuple(inv((rx, ry)))
                            base_d = tuple(inv((bx, by)))

                            if arrow_head == "open":
                                # Open head: V자 head 두 선만 그림
                                (l1,) = ax.plot(
                                    [tip_d[0], left_d[0]],
                                    [tip_d[1], left_d[1]],
                                    color=rgba_color,
                                    linewidth=max(0.9, linewidth * 0.9),
                                    zorder=arrow_z,
                                    clip_on=False,
                                )
                                (l2,) = ax.plot(
                                    [tip_d[0], right_d[0]],
                                    [tip_d[1], right_d[1]],
                                    color=rgba_color,
                                    linewidth=max(0.9, linewidth * 0.9),
                                    zorder=arrow_z,
                                    clip_on=False,
                                )
                                self._draw_layer_artists.extend([l1, l2])
                            elif arrow_head == "latex":
                                # Latex head: 꽉 찬 3점 이등변 삼각형
                                poly = MplPolygon(
                                    [tip_d, left_d, right_d],
                                    closed=True,
                                    facecolor=rgba_color,
                                    edgecolor=rgba_color,
                                    linewidth=max(0.5, linewidth * 0.5),
                                    zorder=arrow_z,
                                    clip_on=False,
                                )
                                ax.add_patch(poly)
                                self._draw_layer_artists.append(poly)
                            else:
                                # Stealth head: latex 삼각형 기반 + 꼬리 중앙 안쪽 indent
                                indent = head_len * (3.6 / 8.5)
                                mx, my = bx + ux * indent, by + uy * indent
                                mid_d = tuple(inv((mx, my)))
                                poly = MplPolygon(
                                    [tip_d, left_d, mid_d, right_d],
                                    closed=True,
                                    facecolor=rgba_color,
                                    edgecolor=rgba_color,
                                    linewidth=max(0.5, linewidth * 0.5),
                                    zorder=arrow_z,
                                    clip_on=False,
                                )
                                ax.add_patch(poly)
                                self._draw_layer_artists.append(poly)

                        pts = obj.points
                        if arrow_mode == "end":
                            _add_arrow(pts[-2], pts[-1])
                        elif arrow_mode == "all":
                            for j in range(len(pts) - 1):
                                _add_arrow(pts[j], pts[j + 1])
                elif getattr(obj, "type", None) == "polygon" and hasattr(obj, "points"):
                    from matplotlib.patches import Polygon as MplPolygon

                    # semi: 내부·테두리 모두 반투명, 확정 외곽선은 진하게
                    face_alpha = 0.15 if not is_semi else 0.06
                    edge_alpha = 1.0 if not is_semi else 0.4

                    border_style = getattr(obj, "border_style", "-") or "-"
                    border_hex = getattr(obj, "border_color", "#000000") or "#000000"
                    fill_hex = getattr(obj, "fill_color", "#3366CC") or "#3366CC"

                    if str(fill_hex).lower() == "transparent":
                        face_rgba = (0.0, 0.0, 0.0, 0.0)
                    else:
                        face_rgba = mcolors.to_rgba(fill_hex, float(face_alpha))
                    edge_rgba = mcolors.to_rgba(border_hex, float(edge_alpha))

                    poly = MplPolygon(
                        obj.points,
                        facecolor=face_rgba,
                        edgecolor=edge_rgba,
                        linestyle=_line_style_to_mpl(border_style),
                        linewidth=1.0,
                        zorder=1,
                    )
                    ax.add_patch(poly)
                    self._draw_layer_artists.append(poly)
                elif getattr(obj, "type", None) == "reference" and hasattr(obj, "mode"):
                    # 참조선은 아래 별도 루프에서 그림
                    pass
                elif getattr(obj, "type", None) == "area_label":
                    # 넓이 텍스트: 값/좌표가 잘못되어도 전체 루프가 죽지 않도록 try 블록 안에서 처리
                    v = getattr(obj, "value", 0)
                    u = (getattr(obj, "axis_units", "Hz") or "Hz").strip().lower()
                    if u == "norm" or "norm" in u:
                        txt = f"{v:.2f}"
                    else:
                        txt = str(int(round(v)))
                    font_family = ["DejaVu Sans", "Malgun Gothic"]
                    if (
                        getattr(self, "design_settings", None)
                        and self.design_settings.get("font_style") == "serif"
                    ):
                        font_family = [
                            "Times New Roman",
                            "Noto Serif KR",
                            "DejaVu Serif",
                        ]
                    text_alpha = 0.3 if getattr(obj, "semi", False) else 1.0
                    txt_artist = ax.text(
                        getattr(obj, "x", 0),
                        getattr(obj, "y", 0),
                        txt,
                        fontsize=10,
                        fontfamily=font_family,
                        color="#303133",
                        alpha=text_alpha,
                        va="center",
                        ha="center",
                        zorder=2,
                        clip_on=True,
                    )
                    self._draw_layer_artists.append(txt_artist)
                    self._draw_layer_area_label_refs.append((txt_artist, obj))
            except Exception:
                # 한 객체에서 에러가 나더라도 나머지 객체는 계속 그리도록 방어
                continue

        # 참조선은 별도 루프에서 기존 로직 유지 (가독성을 위해 위 try/except에서 분리)
        for obj in self._get_current_draw_objects():
            if not getattr(obj, "visible", True):
                continue
            if getattr(obj, "type", None) != "reference" or not hasattr(obj, "mode"):
                continue

            from draw.draw_reference import (
                REF_LINE_COLOR,
                REF_LINE_ALPHA,
                format_ref_label,
            )

            xlim, ylim = ax.get_xlim(), ax.get_ylim()
            v = obj.value  # 단위(Unit) 기준 순수 데이터 값 (Hz 등)
            axis_units = getattr(obj, "axis_units", "") or "Hz"
            axis_scale = getattr(obj, "axis_scale", "linear")
            if axis_scale == "bark" and (axis_units or "").strip().lower() == "hz":
                plot_v = float(hz_to_bark(v))
            else:
                plot_v = v
            lbl = format_ref_label(v, axis_units)
            font_family = ["DejaVu Sans", "Malgun Gothic"]
            if (
                getattr(self, "design_settings", None)
                and self.design_settings.get("font_style") == "serif"
            ):
                font_family = ["Times New Roman", "Noto Serif KR", "DejaVu Serif"]
            style = getattr(obj, "line_style", "-") or "-"
            color_override = getattr(obj, "line_color", None)
            base_color = color_override or REF_LINE_COLOR
            ref_alpha = 0.3 if getattr(obj, "semi", False) else REF_LINE_ALPHA
            rgba_line = mcolors.to_rgba(base_color, float(ref_alpha))
            text_alpha = 0.3 if getattr(obj, "semi", False) else 1.0
            if obj.mode == "horizontal":
                (ref_line,) = ax.plot(
                    xlim,
                    [plot_v, plot_v],
                    color=rgba_line,
                    linestyle=_line_style_to_mpl(style),
                    linewidth=1,
                    zorder=1.5,
                    clip_on=True,
                )
                ref_txt = ax.text(
                    xlim[0],
                    plot_v,
                    lbl,
                    fontsize=12,
                    fontfamily=font_family,
                    color="#303133",
                    alpha=text_alpha,
                    va="center",
                    zorder=2,
                    clip_on=False,
                )
                self._draw_layer_artists.append(ref_line)
                self._draw_layer_artists.append(ref_txt)
            else:
                (ref_line,) = ax.plot(
                    [plot_v, plot_v],
                    ylim,
                    color=rgba_line,
                    linestyle=_line_style_to_mpl(style),
                    linewidth=1,
                    zorder=1.5,
                    clip_on=True,
                )
                ref_txt = ax.text(
                    plot_v,
                    ylim[0],
                    lbl,
                    fontsize=12,
                    fontfamily=font_family,
                    color="#303133",
                    alpha=text_alpha,
                    va="bottom",
                    ha="center",
                    zorder=2,
                    clip_on=False,
                )
                self._draw_layer_artists.append(ref_line)
                self._draw_layer_artists.append(ref_txt)
        if self.canvas:
            self._ensure_area_label_drag_connected()
            self.canvas.draw_idle()

    def _ensure_area_label_drag_connected(self):
        """넓이 텍스트 드래그 이동: 그리기 모드가 꺼져 있을 때만 동작."""
        if getattr(self, "_area_label_drag_cids", None) is not None:
            return
        if not getattr(self, "canvas", None):
            return
        c = self.canvas
        try:
            cid_bp = c.mpl_connect(
                "button_press_event", self._on_canvas_area_label_press
            )
            cid_mv = c.mpl_connect(
                "motion_notify_event", self._on_canvas_area_label_move
            )
            cid_br = c.mpl_connect(
                "button_release_event", self._on_canvas_area_label_release
            )
            self._area_label_drag_cids = (cid_bp, cid_mv, cid_br)
            self._dragging_area_label_obj = None
            self._area_label_cursor_changed = False
        except Exception:
            self._area_label_drag_cids = ()

    def _area_label_draw_index(self, obj):
        """넓이 텍스트 객체 obj가 그리기 객체 목록에서 차지하는 인덱스. 없으면 None."""
        objs = self._get_current_draw_objects()
        for i, o in enumerate(objs):
            if o is obj:
                return i
        return None

    def _is_area_label_focused(self, obj):
        """해당 넓이 텍스트 레이어가 레이어 도크에서 포커스(단일 선택)되어 있을 때만 True."""
        idx = self._area_label_draw_index(obj)
        if idx is None:
            return False
        dock = getattr(self, "_layer_dock_content", None)
        if not dock:
            return False
        sel = getattr(dock, "_selected_draw_indices", set())
        return len(sel) == 1 and idx in sel

    def _area_label_reset_to_centroid(self, obj):
        """넓이 텍스트를 부모 폴리곤 무게중심으로 되돌린 뒤 화면·레이어 목록 갱신."""
        objs = self._get_current_draw_objects()
        pid = getattr(obj, "parent_id", None)
        if not pid:
            return
        for o in objs:
            if getattr(o, "type", "") == "polygon" and getattr(o, "id", None) == pid:
                pts = getattr(o, "points", None)
                if pts and len(pts) >= 3:
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    obj.x = sum(xs) / len(xs)
                    obj.y = sum(ys) / len(ys)
                break
        refs = getattr(self, "_draw_layer_area_label_refs", [])
        for art, o in refs:
            if o is obj:
                try:
                    art.set_position((obj.x, obj.y))
                except Exception:
                    pass
                break
        if self.canvas:
            self.canvas.draw_idle()
        if (
            hasattr(self, "_layer_dock_content")
            and self._layer_dock_content is not None
        ):
            self._layer_dock_content.update_draw_layer_list(objs)

    def _area_label_hit_at_px(self, x_px, y_px, pad_px=14):
        """픽셀 좌표 (x_px, y_px)에서 넓이 텍스트 히트 여부. 라벨 이동 툴과 동일하게 get_window_extent+패딩 사용."""
        refs = getattr(self, "_draw_layer_area_label_refs", [])
        if not refs or not getattr(self, "figure", None) or not self.figure.axes:
            return None
        try:
            renderer = self.canvas.get_renderer()
        except Exception:
            return None
        for art, obj in refs:
            try:
                bbox = art.get_window_extent(renderer)
                x0, x1 = min(bbox.x0, bbox.x1) - pad_px, max(bbox.x0, bbox.x1) + pad_px
                y0, y1 = min(bbox.y0, bbox.y1) - pad_px, max(bbox.y0, bbox.y1) + pad_px
                if x0 <= x_px <= x1 and y0 <= y_px <= y1:
                    return obj
            except Exception:
                continue
        return None

    def _on_canvas_area_label_press(self, event):
        if getattr(self, "btn_draw", None) and self.btn_draw.isChecked():
            return
        if getattr(self, "_draw_tool", None) is not None:
            return
        hit = self._area_label_hit_at_px(event.x, event.y)
        if hit is None:
            return
        # 우클릭: 포커스된 넓이 텍스트만 디폴트 위치(무게중심)로 복귀
        if event.button == 3:
            if self._is_area_label_focused(hit):
                self._area_label_reset_to_centroid(hit)
            return
        if event.button != 1:
            return
        # 포커스(해당 넓이 텍스트 레이어가 단일 선택)일 때만 드래그 허용
        if self._is_area_label_focused(hit):
            self._dragging_area_label_obj = hit

    def _on_canvas_area_label_move(self, event):
        obj = getattr(self, "_dragging_area_label_obj", None)
        if obj is not None:
            if (
                event.inaxes is not None
                and event.xdata is not None
                and event.ydata is not None
            ):
                obj.x = float(event.xdata)
                obj.y = float(event.ydata)
                refs = getattr(self, "_draw_layer_area_label_refs", [])
                for art, o in refs:
                    if o is obj:
                        try:
                            art.set_position((obj.x, obj.y))
                        except Exception:
                            pass
                        break
                if self.canvas:
                    self.canvas.draw_idle()
            return
        if getattr(self, "btn_draw", None) and self.btn_draw.isChecked():
            return
        if getattr(self, "_draw_tool", None) is not None:
            return
        hit = (
            self._area_label_hit_at_px(event.x, event.y)
            if event.inaxes is not None
            else None
        )
        try:
            # 포커스된 넓이 텍스트 위에서만 이동 커서 표시
            if hit is not None and self._is_area_label_focused(hit):
                if not getattr(self, "_area_label_cursor_changed", False):
                    self.canvas.setCursor(Qt.CursorShape.SizeAllCursor)
                    self._area_label_cursor_changed = True
            else:
                if getattr(self, "_area_label_cursor_changed", False):
                    self.canvas.unsetCursor()
                    self._area_label_cursor_changed = False
        except Exception:
            pass

    def _on_canvas_area_label_release(self, event):
        if getattr(self, "_dragging_area_label_obj", None) is not None:
            self._dragging_area_label_obj = None
        if getattr(self, "_area_label_cursor_changed", False):
            try:
                self.canvas.unsetCursor()
            except Exception:
                pass
            self._area_label_cursor_changed = False

    def _on_draw_mode_changed(self, mode):
        if mode is None:
            self._draw_tool_deactivate()
            return
        if self.btn_ruler.isChecked():
            self.controller.toggle_ruler(self)
        if self.design_tab.btn_label_move.isChecked():
            self.controller.toggle_label_move(self)
        ax = self.figure.axes[0] if self.figure.axes else None
        snapping_data = getattr(self, "snapping_data", None) or []
        # Scale과 Unit 완전 분리: 그리기 도구에는 실제 눈금 단위(Unit)만 전달. 스케일이 Bark여도 단위가 Hz면 Hz.
        params = getattr(self, "fixed_plot_params", None) or {}
        if params.get("normalization"):
            x_unit = y_unit = "norm"
        else:
            x_unit = (params.get("f2_unit") or "Hz").strip()
            y_unit = (params.get("f1_unit") or "Hz").strip()
        x_scale = (params.get("f2_scale") or "linear").strip().lower()
        y_scale = (params.get("f1_scale") or "linear").strip().lower()
        x_name = getattr(self, "x_axis_label", None) or "F2"
        y_name = "F1"
        if ax is None:
            return
        self._draw_tool_deactivate()
        font_family = ["DejaVu Sans", "Malgun Gothic"]
        if (
            getattr(self, "design_settings", None)
            and self.design_settings.get("font_style") == "serif"
        ):
            font_family = ["Times New Roman", "Noto Serif KR", "DejaVu Serif"]

        def _on_draw_cancel():
            self.draw_indicator.set_mode(None)

        if mode == DrawMode.LINE:
            self._draw_tool = draw_line.DrawLineTool(
                self.canvas,
                ax,
                snapping_data,
                axis_units=y_unit,
                on_complete=self._on_draw_object_complete,
                on_cancel=_on_draw_cancel,
            )
        elif mode == DrawMode.POLYGON:
            self._draw_tool = draw_polygon.DrawPolygonTool(
                self.canvas,
                ax,
                snapping_data,
                axis_units=y_unit,
                on_complete=self._on_draw_object_complete,
                on_cancel=_on_draw_cancel,
            )
        elif mode in (DrawMode.REF_H, DrawMode.REF_V):
            self._draw_tool = draw_reference.DrawReferenceTool(
                self.canvas,
                ax,
                horizontal=(mode == DrawMode.REF_H),
                snapping_data=snapping_data,
                x_unit=x_unit,
                y_unit=y_unit,
                x_scale=x_scale,
                y_scale=y_scale,
                x_name=x_name,
                y_name=y_name,
                on_complete=self._on_draw_object_complete,
                on_cancel=_on_draw_cancel,
                font_family=font_family,
                tick_color="#303133",
            )
        else:
            return
        self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.canvas.setFocus()
        self._draw_tool.activate()

    def _safe_compare_click(self):
        if self._is_input_focused() or not self.btn_compare.isEnabled():
            return
        self.btn_compare.click()

    def on_btn_compare_click(self):
        self.setFocus()
        idx = getattr(self, "current_idx", self.controller.get_current_index())
        self.controller.open_compare_dialog(idx, parent_window=self)

    def _on_vowel_analysis_clicked(self):
        """모음 상세 분석 버튼 클릭 핸들러: 별도 Analysis 창을 연다."""
        self.setFocus()
        if hasattr(self.controller, "open_vowel_analysis_window"):
            self.controller.open_vowel_analysis_window(self)

    def _safe_toggle_layer_dock(self):
        if self._is_input_focused():
            return
        self.on_layer_dock_toggle()

    def on_layer_dock_toggle(self):
        self.setFocus()
        if self.layer_dock_widget.isVisible():
            self._layer_dock_visible = False
            self._layer_dock_saved_area = self.dockWidgetArea(self.layer_dock_widget)
            self._layer_dock_saved_floating = self.layer_dock_widget.isFloating()
            self._layer_dock_saved_geometry = (
                self.layer_dock_widget.geometry()
                if self.layer_dock_widget.isFloating()
                else None
            )
            self.layer_dock_widget.hide()
        else:
            self._layer_dock_visible = True
            self._restore_layer_dock_position()
            self.layer_dock_widget.show()
        self._resize_for_dock_state()
        self._update_dock_separators()
        self._update_layer_button_style()

    def _restore_layer_dock_position(self):
        """L로 다시 열 때 또는 Tab으로 패널 복원 시 레이어 도크 위치 복원."""
        if (
            getattr(self, "_layer_dock_saved_floating", False)
            and getattr(self, "_layer_dock_saved_geometry", None) is not None
        ):
            self.layer_dock_widget.setFloating(True)
            self.layer_dock_widget.setGeometry(self._layer_dock_saved_geometry)
        else:
            area = getattr(
                self, "_layer_dock_saved_area", Qt.DockWidgetArea.RightDockWidgetArea
            )
            if not self.layer_dock_widget.isFloating():
                self.addDockWidget(area, self.layer_dock_widget)

    def _update_layer_button_style(self):
        # 레이어 도크는 항상 표시되므로, 별도 버튼 스타일은 더 이상 사용하지 않습니다.
        return

    def _refresh_layer_dock_vowels(self):
        if not hasattr(self, "_layer_dock_content"):
            return
        try:
            data_list = (
                getattr(self, "plot_data_snapshot", None)
                or self.controller.get_plot_data_list()
            )
            idx = getattr(self, "current_idx", self.controller.get_current_index())
            current_data = data_list[idx]
            df = current_data["df"]
            col = (
                "Label"
                if "Label" in df.columns
                else "label"
                if "label" in df.columns
                else None
            )
            if col:
                vowels = sorted(df[col].dropna().astype(str).unique().tolist())
                self._layer_dock_content.set_vowels(vowels)
        except (IndexError, KeyError, TypeError):
            pass

    def _on_layer_filter_state_changed(self, state: dict):
        """레이어 도크에서 필터 상태가 바뀌었을 때 플롯만 다시 그립니다."""
        # state 자체는 LayerDockWidget에서 popup.vowel_filter_state에 이미 반영함.
        self.on_apply()

    def _on_layer_overrides_changed(self, overrides: dict):
        """레이어 도크에서 디자인 오버라이드가 바뀌었을 때 플롯만 다시 그립니다."""
        # overrides 역시 LayerDockWidget에서 popup.layer_design_overrides에 반영된 상태.
        self.on_apply()

    def _safe_save_jpg(self):
        if self._is_input_focused():
            return
        self.controller.download_plot(self.figure, "jpg", parent_window=self)

    def on_apply(self):
        self.setFocus()
        self.figure.set_size_inches(6.5, 6.5)
        try:
            y_min = float(self.range_widgets["y_min"].text())
            y_max = float(self.range_widgets["y_max"].text())
            x_min = float(self.range_widgets["x_min"].text())
            x_max = float(self.range_widgets["x_max"].text())

            y_name, x_name = "F1", self.x_axis_label
            if y_min >= y_max:
                QMessageBox.warning(
                    self,
                    "입력 오류",
                    f"Y축({y_name}) 범위 오류:\n최소값이 최대값보다 작아야 합니다.",
                )
                return False
            if x_min >= x_max:
                QMessageBox.warning(
                    self,
                    "입력 오류",
                    f"X축({x_name}) 범위 오류:\n최소값이 최대값보다 작아야 합니다.",
                )
                return False
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "숫자만 입력해주세요.")
            return False

        self.controller.refresh_plot(
            self.figure, self.canvas, self.range_widgets, self.lbl_info, self
        )
        # 플롯 갱신으로 axes 인스턴스가 바뀔 수 있으므로, Draw 모드가 켜져 있으면
        # 현재 선택 모드 도구를 새 axes에 즉시 재바인딩한다.
        self._rebind_draw_tool_if_active()
        data_list = (
            getattr(self, "plot_data_snapshot", None)
            or self.controller.get_plot_data_list()
        )
        idx = getattr(self, "current_idx", self.controller.get_current_index())
        current_data = data_list[idx]
        self._update_window_title(current_data["name"])
        # on_apply는 좌표/디자인/필터 등의 변경에 대한 플롯 갱신만 담당하고,
        # 레이어 도크(모음 목록) 재구성은 파일 전환 시점(_on_file_index_changed 등)에서만 수행한다.
        return True

    def _rebind_draw_tool_if_active(self):
        if not getattr(self, "btn_draw", None) or not self.btn_draw.isChecked():
            return
        if not getattr(self, "draw_indicator", None):
            return
        mode = self.draw_indicator.get_mode()
        if mode is None:
            return
        self._on_draw_mode_changed(mode)

    def _on_range_apply_clicked(self):
        """좌표축 범위 '적용' 버튼 전용: 적용 성공 시에만 로그 기록."""
        if self.on_apply():
            app_logger.info(config.LOG_MSG["PLOT_UPDATE"])

    def update_unit_labels(self, f1_unit, f2_unit=None):
        if f2_unit is None:
            f2_unit = f1_unit

        self.lbl_f1_axis.setText("F1:")
        self.lbl_x_axis.setText(f"{self.x_axis_label}:")

        self.lbl_f1_unit.setText(f"({f1_unit})")
        self.lbl_f2_unit.setText(f"({f2_unit})")

    def update_x_label(self, new_label):
        self.x_axis_label = new_label
        self.lbl_x_axis.setText(f"{new_label}:")

    def get_sigma(self):
        return self.cb_sigma.currentText()

    def update_ruler_style(self, is_on):
        self.btn_ruler.setChecked(is_on)
        self.btn_ruler.setStyleSheet(
            """
            QPushButton#BtnRuler { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #333; }
            QPushButton#BtnRuler:hover:!checked { background-color: #E4E7ED; border: 1px solid #C0C4CC; }
            QPushButton#BtnRuler:checked { background-color: #67C23A; color: white; font-weight: bold; border: none; }
            """
        )
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_ruler_on(is_on)
        if is_on and getattr(self, "btn_draw", None) and self.btn_draw.isChecked():
            self.btn_draw.setChecked(False)
            if hasattr(self, "draw_indicator") and self.draw_indicator is not None:
                self.draw_indicator.hide()
            self._draw_tool_deactivate()

    def open_vowel_filter(self):
        data_list = (
            getattr(self, "plot_data_snapshot", None)
            or self.controller.get_plot_data_list()
        )
        idx = getattr(self, "current_idx", self.controller.get_current_index())
        current_data = data_list[idx]
        df = current_data["df"]

        col_label = (
            "Label"
            if "Label" in df.columns
            else "label"
            if "label" in df.columns
            else None
        )
        if not col_label:
            QMessageBox.warning(
                self, "오류", "데이터에 모음 라벨(Label) 컬럼이 없습니다."
            )
            return

        if self.filter_panel is not None and self.filter_panel.isVisible():
            self.filter_panel.raise_()
            self.filter_panel.activateWindow()
            return

        unique_vowels = df[col_label].dropna().unique().tolist()

        self.filter_panel = LiveVowelFilterPanel(
            parent=self,
            vowels=unique_vowels,
            current_state=self.vowel_filter_state,
            file_name=current_data["name"],
            on_change_callback=self._on_filter_changed,
        )
        self.filter_panel.show()

    def _on_filter_changed(self, new_state):
        self.vowel_filter_state = new_state
        self.on_apply()

    def on_batch_save(self):
        current_ranges = {k: v.text() for k, v in self.range_widgets.items()}
        current_sigma = self.cb_sigma.currentText()

        f1_unit_text = self.lbl_f1_unit.text().strip("()")
        f2_unit_text = self.lbl_f2_unit.text().strip("()")

        dialog = BatchSaveDialog(
            self,
            self.controller,
            current_ranges,
            f1_unit_text,
            f2_unit_text,
            self.x_axis_label,
            current_sigma,
        )
        dialog.exec()
