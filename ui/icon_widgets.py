# ui/icon_widgets.py — QPainter로 그리는 아이콘·버튼·인디케이터 모음
# design_panel, layer_dock, compare_plot, tool_indicator에서 import하여 사용.

from PyQt6.QtWidgets import QPushButton, QFrame
from PyQt6.QtCore import Qt, QSize, QRectF, QPointF, QVariantAnimation
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QPixmap,
    QIcon,
    QFont,
    QPolygonF,
    QPainterPath,
    QCursor,
)


def create_font_style_icon(is_serif=False):
    """폰트 스타일 선택 버튼용 아이콘: 투명 배경 QPixmap 중앙에 'A'를 Sans-serif/Serif로 그려 QIcon 반환."""
    w, h = 40, 26
    pixmap = QPixmap(w, h)
    pixmap.fill(Qt.GlobalColor.transparent)
    try:
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            font = QFont("Times New Roman", 12) if is_serif else QFont("Arial", 12)
            painter.setFont(font)
            painter.setPen(QColor("#303133"))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "A")
        finally:
            painter.end()
    except Exception:
        pass
    return QIcon(pixmap)


def create_raw_marker_icon(marker_kind):
    """데이터 포인트 선택용 아이콘: 'o'(빈 원), 'x', 'a'(라벨 문자). QIcon 반환."""
    w, h = 24, 24
    pixmap = QPixmap(w, h)
    pixmap.fill(Qt.GlobalColor.transparent)
    try:
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            cx, cy = 12, 12
            if marker_kind == "o":
                r = 5
                pen = QPen(QColor("#303133"), 1.5)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(int(cx - r), int(cy - r), 2 * r, 2 * r)
            elif marker_kind == "x":
                r = 4.5
                pen = QPen(QColor("#303133"), 1.5)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawLine(QPointF(cx - r, cy - r), QPointF(cx + r, cy + r))
                painter.drawLine(QPointF(cx + r, cy - r), QPointF(cx - r, cy + r))
            else:
                painter.setPen(QColor("#303133"))
                font = QFont("Arial", 12)
                font.setBold(False)
                painter.setFont(font)
                painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "a")
        finally:
            painter.end()
    except Exception:
        pass
    return QIcon(pixmap)


def create_legend_icon_design(color_hex, line_style_str, marker_char="o"):
    """선 스타일 + 점 아이콘 (50x16). line_style_str: '-' (실선), '--' (짧은 점선), '---' (긴 점선), ':' (레거시 DotLine). marker_char: o/s/^/D."""
    # UI 버튼의 Qt.PenStyle 매핑 기준 ('-': 실선, '---': 긴 점선, '--': 짧은 점선)
    qt_style = Qt.PenStyle.SolidLine
    dash_pattern = None
    cap_style = Qt.PenCapStyle.RoundCap  # 실선일 때는 둥근 캡 유지
    if line_style_str == "---":  # 긴 점선: 조금 길게 끊어짐
        qt_style = Qt.PenStyle.CustomDashLine
        # 펜 두께(2.0) 기준. 3.0=6px 선, 1.5=3px 공백 -> 약 2~3개 패턴
        dash_pattern = [3.0, 1.5]
        cap_style = Qt.PenCapStyle.FlatCap  # 점선은 뭉개지지 않게 평면 캡
    elif line_style_str == "--" or line_style_str == ":":  # 짧은 점선: 더 잘게 쪼개짐
        qt_style = Qt.PenStyle.CustomDashLine
        # 1.5=3px 선, 1.0=2px 공백 -> 약 3~4개 패턴
        dash_pattern = [1.5, 1.0]
        cap_style = Qt.PenCapStyle.FlatCap
    pixmap = QPixmap(50, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    try:
        pen = QPen()
        pen.setColor(QColor(color_hex))
        pen.setWidthF(2.0)
        pen.setStyle(qt_style)
        if dash_pattern:
            pen.setDashPattern(dash_pattern)
        pen.setCapStyle(cap_style)
        painter.setPen(pen)
        # 대칭 점선을 위해 왼쪽(2~18), 오른쪽(32~48) 두 구간으로 끊어서 그림. 중앙(25)은 마커가 덮음.
        painter.drawLine(2, 8, 18, 8)
        painter.drawLine(32, 8, 48, 8)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color_hex))
        cx, cy = 25, 8
        r = 4
        if marker_char == "o":
            painter.drawEllipse(int(cx - r), int(cy - r), 2 * r, 2 * r)
        elif marker_char == "s":
            painter.drawRect(int(cx - r), int(cy - r), 2 * r, 2 * r)
        elif marker_char == "^":
            poly = QPolygonF(
                [QPointF(cx, cy - r), QPointF(cx + r, cy + r), QPointF(cx - r, cy + r)]
            )
            painter.drawPolygon(poly)
        elif marker_char == "D":
            poly = QPolygonF(
                [
                    QPointF(cx, cy - r),
                    QPointF(cx + r, cy),
                    QPointF(cx, cy + r),
                    QPointF(cx - r, cy),
                ]
            )
            painter.drawPolygon(poly)
        else:
            painter.drawEllipse(int(cx - r), int(cy - r), 2 * r, 2 * r)
    finally:
        painter.end()
    return pixmap


