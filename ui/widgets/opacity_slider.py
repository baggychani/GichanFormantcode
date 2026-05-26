"""공통 불투명도(Opacity) 슬라이더 — 얇은 선 + 원형 손잡이만 직접 그림 (QSlider groove 회색 띠 회피)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent, QPainter, QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

DEFAULT_ELL_FILL_OPACITY = 0.15
DEFAULT_LEGEND_FILL_OPACITY = 0.92

_HANDLE_R = 7
_TRACK_H = 4


class OpacitySlider(QWidget):
    """0–100 불투명도 슬라이더. 채워진 구간(선) + 손잡이만 표시."""

    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._minimum = 0
        self._maximum = 100
        self._value = 0
        self._dragging = False
        self.setFixedHeight(24)
        self.setMinimumWidth(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def setRange(self, minimum: int, maximum: int) -> None:
        self._minimum = int(minimum)
        self._maximum = int(maximum)
        self.setValue(self._value)

    def setValue(self, value: int) -> None:
        value = max(self._minimum, min(self._maximum, int(value)))
        if value == self._value:
            return
        self._value = value
        self.update()
        self.valueChanged.emit(self._value)

    def value(self) -> int:
        return self._value

    def _track_rect(self):
        left = _HANDLE_R
        right = max(left + 1, self.width() - _HANDLE_R)
        cy = self.height() // 2
        return left, right, cy

    def _value_from_x(self, x: float) -> int:
        left, right, _cy = self._track_rect()
        span = max(1, right - left)
        t = max(0.0, min(1.0, (x - left) / span))
        return int(round(self._minimum + t * (self._maximum - self._minimum)))

    def _handle_center_x(self) -> int:
        left, right, _cy = self._track_rect()
        span = max(1, right - left)
        t = (self._value - self._minimum) / max(
            1, (self._maximum - self._minimum)
        )
        return int(left + span * t)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        left, _right, cy = self._track_rect()
        hx = self._handle_center_x()
        active = QColor("#409EFF")
        inactive = QColor("#C0C4CC")
        color = active if self.isEnabled() else inactive

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        fill_w = max(0, hx - left)
        if fill_w > 0:
            painter.drawRoundedRect(
                left, cy - _TRACK_H // 2, fill_w, _TRACK_H, 2, 2
            )
        painter.drawEllipse(hx - _HANDLE_R, cy - _HANDLE_R, _HANDLE_R * 2, _HANDLE_R * 2)
        painter.end()

    def _set_from_mouse(self, event: QMouseEvent) -> None:
        if not self.isEnabled():
            return
        self.setValue(self._value_from_x(event.position().x()))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._set_from_mouse(event)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self._set_from_mouse(event)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)


def opacity_to_slider(opacity: float) -> int:
    opacity = max(0.0, min(1.0, float(opacity)))
    return int(round(opacity * 100))


def slider_to_opacity(value: int) -> float:
    return max(0.0, min(1.0, int(value) / 100.0))


class OpacitySliderRow(QWidget):
    """캡션 + % 라벨 + OpacitySlider."""

    def __init__(
        self,
        caption: str,
        font: QFont,
        *,
        default_percent: int = 100,
        enabled: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        caption_row = QHBoxLayout()
        caption_row.setContentsMargins(0, 0, 0, 0)
        caption_row.setSpacing(8)
        self.caption_label = QLabel(caption)
        self.caption_label.setFont(font)
        self.caption_label.setStyleSheet("color: #606266;")
        caption_row.addWidget(self.caption_label)
        caption_row.addStretch()
        self.value_label = QLabel(f"{default_percent}%")
        self.value_label.setFont(font)
        self.value_label.setStyleSheet("color: #909399;")
        caption_row.addWidget(self.value_label)
        layout.addLayout(caption_row)

        self.slider = OpacitySlider(parent=self)
        self.slider.setRange(0, 100)
        self.slider.setValue(default_percent)
        self.slider.setEnabled(enabled)
        self.slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.slider)

    def _on_value_changed(self, value: int) -> None:
        self.value_label.setText(f"{value}%")

    def set_opacity(self, opacity: float) -> None:
        pct = opacity_to_slider(opacity)
        self.slider.blockSignals(True)
        self.slider.setValue(pct)
        self.slider.blockSignals(False)
        self.value_label.setText(f"{pct}%")

    def get_opacity(self) -> float:
        return slider_to_opacity(self.slider.value())

    def set_enabled(self, enabled: bool) -> None:
        self.slider.setEnabled(enabled)
        self.caption_label.setEnabled(enabled)
        self.value_label.setEnabled(enabled)
