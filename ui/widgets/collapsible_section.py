# ui/widgets/collapsible_section.py
"""디자인 패널 등 — 섹션 접기 + 고급 옵션 접기 위젯."""

from __future__ import annotations

import config
from PySide6.QtCore import Qt, QSettings, Signal
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

import ui.widgets.layout_constants as lc

_SETTINGS_ORG = "GichanFormant"
_SETTINGS_APP = "GichanFormant"


def _collapse_settings_key(panel_id: str, *parts: str) -> str:
    return "/".join(("ui", "collapse", panel_id, *parts))


def _read_collapsed(full_key: str, default: bool) -> bool:
    value = QSettings(_SETTINGS_ORG, _SETTINGS_APP).value(full_key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes")
    return bool(default)


def _write_collapsed(full_key: str, collapsed: bool) -> None:
    QSettings(_SETTINGS_ORG, _SETTINGS_APP).setValue(full_key, collapsed)


class _ClickHeader(QWidget):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class CollapsibleSection(QWidget):
    """섹션 제목 행 클릭 시 본문 전체를 접거나 펼칩니다."""

    expanded_changed = Signal(bool)

    def __init__(
        self,
        title: str,
        title_font: QFont,
        *,
        panel_id: str = "design",
        settings_key: str | None = None,
        default_collapsed: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._settings_full_key = (
            _collapse_settings_key(panel_id, "section", settings_key)
            if settings_key
            else None
        )
        collapsed = (
            _read_collapsed(self._settings_full_key, default_collapsed)
            if self._settings_full_key
            else default_collapsed
        )
        self._collapsed = collapsed

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = _ClickHeader(self)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(0, 2, 0, 0)
        header_layout.setSpacing(6)

        self._chevron = QLabel()
        self._chevron.setFixedWidth(14)
        self._chevron.setStyleSheet("color: #909399; font-size: 10px;")

        self._title_label = QLabel(title)
        self._title_label.setFont(title_font)

        header_layout.addWidget(self._chevron)
        header_layout.addWidget(self._title_label)
        header_layout.addStretch(1)

        self._body = QWidget(self)
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(
            0, lc.SPACING_SECTION_FIRST_ITEM_PX, 0, 0
        )
        self._body_layout.setSpacing(lc.SPACING_SECTION_ITEMS_PX)

        root.addWidget(self._header)
        root.addWidget(self._body)

        self._header.clicked.connect(self._toggle)
        self._apply_collapsed_state(notify=False)

    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        if self._collapsed == collapsed:
            return
        self._collapsed = collapsed
        self._apply_collapsed_state(notify=True)

    def _toggle(self) -> None:
        self.set_collapsed(not self._collapsed)

    def _apply_collapsed_state(self, *, notify: bool) -> None:
        self._body.setVisible(not self._collapsed)
        self._chevron.setText("▶" if self._collapsed else "▼")
        if self._settings_full_key:
            _write_collapsed(self._settings_full_key, self._collapsed)
        if notify:
            self.expanded_changed.emit(not self._collapsed)


class AdvancedOptionsBlock(QWidget):
    """섹션 본문 안 — '고급 옵션'만 따로 접기."""

    def __init__(
        self,
        *,
        panel_id: str = "design",
        settings_key: str | None = None,
        default_collapsed: bool = True,
        ui_font_name: str = "Malgun Gothic",
        parent=None,
    ):
        super().__init__(parent)
        self._settings_full_key = (
            _collapse_settings_key(panel_id, "advanced", settings_key)
            if settings_key
            else None
        )
        collapsed = (
            _read_collapsed(self._settings_full_key, default_collapsed)
            if self._settings_full_key
            else default_collapsed
        )
        self._collapsed = collapsed

        root = QVBoxLayout(self)
        root.setContentsMargins(0, lc.SPACING_ADVANCED_TOP_PX, 0, 0)
        root.setSpacing(lc.SPACING_SECTION_ITEMS_PX)

        self._toggle_btn = QPushButton()
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # 섹션 제목(10pt bold)보다 작게 — 보조 라벨 톤
        self._toggle_btn.setFont(
            QFont(ui_font_name, config.FONT_SIZE_SMALL, QFont.Weight.Normal)
        )
        self._toggle_btn.setStyleSheet(
            "QPushButton { color: #909399; text-align: left; border: none; "
            "padding: 2px 0; background: transparent; }"
            "QPushButton:hover { color: #409EFF; }"
        )
        self._toggle_btn.clicked.connect(self._toggle)

        self._content = QWidget(self)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(lc.SPACING_SECTION_ITEMS_PX)

        root.addWidget(self._toggle_btn)
        root.addWidget(self._content)

        self._apply_collapsed_state()

    def body_layout(self) -> QVBoxLayout:
        return self._content_layout

    def _toggle(self) -> None:
        self._collapsed = not self._collapsed
        self._apply_collapsed_state()

    def _apply_collapsed_state(self) -> None:
        expanded = not self._collapsed
        self._content.setVisible(expanded)
        self._toggle_btn.setText(
            "고급 옵션  ▼" if expanded else "고급 옵션  ▶"
        )
        if self._settings_full_key:
            _write_collapsed(self._settings_full_key, self._collapsed)