# ---------------------------------------------------------------------------
# 버튼/위젯 클래스
# ---------------------------------------------------------------------------


class LinePreviewButton(QPushButton):
    """QPixmap에 선을 그려 QIcon으로 삽입하는 버튼 (타원 선 타입 등)."""

    def __init__(
        self,
        line_width=1.0,
        line_style=Qt.PenStyle.SolidLine,
        radius_css="0px",
        tooltip="",
        parent=None,
        dash_pattern=None,
    ):
        super().__init__("", parent)
        self.setToolTip(tooltip)
        self.setFixedHeight(26)
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; border: none; border-radius: {radius_css}; }}
            QPushButton:checked {{ background-color: #E4E7ED; }}
            QPushButton:hover:!checked {{ background-color: #F5F7FA; }}
        """)
        pixmap = QPixmap(50, 14)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen()
        pen.setColor(QColor("#606266"))
        pen.setWidthF(float(line_width))
        if dash_pattern is not None:
            pen.setStyle(Qt.PenStyle.CustomDashLine)
            pen.setDashPattern(dash_pattern)
        else:
            pen.setStyle(line_style)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(2, 7, 48, 7)
        painter.end()
        self.setIcon(QIcon(pixmap))
        self.setIconSize(pixmap.size())


class MarkerShapeButton(QPushButton):
    """모음 중심점 모양 선택용 버튼 (동그라미/사각형/삼각형/다이아몬드)."""

    MARKER_MAP = {"o": "circle", "s": "square", "^": "triangle", "D": "diamond"}

    def __init__(self, marker_char, tooltip="", parent=None):
        super().__init__("", parent)
        self.marker_char = marker_char
        self.setToolTip(tooltip)
        self.setFixedSize(28, 28)
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QPushButton { background-color: transparent; border: 1px solid transparent; border-radius: 4px; }
            QPushButton:checked { background-color: #E4E7ED; border: 1px solid #C0C4CC; }
            QPushButton:hover:!checked { background-color: #F5F7FA; }
        """)
        self.setIcon(QIcon(self._draw_icon(marker_char)))
        self.setIconSize(QPixmap(24, 24).size())

    def _draw_icon(self, marker):
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        try:
            painter = QPainter(pixmap)
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#606266"))
                cx, cy = 12, 12
                r = 6
                if marker == "o":
                    painter.drawEllipse(int(cx - r), int(cy - r), 2 * r, 2 * r)
                elif marker == "s":
                    painter.drawRect(int(cx - r), int(cy - r), 2 * r, 2 * r)
                elif marker == "^":
                    poly = QPolygonF(
                        [
                            QPointF(cx, cy - r),
                            QPointF(cx + r, cy + r),
                            QPointF(cx - r, cy + r),
                        ]
                    )
                    painter.drawPolygon(poly)
                elif marker == "D":
                    poly = QPolygonF(
                        [
                            QPointF(cx, cy - r),
                            QPointF(cx + r, cy),
                            QPointF(cx, cy + r),
                            QPointF(cx - r, cy),
                        ]
                    )
                    painter.drawPolygon(poly)
            finally:
                painter.end()
        except Exception:
            pass
        return pixmap


class ColorCircleButton(QPushButton):
    """포토샵 스타일의 동그란 색상 버튼."""

    def __init__(self, color_hex, is_transparent=False, tooltip="", parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.is_transparent = is_transparent
        self.is_custom_icon = color_hex == "custom"
        self.setFixedSize(16, 16)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if tooltip:
            self.setToolTip(tooltip)

    def set_color(self, color_hex, is_transparent=False):
        self.color_hex = color_hex
        self.is_transparent = is_transparent
        self.update()

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                rect = QRectF(self.rect())
                side = min(rect.width(), rect.height()) - 2.0
                cx, cy = rect.center().x(), rect.center().y()
                circle_rect = QRectF(cx - side / 2.0, cy - side / 2.0, side, side)
                if self.is_transparent:
                    path = QPainterPath()
                    path.addEllipse(circle_rect)
                    painter.setClipPath(path)
                    painter.setBrush(QColor("white"))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(circle_rect)
                    pen1 = QPen()
                    pen1.setColor(QColor("#F56C6C"))
                    pen1.setWidthF(1.5)
                    painter.setPen(pen1)
                    painter.drawLine(
                        QPointF(cx - side, cy - side), QPointF(cx + side, cy + side)
                    )
                    painter.setClipping(False)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    pen2 = QPen()
                    pen2.setColor(QColor("#DCDFE6"))
                    pen2.setWidthF(1.0)
                    painter.setPen(pen2)
                    painter.drawEllipse(circle_rect)
                elif self.is_custom_icon:
                    painter.setBrush(QColor("#F0F2F5"))
                    pen3 = QPen()
                    pen3.setColor(QColor("#DCDFE6"))
                    pen3.setWidthF(1.0)
                    painter.setPen(pen3)
                    painter.drawEllipse(circle_rect)
                    pen4 = QPen()
                    pen4.setColor(QColor("#606266"))
                    pen4.setWidthF(1.5)
                    pen4.setStyle(Qt.PenStyle.SolidLine)
                    pen4.setCapStyle(Qt.PenCapStyle.RoundCap)
                    painter.setPen(pen4)
                    line_len = side * 0.25
                    painter.drawLine(
                        QPointF(cx - line_len, cy), QPointF(cx + line_len, cy)
                    )
                    painter.drawLine(
                        QPointF(cx, cy - line_len), QPointF(cx, cy + line_len)
                    )
                else:
                    painter.setBrush(QColor(self.color_hex))
                    pen5 = QPen()
                    pen5.setColor(QColor(0, 0, 0, 40))
                    pen5.setWidthF(1.0)
                    painter.setPen(pen5)
                    painter.drawEllipse(circle_rect)
            finally:
                painter.end()
        except Exception:
            pass


class LayerEyeButton(QPushButton):
    """QPainter로 그리는 눈(Eye) 토글 아이콘 (레이어 표시/숨김)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        is_on = self.isChecked()
        is_hover = self.underMouse()
        icon_color = QColor("#606266") if is_on else QColor("#C0C4CC")
        if is_hover and is_on:
            icon_color = icon_color.lighter(120)
        elif is_hover and not is_on:
            icon_color = icon_color.darker(110)
        pen = QPen(
            icon_color,
            1.5,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        w, h = 14.0, 7.0
        left = QPointF(cx - w / 2, cy)
        right = QPointF(cx + w / 2, cy)
        top_ctrl = QPointF(cx, cy - h)
        bottom_ctrl = QPointF(cx, cy + h)
        path = QPainterPath()
        path.moveTo(left)
        path.quadTo(top_ctrl, right)
        path.quadTo(bottom_ctrl, left)
        painter.drawPath(path)
        if is_on:
            painter.setBrush(icon_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), 2.5, 2.5)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(pen)
            painter.drawEllipse(QPointF(cx, cy), 1.5, 1.5)
            slash_pen = QPen(
                icon_color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap
            )
            painter.setPen(slash_pen)
            painter.drawLine(
                QPointF(cx - w / 2 - 2, cy + h / 2 + 2),
                QPointF(cx + w / 2 + 2, cy - h / 2 - 2),
            )
        painter.end()


class LayerLockButton(QPushButton):
    """QPainter로 그리는 자물쇠(잠금) 토글 아이콘."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")
        self.setToolTip("잠금: 레이어 설정 초기화 시 이 레이어는 제외됩니다.")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        is_locked = self.isChecked()
        is_hover = self.underMouse()
        is_down = self.isDown()
        if is_hover or is_down:
            bg = QColor("#E8ECF1")
            if is_down:
                bg = QColor("#D0D5DD")
            painter.fillRect(0, 0, self.width(), self.height(), bg)
        icon_color = QColor("#606266") if is_locked else QColor("#C0C4CC")
        if is_hover and is_locked:
            icon_color = icon_color.lighter(120)
        elif is_hover and not is_locked:
            icon_color = icon_color.darker(110)
        pen = QPen(
            icon_color,
            1.5,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        body_w, body_h = 12.0, 9.0
        body_left = cx - body_w / 2.0
        body_top = cy - 1.0
        painter.drawRoundedRect(
            int(body_left), int(body_top), int(body_w), int(body_h), 2.0, 2.0
        )
        path = QPainterPath()
        shackle_radius = 3.5
        shackle_right_x = cx + shackle_radius
        if is_locked:
            path.moveTo(cx - shackle_radius, body_top)
            path.lineTo(cx - shackle_radius, body_top - 3.0)
            path.arcTo(
                cx - shackle_radius,
                body_top - 6.5,
                shackle_radius * 2,
                shackle_radius * 2,
                180,
                -180,
            )
            path.lineTo(shackle_right_x, body_top)
        else:
            path.moveTo(cx - shackle_radius, body_top)
            path.lineTo(cx - shackle_radius, body_top - 5.0)
            path.arcTo(
                cx - shackle_radius,
                body_top - 8.5,
                shackle_radius * 2,
                shackle_radius * 2,
                180,
                -180,
            )
            path.lineTo(shackle_right_x, body_top - 4.0)
        painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(icon_color)
        painter.drawEllipse(QPointF(cx, body_top + body_h / 2.0), 1.0, 1.0)
        painter.end()


class ToolStatusIndicator(QFrame):
    """눈금자 / 라벨 이동 / 설정 잠금 상태 인디케이터. QPainter로 아이콘을 그립니다."""

    def __init__(
        self, parent=None, ui_font_name: str = "Malgun Gothic", show_lock: bool = True
    ):
        super().__init__(parent)
        self.setObjectName("ToolStatusIndicator")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._ruler_on = False
        self._move_on = False
        self._lock_on = False
        self._show_lock = show_lock
        self._bg_color = QColor(0, 0, 0, 40)
        self._icon_off = QColor(0, 0, 0, 110)
        self._ruler_on_color = QColor("#67C23A")
        self._move_on_color = QColor("#409EFF")
        self._lock_on_color = QColor(30, 144, 255)
        self.setFixedHeight(30)
        self._update_width()

    def _update_width(self):
        if self._show_lock:
            self.setMinimumWidth(114)
        else:
            self.setMinimumWidth(76)

    def sizeHint(self) -> QSize:
        return QSize(114 if self._show_lock else 76, 30)

    def set_ruler_on(self, is_on: bool):
        if self._ruler_on != is_on:
            self._ruler_on = is_on
            self.update()

    def set_label_move_on(self, is_on: bool):
        if self._move_on != is_on:
            self._move_on = is_on
            self.update()

    def set_lock_on(self, is_on: bool):
        if self._lock_on != is_on:
            self._lock_on = is_on
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.rect().adjusted(1, 1, -1, -1)
            if rect.width() <= 0 or rect.height() <= 0:
                return
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._bg_color)
            radius = rect.height() / 2.0
            painter.drawRoundedRect(rect, radius, radius)

            if self._show_lock:
                seg_w = rect.width() / 3.0
                left_rect = QRectF(rect.left(), rect.top(), seg_w, rect.height())
                mid_rect = QRectF(left_rect.right(), rect.top(), seg_w, rect.height())
                right_rect = QRectF(mid_rect.right(), rect.top(), seg_w, rect.height())
                self._draw_ruler_icon(painter, left_rect, self._ruler_on)
                self._draw_move_icon(painter, mid_rect, self._move_on)
                self._draw_lock_icon(painter, right_rect, self._lock_on)
            else:
                w_half = rect.width() / 2.0
                left_rect = QRectF(rect.left(), rect.top(), w_half, rect.height())
                right_rect = QRectF(
                    left_rect.right(), rect.top(), w_half, rect.height()
                )
                self._draw_ruler_icon(painter, left_rect, self._ruler_on)
                self._draw_move_icon(painter, right_rect, self._move_on)
        finally:
            painter.end()

    def _draw_ruler_icon(self, painter: QPainter, rect: QRectF, is_on: bool):
        color = self._ruler_on_color if is_on else self._icon_off
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        w = rect.width() * 0.55
        h = rect.height() * 0.32
        cx, cy = rect.center().x(), rect.center().y()
        body_rect = QRectF(cx - w / 2, cy - h / 2, w, h)
        painter.drawRoundedRect(body_rect, 2, 2)
        bg_pen = QPen(
            self._bg_color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap
        )
        painter.setPen(bg_pen)
        tick_top = body_rect.top()
        tick_bottom_long = body_rect.top() + h * 0.55
        tick_bottom_short = body_rect.top() + h * 0.35
        for i in range(1, 6):
            tx = body_rect.left() + (w / 6) * i
            bottom = tick_bottom_long if i % 2 == 0 else tick_bottom_short
            painter.drawLine(QPointF(tx, tick_top), QPointF(tx, bottom))

    def _draw_move_icon(self, painter: QPainter, rect: QRectF, is_on: bool):
        color = self._move_on_color if is_on else self._icon_off
        pen = QPen(
            color,
            1.6,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = rect.center().x(), rect.center().y()
        size = min(rect.width(), rect.height()) * 0.28
        arr_len = size * 0.35
        arr_width = size * 0.35
        painter.drawLine(QPointF(cx, cy - size), QPointF(cx, cy + size))
        painter.drawLine(QPointF(cx - size, cy), QPointF(cx + size, cy))
        painter.drawLine(
            QPointF(cx, cy - size), QPointF(cx - arr_width, cy - size + arr_len)
        )
        painter.drawLine(
            QPointF(cx, cy - size), QPointF(cx + arr_width, cy - size + arr_len)
        )
        painter.drawLine(
            QPointF(cx, cy + size), QPointF(cx - arr_width, cy + size - arr_len)
        )
        painter.drawLine(
            QPointF(cx, cy + size), QPointF(cx + arr_width, cy + size - arr_len)
        )
        painter.drawLine(
            QPointF(cx - size, cy), QPointF(cx - size + arr_len, cy - arr_width)
        )
        painter.drawLine(
            QPointF(cx - size, cy), QPointF(cx - size + arr_len, cy + arr_width)
        )
        painter.drawLine(
            QPointF(cx + size, cy), QPointF(cx + size - arr_len, cy - arr_width)
        )
        painter.drawLine(
            QPointF(cx + size, cy), QPointF(cx + size - arr_len, cy + arr_width)
        )

    def _draw_lock_icon(self, painter: QPainter, rect: QRectF, is_on: bool):
        """자물쇠 아이콘 그리기 (설정 유지 잠금 상태 표시)"""
        body_color = self._lock_on_color if is_on else self._icon_off
        keyhole_color = QColor(255, 255, 255)

        seg_side = min(rect.width(), rect.height()) * 0.65
        icon_rect = QRectF(
            rect.center().x() - seg_side / 2,
            rect.center().y() - seg_side / 2,
            seg_side,
            seg_side,
        )

        w = icon_rect.width()
        h = icon_rect.height()
        x = icon_rect.x()
        y = icon_rect.y()

        shackle_w = w * 0.55
        shackle_h = h * 0.45
        shackle_x = x + (w - shackle_w) / 2
        shackle_y = y + h * 0.1

        pen_width = w * 0.12
        pen = QPen(body_color, pen_width)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # 고리(Shackle): 꺼짐/켜짐 모두 동일하게 전체 표시
        painter.drawArc(
            int(shackle_x), int(shackle_y), int(shackle_w), int(shackle_h), 0, 180 * 16
        )
        painter.drawLine(
            int(shackle_x),
            int(shackle_y + shackle_h / 2),
            int(shackle_x),
            int(y + h * 0.5),
        )
        painter.drawLine(
            int(shackle_x + shackle_w),
            int(shackle_y + shackle_h / 2),
            int(shackle_x + shackle_w),
            int(y + h * 0.5),
        )

        body_w = w * 0.8
        body_h = h * 0.55
        body_x = x + (w - body_w) / 2
        body_y = y + h * 0.45

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(body_color)
        painter.drawRoundedRect(
            QRectF(body_x, body_y, body_w, body_h), w * 0.1, w * 0.1
        )

        painter.setBrush(keyhole_color)

        hole_radius = w * 0.08
        hole_center_x = body_x + body_w / 2
        hole_center_y = body_y + body_h * 0.35
        painter.drawEllipse(
            QRectF(
                hole_center_x - hole_radius,
                hole_center_y - hole_radius,
                hole_radius * 2,
                hole_radius * 2,
            )
        )

        path = QPainterPath()
        path.moveTo(hole_center_x - hole_radius * 0.5, hole_center_y)
        path.lineTo(hole_center_x + hole_radius * 0.5, hole_center_y)
        path.lineTo(
            hole_center_x + hole_radius * 1.0, hole_center_y + hole_radius * 3.0
        )
        path.lineTo(
            hole_center_x - hole_radius * 1.0, hole_center_y + hole_radius * 3.0
        )
        path.closeSubpath()
        painter.drawPath(path)


class BidirectionalArrowButton(QPushButton):
    """Hz↔Bark 변환용 버튼. 위(→)·아래(←) 화살표, 호버 시 색상 애니메이션."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlat(True)
        self.setStyleSheet("background: transparent; border: none;")
        self.setFixedSize(28, 24)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.default_color = QColor("#666666")
        self.hover_color = QColor("#E5A93A")
        self._current_color = QColor(self.default_color)

        self.color_anim = QVariantAnimation(self)
        self.color_anim.setDuration(200)
        self.color_anim.valueChanged.connect(self._on_color_changed)

    def _on_color_changed(self, color):
        self._current_color = color
        self.update()

    def enterEvent(self, event):
        self.color_anim.setStartValue(self._current_color)
        self.color_anim.setEndValue(self.hover_color)
        self.color_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.color_anim.setStartValue(self._current_color)
        self.color_anim.setEndValue(self.default_color)
        self.color_anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(self._current_color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        rect = self.rect()
        w, h = rect.width(), rect.height()
        cx, cy = w / 2, h / 2
        length = min(w, h) * 0.4
        spacing = min(w, h) * 0.15
        head = length * 0.35

        # 위쪽 화살표 (오른쪽 →)
        y_top = cy - spacing
        x_left = cx - length / 2
        x_right = cx + length / 2
        painter.drawLine(int(x_left), int(y_top), int(x_right), int(y_top))
        painter.drawLine(
            int(x_right), int(y_top), int(x_right - head), int(y_top - head)
        )
        painter.drawLine(
            int(x_right), int(y_top), int(x_right - head), int(y_top + head)
        )

        # 아래쪽 화살표 (왼쪽 ←)
        y_bottom = cy + spacing
        painter.drawLine(int(x_right), int(y_bottom), int(x_left), int(y_bottom))
        painter.drawLine(
            int(x_left), int(y_bottom), int(x_left + head), int(y_bottom - head)
        )
        painter.drawLine(
            int(x_left), int(y_bottom), int(x_left + head), int(y_bottom + head)
        )
        painter.end()
