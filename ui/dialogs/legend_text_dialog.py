"""범례 텍스트 편집 다이얼로그."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from draw.draw_common import LegendEntry, LegendObject


class _LegendEntryRow(QWidget):
    def __init__(
        self,
        entry: LegendEntry,
        legend: LegendObject,
        *,
        ui_font_name: str = "Malgun Gothic",
        parent=None,
    ):
        super().__init__(parent)
        self.entry = entry
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        caption = "항목"
        if getattr(legend, "is_compare", False):
            caption = f"시리즈 {int(getattr(entry, 'series_id', 0)) + 1}"
        label = QLabel(caption)
        label.setFont(QFont(ui_font_name, 9))
        label.setStyleSheet("color: #606266;")
        label.setMinimumWidth(56)

        self.field = QLineEdit(str(getattr(entry, "text", "") or ""))
        self.field.setFont(QFont(ui_font_name, 10))

        layout.addWidget(label)
        layout.addWidget(self.field, 1)


class LegendTextDialog(QDialog):
    def __init__(
        self,
        legend: LegendObject,
        *,
        ui_font_name: str = "Malgun Gothic",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("범례 텍스트 편집")
        self.setModal(True)
        self._legend = legend
        self._fields: list[QLineEdit] = []
        self._entry_rows: list[_LegendEntryRow] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        hint = QLabel("각 시리즈(행)의 범례 표시 텍스트를 입력하세요.")
        hint.setFont(QFont(ui_font_name, 9))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        entries: list[LegendEntry] = list(getattr(legend, "entries", []) or [])
        if not entries:
            entries = [LegendEntry(series_id=0, text="")]

        if len(entries) > 1:
            order_hint = QLabel("항목 순서는 드래그하여 변경할 수 있습니다.")
            order_hint.setFont(QFont(ui_font_name, 9))
            order_hint.setStyleSheet("color: #909399;")
            order_hint.setWordWrap(True)
            layout.addWidget(order_hint)

            self._list = QListWidget()
            self._list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
            self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
            self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
            self._list.setSpacing(4)
            for entry in entries:
                item = QListWidgetItem(self._list)
                row = _LegendEntryRow(
                    entry,
                    legend,
                    ui_font_name=ui_font_name,
                    parent=self._list,
                )
                item.setSizeHint(row.sizeHint())
                self._list.addItem(item)
                self._list.setItemWidget(item, row)
                self._entry_rows.append(row)
            layout.addWidget(self._list)
        else:
            self._list = None
            form = QFormLayout()
            form.setSpacing(8)
            entry = entries[0]
            label = "항목 1"
            field = QLineEdit(str(getattr(entry, "text", "") or ""))
            field.setFont(QFont(ui_font_name, 10))
            form.addRow(label, field)
            self._fields.append(field)
            layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setMinimumWidth(360)

    def apply_to_legend(self) -> None:
        if self._list is not None:
            new_entries: list[LegendEntry] = []
            for i in range(self._list.count()):
                item = self._list.item(i)
                row = self._list.itemWidget(item)
                if isinstance(row, _LegendEntryRow):
                    row.entry.text = row.field.text().strip()
                    new_entries.append(row.entry)
            self._legend.entries = new_entries
            return

        entries = list(getattr(self._legend, "entries", []) or [])
        for i, field in enumerate(self._fields):
            text = field.text().strip()
            if i < len(entries):
                entries[i].text = text
        self._legend.entries = entries
