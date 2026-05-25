# ui/widgets/file_nav_bar.py
"""플롯 창 좌측 도크 — 파일 인덱스 점프 UI ([n] / total + 파일명)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QIntValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.display_utils import apply_file_indicator_style, strip_gichan_prefix

_INDEX_EDIT_STYLE = """
    QLineEdit {
        border: 1px solid #DCDFE6;
        border-radius: 4px;
        background-color: #FFFFFF;
        padding: 0 6px;
        color: #303133;
        selection-background-color: #ECF5FF;
        selection-color: #303133;
    }
    QLineEdit:hover {
        border-color: #C0C4CC;
    }
    QLineEdit:focus {
        border: 1px solid #409EFF;
        background-color: #FFFFFF;
    }
    QLineEdit:disabled {
        background-color: #F5F7FA;
        color: #C0C4CC;
        border-color: #E4E7ED;
    }
"""

_TOTAL_LABEL_STYLE = """
    QLabel {
        color: #909399;
        border: none;
        background: transparent;
        padding: 0;
        margin: 0;
    }
"""

_NAME_LABEL_STYLE = """
    QLabel {
        color: #606266;
        border: none;
        background: transparent;
        padding: 0 4px;
    }
"""


def _index_edit_width_px(total: int) -> int:
    digits = max(1, len(str(max(1, total))))
    return 22 + digits * 10


def _elide_filename(name: str, max_len: int = 30) -> str:
    name = strip_gichan_prefix(name)
    if len(name) <= max_len:
        return name
    keep = max_len - 1
    left = keep // 2
    right = keep - left
    return f"{name[:left]}…{name[-right:]}"


class NavIndexLineEdit(QLineEdit):
    """인덱스 입력: ▲▼ 없음. Home/End는 파일 처음·끝으로 해석."""

    home_requested = Signal()
    end_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # 창이 열릴 때 자동 포커스되지 않음 — 클릭 시에만 편집
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Home:
            self.home_requested.emit()
            event.accept()
            return
        if key == Qt.Key.Key_End:
            self.end_requested.emit()
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept()
            self.returnPressed.emit()
            QTimer.singleShot(0, self.clearFocus)
            return
        if key == Qt.Key.Key_Escape:
            self.clearFocus()
            event.accept()
            return
        super().keyPressEvent(event)


class FileNavBar(QWidget):
    """[n] / total 한 줄 + 파일명. jump_requested(1-based index)."""

    jump_requested = Signal(int)
    home_requested = Signal()
    end_requested = Signal()

    def __init__(self, font_family: str, parent=None):
        super().__init__(parent)
        self._total = 1
        self._last_index = 1
        self._last_filename = ""
        self._last_data_item = None
        self._syncing = False
        self._font_family = font_family

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(5)

        index_row = QHBoxLayout()
        index_row.setContentsMargins(0, 0, 0, 0)
        index_row.setSpacing(0)

        index_row.addStretch(1)

        inner = QHBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(5)

        self.index_edit = NavIndexLineEdit()
        self.index_edit.setFont(QFont(font_family, 11, QFont.Weight.Bold))
        self.index_edit.setStyleSheet(_INDEX_EDIT_STYLE)
        self.index_edit.setFixedHeight(30)
        self.index_edit.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.index_edit.home_requested.connect(self.home_requested.emit)
        self.index_edit.end_requested.connect(self.end_requested.emit)
        self.index_edit.returnPressed.connect(self._on_editing_finished)
        self.index_edit.editingFinished.connect(self._on_editing_finished)

        self.lbl_total = QLabel("/ 1")
        self.lbl_total.setFont(QFont(font_family, 11, QFont.Weight.Bold))
        self.lbl_total.setStyleSheet(_TOTAL_LABEL_STYLE)
        self.lbl_total.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        inner.addWidget(self.index_edit, 0, Qt.AlignmentFlag.AlignVCenter)
        inner.addWidget(self.lbl_total, 0, Qt.AlignmentFlag.AlignVCenter)

        index_row.addLayout(inner)
        index_row.addStretch(1)
        root.addLayout(index_row)

        self.lbl_name = QLabel("")
        self.lbl_name.setFont(QFont(font_family, 9))
        self.lbl_name.setStyleSheet(_NAME_LABEL_STYLE)
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setWordWrap(False)
        self.lbl_name.setToolTipDuration(4000)
        root.addWidget(self.lbl_name)

        self._validator = QIntValidator(1, 1, self.index_edit)
        self.index_edit.setValidator(self._validator)

    def set_display(
        self,
        index_1based: int,
        total: int,
        filename: str,
        data_item=None,
    ) -> None:
        """외부에서 인덱스·총개수·파일명 동기화 (포커스·시그널 없음)."""
        total = max(1, int(total))
        index_1based = max(1, min(int(index_1based), total))
        self._total = total
        self._last_index = index_1based
        self._last_filename = filename
        self._last_data_item = data_item

        self._syncing = True
        try:
            self._validator.setRange(1, total)
            self.index_edit.setFixedWidth(_index_edit_width_px(total))
            self.lbl_total.setText(f"/ {total}")
            self.index_edit.setText(str(index_1based))
            self.index_edit.setEnabled(total > 1)

            plain = strip_gichan_prefix(filename)
            self.lbl_name.setText(_elide_filename(plain))
            self.lbl_name.setToolTip(plain if plain else "")
            apply_file_indicator_style(self.lbl_name, data_item)
        finally:
            self._syncing = False

    def _on_editing_finished(self) -> None:
        if self._syncing or not self.index_edit.isEnabled():
            return
        text = self.index_edit.text().strip()
        if not text:
            target = self._last_index
        else:
            try:
                target = int(text)
            except ValueError:
                self.set_display(
                    self._last_index,
                    self._total,
                    self._last_filename,
                    self._last_data_item,
                )
                return
            target = max(1, min(target, self._total))
        self.jump_requested.emit(target)

    def _parse_current_fallback(self) -> int:
        text = self.index_edit.text().strip()
        if text.isdigit():
            return max(1, min(int(text), self._total))
        return 1
