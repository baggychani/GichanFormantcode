# ui_main.py

import os
import platform
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QCheckBox,
    QTextEdit,
    QButtonGroup,
    QHeaderView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QFileDialog,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

import config
from utils import icon_utils, app_logger
from ui.widgets.design_panel import NoWheelComboBox

# 중앙 설정 열(ANALYSIS STRUCTURE ~ DATA PROCESSING) 공통 레이아웃 상수
_SETTINGS_LABEL_COL_W = 115
_SETTINGS_GRID_V_SPACING = 10
_SETTINGS_GRID_H_SPACING = 8
_SETTINGS_GROUP_MARGINS = (12, 10, 12, 10)
_SETTINGS_SECTION_GAP = 10
_SETTINGS_CTRL_H = 30


def _settings_field_label(text: str) -> QLabel:
    """설정 그리드 좌측 라벨 — 행 높이에 맞춰 수직 중앙 정렬."""
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    return lbl


def _apply_settings_grid(
    grid: QGridLayout, row_count: int, *, apply_row_min: bool = True
) -> None:
    """AXIS SCALES / DATA PROCESSING 그리드 줄 간격·행 높이 통일."""
    grid.setColumnMinimumWidth(0, _SETTINGS_LABEL_COL_W)
    grid.setVerticalSpacing(_SETTINGS_GRID_V_SPACING)
    grid.setHorizontalSpacing(_SETTINGS_GRID_H_SPACING)
    grid.setContentsMargins(*_SETTINGS_GROUP_MARGINS)
    if apply_row_min:
        for row in range(row_count):
            grid.setRowMinimumHeight(row, _SETTINGS_CTRL_H)


class DropLabel(QLabel):
    def __init__(self, text, controller, parent=None):
        super().__init__(text, parent)
        self.controller = controller
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setWordWrap(True)
        # 점선(dashed) 대신 실선(solid) 유지 + 완벽한 라운딩(border-radius: 8px) 적용
        self.setStyleSheet(
            "background-color: #fcfcfc; color: #777; border: 1px solid #dcdfe6; border-radius: 8px; padding: 5px;"
        )
        self.setMinimumHeight(56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                "background-color: #ecf5ff; color: #409eff; border: 2px solid #409eff; border-radius: 8px; padding: 5px;"
            )

    def dragLeaveEvent(self, event):
        self.setStyleSheet(
            "background-color: #fcfcfc; color: #777; border: 1px solid #dcdfe6; border-radius: 8px; padding: 5px;"
        )

    def dropEvent(self, event):
        self.setStyleSheet(
            "background-color: #fcfcfc; color: #777; border: 1px solid #dcdfe6; border-radius: 8px; padding: 5px;"
        )
        files = [
            url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()
        ]
        if files:
            self.controller.handle_file_drop(files)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.controller.open_file_dialog()


