from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QButtonGroup,
    QLabel,
    QGraphicsOpacityEffect,
    QLayout,
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QCursor, QFont


class DrawModeIndicator(QFrame):
    """캔버스 좌측 하단에 배치하는 그리기 모드 버튼 그룹.
    기존 우측 상단 ToolStatusIndicator와 동일하게 캔버스 안에 배치.
    텍스트 버튼(선, 영역, 수평 참조선, 수직 참조선), 투명 스타일.
    """

    # 모드가 바뀌었을 때: (mode_str) 시그널. None = 그리기 끔.
    mode_changed = Signal(object)  # str | None

    MODE_LINE = "line"
    MODE_POLYGON = "polygon"
    MODE_REF_H = "ref_h"
    MODE_REF_V = "ref_v"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DrawModeIndicator")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # 외부 레이아웃: 버튼 컨테이너와 힌트 라벨을 나열
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        # 위젯 크기가 레이아웃 내용물에 맞춰 강제 고정/변동되도록 설정
        self.layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        # 실제 버튼들이 담길 배경 박스 컨테이너
        self.button_container = QFrame(self)
        self.button_container.setObjectName("ButtonContainer")
        self.button_container.setStyleSheet(
            """
            QFrame#ButtonContainer {
                background-color: rgba(0, 0, 0, 25);
                border-radius: 4px;
            }
            """
        )
        self.btn_layout = QHBoxLayout(self.button_container)
        self.btn_layout.setContentsMargins(6, 4, 6, 4)
        self.btn_layout.setSpacing(3)

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
            btn = QPushButton(text, self.button_container)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setToolTip(tooltip)
            btn.setFont(QFont("Malgun Gothic", 10))
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 3px;
                    color: #303133;
                    font-size: 11px;
                    font-family: "Malgun Gothic";
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
            self.btn_layout.addWidget(btn)

        self.layout.addWidget(self.button_container)

        # [사용자 요청] 시각적 힌트 라벨 (Enter 키 안내)
        self.hint_label = QLabel(self)
        self.hint_label.setStyleSheet(
            """
            QLabel {
                color: #FFFFFF;
                background-color: rgba(0, 0, 0, 160);
                padding: 4px 12px;
                border-radius: 13px;
                font-size: 11px;
                font-family: "Malgun Gothic";
                margin-left: 10px;
            }
            """
        )
        self.hint_label.hide()

        # 페이드 아웃 효과 설정
        self.hint_opacity = QGraphicsOpacityEffect(self.hint_label)
        self.hint_label.setGraphicsEffect(self.hint_opacity)

        self.hint_timer = QTimer(self)
        self.hint_timer.setSingleShot(True)
        self.hint_timer.timeout.connect(self._start_fade_out)

        self.fade_anim = QPropertyAnimation(self.hint_opacity, b"opacity")
        self.fade_anim.setDuration(800)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_anim.finished.connect(self.hint_label.hide)

        self.layout.addWidget(self.hint_label)
        self.layout.addStretch()

        # "그리기 끄기"용: 모든 버튼이 unchecked일 수 있도록.
        self._group.setExclusive(True)  # 하나만 선택 가능
        # 같은 버튼 다시 누르면 해제 → None 방출
        for mode, btn in self._buttons.items():
            btn.setCheckable(True)
        self._current_mode = None

    def _on_mode_clicked(self, mode: str, checked: bool):
        if checked:
            if self._current_mode != mode:
                self._current_mode = mode
                self.mode_changed.emit(mode)

                # [참고] set_mode에서도 힌트를 트리거함
                self._trigger_hint_by_mode(mode)
        else:
            # 같은 버튼 다시 클릭 → 그리기 끔
            self._current_mode = None
            self.mode_changed.emit(None)
            self._stop_hint()

    def _trigger_hint_by_mode(self, mode):
        """특정 모드 진입 시 힌트 표시 여부 결정 및 실행."""
        if mode in (self.MODE_LINE, self.MODE_POLYGON):
            self._show_hint("Enter 키를 눌러 그리기를 완료하세요.")
        else:
            self._stop_hint()

    def _show_hint(self, text):
        """2초간 힌트 표시 후 페이드 아웃."""
        self._stop_hint()
        self.hint_label.setText(text)
        self.hint_opacity.setOpacity(1.0)
        self.hint_label.show()
        self.adjustSize()  # 위젯 크기를 라벨 포함 크기로 갱신
        self.hint_timer.start(2000)

    def _stop_hint(self):
        """현재 진행 중인 힌트 중단 및 숨기기."""
        self.hint_timer.stop()
        self.fade_anim.stop()
        self.hint_label.hide()
        self.adjustSize()  # 위젯 크기를 버튼 컨테이너 크기로 축소

    def _start_fade_out(self):
        """페이드 아웃 애니메이션 시작."""
        self.fade_anim.start()

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
            self._stop_hint()
        else:
            for m, btn in self._buttons.items():
                btn.setChecked(m == mode)

            # [사용자 요청] 단축키 등으로 진입 시에도 힌트 표시
            self._trigger_hint_by_mode(mode)
        self.update()

    def turn_off(self):
        """그리기 모드 끄기 (기존 도구와 상호 배타 시 호출)."""
        self.set_mode(None)
