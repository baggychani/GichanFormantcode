from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QButtonGroup,
    QWidget,
    QSizePolicy,
    QFileDialog,
    QProgressDialog,
    QMessageBox,
    QFrame,
    QCheckBox,
)
from PySide6.QtGui import QFont, QRegularExpressionValidator
from PySide6.QtCore import Qt, QRegularExpression, QObject, QEvent

import config
from utils import icon_utils, app_logger


class BatchSaveInputFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if (
                key
                in (
                    Qt.Key.Key_Backspace,
                    Qt.Key.Key_Delete,
                    Qt.Key.Key_Left,
                    Qt.Key.Key_Right,
                    Qt.Key.Key_Up,
                    Qt.Key.Key_Down,
                    Qt.Key.Key_Enter,
                    Qt.Key.Key_Return,
                    Qt.Key.Key_Tab,
                    Qt.Key.Key_Home,
                    Qt.Key.Key_End,
                )
                or event.modifiers() & Qt.KeyboardModifier.ControlModifier
            ):
                return False

            text = event.text()
            if text and not (text.isdigit() or text in ("-", ".")):
                return True
        return super().eventFilter(obj, event)


def _seg_btn_style():
    return """
        QPushButton {
            background-color: #f5f7fa;
            border: 1px solid #dcdfe6;
            color: #606266;
            padding: 6px 10px;
        }
        QPushButton:hover {
            background-color: #ecf5ff;
            color: #409eff;
            border-color: #c6e2ff;
        }
        QPushButton:checked {
            background-color: #409eff;
            color: white;
            border-color: #409eff;
            font-weight: bold;
        }
    """


