# draw/indicator.py — 그리기 모드 인디케이터 (캔버스 좌측 하단)
# 텍스트 투명 버튼: 선, 영역, 수평 참조선, 수직 참조선. 아이콘은 추후 QPainter로 교체.

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QButtonGroup
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor


class DrawModeIndicator(QFrame):
    """캔버스 좌측 하단에 배치하는 그리기 모드 버튼 그룹.
    기존 우측 상단 ToolStatusIndicator와 동일하게 캔버스 안에 배치.
    텍스트 버튼(선, 영역, 수평 참조선, 수직 참조선), 투명 스타일.
    """

    # 모드가 바뀌었을 때: (mode_str) 시그널. None = 그리기 끔.
    mode_changed = pyqtSignal(object)  # str | None

    MODE_LINE = "line"
    MODE_POLYGON = "polygon"
    MODE_REF_H = "ref_h"
    MODE_REF_V = "ref_v"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DrawModeIndicator")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        self._bg_color = (0, 0, 0, 40)
        self.setStyleSheet(
            """
            DrawModeIndicator {
                background-color: rgba(0, 0, 0, 25);
                border-radius: 4px;
            }
            """
        )

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        labels = [
            ("선", self.MODE_LINE, "선 (Polyline)"),
            ("영역", self.MODE_POLYGON, "영역 (Polygon)"),
            ("수평 참조선", self.MODE_REF_H, "수평 참조선"),
            ("수직 참조선", self.MODE_REF_V, "수직 참조선"),
        ]
        self._buttons = {}
        for text, mode, tooltip in labels:
            btn = QPushButton(text, self)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setToolTip(tooltip)
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 3px;
                    color: #303133;
                    font-size: 11px;
                    padding: 4px 8px;
                }
                QPushButton:checked {
                    background-color: rgba(255,255,255,0.5);
                }
                QPushButton:hover:!checked {
                    background-color: rgba(255,255,255,0.25);
                }
                """
            )
            btn.setFixedHeight(26)
            btn.clicked.connect(
                lambda checked, m=mode: self._on_mode_clicked(m, checked)
            )
            self._group.addButton(btn)
            self._buttons[mode] = btn
            layout.addWidget(btn)

        # "그리기 끄기"용: 모든 버튼이 unchecked일 수 있도록.
        self._group.setExclusive(True)  # 하나만 선택 가능
        # 같은 버튼 다시 누르면 해제 → None 방출
        for mode, btn in self._buttons.items():
            btn.setCheckable(True)
            # 이미 연결된 lambda에서 같은 버튼을 다시 누르면 checked=False로 들어옴
        self._current_mode = None

    def _on_mode_clicked(self, mode: str, checked: bool):
        if checked:
            if self._current_mode != mode:
                self._current_mode = mode
                self.mode_changed.emit(mode)
        else:
            # 같은 버튼 다시 클릭 → 그리기 끔
            self._current_mode = None
            self.mode_changed.emit(None)

    def get_mode(self):
        """현재 선택된 모드. 없으면 None."""
        return self._current_mode

    def set_mode(self, mode: str | None):
        """외부에서 모드 설정 (예: Esc 시 포커스 해제, 다른 도구 활성화 시 그리기 끄기)."""
        self._current_mode = mode
        if mode is None:
            self._group.setExclusive(False)
            for btn in self._buttons.values():
                btn.setChecked(False)
                btn.clearFocus()
                btn.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                btn.repaint()
            self._group.setExclusive(True)
        else:
            for m, btn in self._buttons.items():
                btn.setChecked(m == mode)
        self.update()

    def turn_off(self):
        """그리기 모드 끄기 (기존 도구와 상호 배타 시 호출)."""
        self.set_mode(None)
