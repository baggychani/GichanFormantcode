# ui_compare.py

import os
import platform
import base64
from PyQt6.QtWidgets import (
    QDialog,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QDockWidget,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QFrame,
    QAbstractItemView,
    QTabWidget,
    QApplication,
    QSizePolicy,
    QStackedWidget,
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
    QPixmap,
    QShortcut,
    QKeySequence,
)

from .canvas_fixed import FixedFigureCanvas

from engine.plot_engine import PlotEngine
from .tool_indicator import ToolStatusIndicator
from utils import icon_utils
import config
import app_logger
from .filter_panel import MultiVowelFilterPanel

from .design_panel import CompareDesignSettingsPanel, NoWheelComboBox
from .icon_widgets import create_legend_icon_design, BidirectionalArrowButton
from .display_utils import truncate_display_name, MAX_DISPLAY_NAME_LEN
from utils.math_utils import hz_to_bark, bark_to_hz
from .layer_dock import LayerDockWidget
from . import layout_constants as layout


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


class SelectCompareDialog(QDialog):
    """
    사용자가 비교 분석을 수행할 대상 파일을 선택할 수 있도록 제공하는 다이얼로그입니다.
    QListWidget을 활용하여 직관적인 스크롤 및 키보드 네비게이션을 지원합니다.
    """

    def __init__(self, parent, controller, current_idx):
        super().__init__(parent)
        self.controller = controller
        self.current_idx = current_idx

        self.setWindowTitle("비교할 데이터 선택")
        self.setFixedSize(
            config.DIALOG_SELECT_COMPARE_WIDTH_PX,
            config.DIALOG_SELECT_COMPARE_HEIGHT_PX,
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._apply_pyqt6_icon()
        self._setup_ui()

        self.available_items = self.controller.get_compare_choices(self.current_idx)
        self._populate_list()

    def _apply_pyqt6_icon(self):
        try:
            icon_data = base64.b64decode(icon_utils.ICON_BASE64)
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.setWindowIcon(QIcon(pixmap))
        except Exception:
            pass

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #f5f7fa; }
            QListWidget { 
                background-color: white; border: 1px solid #dcdfe6; 
                border-radius: 6px; font-size: 13px; padding: 5px;
            }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #f0f2f5; }
            QListWidget::item:selected { background-color: #ecf5ff; color: #409eff; font-weight: bold; }
            QPushButton { 
                background-color: #ffffff; border: 1px solid #dcdfe6; 
                border-radius: 4px; padding: 8px; color: #606266; font-weight: bold;
            }
            QPushButton#btn_confirm { background-color: #67c23a; color: white; border: none; }
            QPushButton#btn_confirm:hover { background-color: #85ce61; }
            QPushButton:hover { background-color: #ecf5ff; color: #409eff; border-color: #c6e2ff; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        lbl_title = QLabel("비교할 대상 파일을 선택하세요")
        lbl_title.setFont(QFont("Malgun Gothic", 12, QFont.Weight.Bold))
        layout.addWidget(lbl_title)

        current_item = self.controller.get_data_item_at(self.current_idx)
        current_name = current_item["name"] if current_item else ""
        self.lbl_current_file = QLabel(f"현재 파일: {current_name}")
        self.lbl_current_file.setFont(QFont("Malgun Gothic", 10))
        self.lbl_current_file.setStyleSheet("color: #606266; padding: 4px 0;")
        layout.addWidget(self.lbl_current_file)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.list_widget.itemDoubleClicked.connect(self.on_confirm)
        self.list_widget.itemActivated.connect(self.on_confirm)
        layout.addWidget(self.list_widget)

        norm_row = QHBoxLayout()
        norm_row.addWidget(QLabel("정규화:", font=QFont("Malgun Gothic", 9)))
        self.combo_normalization = QComboBox()
        self.combo_normalization.setFont(QFont("Malgun Gothic", 9))
        self.combo_normalization.addItem("없음", None)
        self.combo_normalization.addItem("Lobanov", "Lobanov")
        self.combo_normalization.addItem("Gerstman", "Gerstman")
        self.combo_normalization.addItem("2mW/F", "2mW/F")
        self.combo_normalization.addItem("Bigham", "Bigham")
        self.combo_normalization.addItem("Nearey1", "Nearey1")
        ptype = self.controller.get_plot_type()
        if ptype in ("f1_f2_minus_f1", "f1_f2_prime_minus_f1"):
            self.combo_normalization.setEnabled(False)
        else:
            for i in range(self.combo_normalization.count()):
                data = self.combo_normalization.itemData(i)
                # 2mW/F와 Bigham은 f1_f2일 때만 허용, Nearey1은 f1_f2·f1_f3에서만 허용
                if data in ("2mW/F", "Bigham") and ptype != "f1_f2":
                    self.combo_normalization.model().item(i).setEnabled(False)
                if data == "Nearey1" and ptype not in ("f1_f2", "f1_f3"):
                    self.combo_normalization.model().item(i).setEnabled(False)
        norm_row.addWidget(self.combo_normalization, stretch=1)
        layout.addLayout(norm_row)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("취소")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("비교 시작")
        self.btn_confirm.setObjectName("btn_confirm")
        self.btn_confirm.setFixedWidth(120)
        self.btn_confirm.setDefault(True)
        self.btn_confirm.clicked.connect(self.on_confirm)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)

    def _populate_list(self):
        for idx, name in self.available_items:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.list_widget.addItem(item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _labels_in_df(self, df):
        col = "Label" if "Label" in df.columns else "label"
        if col not in df.columns:
            return set()
        return set(df[col].dropna().astype(str).str.strip().str.lower())

    def on_confirm(self):
        if getattr(self, "_confirming", False):
            return
        selected_item = self.list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(
                self, "선택 오류", "비교할 대상을 올바르게 선택해주세요."
            )
            return

        target_idx = selected_item.data(Qt.ItemDataRole.UserRole)
        norm = (
            self.combo_normalization.currentData()
            if self.combo_normalization.isEnabled()
            else None
        )
        if norm == "2mW/F":
            cur_item = self.controller.get_data_item_at(self.current_idx)
            tgt_item = self.controller.get_data_item_at(target_idx)
            lb = self._labels_in_df(cur_item["df"]) if cur_item else set()
            lr = self._labels_in_df(tgt_item["df"]) if tgt_item else set()
            if not ({"i", "a"} <= lb and {"i", "a"} <= lr):
                QMessageBox.warning(
                    self,
                    "정규화 불가",
                    "2mW/F 정규화는 두 파일 모두 모음 i, a가 필요합니다.",
                )
                return
        elif norm == "Bigham":
            cur_item = self.controller.get_data_item_at(self.current_idx)
            tgt_item = self.controller.get_data_item_at(target_idx)
            lb = self._labels_in_df(cur_item["df"]) if cur_item else set()
            lr = self._labels_in_df(tgt_item["df"]) if tgt_item else set()
            required = {"i", "a", "o", "u"}
            if not (required <= lb and required <= lr):
                QMessageBox.warning(
                    self,
                    "정규화 불가",
                    "Bigham 정규화는 두 파일 모두 모음 i, a, o, u가 필요합니다.",
                )
                return

        self._confirming = True
        self.btn_confirm.setEnabled(False)
        self.list_widget.setEnabled(False)

        self.accept()
        self.controller.open_compare_plot(
            self.current_idx,
            target_idx,
            normalization=norm,
            parent_window=self.parent(),
        )


class ComparePlotPopup(QMainWindow):
    """
    두 데이터 세트 간의 포먼트 분포 차이를 시각적으로 대조 분석하는 다중 플롯 창입니다.
    """

    def __init__(
        self,
        parent,
        controller,
        figure,
        idx_blue,
        idx_red,
        x_axis_label="F2",
        normalization=None,
    ):
        super().__init__(parent)

        self.controller = controller
        self.figure = figure
        self.idx_blue = idx_blue
        self.idx_red = idx_red
        self.x_axis_label = x_axis_label
        self.normalization = normalization
        self.fixed_plot_params = {}
        # 이 비교 창 인스턴스 전용 라벨 오프셋 캐시 (필요 시 사용)
        self.custom_offsets = {}

        self.was_dock_visible = True
        self.dock_floating_state = False
        self.was_layer_dock_visible = True
        self.layer_dock_floating_state = False
        self._layer_dock_geometry = None

        self.vowel_filter_state_blue = {}
        self.vowel_filter_state_red = {}
        self.layer_design_overrides_blue = {}
        self.layer_design_overrides_red = {}
        self.layer_order = []
        self.layer_locked_vowels_blue = set()
        self.layer_locked_vowels_red = set()
        self.filter_panel = None
        self.design_settings = {}
        # 다중 플롯 draw는 파일별이 아닌 공통 리스트를 사용할 계획.
        # (도구 이식 전 준비 단계: layer_dock/draw_manager 연동용 저장소)
        self._draw_objects_shared = []

        # 범례 위젯들을 저장하여 실시간 렌더링에 사용
        self.legend_refs = {"blue": {}, "red": {}}

        data_blue_item, data_red_item = self.controller.get_compare_data(
            self.idx_blue, self.idx_red
        )
        data_blue = data_blue_item["name"] if data_blue_item else ""
        data_red = data_red_item["name"] if data_red_item else ""
        self.default_save_name = (
            f"{os.path.splitext(data_blue)[0]}_{os.path.splitext(data_red)[0]}"
        )

        self._update_compare_window_title(data_blue, data_red)
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
            QMainWindow {{ background-color: #F5F7FA; }}
            QWidget#CentralWidget {{ background-color: transparent; }}

            QMainWindow::separator {{
                width: 0px; height: 0px; margin: 0px; padding: 0px; border: none; background: transparent;
            }}

            QDockWidget::title {{
                text-align: left; background: #FFFFFF; padding-left: 10px; padding-top: 6px; padding-bottom: 6px;
                font-size: 11px; font-weight: bold; color: #555555;
            }}

            QTabWidget::pane {{ border-top: 1px solid #E4E7ED; background: white; }}
            QTabBar::tab {{
                background: #E4E7ED; border: 1px solid #DCDFE6; border-bottom: none;
                border-top-left-radius: 4px; border-top-right-radius: 4px; min-width: {0}px; padding: 6px 0px; color: #606266;
            }}
            QTabBar::tab:selected {{ background: #FFFFFF; color: #303133; font-weight: bold; }}
            QTabBar::tab:hover:!selected {{ background: #EBEEF5; color: #409EFF; }}
        """.format(config.TAB_BAR_MIN_WIDTH_PX)
        )

        self.current_unit = "Hz"
        self._setup_ui(data_blue, data_red)
        self._bind_shortcuts()

    def get_filter_state_blue(self):
        return self.vowel_filter_state_blue

    def get_filter_state_red(self):
        return self.vowel_filter_state_red

    def get_design_settings(self):
        return self.design_settings

    def get_layer_design_overrides_blue(self):
        return self.layer_design_overrides_blue

    def get_layer_design_overrides_red(self):
        return self.layer_design_overrides_red

    def _apply_pyqt6_icon(self):
        try:
            icon_data = base64.b64decode(icon_utils.ICON_BASE64)
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.setWindowIcon(QIcon(pixmap))
        except Exception:
            pass

    def _setup_ui(self, data_blue, data_red):
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
            canvas_container, ui_font_name=self.ui_font_name, show_lock=False
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

        self._build_unified_dock(data_blue, data_red)

    def _build_unified_dock(self, data_blue, data_red):
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

        dock_layout = QVBoxLayout(self.dock_container)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._tab_wheel_blocker1 = TabBarWheelBlocker(self)
        self.tab_widget.tabBar().installEventFilter(self._tab_wheel_blocker1)

        self.analysis_tab = QWidget()
        self._setup_analysis_ui(self.analysis_tab, data_blue, data_red)
        self.tab_widget.addTab(self.analysis_tab, "분석 도구")

        self.design_tab = CompareDesignSettingsPanel(
            name_blue=data_blue,
            name_red=data_red,
            parent=self,
            ui_font_name=self.ui_font_name,
            is_normalized=bool(self.normalization),
        )
        self.design_settings = self.design_tab.get_current_settings()
        self.design_tab.settings_changed.connect(self._on_design_settings_changed)

        # --- [수정된 부분] 시그널 실행 순서 강제 재배치 ---
        try:
            self.design_tab.btn_reset.clicked.disconnect(
                self.design_tab._reset_to_defaults
            )  # 1. 기본 화면 새로고침 끊기
        except TypeError:
            pass

        self.design_tab.btn_reset.clicked.connect(
            lambda: app_logger.info(config.LOG_MSG["DESIGN_RESET_ALL"])
        )  # 2. 로그 기록
        self.design_tab.btn_reset.clicked.connect(
            lambda: self.controller.clear_label_offsets_for_popup(self)
        )  # 3. 데이터 먼저 삭제
        self.design_tab.btn_reset.clicked.connect(
            self.design_tab._reset_to_defaults
        )  # 4. 그 다음에 화면 그리기
        # ---------------------------------------------------

        self.design_tab.label_move_clicked.connect(self._on_compare_label_move_clicked)
        self.tab_widget.addTab(self.design_tab, "디자인 설정")
        self._tab_wheel_blocker2 = TabBarWheelBlocker(self)
        self.design_tab.sub_tabs.tabBar().installEventFilter(self._tab_wheel_blocker2)

        dock_layout.addWidget(self.tab_widget)
        self.dock_widget.setWidget(self.dock_container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_widget)

        self.dock_widget.dockLocationChanged.connect(self._on_dock_state_changed)
        self.dock_widget.topLevelChanged.connect(self._on_dock_state_changed)

        # 레이어 설정 도크 (우측 별도 도크). 파일 선택 버튼은 layer_dock 내부(레이어 탭, 전체 눈/반투명 행 바로 위)에 있음.
        data_blue_item, data_red_item = self.controller.get_compare_data(
            self.idx_blue, self.idx_red
        )
        name_blue = (data_blue_item or {}).get("name", data_blue)
        name_red = (data_red_item or {}).get("name", data_red)

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
        layer_dock_layout = QVBoxLayout(self._layer_dock_container)
        layer_dock_layout.setContentsMargins(0, 0, 0, 0)
        layer_dock_layout.setSpacing(0)

        self._layer_stack = QStackedWidget()
        self._layer_dock_blue = LayerDockWidget(
            self,
            ui_font_name=self.ui_font_name,
            state_key="blue",
            compare_mode=True,
            file_a_name=name_blue,
            file_b_name=name_red,
            get_default_design=lambda: self._get_layer_dock_default_design("blue"),
        )
        self._layer_dock_blue.filter_state_changed.connect(
            self._on_compare_layer_filter_changed
        )
        self._layer_dock_blue.overrides_changed.connect(
            self._on_compare_layer_overrides_changed
        )
        self._layer_dock_blue.compare_switch_requested.connect(
            self._on_compare_layer_switch_requested
        )
        self._layer_stack.addWidget(self._layer_dock_blue)
        self.layer_dock_splitter_sizes = self._layer_dock_blue._splitter.sizes()
        self._layer_dock_blue.splitter_sizes_changed.connect(
            self._on_compare_layer_splitter_changed
        )
        self._layer_dock_blue.order_changed.connect(
            self._on_compare_layer_order_changed
        )
        self._layer_dock_red = LayerDockWidget(
            self,
            ui_font_name=self.ui_font_name,
            state_key="red",
            compare_mode=True,
            file_a_name=name_blue,
            file_b_name=name_red,
            get_default_design=lambda: self._get_layer_dock_default_design("red"),
        )
        self._layer_dock_red.filter_state_changed.connect(
            self._on_compare_layer_filter_changed
        )
        self._layer_dock_red.overrides_changed.connect(
            self._on_compare_layer_overrides_changed
        )
        self._layer_dock_red.compare_switch_requested.connect(
            self._on_compare_layer_switch_requested
        )
        self._layer_dock_red.splitter_sizes_changed.connect(
            self._on_compare_layer_splitter_changed
        )
        self._layer_dock_red.order_changed.connect(self._on_compare_layer_order_changed)
        self._layer_stack.addWidget(self._layer_dock_red)
        layer_dock_layout.addWidget(self._layer_stack, 1)

        # Blue/Red 레이어 도크 디자인 영역 스크롤 위치 동기화 (탭 전환 시 스크롤 유지)
        self._layer_scroll_sync_block = False
        vbar_blue = self._layer_dock_blue._design_scroll.verticalScrollBar()
        vbar_red = self._layer_dock_red._design_scroll.verticalScrollBar()

        def _sync_scroll_to_red(value):
            if self._layer_scroll_sync_block:
                return
            self._layer_scroll_sync_block = True
            vbar_red.setValue(value)
            self._layer_scroll_sync_block = False

        def _sync_scroll_to_blue(value):
            if self._layer_scroll_sync_block:
                return
            self._layer_scroll_sync_block = True
            vbar_blue.setValue(value)
            self._layer_scroll_sync_block = False

        vbar_blue.valueChanged.connect(_sync_scroll_to_red)
        vbar_red.valueChanged.connect(_sync_scroll_to_blue)

        self.layer_dock_widget.setWidget(self._layer_dock_container)
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.layer_dock_widget
        )

        def _get_label_column(df):
            if df is None:
                return None
            return (
                "Label"
                if "Label" in df.columns
                else ("label" if "label" in df.columns else None)
            )

        def _feed_layer_vowels():
            d_blue = (data_blue_item or {}).get("df")
            d_red = (data_red_item or {}).get("df")
            lbl_col_blue = _get_label_column(d_blue)
            lbl_col_red = _get_label_column(d_red)
            if d_blue is not None and lbl_col_blue:
                vowels_blue = sorted(
                    d_blue[lbl_col_blue].dropna().astype(str).unique().tolist()
                )
                self._layer_dock_blue.set_vowels(vowels_blue)
            if d_red is not None and lbl_col_red:
                vowels_red = sorted(
                    d_red[lbl_col_red].dropna().astype(str).unique().tolist()
                )
                self._layer_dock_red.set_vowels(vowels_red)

        _feed_layer_vowels()
        self._layer_dock_blue.set_compare_file_index(0)
        self._layer_dock_red.set_compare_file_index(0)

        self._on_dock_state_changed()

    def _on_dock_state_changed(self, *args):
        tools_floating = self.dock_widget.isFloating()
        layer_floating = (
            self.layer_dock_widget.isFloating()
            if hasattr(self, "layer_dock_widget") and self.layer_dock_widget
            else True
        )
        if tools_floating and layer_floating:
            self.sep_left.hide()
            self.sep_right.hide()
        else:
            sep_left_show = (
                not tools_floating
                and self.dockWidgetArea(self.dock_widget)
                == Qt.DockWidgetArea.LeftDockWidgetArea
            )
            sep_right_show = (
                not layer_floating
                and self.dockWidgetArea(self.layer_dock_widget)
                == Qt.DockWidgetArea.RightDockWidgetArea
                if hasattr(self, "layer_dock_widget") and self.layer_dock_widget
                else False
            )
            self.sep_left.setVisible(sep_left_show)
            self.sep_right.setVisible(sep_right_show)

    def _setup_analysis_ui(self, parent_widget, data_blue, data_red):
        parent_widget.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(12, 15, 12, 15)
        layout.setSpacing(12)

        font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        font_normal = QFont(self.ui_font_name, 9)

        legend_group = QVBoxLayout()
        legend_group.setSpacing(8)
        lbl_title = QLabel("데이터 범례", font=font_bold)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        legend_group.addWidget(lbl_title)

        def create_legend_item(
            group_id, default_color, default_style, file_name, default_marker="o"
        ):
            row = QWidget()
            rlayout = QHBoxLayout(row)
            rlayout.setContentsMargins(0, 0, 0, 0)
            rlayout.setSpacing(0)

            icon_lbl = QLabel()
            icon_lbl.setFixedSize(50, 16)
            icon_lbl.setPixmap(
                create_legend_icon_design(default_color, default_style, default_marker)
            )

            lbl_a = QLabel("a")
            lbl_a.setFont(font_bold)
            lbl_a.setStyleSheet(f"color: {default_color};")

            clean_name = os.path.splitext(file_name)[0]
            display_name = truncate_display_name(clean_name, MAX_DISPLAY_NAME_LEN)
            lbl_text = QLabel(display_name)
            lbl_text.setFont(font_normal)
            lbl_text.setStyleSheet("color: #333333;")
            lbl_text.setToolTip(clean_name)
            lbl_text.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
            )

            rlayout.addWidget(icon_lbl)
            rlayout.addSpacing(6)
            rlayout.addWidget(lbl_a)
            rlayout.addSpacing(15)
            rlayout.addWidget(lbl_text, stretch=1)

            self.legend_refs[group_id] = {"icon": icon_lbl, "text": lbl_a}
            return row

        legend_group.addWidget(
            create_legend_item("blue", "#1976D2", "-", data_blue, "o")
        )
        legend_group.addWidget(
            create_legend_item("red", "#E64A19", "---", data_red, "o")
        )
        layout.addLayout(legend_group)
        legend_group.addSpacing(8)

        self.norm_section_widget = QWidget()
        norm_group = QVBoxLayout(self.norm_section_widget)
        norm_group.setSpacing(4)
        norm_group.setContentsMargins(0, 0, 0, 0)
        lbl_norm_title = QLabel("정규화", font=font_bold)
        lbl_norm_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        norm_group.addWidget(lbl_norm_title)
        self.lbl_norm_value = QLabel(
            getattr(self, "normalization", None) or "없음", font=font_normal
        )
        self.lbl_norm_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_norm_value.setStyleSheet("color: #606266;")
        norm_group.addWidget(self.lbl_norm_value)
        layout.addWidget(self.norm_section_widget)

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color: #E4E7ED;")
        layout.addWidget(line1)

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
        self._last_conv_focus = "hz"  # 마지막으로 포커스된 입력 (버튼 클릭 시 포커스가 버튼으로 가므로 이 값 사용)

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
                # 마지막으로 포커스된 입력란을 소스로 사용 (버튼 클릭 시 포커스가 버튼으로 가므로 hasFocus 대신 사용)
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

        self._apply_normalization_axis_ui()

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #E4E7ED;")
        layout.addWidget(line2)

        tool_group = QVBoxLayout()
        tool_group.setSpacing(8)
        t_lbl = QLabel("분석 도구", font=font_bold)
        t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tool_group.addWidget(t_lbl)

        self.btn_vowel_analysis = QPushButton("모음 상세 분석")
        self.btn_vowel_analysis.setFixedHeight(35)
        self.btn_vowel_analysis.setFont(font_normal)
        self.btn_vowel_analysis.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_vowel_analysis.setEnabled(True)
        self.btn_vowel_analysis.clicked.connect(self._on_vowel_analysis_clicked)
        tool_group.addWidget(self.btn_vowel_analysis)

        nav_btn_style = """
            QPushButton { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; color: #333333; }
            QPushButton:hover { background-color: #F5F7FA; color: #409EFF; border-color: #C0C4CC; }
        """
        self.btn_vowel_analysis.setStyleSheet(nav_btn_style)

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
        self.btn_draw.setCheckable(True)
        self.btn_draw.setToolTip("")
        self.btn_draw.setFixedHeight(35)
        self.btn_draw.setFont(font_normal)
        self.btn_draw.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_draw.setEnabled(False)
        self.btn_draw.setStyleSheet("""
            QPushButton { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #606266; }
            QPushButton:hover:!checked { background-color: #E4E7ED; }
            QPushButton:checked { background-color: #409EFF; color: white; font-weight: bold; border: none; }
            QPushButton:disabled { background-color: #F5F7FA; color: #C0C4CC; border: 1px solid #E4E7ED; }
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
        layout.addLayout(export_group)

    def _apply_normalization_axis_ui(self):
        """정규화 플롯일 때 좌표축 레이블/단위/범위 적용. Gerstman만 읽기 전용. 정규화 없으면 정규화 섹션 숨김."""
        norm = getattr(self, "normalization", None)
        if hasattr(self, "norm_section_widget"):
            self.norm_section_widget.setVisible(bool(norm))
        if not getattr(self, "range_widgets", None):
            return
        if not norm:
            return
        r = PlotEngine.NORM_RANGES.get(norm, PlotEngine.NORM_RANGES["Lobanov"])
        if hasattr(self, "lbl_f1_axis"):
            self.lbl_f1_axis.setText("nF1:")
        if hasattr(self, "lbl_x_axis"):
            self.lbl_x_axis.setText("nF2:")
        if hasattr(self, "lbl_f1_unit"):
            self.lbl_f1_unit.setText("")
        if hasattr(self, "lbl_f2_unit"):
            self.lbl_f2_unit.setText("")
        for key in ["y_min", "y_max", "x_min", "x_max"]:
            self.range_widgets[key].setText(str(r[key]))
            self.range_widgets[key].setReadOnly(norm == "Gerstman")

    def _update_legend_style(self):
        """디자인 설정 변경 시 범례 아이콘과 텍스트 색상을 실시간 업데이트합니다."""
        if not self.design_settings:
            return

        for ds_type in ["blue", "red"]:
            if ds_type in self.design_settings and ds_type in self.legend_refs:
                cfg = self.design_settings[ds_type]

                ell_color = cfg.get("ell_color")
                if not ell_color or ell_color == "transparent":
                    ell_color = "#1976D2" if ds_type == "blue" else "#E64A19"

                ell_style = cfg.get("ell_style", "-" if ds_type == "blue" else "--")
                centroid_marker = cfg.get("centroid_marker", "o")
                if centroid_marker not in ("o", "s", "^", "D", "wo", "ws", "w^", "wD"):
                    centroid_marker = "o"
                legend_marker = (
                    centroid_marker[1]
                    if centroid_marker in ("wo", "ws", "w^", "wD")
                    else centroid_marker
                )

                lbl_color = cfg.get("lbl_color")
                if not lbl_color or lbl_color == "transparent":
                    lbl_color = "#1976D2" if ds_type == "blue" else "#E64A19"

                # 범례 아이콘(선과 점) 새로 그리기 — 디자인 설정과 동일한 create_legend_icon_design 사용
                new_pixmap = create_legend_icon_design(
                    ell_color, ell_style, legend_marker
                )
                self.legend_refs[ds_type]["icon"].setPixmap(new_pixmap)

                # 라벨(a) 텍스트 색상 적용
                self.legend_refs[ds_type]["text"].setStyleSheet(f"color: {lbl_color};")

    def _get_layer_dock_default_design(self, series):
        """레이어 도크에서 개별 오버라이드 없을 때 쓸 기본값. series='blue'|'red' → 좌측 디자인 탭의 해당 파일 설정(common+blue/red) 반환."""
        if not hasattr(self, "design_tab") or self.design_tab is None:
            return {}
        s = self.design_tab.get_current_settings()
        common = s.get("common", {})
        ind = s.get(series, {})
        return {**common, **ind}

    def _on_design_settings_changed(self, settings):
        """디자인 패널의 설정이 변경되었을 때 실시간 반영을 위한 콜백"""
        self.design_settings = settings
        self._update_legend_style()
        if hasattr(self.design_tab, "update_legend_indicators"):
            self.design_tab.update_legend_indicators(settings)
        self.on_apply()
        if hasattr(self, "_layer_dock_blue") and self._layer_dock_blue:
            self._layer_dock_blue.refresh_design_ui()
        if hasattr(self, "_layer_dock_red") and self._layer_dock_red:
            self._layer_dock_red.refresh_design_ui()

    def closeEvent(self, event):
        if self.controller.ruler_tool.active:
            self.controller.toggle_ruler(self)
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
            if hasattr(self, "layer_dock_widget") and self.layer_dock_widget:
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
        QShortcut(
            QKeySequence(Qt.Key.Key_R), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_ruler)
        QShortcut(
            QKeySequence(Qt.Key.Key_P), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_draw)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._safe_save_jpg)
        QShortcut(
            QKeySequence("Esc"), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_cancel_ruler_point)
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

    def _safe_toggle_bold(self):
        if self._is_input_focused():
            return
        if hasattr(self, "design_tab") and self.design_tab is not None:
            ctrl = (
                self.design_tab.ctrl_blue
                if self.design_tab.sub_tabs.currentIndex() == 0
                else self.design_tab.ctrl_red
            )
            ctrl["btn_bold"].setChecked(not ctrl["btn_bold"].isChecked())

    def _safe_toggle_italic(self):
        if self._is_input_focused():
            return
        if hasattr(self, "design_tab") and self.design_tab is not None:
            ctrl = (
                self.design_tab.ctrl_blue
                if self.design_tab.sub_tabs.currentIndex() == 0
                else self.design_tab.ctrl_red
            )
            ctrl["btn_italic"].setChecked(not ctrl["btn_italic"].isChecked())

    def _safe_switch_to_tab(self, index):
        if self._is_input_focused():
            return
        if self.tab_widget.currentIndex() != index:
            self.tab_widget.setCurrentIndex(index)

    def _toggle_panels_visibility(self):
        if self.dock_widget.isVisible():
            self.was_dock_visible = True
            self.dock_floating_state = self.dock_widget.isFloating()
            self.dock_widget.hide()
            if hasattr(self, "layer_dock_widget") and self.layer_dock_widget:
                self.was_layer_dock_visible = self.layer_dock_widget.isVisible()
                self.layer_dock_floating_state = self.layer_dock_widget.isFloating()
                self._layer_dock_geometry = (
                    self.layer_dock_widget.geometry()
                    if self.layer_dock_widget.isVisible()
                    else self._layer_dock_geometry
                )
                self.layer_dock_widget.hide()
        else:
            if self.was_dock_visible:
                if self.dock_floating_state:
                    self.dock_widget.setFloating(True)
                self.dock_widget.show()
            if (
                hasattr(self, "layer_dock_widget")
                and self.layer_dock_widget
                and self.was_layer_dock_visible
            ):
                if self.layer_dock_floating_state:
                    self.layer_dock_widget.setFloating(True)
                if self._layer_dock_geometry is not None:
                    self.layer_dock_widget.setGeometry(self._layer_dock_geometry)
                self.layer_dock_widget.show()

    def on_reset_clicked(self):
        self.setFocus()
        self._reset_ranges_to_default(apply_plot=True)
        app_logger.info(config.LOG_MSG["PLOT_RANGE_INIT"])

    def on_apply(self):
        self.setFocus()
        self.figure.set_size_inches(6.5, 6.5)
        try:
            y_min = float(self.range_widgets["y_min"].text())
            y_max = float(self.range_widgets["y_max"].text())
            x_min = float(self.range_widgets["x_min"].text())
            x_max = float(self.range_widgets["x_max"].text())

            norm = getattr(self, "normalization", None)
            y_name = "nF1" if norm else "F1"
            x_name = "nF2" if norm else self.x_axis_label
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

        self.controller.refresh_compare_plot(
            self.figure,
            self.canvas,
            self.range_widgets,
            None,
            self,
            self.idx_blue,
            self.idx_red,
        )
        data_blue_item, data_red_item = self.controller.get_compare_data(
            self.idx_blue, self.idx_red
        )
        data_blue = data_blue_item["name"] if data_blue_item else ""
        data_red = data_red_item["name"] if data_red_item else ""
        self._update_compare_window_title(data_blue, data_red)
        return True

    def _on_range_apply_clicked(self):
        """좌표축 범위 '적용' 버튼 전용: 적용 후 로그만 기록."""
        if self.on_apply():
            app_logger.info(config.LOG_MSG["PLOT_RANGE_APPLIED"])

    def _safe_toggle_ruler(self):
        if self._is_input_focused():
            return
        next_state = not self.btn_ruler.isChecked()
        # 배타 모드: ruler를 켜려면 draw/label_move가 모두 꺼져 있어야 함
        if next_state and (
            self._is_draw_active() or self._is_compare_label_move_active()
        ):
            return
        self.btn_ruler.setChecked(next_state)
        self.on_toggle_ruler()

    def on_toggle_ruler(self):
        # 버튼 직접 클릭 경로에서도 배타 모드 강제
        if self.btn_ruler.isChecked() and (
            self._is_draw_active() or self._is_compare_label_move_active()
        ):
            self.btn_ruler.setChecked(False)
            self.update_ruler_style(False)
            return
        self.setFocus()
        self.controller.toggle_ruler(self)
        self.update_ruler_style(self.controller.ruler_tool.active)

    def _safe_toggle_draw(self):
        if self._is_input_focused():
            return
        if not getattr(self, "btn_draw", None):
            return
        # 현재 compare 모드의 draw는 이식 전이라 비활성화. 키맵은 준비만 해두고 무시.
        if not self.btn_draw.isEnabled():
            return
        next_state = not self.btn_draw.isChecked()
        if next_state and (
            self._is_ruler_active() or self._is_compare_label_move_active()
        ):
            return
        self.btn_draw.setChecked(next_state)
        self._on_toggle_draw()

    def _on_toggle_draw(self):
        # 버튼 직접 클릭 경로에서도 배타 모드 강제
        if self.btn_draw.isChecked() and (
            self._is_ruler_active() or self._is_compare_label_move_active()
        ):
            self.btn_draw.setChecked(False)
            if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
                self.tool_indicator.set_draw_mode_on(False)
            return
        # compare 모드 draw 이식 전: UI 표시만 OFF 유지
        if not self.btn_draw.isEnabled():
            self.btn_draw.setChecked(False)
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_draw_mode_on(self.btn_draw.isChecked())

    def keyPressEvent(self, event):
        """T 키: 현재 디자인 서브 탭(Blue/Red)에 해당하는 라벨 위치 이동 툴만 토글."""
        if event.key() == Qt.Key.Key_T:
            if (
                not self._is_input_focused()
                and hasattr(self, "design_tab")
                and self.design_tab is not None
            ):
                idx = self.design_tab.sub_tabs.currentIndex()
                series = "blue" if idx == 0 else "red"
                self._safe_toggle_compare_label_move(series)
            return
        super().keyPressEvent(event)

    def _on_compare_label_move_clicked(self, series):
        self._safe_toggle_compare_label_move(series)

    def _safe_toggle_compare_label_move(self, series):
        if self._is_input_focused():
            return
        active = self._is_compare_label_move_active()
        current_series = getattr(self, "_label_move_series", None)
        wants_on = (not active) or (current_series != series)
        # 배타 모드: label_move를 켜려면 draw/ruler가 모두 꺼져 있어야 함
        if wants_on and (self._is_draw_active() or self._is_ruler_active()):
            # 클릭으로 체크 상태가 흔들렸을 수 있으니 실제 툴 상태로 UI 재동기화
            sync_series = (
                current_series if current_series in ("blue", "red") else series
            )
            self.update_compare_label_move_style(sync_series, active)
            return
        self.setFocus()
        self.controller.toggle_compare_label_move(self, series)

    def update_compare_label_move_style(self, series, is_on):
        self.design_tab.ctrl_blue["btn_label_move"].setChecked(
            is_on and series == "blue"
        )
        self.design_tab.ctrl_red["btn_label_move"].setChecked(is_on and series == "red")
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_label_move_on(is_on)

    def _is_ruler_active(self):
        return bool(
            getattr(self.controller, "ruler_tool", None)
            and self.controller.ruler_tool.active
        )

    def _is_compare_label_move_active(self):
        return bool(
            getattr(self.controller, "label_move_tool", None)
            and self.controller.label_move_tool.active
        )

    def _is_draw_active(self):
        return bool(getattr(self, "btn_draw", None) and self.btn_draw.isChecked())

    def _safe_open_filter(self):
        if self._is_input_focused():
            return
        self.open_vowel_filter()

    def on_filter_clicked(self):
        self.setFocus()
        self.open_vowel_filter()

    def _on_vowel_analysis_clicked(self):
        """모음 상세 분석: 비교 중인 두 파일에 대해 탭 2개짜리 분석 창을 연다."""
        self.setFocus()
        self.controller.open_vowel_analysis_window(self)

    def open_vowel_filter(self):
        if self.filter_panel is not None and self.filter_panel.isVisible():
            self.filter_panel.raise_()
            self.filter_panel.activateWindow()
            return

        data_blue, data_red = self.controller.get_compare_data(
            self.idx_blue, self.idx_red
        )
        if not data_blue or not data_red:
            return
        df_blue = data_blue["df"]
        col_label_blue = (
            "Label"
            if "Label" in df_blue.columns
            else "label"
            if "label" in df_blue.columns
            else None
        )

        df_red = data_red["df"]
        col_label_red = (
            "Label"
            if "Label" in df_red.columns
            else "label"
            if "label" in df_red.columns
            else None
        )

        if not col_label_blue or not col_label_red:
            QMessageBox.warning(
                self,
                "오류",
                "비교할 데이터 중 모음 라벨(Label) 컬럼이 누락된 파일이 있습니다.",
            )
            return

        vowels_blue = df_blue[col_label_blue].dropna().unique().tolist()
        vowels_red = df_red[col_label_red].dropna().unique().tolist()

        self.filter_panel = MultiVowelFilterPanel(
            parent=self,
            file1_name=data_blue["name"],
            vowels1=vowels_blue,
            state1=self.vowel_filter_state_blue,
            file2_name=data_red["name"],
            vowels2=vowels_red,
            state2=self.vowel_filter_state_red,
            on_change_callback=self._on_multi_filter_changed,
        )
        self.filter_panel.show()

    def _on_multi_filter_changed(self, state_blue, state_red):
        self.vowel_filter_state_blue = state_blue
        self.vowel_filter_state_red = state_red
        self.on_apply()

    def _on_compare_layer_filter_changed(self, state):
        """레이어 도크에서 필터(눈/반투명) 변경 시 플롯만 갱신. 상태는 도크가 이미 반영함."""
        self.on_apply()

    def _on_compare_layer_switch_requested(self, index):
        """레이어 도크 내 파일 선택 버튼 클릭 시 스택 전환 및 양쪽 도크 버튼 상태 동기화."""
        self._layer_stack.setCurrentIndex(index)
        self._layer_dock_blue.set_compare_file_index(index)
        self._layer_dock_red.set_compare_file_index(index)

    def _on_compare_layer_splitter_changed(self, sizes):
        """한쪽 레이어 도크 스플리터 조절 시 비율 저장 후 다른 쪽에 동일 적용."""
        self.layer_dock_splitter_sizes = list(sizes)
        self._layer_dock_blue.set_splitter_sizes(sizes)
        self._layer_dock_red.set_splitter_sizes(sizes)

    def _on_compare_layer_overrides_changed(self, overrides):
        """레이어 도크에서 디자인 오버라이드 변경 시 플롯만 갱신. 상태는 도크가 이미 반영함."""
        self.on_apply()

    def _on_compare_layer_order_changed(self, order):
        sender = self.sender()
        if sender is None:
            return
        # Blue에서 바꿨으면 Red를 새로고침
        if sender == self._layer_dock_blue:
            current_red_vowels = list(self._layer_dock_red._layer_rows.keys())
            self._layer_dock_red.set_vowels(current_red_vowels)

        # Red에서 바꿨으면 Blue를 새로고침
        if sender == self._layer_dock_red:
            current_blue_vowels = list(self._layer_dock_blue._layer_rows.keys())
            self._layer_dock_blue.set_vowels(current_blue_vowels)

    def _safe_save_jpg(self):
        if self._is_input_focused():
            return
        self.controller.download_plot(self.figure, "jpg", parent_window=self)

    def _reset_ranges_to_default(self, apply_plot=True):
        if not hasattr(self, "fixed_plot_params"):
            return
        norm = getattr(self, "normalization", None)
        if norm:
            r = PlotEngine.NORM_RANGES.get(norm, PlotEngine.NORM_RANGES["Lobanov"])
            for k in ["y_min", "y_max", "x_min", "x_max"]:
                self.range_widgets[k].setText(str(r[k]))
            self.range_widgets["y_min"].setReadOnly(norm == "Gerstman")
            self.range_widgets["y_max"].setReadOnly(norm == "Gerstman")
            self.range_widgets["x_min"].setReadOnly(norm == "Gerstman")
            self.range_widgets["x_max"].setReadOnly(norm == "Gerstman")
        else:
            ptype = self.fixed_plot_params.get("type", "f1_f2")
            use_bark = self.fixed_plot_params.get("use_bark_units", False)
            smart_ranges = self.controller.get_smart_ranges_for_params(ptype, use_bark)
            for k in ["y_min", "y_max", "x_min", "x_max"]:
                self.range_widgets[k].setText(smart_ranges[k])
                self.range_widgets[k].setReadOnly(False)
        self.cb_sigma.setCurrentText(str(config.DEFAULT_SIGMA))
        if apply_plot is True:
            self.on_apply()

    def update_unit_labels(self, f1_unit, f2_unit=None):
        if f2_unit is None:
            f2_unit = f1_unit

        self.lbl_f1_axis.setText("F1:")
        self.lbl_x_axis.setText(f"{self.x_axis_label}:")

        if hasattr(self, "lbl_f1_unit"):
            self.lbl_f1_unit.setText(f"({f1_unit})")
        if hasattr(self, "lbl_f2_unit"):
            self.lbl_f2_unit.setText(f"({f2_unit})")

    def update_x_label(self, new_label):
        self.x_axis_label = new_label
        self.lbl_x_axis.setText(f"{new_label}:")

    def _update_compare_window_title(self, data_blue, data_red):
        base = f"다중 플롯 모드 - {data_blue} vs {data_red}"
        mode = self.controller.get_outlier_mode()
        if mode == "1sigma":
            base += " (이상치 제거 : 1σ)"
        elif mode == "2sigma":
            base += " (이상치 제거 : 2σ)"
        if getattr(self, "normalization", None):
            base += f" / {self.normalization}"
        self.setWindowTitle(base)

    def get_sigma(self):
        return self.cb_sigma.currentText()

    def _get_current_draw_objects(self):
        """다중 플롯용 공통 draw 객체 리스트 반환 (이식 준비용)."""
        return self._draw_objects_shared

    def _set_current_draw_objects(self, lst):
        """다중 플롯용 공통 draw 객체 리스트 교체 (이식 준비용)."""
        self._draw_objects_shared = list(lst or [])

    def _redraw_draw_layer(self):
        """draw 렌더러 이식 전 no-op. 레이어 도크 호출 경로만 준비."""
        if getattr(self, "canvas", None) is not None:
            self.canvas.draw_idle()

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
            # compare draw는 아직 미이식 상태이므로 indicator는 항상 OFF를 유지
            if not self.btn_draw.isEnabled():
                self.tool_indicator.set_draw_mode_on(False)
