# ui_popup.py

import base64
import inspect
import platform
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QDialog,
    QButtonGroup,
    QMessageBox,
    QDockWidget,
    QApplication,
    QFrame,
    QSizePolicy,
    QFormLayout,
    QStyle,
    QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer, QObject, QEvent


class TabBarWheelBlocker(QObject):
    """탭 위에서 마우스 휠로 탭이 바뀌지 않도록 휠 이벤트를 흡수합니다."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            return True
        return False


from PyQt6.QtGui import (
    QFont,
    QIcon,
    QPixmap,
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
from . import layout_constants as layout
from .display_utils import format_file_label
from utils.math_utils import hz_to_bark, bark_to_hz

class ClickClearFocusFilter(QObject):
    """다른 위젯 클릭 시 지정한 LineEdit들에서 포커스를 빼서 분석 탭으로 넘깁니다."""

    def __init__(self, window, analysis_tab, edits, parent=None):
        super().__init__(parent)
        self._window = window
        self._analysis_tab = analysis_tab
        self._edits = set(edits)

    def eventFilter(self, obj, event):
        if event.type() != QEvent.Type.MouseButtonPress or event.button() != Qt.MouseButton.LeftButton:
            return False
        f = QApplication.focusWidget()
        if not f or f not in self._edits:
            return False
        try:
            # obj가 QWindow일 수 있음 → isAncestorOf는 QWidget에만 사용
            clicked_inside_edit = obj is f
            if not clicked_inside_edit and isinstance(obj, QWidget) and hasattr(f, "isAncestorOf"):
                clicked_inside_edit = f.isAncestorOf(obj)
            if clicked_inside_edit:
                return False
            same_window = False
            if isinstance(obj, QWidget) and hasattr(obj, "window"):
                same_window = (obj.window() is self._window)
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

        # 캔버스 고정 크기: config.PLOT_CANVAS_SIZE_PX (compare_plot / popup_plot 동일)
        central_layout.addStretch(1)
        self.canvas = FixedFigureCanvas(self.figure)
        self.canvas.setFixedSize(config.PLOT_CANVAS_SIZE_PX, config.PLOT_CANVAS_SIZE_PX)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        central_layout.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignCenter)
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
        self._range_toggle_btn.setStyleSheet("background: transparent; border: none; font-size: 11px;")
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
        self.lbl_f1_axis = QLabel(f"F1:", font=font_normal)
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

        analysis_edits = set(self.range_widgets.values()) | {self._hz_edit, self._bark_edit}
        self._click_clear_focus_filter = ClickClearFocusFilter(self, parent_widget, analysis_edits)
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
            QPushButton#BtnRuler:checked { background-color: #67C23A; color: white; font-weight: bold; border: none; }
        """)
        self.btn_ruler.clicked.connect(self.on_toggle_ruler)
        tool_group.addWidget(self.btn_ruler)

        self.btn_draw = QPushButton("그리기")
        self.btn_draw.setToolTip("추후 업데이트로 추가될 기능입니다.")
        self.btn_draw.setFixedHeight(35)
        self.btn_draw.setFont(font_normal)
        self.btn_draw.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_draw.setEnabled(False)
        self.btn_draw.setStyleSheet("""
            QPushButton { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #606266; }
            QPushButton:hover { background-color: #E4E7ED; }
            QPushButton:disabled { background-color: #F5F7FA; color: #C0C4CC; border: 1px solid #E4E7ED; }
        """)
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
        if hasattr(self, "_click_clear_focus_filter") and self._click_clear_focus_filter is not None:
            try:
                QApplication.instance().removeEventFilter(self._click_clear_focus_filter)
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
        ).activated.connect(self._safe_cancel_ruler_point)
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

    def _safe_cancel_ruler_point(self):
        if self._is_input_focused():
            return
        if self.controller.ruler_tool.active:
            self.controller.ruler_tool._cancel_current_drawing()

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
        self.btn_ruler.setChecked(not self.btn_ruler.isChecked())
        self.on_toggle_ruler()

    def on_toggle_ruler(self):
        self.setFocus()
        self.controller.toggle_ruler(self)
        self.btn_ruler.setChecked(self.controller.ruler_tool.active)

    def _safe_toggle_label_move(self):
        if self._is_input_focused():
            return
        self.design_tab.btn_label_move.setChecked(
            not self.design_tab.btn_label_move.isChecked()
        )
        self.on_toggle_label_move()

    def on_toggle_label_move(self):
        self.setFocus()
        self.controller.toggle_label_move(self)
        if self.controller.label_move_tool:
            self.design_tab.btn_label_move.setChecked(
                self.controller.label_move_tool.active
            )

    def update_label_move_style(self, is_on):
        self.design_tab.btn_label_move.setChecked(is_on)
        self.design_tab.btn_label_move.setStyleSheet(
            "QPushButton#BtnLabelMove { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #333;} "
            "QPushButton#BtnLabelMove:checked { background-color: #E6A23C; color: white; font-weight: bold; border: none; }"
        )
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_label_move_on(is_on)

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

    def _on_range_apply_clicked(self):
        """좌표축 범위 '적용' 버튼 전용: 적용 성공 시에만 로그 기록."""
        if self.on_apply():
            app_logger.info(config.LOG_MSG["PLOT_UPDATE"])

    def update_unit_labels(self, f1_unit, f2_unit=None):
        if f2_unit is None:
            f2_unit = f1_unit

        self.lbl_f1_axis.setText(f"F1:")
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
            f"background-color: {'#67C23A' if is_on else '#F0F2F5'}; color: {'white' if is_on else '#333'}; font-weight: {'bold' if is_on else 'normal'}; border-radius: 4px;"
        )
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_ruler_on(is_on)

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
