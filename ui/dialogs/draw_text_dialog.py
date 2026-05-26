"""그리기 텍스트 입력·편집 다이얼로그."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)

from draw.draw_common import TextObject


class DrawTextDialog(QDialog):
    def __init__(
        self,
        *,
        initial_text: str = "",
        ui_font_name: str = "Malgun Gothic",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("텍스트 입력")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        hint = QLabel("표시할 텍스트를 입력하세요. (여러 줄 가능, Enter로 줄바꿈)")
        hint.setFont(QFont(ui_font_name, 9))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._editor = QPlainTextEdit(initial_text or "")
        self._editor.setFont(QFont(ui_font_name, 10))
        self._editor.setMinimumHeight(120)
        layout.addWidget(self._editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setMinimumWidth(360)
        self._editor.setFocus()

    def get_text(self) -> str:
        return self._editor.toPlainText()

    def apply_to_text_object(self, obj: TextObject) -> None:
        obj.text = self.get_text()
