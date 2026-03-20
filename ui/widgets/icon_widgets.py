# ui/icon_widgets.py — QPainter로 그리는 아이콘·버튼·인디케이터 모음
# design_panel, layer_dock, compare_plot, tool_indicator에서 import하여 사용.

from PyQt6.QtWidgets import QPushButton, QFrame, QApplication
from PyQt6.QtCore import Qt, QSize, QRectF, QPointF, QVariantAnimation
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QBrush,
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
    app = QApplication.instance()
    dpr = app.primaryScreen().devicePixelRatio() if app else 1.0

    pixmap = QPixmap(int(w * dpr), int(h * dpr))
    pixmap.setDevicePixelRatio(dpr)
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
    app = QApplication.instance()
    dpr = app.primaryScreen().devicePixelRatio() if app else 1.0

    pixmap = QPixmap(int(w * dpr), int(h * dpr))
    pixmap.setDevicePixelRatio(dpr)
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
    app = QApplication.instance()
    dpr = app.primaryScreen().devicePixelRatio() if app else 1.0

    pixmap = QPixmap(int(50 * dpr), int(16 * dpr))
    pixmap.setDevicePixelRatio(dpr)
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
        cx, cy = 25.0, 8.0
        r = 4.0
        if marker_char == "o":
            painter.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
        elif marker_char == "s":
            painter.drawRect(QRectF(cx - r, cy - r, 2 * r, 2 * r))
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
            painter.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
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
        app = QApplication.instance()
        dpr = app.primaryScreen().devicePixelRatio() if app else 1.0

        pixmap = QPixmap(int(50 * dpr), int(14 * dpr))
        pixmap.setDevicePixelRatio(dpr)
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
    """모음 중심점 모양 선택용 버튼. 검은색 채움(o,s,^,D) 또는 흰색 채움+검은 외곽선(wo,ws,w^,wD)."""

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
        dpr = self.devicePixelRatio()
        w_px, h_px = int(24 * dpr), int(24 * dpr)
        pixmap = QPixmap(w_px, h_px)
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)
        try:
            painter = QPainter(pixmap)
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                cx, cy = 12.0, 12.0

                white_fill = marker.startswith("w") and len(marker) == 2
                base = marker[1] if white_fill else marker

                # 흰색 도형 테두리를 1.0px로 줄이고 inset 보정
                pen_width = 1.0
                inset = (pen_width / 2.0) if white_fill else 0.0
                r = 6.0 - inset
                if white_fill:
                    painter.setPen(QPen(QColor("#000000"), pen_width))
                    painter.setBrush(QBrush(QColor("#FFFFFF")))
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor("#606266"))

                # int() 변환을 제거하여 깔끔한 렌더링 보장 (다각형 형태는 기존과 완벽히 동일하게 유지)
                if base == "o":
                    painter.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
                elif base == "s":
                    painter.drawRect(QRectF(cx - r, cy - r, 2 * r, 2 * r))
                elif base == "^":
                    poly = QPolygonF(
                        [
                            QPointF(cx, cy - r),
                            QPointF(cx + r, cy + r),
                            QPointF(cx - r, cy + r),
                        ]
                    )
                    painter.drawPolygon(poly)
                elif base == "D":
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
        # 라벨/레이어 도크에서 불필요한 검은 툴팁을 없애기 위해 기본 툴팁은 비워 둔다.
        self.setToolTip("")

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


