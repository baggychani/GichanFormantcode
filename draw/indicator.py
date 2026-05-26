from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QButtonGroup,
    QLabel,
    QGraphicsOpacityEffect,
    QLayout,
    QSizePolicy,
    QWidget,
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
    MODE_TEXT = "text"
    MODE_REF_H = "ref_h"
    MODE_REF_V = "ref_v"

    _BAR_SIDE_PAD = 6
    _BAR_VPAD = 4
    _BTN_HEIGHT = 26
    _COL_SPACING = 3

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

        # 5열 × (숫자 + 버튼) + 회색 바(그리드 row1, 레이아웃)
        self._mode_block = QWidget(self)
        self._mode_block.setStyleSheet("background: transparent;")
        mode_grid = QGridLayout(self._mode_block)
        mode_grid.setContentsMargins(self._BAR_SIDE_PAD, 0, self._BAR_SIDE_PAD, 0)
        mode_grid.setHorizontalSpacing(self._COL_SPACING)
        mode_grid.setVerticalSpacing(2)
        for col in range(5):
            mode_grid.setColumnStretch(col, 1)
        bar_row_h = self._BTN_HEIGHT + 2 * self._BAR_VPAD
        mode_grid.setRowMinimumHeight(1, bar_row_h)
        mode_grid.setRowStretch(0, 0)
        mode_grid.setRowStretch(1, 0)

        self._bar_bg = QFrame(self._mode_block)
        self._bar_bg.setObjectName("ButtonContainer")
        self._bar_bg.setStyleSheet(
            """
            QFrame#ButtonContainer {
                background-color: rgba(0, 0, 0, 25);
                border-radius: 4px;
            }
            """
        )
        self._bar_bg.setMinimumHeight(bar_row_h)
        self._bar_bg.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        mode_grid.addWidget(self._bar_bg, 1, 0, 1, 5)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        labels = [
            ("선", self.MODE_LINE, "선 (Polyline)"),
            ("영역", self.MODE_POLYGON, "영역 (Polygon)"),
            ("텍스트", self.MODE_TEXT, "텍스트"),
            ("수평 참조선", self.MODE_REF_H, "수평 참조선"),
            ("수직 참조선", self.MODE_REF_V, "수직 참조선"),
        ]
        self._buttons = {}
        num_font = QFont("Malgun Gothic", 7)
        btn_style = (
            "QPushButton {"
            "background-color: transparent; border: none; border-radius: 3px;"
            'color: #303133; font-size: 11px; font-family: "Malgun Gothic";'
            f"padding: {self._BAR_VPAD}px 8px;"
            "}"
            "QPushButton:checked { background-color: rgba(255,255,255,0.5); }"
            "QPushButton:hover:!checked { background-color: rgba(255,255,255,0.25); }"
        )
        for col, (text, mode, tooltip) in enumerate(labels):
            num_lbl = QLabel(str(col + 1), self._mode_block)
            num_lbl.setFont(num_font)
            num_lbl.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
            )
            num_lbl.setStyleSheet(
                "color: #909399; background: transparent; border: none;"
            )
            num_lbl.setFixedHeight(11)
            mode_grid.addWidget(num_lbl, 0, col, Qt.AlignmentFlag.AlignHCenter)

            btn = QPushButton(text, self._mode_block)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setToolTip(tooltip)
            btn.setFont(QFont("Malgun Gothic", 10))
            btn.setStyleSheet(btn_style)
            btn.setFixedHeight(self._BTN_HEIGHT)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(
                lambda _checked=False, m=mode: self._on_mode_button_clicked(m)
            )
            self._group.addButton(btn)
            self._buttons[mode] = btn
            mode_grid.addWidget(
                btn,
                1,
                col,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            )

        self.layout.addWidget(self._mode_block)

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

        # "그리기 끄기"용: 모든 버튼이 unchecked일 수 있도록.
        self._group.setExclusive(True)  # 하나만 선택 가능
        # 같은 버튼 다시 누르면 해제 → None 방출
        for mode, btn in self._buttons.items():
            btn.setCheckable(True)
        self._current_mode = None

    def toggle_or_select(self, mode: str) -> str | None:
        """같은 모드면 해제, 다른 모드면 선택. 적용된 모드(없으면 None) 반환."""
        if self._current_mode == mode:
            self.set_mode(None)
            return None
        self.set_mode(mode)
        return mode

    def _on_mode_button_clicked(self, mode: str):
        effective = self.toggle_or_select(mode)
        self.mode_changed.emit(effective)

    def _trigger_hint_by_mode(self, mode):
        """특정 모드 진입 시 힌트 표시 여부 결정 및 실행."""
        if mode in (self.MODE_LINE, self.MODE_POLYGON):
            self._show_hint("Enter 키를 눌러 그리기를 완료하세요.")
        elif mode == self.MODE_TEXT:
            self._show_hint("캔버스를 더블클릭하여 텍스트를 배치하세요.")
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