class BatchSaveDialog(QDialog):
    """일괄 저장 설정 다이얼로그"""

    _LABEL_WIDTH = 64
    _CONTROL_WIDTH = 248

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
        self.setWindowTitle("일괄 저장")
        self.setFixedSize(
            config.DIALOG_BATCH_SAVE_WIDTH_PX, config.DIALOG_BATCH_SAVE_HEIGHT_PX
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self.ui_font_name = parent.ui_font_name
        self._apply_window_icon()
        self._setup_ui(current_ranges, f1_unit, f2_unit, x_axis_label, current_sigma)

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)

    def _apply_window_icon(self):
        try:
            self.setWindowIcon(icon_utils.get_app_icon())
        except Exception:
            pass

    def _make_section_title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont(self.ui_font_name, 10, QFont.Weight.Bold))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #303133; padding: 2px 0 4px 0;")
        return lbl

    def _make_field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFixedWidth(self._LABEL_WIDTH)
        lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        lbl.setFont(QFont(self.ui_font_name, 9))
        lbl.setStyleSheet("color: #606266;")
        return lbl

    def _add_field_row(self, layout, label_text, widget):
        row = QHBoxLayout()
        row.setSpacing(8)
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(2)
        row.addWidget(self._make_field_label(label_text))
        widget.setFixedWidth(self._CONTROL_WIDTH)
        row.addWidget(widget)
        row.addStretch(3)
        layout.addLayout(row)

    def _make_range_row(self, y_min, y_max, validator, input_filter):
        frame = QWidget()
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        ent_min = QLineEdit(y_min)
        ent_max = QLineEdit(y_max)
        for le in (ent_min, ent_max):
            le.setFixedWidth(config.RANGE_EDIT_FIXED_WIDTH_PX)
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            le.setValidator(validator)
            le.installEventFilter(input_filter)
            le.setStyleSheet(
                "QLineEdit { border: 1px solid #DCDFE6; border-radius: 4px; padding: 4px; }"
                "QLineEdit:focus { border-color: #409EFF; }"
            )
        sep = QLabel("~")
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep.setFixedWidth(14)
        sep.setStyleSheet("color: #909399;")
        row.addStretch(1)
        row.addWidget(ent_min)
        row.addWidget(sep)
        row.addWidget(ent_max)
        row.addStretch(1)
        return frame, ent_min, ent_max

    def _make_segment_row(self, items, radius_styles):
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        group = QButtonGroup(self)
        group.setExclusive(True)
        style = _seg_btn_style()
        buttons = []
        for i, (text, val) in enumerate(items):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("val", val)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(style + radius_styles[i])
            btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            group.addButton(btn, i)
            row.addWidget(btn, stretch=1)
            buttons.append(btn)
        return container, group, buttons

    def _setup_ui(self, ranges, f1_unit, f2_unit, x_label, sigma):
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QCheckBox {
                color: #303133;
                spacing: 8px;
                padding: 3px 0;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 20)
        main_layout.setSpacing(14)

        title = QLabel("일괄 저장")
        title.setFont(QFont(self.ui_font_name, 13, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        file_count = self.controller.get_plot_data_count()
        scope = QLabel(f"로드된 파일 {file_count}개 전체를 저장합니다.")
        scope.setFont(QFont(self.ui_font_name, 9))
        scope.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scope.setStyleSheet("color: #909399;")
        main_layout.addWidget(scope)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 4, 0, 0)
        content_layout.setSpacing(10)

        content_layout.addWidget(self._make_section_title("저장 설정"))

        num_validator = QRegularExpressionValidator(
            QRegularExpression(r"^-?\d*\.?\d*$")
        )
        self._input_filter = BatchSaveInputFilter(self)

        f1_frame, self.ent_y_min, self.ent_y_max = self._make_range_row(
            ranges["y_min"], ranges["y_max"], num_validator, self._input_filter
        )
        self._add_field_row(content_layout, f"F1 ({f1_unit})", f1_frame)

        f2_frame, self.ent_x_min, self.ent_x_max = self._make_range_row(
            ranges["x_min"], ranges["x_max"], num_validator, self._input_filter
        )
        self._add_field_row(content_layout, f"{x_label} ({f2_unit})", f2_frame)

        sig_container, self.sig_group, sig_buttons = self._make_segment_row(
            [("1σ (68%)", "1.0"), ("2σ (95%)", "2.0")],
            [
                "QPushButton { border-top-left-radius: 4px; border-bottom-left-radius: 4px; border-right: none; }",
                "QPushButton { border-top-right-radius: 4px; border-bottom-right-radius: 4px; border-left: none; }",
            ],
        )
        self._add_field_row(content_layout, "신뢰 타원", sig_container)
        if sigma == "1.0":
            sig_buttons[0].setChecked(True)
        else:
            sig_buttons[1].setChecked(True)

        fmt_container, self.fmt_group, fmt_buttons = self._make_segment_row(
            [("JPG", "jpg"), ("PNG", "png"), ("SVG", "svg")],
            [
                "QPushButton { border-top-left-radius: 4px; border-bottom-left-radius: 4px; border-right: none; }",
                "QPushButton { border-left: none; border-right: none; }",
                "QPushButton { border-top-right-radius: 4px; border-bottom-right-radius: 4px; border-left: none; }",
            ],
        )
        self._add_field_row(content_layout, "저장 형식", fmt_container)
        fmt_buttons[0].setChecked(True)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E4E7ED;")
        content_layout.addWidget(line)

        content_layout.addWidget(self._make_section_title("디자인 반영"))

        design_box = QFrame()
        design_box.setStyleSheet("""
            QFrame {
                background-color: #F5F7FA;
                border: 1px solid #E4E7ED;
                border-radius: 6px;
            }
        """)
        design_layout = QVBoxLayout(design_box)
        design_layout.setContentsMargins(14, 12, 14, 12)
        design_layout.setSpacing(2)

        font_chk = QFont(self.ui_font_name, 9)
        self.chk_global_design = QCheckBox("광역 디자인 설정", design_box)
        self.chk_global_design.setToolTip(
            "디자인 설정 탭의 폰트, 색상, 마커, 축·배경 등 전역 설정을 각 이미지에 반영합니다."
        )
        self.chk_layer_design = QCheckBox("레이어별 디자인 설정", design_box)
        self.chk_layer_design.setToolTip(
            "파일·모음별로 지정한 레이어 디자인(색, 마커, 타원 등)을 반영합니다."
        )
        self.chk_layer_visibility = QCheckBox(
            "레이어 표시·투명도 (숨김/반투명)", design_box
        )
        self.chk_layer_visibility.setToolTip(
            "파일별 숨김·반투명 상태를 반영합니다. 해제 시 모든 모음을 표시합니다."
        )
        self.chk_label_positions = QCheckBox("라벨 위치", design_box)
        self.chk_label_positions.setToolTip(
            "파일별로 옮긴 모음 라벨 위치를 반영합니다."
        )
        for chk in (
            self.chk_global_design,
            self.chk_layer_design,
            self.chk_layer_visibility,
            self.chk_label_positions,
        ):
            chk.setFont(font_chk)
            chk.setChecked(True)
            chk.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            design_layout.addWidget(chk)

        content_layout.addWidget(design_box)
        main_layout.addWidget(content)
        main_layout.addStretch(1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        btn_cancel = QPushButton("취소")
        btn_cancel.setFixedSize(100, 38)
        btn_cancel.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #DCDFE6;
                border-radius: 4px;
                color: #606266;
            }
            QPushButton:hover { background-color: #F5F7FA; border-color: #C0C4CC; }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_next = QPushButton("일괄 저장")
        btn_next.setFixedSize(140, 38)
        btn_next.setStyleSheet("""
            QPushButton {
                background-color: #409EFF;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #66B1FF; }
        """)
        btn_next.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        btn_next.setDefault(True)
        btn_next.clicked.connect(self.on_next)

        btn_layout.addWidget(btn_cancel)
        btn_layout.setSpacing(12)
        btn_layout.addWidget(btn_next)
        btn_layout.addStretch(1)
        main_layout.addLayout(btn_layout)

    def get_batch_options(self):
        return {
            "apply_global_design": self.chk_global_design.isChecked(),
            "apply_layer_design": self.chk_layer_design.isChecked(),
            "apply_layer_visibility": self.chk_layer_visibility.isChecked(),
            "apply_label_positions": self.chk_label_positions.isChecked(),
        }

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
            parent_popup.get_design_settings()
            if hasattr(parent_popup, "get_design_settings")
            else None
        )

        initial_dir = self.controller.get_default_batch_save_dir()
        save_dir = QFileDialog.getExistingDirectory(
            self, "일괄 저장 폴더 선택", initial_dir
        )
        if not save_dir:
            return

        worker = self.controller.create_batch_save_worker(
            save_dir,
            ranges,
            sigma,
            img_format,
            design_settings=design_settings,
            parent_popup=parent_popup,
            batch_options=self.get_batch_options(),
        )

        total = self.controller.get_plot_data_count()
        progress_dialog = QProgressDialog(
            "이미지 저장 중...", "취소", 0, total, parent_popup
        )
        progress_dialog.setWindowTitle("일괄 저장")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)

        def on_progress(current, tot):
            progress_dialog.setValue(current)
            progress_dialog.setLabelText(f"저장 중... ({current}/{tot})")

        def on_finished(success_count):
            progress_dialog.close()
            errors = getattr(worker, "errors", [])
            if success_count == 0 and errors:
                sample = ", ".join(f"{name}: {msg}" for name, msg in errors[:3])
                app_logger.warning(
                    config.LOG_MSG["BATCH_ALL_FAILED"].format(
                        fail_count=len(errors), sample=sample
                    )
                )
                QMessageBox.warning(
                    parent_popup,
                    "일괄 저장 실패",
                    config.LOG_MSG["BATCH_ALL_FAILED_BOX"],
                )
            else:
                app_logger.info(
                    config.LOG_MSG["BATCH_SUCCESS"].format(success_count=success_count)
                )
                QMessageBox.information(
                    parent_popup,
                    "일괄 저장 완료",
                    f"총 {success_count}개의 이미지가 '{save_dir}'에 저장되었습니다.",
                )

        def on_log_error(msg):
            app_logger.warning(msg)

        worker.progress.connect(on_progress)
        worker.finished_with_count.connect(on_finished)
        worker.log_error.connect(on_log_error)
        progress_dialog.canceled.connect(worker.terminate)

        parent_popup._batch_worker = worker
        parent_popup._batch_progress = progress_dialog

        worker.start()
        progress_dialog.show()