def create_trajectory_icon(
    arrow_mode: str = "none", head_style: str = "stealth", color_hex: str = "#606266"
) -> QIcon:
    """점 3개를 잇는 방향성 아이콘 생성 (그리기 디자인 패널용)."""
    w, h = 54, 24
    pixmap = QPixmap(w, h)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    try:
        cy = h / 2.0
        x_left, x_mid, x_right = 10.0, 27.0, 44.0

        # 1. 선 그리기
        pen = QPen(QColor(color_hex))
        pen.setWidthF(1.7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(QPointF(x_left, cy), QPointF(x_right, cy))

        # 화살표 촉 위치
        arrow_x_positions: list[float] = []
        if arrow_mode == "end":
            arrow_x_positions = [x_right]
        elif arrow_mode == "all":
            arrow_x_positions = [x_mid, x_right]

        # 화살표 촉 크기
        length = 8.5
        width = 4.6

        for ax in arrow_x_positions:
            if head_style == "open":
                # 1. Open: 선으로만 그려진 꺾쇠 (>)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawLine(QPointF(ax - length, cy - width), QPointF(ax, cy))
                painter.drawLine(QPointF(ax - length, cy + width), QPointF(ax, cy))

            elif head_style == "latex":
                # 2. Latex: 파인 곳 없는 평평한 뒷면을 가진 꽉 찬 삼각형 (▶)
                painter.setBrush(QBrush(QColor(color_hex)))
                painter.setPen(Qt.PenStyle.NoPen)
                poly = QPolygonF(
                    [
                        QPointF(ax, cy),  # 뾰족한 끝점
                        QPointF(ax - length, cy - width),  # 위쪽 꼬리
                        QPointF(
                            ax - length, cy + width
                        ),  # 아래쪽 꼬리 (일직선으로 이어짐)
                    ]
                )
                painter.drawPolygon(poly)
                painter.setPen(pen)

            elif head_style == "stealth":
                # 3. Stealth: Latex 기반이지만 뒷면이 안쪽으로 파인 형태
                painter.setBrush(QBrush(QColor(color_hex)))
                painter.setPen(Qt.PenStyle.NoPen)
                indent = 3.6  # 안쪽으로 파이는 정도
                poly = QPolygonF(
                    [
                        QPointF(ax, cy),  # 뾰족한 끝점
                        QPointF(ax - length, cy - width),  # 위쪽 꼬리
                        QPointF(ax - length + indent, cy),  # 안쪽으로 쏙 파인 중간점
                        QPointF(ax - length, cy + width),  # 아래쪽 꼬리
                    ]
                )
                painter.drawPolygon(poly)
                painter.setPen(pen)

        # 3. 점(마커) 3개 그리기
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(Qt.PenStyle.NoPen)
        r = 2.0
        for x in [x_left, x_mid, x_right]:
            painter.drawEllipse(QRectF(x - r, cy - r, r * 2, r * 2))
    finally:
        painter.end()

    return QIcon(pixmap)


def draw_palette_icon(painter: QPainter, rect: QRectF, is_active: bool):
    """
    주어진 사각형(rect) 영역 중앙에 맞춰 팔레트 아이콘을 그립니다.
    그리기 모드 ON: 활성(녹색), OFF: 비활성(회색).
    """
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    cx, cy = rect.center().x(), rect.center().y()
    size = min(rect.width(), rect.height()) * 0.8
    painter.translate(cx, cy)
    painter.scale(size / 24.0, size / 24.0)

    fill_color = QColor("#4CAF50") if is_active else QColor("#555555")
    dot_color = QColor("#FFFFFF") if is_active else QColor("#222222")

    body_path = QPainterPath()
    body_path.moveTo(0, -9)
    body_path.cubicTo(8, -9, 11, -3, 10, 4)
    body_path.cubicTo(9, 11, 2, 11, -3, 9)
    body_path.cubicTo(-8, 7, -11, 0, -9, -5)
    body_path.cubicTo(-7, -10, -5, -9, 0, -9)

    hole_path = QPainterPath()
    hole_path.addEllipse(QPointF(4.0, 4.0), 2.5, 2.5)
    final_path = body_path.subtracted(hole_path)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(fill_color))
    painter.drawPath(final_path)

    painter.setBrush(QBrush(dot_color))
    painter.drawEllipse(QPointF(-4.0, -4.0), 1.5, 1.5)
    painter.drawEllipse(QPointF(-5.0, 1.5), 1.5, 1.5)
    painter.drawEllipse(QPointF(-0.5, 5.0), 1.5, 1.5)

    painter.restore()


class ToolStatusIndicator(QFrame):
    """눈금자 / 팔레트(그리기) / 라벨 이동 / 설정 잠금 상태 인디케이터. QPainter로 아이콘을 그립니다."""

    def __init__(
        self, parent=None, ui_font_name: str = "Malgun Gothic", show_lock: bool = True
    ):
        super().__init__(parent)
        self.setObjectName("ToolStatusIndicator")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._ruler_on = False
        self._draw_mode_on = False
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
        # ruler | palette | move | (lock): 고정 폭으로 캔버스/창 크기 변화 방지
        if self._show_lock:
            self.setFixedWidth(152)
        else:
            self.setFixedWidth(114)

    def sizeHint(self) -> QSize:
        return QSize(152 if self._show_lock else 114, 30)

    def set_draw_mode_on(self, is_on: bool):
        if self._draw_mode_on != is_on:
            self._draw_mode_on = is_on
            self.update()

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

            n_seg = 4 if self._show_lock else 3
            seg_w = rect.width() / float(n_seg)
            left_rect = QRectF(rect.left(), rect.top(), seg_w, rect.height())
            palette_rect = QRectF(left_rect.right(), rect.top(), seg_w, rect.height())
            move_rect = QRectF(palette_rect.right(), rect.top(), seg_w, rect.height())
            self._draw_ruler_icon(painter, left_rect, self._ruler_on)
            draw_palette_icon(painter, palette_rect, self._draw_mode_on)
            self._draw_move_icon(painter, move_rect, self._move_on)
            if self._show_lock:
                lock_rect = QRectF(move_rect.right(), rect.top(), seg_w, rect.height())
                self._draw_lock_icon(painter, lock_rect, self._lock_on)
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