class MainUI(QMainWindow):
    def __init__(self, controller, status_callback=None):
        super().__init__()
        self.controller = controller

        def _report(msg):
            if status_callback:
                status_callback(msg)

        _report("Initializing Main Interface...")
        self.setWindowTitle(config.APP_TITLE)

        # 아이콘 로드 및 적용
        _report("Loading UI Resources...")
        self._apply_window_icon()

        # 창 크기 고정 (config.WINDOW_SIZE_MAIN: "WxH")
        win_w, win_h = map(int, config.WINDOW_SIZE_MAIN.split("x"))
        self.setFixedSize(win_w, win_h)

        # 제목 표시줄의 최대화(ㅁ) 버튼 비활성화 (최소화, 닫기 버튼만 유지)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowSystemMenuHint
        )

        _report("Setting up Typography...")
        self.ui_font_name = (
            "Malgun Gothic" if platform.system() == "Windows" else "AppleGothic"
        )
        self._setup_fonts()

        _report("Applying Design System...")
        # [핵심] UI 전반의 둥근 모서리 곡률 통일 (border-radius)
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f7fa; }
            QGroupBox { 
                background-color: white; border: 1px solid #e4e7ed; 
                border-radius: 8px; margin-top: 10px; padding-top: 10px; /* 그룹박스 곡률 8px */
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #909399; font-weight: bold; }

            QPushButton { 
                background-color: #ffffff; border: 1px solid #dcdfe6; 
                border-radius: 6px; padding: 6px; color: #606266; /* 버튼 곡률 6px */
            }
            QPushButton:hover { background-color: #ecf5ff; color: #409eff; border-color: #c6e2ff; }
            QPushButton:checked { 
                background-color: #409eff; color: white; border-color: #409eff; font-weight: bold; 
            }
            QPushButton:disabled { 
                background-color: #f5f5f5; color: #bbbbbb; border: 1px solid #eeeeee; 
            }


            /* QMessageBox 버튼 비정상적 크기 문제 해결 (padding 및 최소 너비 조정) */
            QMessageBox QPushButton { min-width: 80px; padding: 5px 15px; }

            QTableWidget { 
                border: 1px solid #e4e7ed; border-radius: 6px; /* 테이블 곡률 6px */
                background: #fafafa; gridline-color: transparent; 
            }
            QTableWidget::item { border-bottom: 1px solid #f0f2f5; }

            /* 헤더 전체의 배경색을 설정하여 빈 공간을 회색으로 채움 */
            QHeaderView {
                background-color: #fafafa;
                border: none;
            }

            /* 수직 헤더(숫자 열) 섹션 스타일 */
            QHeaderView::section:vertical {
                border: none;
                border-bottom: 1px solid #f0f2f5;
                background-color: #fafafa;
                padding-left: 5px;
                padding-right: 5px;
                color: #909399;
                min-width: 25px;
            }

            /* 가로 헤더(파일명 열) 섹션 스타일 */
            QHeaderView::section:horizontal {
                background-color: #fafafa;
                border: none;
                border-bottom: 1px solid #e4e7ed;
                color: #909399;
            }

            /* 테이블 왼쪽 상단 모서리 빈 칸도 회색으로 */
            QTableWidget QTableCornerButton::section {
                background-color: #fafafa;
                border: none;
            }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_v_layout = QVBoxLayout(self.central_widget)

        self.main_v_layout.setContentsMargins(15, 20, 15, 5)
        self.main_v_layout.setSpacing(8)

        _report("Building Workspace...")
        self._integer_bark_scale_backup = None
        self._build_top_workspace()
        _report("Readying System Logs...")
        self._build_bottom_log()

        # [로직 시그널 연결]
        self.f1_scale_group.buttonClicked.connect(self._on_scale_changed)
        self.f2_scale_group.buttonClicked.connect(self._on_scale_changed)
        self.origin_group.buttonClicked.connect(self._draw_preview)
        self.chk_bark_units.toggled.connect(self._on_bark_units_toggled)
        self.plot_type_group.buttonClicked.connect(self._on_plot_type_changed)
        self.outlier_group.buttonClicked.connect(self._on_outlier_changed)
        self.cb_normalization.currentIndexChanged.connect(
            self._on_normalization_changed
        )

        # 데이터 가이드 버튼 연결
        self.btn_guide.clicked.connect(self.controller.open_guide)

        # [로직] 처음 실행 시 모든 인터랙션 잠금
        self.reset_ui_state()

        self._icon_applied_on_show = False  # showEvent에서 한 번 더 아이콘 적용

    def showEvent(self, event):
        super().showEvent(event)
        # 프로그램 최초 실행 시 작업표시줄(상태 표시줄) 아이콘이 보이지 않는 오류 개선
        if not getattr(self, "_icon_applied_on_show", True):
            self._icon_applied_on_show = True
            self._apply_window_icon()
        QTimer.singleShot(0, self._sync_workspace_column_heights)

    def _sync_workspace_column_heights(self):
        """2열 설정 패널 높이를 기준으로 1·3열 그룹박스 하단을 맞춘다."""
        panel = getattr(self, "_col2_panel", None)
        data_group = getattr(self, "data_group", None)
        preview_group = getattr(self, "preview_group", None)
        if panel is None or data_group is None or preview_group is None:
            return
        ref_h = 0
        try:
            ref_h = panel.sizeHint().height()
            if ref_h <= 0:
                ref_h = panel.minimumSizeHint().height()
        except Exception:
            return
        if ref_h <= 0:
            return
        data_group.setFixedHeight(ref_h)
        preview_group.setFixedHeight(ref_h)

    def _apply_window_icon(self):
        try:
            self.setWindowIcon(icon_utils.get_app_icon())
        except Exception as e:
            # 아이콘 로드 실패는 치명적이지 않으므로 디버그 로그만 남김
            from utils import app_logger

            app_logger.debug(f"[_apply_window_icon] 아이콘 적용 중 예외 발생: {e}")

    def _setup_fonts(self):
        self.font_main = QFont(self.ui_font_name, 10)
        self.font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        self.font_small = QFont(self.ui_font_name, 9)
        self.setFont(self.font_main)

    def _build_top_workspace(self):
        workspace_layout = QHBoxLayout()
        workspace_layout.setSpacing(15)

        # --- 1열: DATA SOURCE ---
        col1 = QVBoxLayout()
        data_group = QGroupBox("DATA SOURCE")
        data_vbox = QVBoxLayout(data_group)
        data_vbox.setSpacing(4)

        self.drop_label = DropLabel(
            "여기를 클릭하여 파일을 선택하거나\n파일을 이곳으로 끌어다 놓으세요",
            self.controller,
        )
        self.drop_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        data_vbox.addWidget(self.drop_label, stretch=4)

        self.lbl_file_count = QLabel("Loaded Files (Total: 0)")
        self.lbl_file_count.setFont(self.font_bold)
        self.lbl_file_count.setStyleSheet(
            "color: #606266; margin-top: 6px; margin-bottom: 2px; padding-left: 2px;"
        )
        data_vbox.addWidget(self.lbl_file_count)

        self.table_files = QTableWidget(0, 2)
        # 가로 헤더(제목란)는 숨기되, 세로 헤더(숫자란)는 보이도록 복구!
        self.table_files.horizontalHeader().setVisible(False)

        self.table_files.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table_files.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )
        self.table_files.setColumnWidth(1, 35)
        self.table_files.setMinimumHeight(120)
        self.table_files.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        self.table_files.verticalHeader().setDefaultSectionSize(36)
        self.table_files.setFont(self.font_small)
        self.table_files.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_files.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table_files.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_files.setShowGrid(False)
        data_vbox.addWidget(self.table_files, stretch=6)

        ctrl_h = QHBoxLayout()
        self.btn_reset = QPushButton("초기화")
        self.btn_reset.setStyleSheet("color: #f56c6c;")
        # 실제 초기화 수행 전에는 항상 사용자 확인을 거친다.
        self.btn_reset.clicked.connect(self._request_reset_all)
        self.btn_guide = QPushButton("데이터 가이드")
        ctrl_h.addWidget(self.btn_reset)
        ctrl_h.addWidget(self.btn_guide)
        data_vbox.addLayout(ctrl_h)
        data_vbox.addSpacing(4)
        data_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.data_group = data_group
        col1.addWidget(data_group, 0, Qt.AlignmentFlag.AlignTop)
        workspace_layout.addLayout(col1, stretch=32)

        # --- 2열: ANALYSIS SETTINGS ---
        col2 = QVBoxLayout()
        col2_container = QWidget()
        col2_container.setFixedWidth(460)
        col2_inner = QVBoxLayout(col2_container)
        col2_inner.setContentsMargins(0, 0, 0, 0)
        col2_inner.setSpacing(_SETTINGS_SECTION_GAP)

        self.group_structure = QGroupBox("ANALYSIS STRUCTURE")
        self.group_structure.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        type_vbox = QVBoxLayout(self.group_structure)
        type_vbox.setContentsMargins(*_SETTINGS_GROUP_MARGINS)
        type_vbox.setSpacing(6)
        self.plot_type_group = QButtonGroup(self)

        row1_h = QHBoxLayout()
        row2_h = QHBoxLayout()
        row1_h.setSpacing(8)
        row2_h.setSpacing(8)

        opts = [
            ("F1 vs F2", "f1_f2"),
            ("F1 vs (F2-F1)", "f1_f2_minus_f1"),
            ("F1 vs F3", "f1_f3"),
            ("F1 vs F2'", "f1_f2_prime"),
            ("F1 vs (F2'-F1)", "f1_f2_prime_minus_f1"),
        ]

        self.f3_btns = []
        for i, (text, val) in enumerate(opts):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("val", val)
            if i < 2:
                btn.setMinimumHeight(35)
            else:
                btn.setMinimumHeight(30)
                self.f3_btns.append(btn)

            if val == "f1_f2":
                btn.setChecked(True)
            self.plot_type_group.addButton(btn, i)
            if i < 2:
                row1_h.addWidget(btn, stretch=1)
            else:
                row2_h.addWidget(btn, stretch=1)
        type_vbox.addLayout(row1_h)
        type_vbox.addLayout(row2_h)

        self.lbl_plot_desc = QLabel("F1 vs F2: 가장 표준적인 모음 사각도입니다.")
        self.lbl_plot_desc.setStyleSheet("color: #606266; padding: 0 2px;")
        self.lbl_plot_desc.setFont(self.font_small)
        self.lbl_plot_desc.setWordWrap(True)
        self.lbl_plot_desc.setFixedHeight(20)
        self.lbl_plot_desc.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        type_vbox.addWidget(self.lbl_plot_desc)
        col2_inner.addWidget(self.group_structure, 0, Qt.AlignmentFlag.AlignTop)

        self.group_scales = QGroupBox("AXIS SCALES")
        self.group_scales.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        scale_grid = QGridLayout(self.group_scales)
        _apply_settings_grid(scale_grid, 3)
        scale_grid.setContentsMargins(12, 10, 12, 6)

        self.lbl_x_axis = _settings_field_label("F2 Axis Scale")
        scale_grid.addWidget(_settings_field_label("F1 Axis Scale"), 0, 0)
        f1_h = QHBoxLayout()
        f1_h.setContentsMargins(0, 0, 0, 0)
        f1_h.setSpacing(_SETTINGS_GRID_H_SPACING)
        self.f1_scale_group = QButtonGroup(self)
        for col, s_val in enumerate(["linear", "log", "bark"]):
            btn = QPushButton(s_val.capitalize())
            btn.setCheckable(True)
            btn.setProperty("val", s_val)
            btn.setFixedHeight(_SETTINGS_CTRL_H)
            self.f1_scale_group.addButton(btn, col)
            f1_h.addWidget(btn, stretch=1)
        scale_grid.addLayout(f1_h, 0, 1, 1, 3)

        scale_grid.addWidget(self.lbl_x_axis, 1, 0)
        f2_h = QHBoxLayout()
        f2_h.setContentsMargins(0, 0, 0, 0)
        f2_h.setSpacing(_SETTINGS_GRID_H_SPACING)
        self.f2_scale_group = QButtonGroup(self)
        for col, s_val in enumerate(["linear", "log", "bark"]):
            btn = QPushButton(s_val.capitalize())
            btn.setCheckable(True)
            btn.setProperty("val", s_val)
            btn.setFixedHeight(_SETTINGS_CTRL_H)
            self.f2_scale_group.addButton(btn, col)
            f2_h.addWidget(btn, stretch=1)
        scale_grid.addLayout(f2_h, 1, 1, 1, 3)

        scale_grid.addWidget(_settings_field_label("Origin (0,0)"), 2, 0)
        origin_h = QHBoxLayout()
        origin_h.setContentsMargins(0, 0, 0, 0)
        origin_h.setSpacing(_SETTINGS_GRID_H_SPACING)
        self.origin_group = QButtonGroup(self)
        for col, (o_text, o_val) in enumerate(
            [("Praat(우측 상단)", "top_right"), ("Math(좌측 하단)", "bottom_left")]
        ):
            btn = QPushButton(o_text)
            btn.setCheckable(True)
            btn.setProperty("val", o_val)
            btn.setFixedHeight(_SETTINGS_CTRL_H)
            self.origin_group.addButton(btn, col)
            origin_h.addWidget(btn, stretch=1)
        scale_grid.addLayout(origin_h, 2, 1, 1, 3)

        scale_grid.setColumnStretch(1, 1)
        scale_grid.setColumnStretch(2, 1)
        scale_grid.setColumnStretch(3, 1)

        self.chk_bark_units = QCheckBox("Bark를 표시 단위로 사용")
        self.chk_bark_units.setFont(QFont(self.ui_font_name, 8))
        self.chk_bark_units.setStyleSheet(
            """
            QCheckBox { color: #333333; }
            QCheckBox:disabled { color: #bbbbbb; }
            """
        )
        scale_grid.addWidget(
            self.chk_bark_units,
            3,
            1,
            1,
            3,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        scale_grid.setRowMinimumHeight(3, 20)
        col2_inner.addWidget(self.group_scales, 0, Qt.AlignmentFlag.AlignTop)

        self.group_data_processing = QGroupBox("DATA PROCESSING")
        self.group_data_processing.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        dp_layout = QGridLayout(self.group_data_processing)
        _apply_settings_grid(dp_layout, 3)
        dp_layout.addWidget(_settings_field_label("이상치 제거"), 0, 0)
        self.outlier_group = QButtonGroup(self)
        self.outlier_group.setExclusive(False)
        outlier_h = QHBoxLayout()
        outlier_h.setContentsMargins(0, 0, 0, 0)
        outlier_h.setSpacing(_SETTINGS_GRID_H_SPACING)
        for col, (text, val) in enumerate(config.OUTLIER_SIGMA_OPTIONS):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("val", val)
            btn.setFont(self.font_small)
            btn.setFixedHeight(_SETTINGS_CTRL_H)
            self.outlier_group.addButton(btn, col)
            btn.toggled.connect(
                lambda checked, b=btn: self._outlier_at_most_one(b, checked)
            )
            outlier_h.addWidget(btn, stretch=1)
        dp_layout.addLayout(outlier_h, 0, 1, 1, 3)

        self.outlier_scope_panel = QWidget()
        scope_panel_layout = QHBoxLayout(self.outlier_scope_panel)
        scope_panel_layout.setContentsMargins(
            _SETTINGS_LABEL_COL_W + _SETTINGS_GRID_H_SPACING, 0, 0, 0
        )
        scope_panel_layout.setSpacing(_SETTINGS_GRID_H_SPACING)

        self.lbl_outlier_scope = QLabel("└ 적용 범위")
        self.lbl_outlier_scope.setFont(self.font_small)
        self.lbl_outlier_scope.setStyleSheet("color: #909399;")
        self.lbl_outlier_scope.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        scope_panel_layout.addWidget(self.lbl_outlier_scope)

        self.outlier_scope_group = QButtonGroup(self)
        self.outlier_scope_group.setExclusive(True)
        scope_h = QHBoxLayout()
        scope_h.setContentsMargins(0, 0, 0, 0)
        scope_h.setSpacing(_SETTINGS_GRID_H_SPACING)
        for col, (text, val) in enumerate(config.OUTLIER_SCOPE_OPTIONS):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("val", val)
            btn.setFont(self.font_small)
            btn.setFixedHeight(_SETTINGS_CTRL_H)
            self.outlier_scope_group.addButton(btn, col)
            scope_h.addWidget(btn, stretch=1)
        scope_panel_layout.addLayout(scope_h, stretch=1)
        self.outlier_scope_group.buttonClicked.connect(self._on_outlier_scope_changed)
        dp_layout.addWidget(self.outlier_scope_panel, 1, 0, 1, 4)
        self._update_outlier_scope_ui()

        dp_layout.addWidget(_settings_field_label("정규화"), 2, 0)
        self.cb_normalization = NoWheelComboBox()
        self.cb_normalization.setFont(self.font_small)
        self.cb_normalization.setFixedHeight(_SETTINGS_CTRL_H)
        self.cb_normalization.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.cb_normalization.addItem("없음", "")
        self.cb_normalization.addItem("Lobanov", "Lobanov")
        self.cb_normalization.setCurrentIndex(0)
        self.cb_normalization.setToolTip(
            "Lobanov: 화자 내 F1·F2 평균·표준편차 기준 Z-score.\n"
            "모음이 1개뿐이면 해당 축 값은 0으로 처리됩니다."
        )
        dp_layout.addWidget(self.cb_normalization, 2, 1, 1, 3)
        dp_layout.setColumnStretch(1, 1)
        dp_layout.setColumnStretch(2, 1)
        dp_layout.setColumnStretch(3, 1)
        col2_inner.addWidget(self.group_data_processing, 0, Qt.AlignmentFlag.AlignTop)

        self._col2_panel = col2_container
        col2.addWidget(col2_container, 0, Qt.AlignmentFlag.AlignTop)
        workspace_layout.addLayout(col2, stretch=36)

        # --- 3열: LIVE MONITOR (플롯 + 생성 버튼을 그룹박스 내부에 통합) ---
        col3 = QVBoxLayout()
        col3.setSpacing(0)
        preview_group = QGroupBox("LIVE MONITOR")
        self.preview_group = preview_group
        preview_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        preview_vbox = QVBoxLayout(preview_group)
        preview_vbox.setContentsMargins(10, 10, 10, 10)
        preview_vbox.setSpacing(8)

        self.preview_label = QLabel("LIVE")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFixedSize(260, 260)

        self.preview_label.setStyleSheet("""
            border: 1px solid #dcdfe6; 
            background: #ffffff; 
            border-radius: 8px; 
            color: #dcdfe6; 
            font-weight: bold; 
            font-size: 16px;
        """)

        preview_vbox.addWidget(
            self.preview_label,
            0,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )

        self.preview_info_label = QLabel("")
        self.preview_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_info_label.setStyleSheet(
            "color: #909399; font-size: 11px; padding: 0 4px;"
        )
        self.preview_info_label.setWordWrap(True)
        self.preview_info_label.setMaximumWidth(280)
        self.preview_info_label.setFixedHeight(52)
        preview_vbox.addWidget(self.preview_info_label)
        preview_vbox.addStretch(1)

        self.btn_generate = QPushButton("포먼트 플롯 생성")
        self.btn_generate.setMinimumHeight(48)
        self.btn_generate.setFont(QFont(self.ui_font_name, 12, QFont.Weight.Bold))
        self.btn_generate.setStyleSheet("""
            QPushButton { background-color: #67C23A; color: white; border: none; border-radius: 8px; }
            QPushButton:hover:enabled { background-color: #85CE61; }
            QPushButton:disabled { background-color: #C0C4CC; color: #909399; }
        """)
        self.btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate.clicked.connect(self.controller.open_single_plot)
        preview_vbox.addWidget(self.btn_generate)

        col3.addWidget(preview_group, 0, Qt.AlignmentFlag.AlignTop)
        workspace_layout.addLayout(col3, stretch=32)

        self.main_v_layout.addLayout(workspace_layout)

    def _build_bottom_log(self):
        log_group = QGroupBox("SYSTEM LOG")
        log_vbox = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet(
            "background-color: #1e1e1e; color: #a5d6a7; border: none; border-radius: 6px;"
        )
        self.log_text.setFixedHeight(115)
        self.log_text.setReadOnly(True)
        log_vbox.addWidget(self.log_text)
        self.main_v_layout.addWidget(log_group)

        lbl_cp = QLabel(config.COPYRIGHT_TEXT)
        lbl_cp.setFont(QFont(self.ui_font_name, 8))
        lbl_cp.setStyleSheet("color: #909399;")
        lbl_cp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_v_layout.addWidget(lbl_cp)

    def update_file_status(self, count):
        self.lbl_file_count.setText(f"Loaded Files (Total: {count})")
        self.table_files.setRowCount(0)
        # 파일 테이블은 실제 화자 파일만 보여준다 (Combined는 파생 항목이므로 제외).
        # row(시각 행 번호)와 i(plot_data_list 인덱스, 삭제용)는 항상 일치하지만
        # 방어적으로 분리해서 관리한다.
        row = 0
        for i, data in enumerate(self.controller.get_plot_data_list()):
            if data.get("is_combined"):
                continue
            self.table_files.insertRow(row)
            item = QTableWidgetItem(data["name"])
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table_files.setItem(row, 0, item)

            btn_del = QPushButton("×")
            btn_del.setFixedSize(22, 22)
            btn_del.setStyleSheet("""
                QPushButton {
                    color: #f56c6c; border: none; background: transparent; 
                    font-size: 18px; font-weight: bold; padding-top: -3px;
                }
                QPushButton:hover { color: #d32f2f; }
            """)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.clicked.connect(lambda _, idx=i: self._request_delete(idx))

            container = QWidget()
            h_layout = QHBoxLayout(container)
            h_layout.addWidget(btn_del)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_files.setCellWidget(row, 1, container)
            row += 1

        self._set_settings_locked(count == 0)
        if count > 0:
            self._update_normalization_combo_for_plot_type()

    def _set_settings_locked(self, locked):
        self.group_structure.setEnabled(not locked)
        self.group_scales.setEnabled(not locked)
        self.group_data_processing.setEnabled(not locked)
        self.btn_generate.setEnabled(not locked)
        if locked and hasattr(self, "outlier_group"):
            for b in self.outlier_group.buttons():
                b.setChecked(False)
            self._update_outlier_scope_ui()

    def _request_reset_all(self):
        """모든 데이터/설정 초기화 여부를 사용자에게 확인한 뒤, Yes인 경우에만 컨트롤러에 요청."""
        if not self.controller.filepaths:
            return
        reply = QMessageBox.question(
            self,
            "초기화",
            "모든 데이터와 설정을 초기화하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.reset_data()

    def request_file_open(self, callback):
        """파일 탐색기를 통해 데이터 파일을 선택하고, 선택된 경로 리스트를 콜백으로 전달한다.
        초기 폴더: 최근 선택 폴더가 있으면 사용, 없으면 문서 폴더 (저장 다이얼로그의 다운로드/최근 폴더와 동일한 로직)."""
        initial_dir = ""
        if hasattr(self, "controller") and self.controller is not None:
            initial_dir = getattr(self.controller, "get_initial_open_dir", lambda: "")()
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "데이터 파일 선택",
            initial_dir,
            "Data Files (*.txt *.csv *.tsv *.xlsx *.xls);;All Files (*.*)",
        )
        if files:
            if hasattr(self, "controller") and self.controller is not None:
                getattr(self.controller, "set_last_open_dir", lambda x: None)(
                    os.path.dirname(os.path.abspath(files[0]))
                )
            callback(files)

    def _request_delete(self, index):
        if index < 0 or index >= self.controller.get_plot_data_count():
            return
        item = self.controller.get_data_item_at(index)
        if not item:
            return
        fname = item["name"]
        reply = QMessageBox.question(
            self,
            "파일 삭제",
            f"'{fname}' 파일을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.remove_file(index)

    def _on_plot_type_changed(self, btn):
        ptype = btn.property("val")
        lbl_map = {
            "f1_f2": "F2 Axis Scale",
            "f1_f3": "F3 Axis Scale",
            "f1_f2_prime": "F2' Axis Scale",
            "f1_f2_minus_f1": "(F2-F1) Axis Scale",
            "f1_f2_prime_minus_f1": "(F2'-F1) Axis Scale",
        }
        self.lbl_x_axis.setText(lbl_map.get(ptype, "X-Axis Scale"))
        _, desc_text = config.PLOT_DESCS.get(ptype, ("", ""))
        self.lbl_plot_desc.setText(desc_text)
        self._update_normalization_combo_for_plot_type()
        self._update_bark_checkbox_state()
        self._draw_preview()

    def _on_scale_changed(self, btn):
        if self.chk_bark_units.isChecked():
            self._apply_integer_bark_display_and_lock()
        self._draw_preview()

    def _set_all_scale_buttons_enabled(self, enabled: bool):
        for b in self.f1_scale_group.buttons():
            b.setEnabled(enabled)
        for b in self.f2_scale_group.buttons():
            b.setEnabled(enabled)

    def _apply_integer_bark_display_and_lock(self):
        """정수 Bark 모드: 화면상 스케일은 Linear+Linear로 고정, 버튼 비활성."""
        self.f1_scale_group.blockSignals(True)
        self.f2_scale_group.blockSignals(True)
        self.f1_scale_group.buttons()[0].setChecked(True)
        self.f2_scale_group.buttons()[0].setChecked(True)
        self.f1_scale_group.blockSignals(False)
        self.f2_scale_group.blockSignals(False)
        self._set_all_scale_buttons_enabled(False)

    def _release_integer_bark_lock_and_restore_scales(self):
        self._set_all_scale_buttons_enabled(True)
        if self._integer_bark_scale_backup:
            f1v, f2v = self._integer_bark_scale_backup
            self.f1_scale_group.blockSignals(True)
            self.f2_scale_group.blockSignals(True)
            for b in self.f1_scale_group.buttons():
                b.setChecked(b.property("val") == f1v)
            for b in self.f2_scale_group.buttons():
                b.setChecked(b.property("val") == f2v)
            self.f1_scale_group.blockSignals(False)
            self.f2_scale_group.blockSignals(False)
        self._integer_bark_scale_backup = None

    def _on_bark_units_toggled(self, checked: bool):
        if checked:
            b1 = self.f1_scale_group.checkedButton()
            b2 = self.f2_scale_group.checkedButton()
            self._integer_bark_scale_backup = (
                b1.property("val") if b1 else "linear",
                b2.property("val") if b2 else "linear",
            )
            self._apply_integer_bark_display_and_lock()
        else:
            self._release_integer_bark_lock_and_restore_scales()
        self._draw_preview()

    def _update_bark_checkbox_state(self):
        """플롯 타입 변경 등 이후에도 정수 Bark 모드면 스케일 잠금 유지."""
        if self.chk_bark_units.isChecked():
            self._apply_integer_bark_display_and_lock()

    def toggle_f3_options(self, has_f3):
        has_files = self.controller.get_plot_data_count() > 0
        enabled = has_files and has_f3
        for b in self.f3_btns:
            b.setEnabled(enabled)

        if not has_f3 and self.get_plot_type() in [
            "f1_f3",
            "f1_f2_prime",
            "f1_f2_prime_minus_f1",
        ]:
            self.plot_type_group.buttons()[0].setChecked(True)
            self._on_plot_type_changed(self.plot_type_group.buttons()[0])

    def get_plot_type(self):
        return self.plot_type_group.checkedButton().property("val")

    def get_f1_scale(self):
        if self.chk_bark_units.isChecked():
            return "bark"
        btn = self.f1_scale_group.checkedButton()
        return btn.property("val") if btn else "linear"

    def get_f2_scale(self):
        if self.chk_bark_units.isChecked():
            return "bark"
        btn = self.f2_scale_group.checkedButton()
        return btn.property("val") if btn else "linear"

    def get_origin(self):
        return self.origin_group.checkedButton().property("val")

    def get_use_bark_units(self):
        return self.chk_bark_units.isChecked()

    def get_display_scale_for_preview(self):
        """LIVE 하단 문구용: AXIS SCALES 버튼에 보이는 스케일(linear/log/bark)."""
        b1 = self.f1_scale_group.checkedButton()
        b2 = self.f2_scale_group.checkedButton()
        return (
            b1.property("val") if b1 else "linear",
            b2.property("val") if b2 else "linear",
        )

    def get_outlier_mode(self):
        """이상치 제거 모드: None(해제) | 'mahalanobis_2sigma' | 'tukey_iqr'."""
        if not hasattr(self, "outlier_group"):
            return None
        btn = self.outlier_group.checkedButton()
        val = btn.property("val") if btn else None
        return val

    def get_outlier_scope(self):
        """이상치 제거 적용 범위. OFF이면 None, ON이면 'individual' | 'combined'."""
        if not hasattr(self, "outlier_scope_group"):
            return None
        if self.get_outlier_mode() is None:
            return None
        btn = self.outlier_scope_group.checkedButton()
        val = btn.property("val") if btn else None
        return val if val in ("individual", "combined") else None

    def _scope_button(self, scope_val: str):
        if not hasattr(self, "outlier_scope_group"):
            return None
        for b in self.outlier_scope_group.buttons():
            if b.property("val") == scope_val:
                return b
        return None

    def _update_outlier_scope_ui(self):
        """이상치 제거 ON일 때만 적용 범위 활성화. 기본값은 통합 그룹."""
        if not hasattr(self, "outlier_scope_panel"):
            return
        active = self.get_outlier_mode() is not None
        self.outlier_scope_panel.setEnabled(active)
        self.outlier_scope_group.blockSignals(True)
        if active:
            if not self.outlier_scope_group.checkedButton():
                combined = self._scope_button("combined")
                if combined is not None:
                    combined.setChecked(True)
        else:
            for b in self.outlier_scope_group.buttons():
                b.setChecked(False)
        self.outlier_scope_group.blockSignals(False)

    def get_normalization(self):
        """정규화 방법: None | 'Lobanov' (1단계)"""
        if not hasattr(self, "cb_normalization"):
            return None
        if not self.cb_normalization.isEnabled():
            return None
        idx = self.cb_normalization.currentIndex()
        if idx < 0:
            return None
        val = self.cb_normalization.currentData()
        return val if val else None

    def _set_norm_mode_active(self, active: bool):
        """정규화 선택 시 Hz/Bark·스케일 설정은 무의미하므로 AXIS SCALES 잠금."""
        if hasattr(self, "group_scales"):
            self.group_scales.setEnabled(not active)

    def _update_normalization_combo_for_plot_type(self):
        """파생 플롯 타입에서는 정규화 불가 (compare와 동일)."""
        if not hasattr(self, "cb_normalization"):
            return
        ptype = self.get_plot_type()
        unsupported = ptype in ("f1_f2_minus_f1", "f1_f2_prime_minus_f1")
        self.cb_normalization.blockSignals(True)
        if unsupported:
            self.cb_normalization.setCurrentIndex(0)
            self.cb_normalization.setEnabled(False)
            self._set_norm_mode_active(False)
        else:
            has_files = self.controller.get_plot_data_count() > 0
            self.cb_normalization.setEnabled(has_files)
            self._set_norm_mode_active(bool(self.get_normalization()))
        self.cb_normalization.blockSignals(False)

    def _on_normalization_changed(self, *_args):
        self._set_norm_mode_active(bool(self.get_normalization()))
        norm = self.get_normalization()
        if norm:
            app_logger.info(config.LOG_MSG["NORM_ON"].format(method=norm))
        else:
            app_logger.info(config.LOG_MSG["NORM_OFF"])
        self._draw_preview()
        if hasattr(self.controller, "_refresh_open_popups"):
            self.controller._refresh_open_popups()

    def _outlier_at_most_one(self, button, checked):
        """최대 1개만 선택: 켜진 버튼이 있으면 나머지 해제. 재클릭 시 해제되어 Optional 가능."""
        if checked:
            for b in self.outlier_group.buttons():
                if b is not button:
                    b.blockSignals(True)
                    b.setChecked(False)
                    b.blockSignals(False)

    def _on_outlier_changed(self, btn):
        """이상치 제거 옵션 변경 시 LIVE 미리보기 및 데이터 반영 (컨트롤러에서 처리)"""
        self._update_outlier_scope_ui()
        if hasattr(self.controller, "on_outlier_mode_changed"):
            self.controller.on_outlier_mode_changed()
        self._draw_preview()

    def _on_outlier_scope_changed(self, _btn):
        """적용 범위 변경 — 이상치 제거가 켜진 상태에서만 재적용."""
        if self.get_outlier_mode() is None:
            return
        if hasattr(self.controller, "on_outlier_mode_changed"):
            self.controller.on_outlier_mode_changed()
        self._draw_preview()

    def append_log(self, msg):
        self.log_text.append(f"▶ {msg}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def reset_ui_state(self):
        self.chk_bark_units.blockSignals(True)
        self.chk_bark_units.setChecked(False)
        self.chk_bark_units.blockSignals(False)
        self._integer_bark_scale_backup = None
        self._set_all_scale_buttons_enabled(True)
        self.plot_type_group.buttons()[0].setChecked(True)
        self.f1_scale_group.buttons()[0].setChecked(True)
        self.f2_scale_group.buttons()[2].setChecked(True)
        self.origin_group.buttons()[0].setChecked(True)
        if hasattr(self, "outlier_group"):
            for b in self.outlier_group.buttons():
                b.setChecked(False)
        if hasattr(self, "outlier_scope_group"):
            for b in self.outlier_scope_group.buttons():
                b.setChecked(False)
        self._update_outlier_scope_ui()
        if hasattr(self, "cb_normalization"):
            self.cb_normalization.blockSignals(True)
            self.cb_normalization.setCurrentIndex(0)
            self.cb_normalization.setEnabled(False)
            self.cb_normalization.blockSignals(False)
            self._set_norm_mode_active(False)
        self._on_plot_type_changed(self.plot_type_group.buttons()[0])
        self._set_settings_locked(True)
        self.update_file_status(0)
        self._draw_preview()

    def show_warning(self, title, text):
        QMessageBox.warning(self, title, text)

    def show_critical(self, title, text):
        QMessageBox.critical(self, title, text)

    def _draw_preview(self, *args):
        if hasattr(self.controller, "update_live_preview"):
            self.controller.update_live_preview()
        else:
            if hasattr(self, "preview_label"):
                self.preview_label.clear()
                self.preview_label.setText("LIVE")
