# ui_main.py

import os
import platform
from PyQt6.QtWidgets import (
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
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

import config
from utils import icon_utils


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
        self.setMinimumHeight(75)
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
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle(config.APP_TITLE)

        # 아이콘 로드 및 적용
        self._apply_pyqt6_icon()

        # 창 크기 고정
        self.setFixedSize(1100, 615)

        # 제목 표시줄의 최대화(ㅁ) 버튼 비활성화 (최소화, 닫기 버튼만 유지)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowSystemMenuHint
        )

        self.ui_font_name = (
            "Malgun Gothic" if platform.system() == "Windows" else "AppleGothic"
        )
        self._setup_fonts()

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

            /* 체크박스 전역 색상 지정 (비활성화 시 색상 변경 적용을 위해) */
            QCheckBox { color: #606266; }
            QCheckBox:disabled { color: #bbbbbb; }

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

        self._build_top_workspace()
        self._build_bottom_log()

        # [로직 시그널 연결]
        self.f1_scale_group.buttonClicked.connect(self._on_scale_changed)
        self.f2_scale_group.buttonClicked.connect(self._on_scale_changed)
        self.origin_group.buttonClicked.connect(self._draw_preview)
        self.chk_bark_units.stateChanged.connect(self._draw_preview)
        self.plot_type_group.buttonClicked.connect(self._on_plot_type_changed)
        self.outlier_group.buttonClicked.connect(self._on_outlier_changed)

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
            self._apply_pyqt6_icon()

    def _apply_pyqt6_icon(self):
        try:
            icon_path = icon_utils.get_icon_path()
            if icon_path:
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

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
        data_vbox.addWidget(self.drop_label, stretch=1)

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
        # 헤더가 사라진 만큼 뷰가 넓어졌으므로 높이 살짝 축소
        self.table_files.setFixedHeight(145)
        self.table_files.verticalHeader().setDefaultSectionSize(36)
        self.table_files.setFont(self.font_small)
        self.table_files.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_files.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table_files.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_files.setShowGrid(False)
        data_vbox.addWidget(self.table_files)

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
        col1.addWidget(data_group)
        workspace_layout.addLayout(col1, stretch=32)

        # --- 2열: ANALYSIS SETTINGS ---
        col2 = QVBoxLayout()
        col2_container = QWidget()
        col2_container.setFixedWidth(460)
        col2_inner = QVBoxLayout(col2_container)
        col2_inner.setContentsMargins(0, 0, 0, 0)

        self.group_structure = QGroupBox("ANALYSIS STRUCTURE")
        type_vbox = QVBoxLayout(self.group_structure)
        type_vbox.setSpacing(5)
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
        self.lbl_plot_desc.setStyleSheet(
            "color: #606266; padding: 4px 5px; line-height: 1.3;"
        )
        self.lbl_plot_desc.setFont(self.font_small)
        self.lbl_plot_desc.setWordWrap(True)
        self.lbl_plot_desc.setMinimumHeight(28)
        type_vbox.addWidget(self.lbl_plot_desc)
        col2_inner.addWidget(self.group_structure)

        self.group_scales = QGroupBox("AXIS SCALES")
        scale_grid = QGridLayout(self.group_scales)
        scale_grid.setColumnMinimumWidth(0, 115)
        scale_grid.setVerticalSpacing(6)

        scale_grid.addWidget(QLabel("F1 Axis Scale"), 0, 0)
        self.f1_scale_group = QButtonGroup(self)
        for col, s_val in enumerate(["linear", "log", "bark"]):
            btn = QPushButton(s_val.capitalize())
            btn.setCheckable(True)
            btn.setProperty("val", s_val)
            self.f1_scale_group.addButton(btn, col)
            scale_grid.addWidget(btn, 0, col + 1)

        self.lbl_x_axis = QLabel("F2 Axis Scale")
        scale_grid.addWidget(self.lbl_x_axis, 1, 0)
        self.f2_scale_group = QButtonGroup(self)
        for col, s_val in enumerate(["linear", "log", "bark"]):
            btn = QPushButton(s_val.capitalize())
            btn.setCheckable(True)
            btn.setProperty("val", s_val)
            self.f2_scale_group.addButton(btn, col)
            scale_grid.addWidget(btn, 1, col + 1)

        scale_grid.addWidget(QLabel("Origin (0,0)"), 2, 0)
        origin_h = QHBoxLayout()
        origin_h.setSpacing(10)
        self.origin_group = QButtonGroup(self)
        for col, (o_text, o_val) in enumerate(
            [("Praat(우측 상단)", "top_right"), ("Math(좌측 하단)", "bottom_left")]
        ):
            btn = QPushButton(o_text)
            btn.setCheckable(True)
            btn.setProperty("val", o_val)
            self.origin_group.addButton(btn, col)
            origin_h.addWidget(btn, stretch=1)
        scale_grid.addLayout(origin_h, 2, 1, 1, 3)

        self.chk_bark_units = QCheckBox("정수 Bark 단위 눈금 사용")
        self.chk_bark_units.setFont(QFont(self.ui_font_name, 8))
        self.chk_bark_units.setStyleSheet(
            "margin-top: 2px; padding-bottom: 1px; max-height: 18px;"
        )
        scale_grid.addWidget(self.chk_bark_units, 3, 1, 1, 3)

        scale_grid.setColumnStretch(1, 1)
        scale_grid.setColumnStretch(2, 1)
        scale_grid.setColumnStretch(3, 1)
        col2_inner.addWidget(self.group_scales)

        self.group_data_processing = QGroupBox("DATA PROCESSING")
        dp_layout = QGridLayout(self.group_data_processing)
        dp_layout.setVerticalSpacing(6)
        dp_layout.setColumnMinimumWidth(0, 115)
        dp_layout.addWidget(QLabel("이상치 제거"), 0, 0)
        self.outlier_group = QButtonGroup(self)
        self.outlier_group.setExclusive(False)
        outlier_h = QHBoxLayout()
        outlier_h.setSpacing(10)
        for col, (text, val) in enumerate(
            [("1σ (68.27%)", "1sigma"), ("2σ (95.45%)", "2sigma")]
        ):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("val", val)
            btn.setFont(self.font_small)
            self.outlier_group.addButton(btn, col)
            btn.toggled.connect(
                lambda checked, b=btn: self._outlier_at_most_one(b, checked)
            )
            outlier_h.addWidget(btn, stretch=1)
        dp_layout.addLayout(outlier_h, 0, 1, 1, 3)
        dp_layout.setColumnStretch(1, 1)
        dp_layout.setColumnStretch(2, 1)
        dp_layout.setColumnStretch(3, 1)
        col2_inner.addWidget(self.group_data_processing)

        col2.addWidget(col2_container)
        workspace_layout.addLayout(col2, stretch=36)

        # --- 3열: LIVE MONITOR ---
        col3 = QVBoxLayout()
        preview_group = QGroupBox("LIVE MONITOR")
        preview_vbox = QVBoxLayout(preview_group)

        preview_vbox.addStretch(1)

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
            self.preview_label, alignment=Qt.AlignmentFlag.AlignCenter
        )
        preview_vbox.addSpacing(8)

        self.preview_info_label = QLabel("")
        self.preview_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_info_label.setStyleSheet(
            "color: #909399; font-size: 11px; padding: 4px 8px;"
        )
        self.preview_info_label.setWordWrap(True)
        self.preview_info_label.setMaximumWidth(280)
        preview_vbox.addWidget(self.preview_info_label)

        preview_vbox.addStretch(1)

        col3.addWidget(preview_group, stretch=1)

        self.btn_generate = QPushButton("포먼트 플롯 생성")
        self.btn_generate.setMinimumHeight(48)
        self.btn_generate.setFont(QFont(self.ui_font_name, 12, QFont.Weight.Bold))
        self.btn_generate.setStyleSheet("""
            QPushButton { background-color: #67C23A; color: white; border: none; border-radius: 8px; }
            QPushButton:hover:enabled { background-color: #85CE61; }
            QPushButton:disabled { background-color: #C0C4CC; color: #909399; }
        """)
        self.btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate.clicked.connect(self.controller.generate_plot)
        col3.addWidget(self.btn_generate)
        workspace_layout.addLayout(col3, stretch=32)

        self.main_v_layout.addLayout(workspace_layout, stretch=85)

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
        for i, data in enumerate(self.controller.get_plot_data_list()):
            self.table_files.insertRow(i)
            item = QTableWidgetItem(data["name"])
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table_files.setItem(i, 0, item)

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
            self.table_files.setCellWidget(i, 1, container)

        self._set_settings_locked(count == 0)

    def _set_settings_locked(self, locked):
        self.group_structure.setEnabled(not locked)
        self.group_scales.setEnabled(not locked)
        self.group_data_processing.setEnabled(not locked)
        self.btn_generate.setEnabled(not locked)
        if locked and hasattr(self, "outlier_group"):
            for b in self.outlier_group.buttons():
                b.setChecked(False)

    def _request_reset_all(self):
        """모든 데이터/설정 초기화 여부를 사용자에게 확인한 뒤, Yes인 경우에만 컨트롤러에 요청."""
        if not self.controller.filepaths:
            return
        reply = QMessageBox.question(
            self,
            "초기화",
            "모든 데이터와 설정을 초기화하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
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
        self._draw_preview()

    def _on_scale_changed(self, btn):
        self._update_bark_checkbox_state()
        self._draw_preview()

    def _update_bark_checkbox_state(self):
        active = self.get_f1_scale() == "bark" and self.get_f2_scale() == "bark"
        self.chk_bark_units.setEnabled(active)
        if not active:
            self.chk_bark_units.setChecked(False)

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
        return self.f1_scale_group.checkedButton().property("val")

    def get_f2_scale(self):
        return self.f2_scale_group.checkedButton().property("val")

    def get_origin(self):
        return self.origin_group.checkedButton().property("val")

    def get_use_bark_units(self):
        return self.chk_bark_units.isChecked()

    def get_outlier_mode(self):
        """이상치 제거 모드: None(해제), '1sigma', '2sigma'"""
        if not hasattr(self, "outlier_group"):
            return None
        btn = self.outlier_group.checkedButton()
        return btn.property("val") if btn else None

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
        if hasattr(self.controller, "on_outlier_mode_changed"):
            self.controller.on_outlier_mode_changed()
        self._draw_preview()

    def append_log(self, msg):
        self.log_text.append(f"▶ {msg}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def reset_ui_state(self):
        self.plot_type_group.buttons()[0].setChecked(True)
        self.f1_scale_group.buttons()[0].setChecked(True)
        self.f2_scale_group.buttons()[2].setChecked(True)
        self.origin_group.buttons()[0].setChecked(True)
        if hasattr(self, "outlier_group"):
            for b in self.outlier_group.buttons():
                b.setChecked(False)
        self._on_plot_type_changed(self.plot_type_group.buttons()[0])
        self._update_bark_checkbox_state()
        self._set_settings_locked(True)
        self.update_file_status(0)
        self._draw_preview()

    def _draw_preview(self, *args):
        if hasattr(self.controller, "update_live_preview"):
            self.controller.update_live_preview()
        else:
            if hasattr(self, "preview_label"):
                self.preview_label.clear()
                self.preview_label.setText("LIVE")
