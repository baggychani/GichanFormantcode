from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QButtonGroup,
    QWidget,
    QSizePolicy,
    QFileDialog,
    QProgressDialog,
    QMessageBox,
)
from PySide6.QtGui import QFont, QRegularExpressionValidator
from PySide6.QtCore import Qt, QRegularExpression
import inspect

from utils import icon_utils
import config
from utils import app_logger


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
        self._apply_window_icon()
        self._setup_ui(current_ranges, f1_unit, f2_unit, x_axis_label, current_sigma)

    def _apply_window_icon(self):
        try:
            self.setWindowIcon(icon_utils.get_app_icon())
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
            [("JPG", "jpg"), ("PNG", "png"), ("SVG", "svg")]
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

        sig_params = inspect.signature(
            self.controller.create_batch_save_worker
        ).parameters

        initial_dir = self.controller.get_default_batch_save_dir()
        save_dir = QFileDialog.getExistingDirectory(
            self, "일괄 저장할 폴더를 선택하세요", initial_dir
        )
        if not save_dir:
            return

        if "design_settings" in sig_params:
            worker = self.controller.create_batch_save_worker(
                save_dir, ranges, sigma, img_format, design_settings=design_settings
            )
        else:
            worker = self.controller.create_batch_save_worker(
                save_dir, ranges, sigma, img_format
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
