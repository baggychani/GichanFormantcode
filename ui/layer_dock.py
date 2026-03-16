# ui/layer_dock.py — 레이어 설정 도크 내부 위젯 (단일 플롯 전용)
#
# compare_plot 이식 시 재사용할 로직 정리:
# - 상태 접근: _get_current_filter_state() / _set_filter_state(state) 로만 읽기·쓰기.
# - 표시 순서: _get_ordered_vowels_for_display(vowels) 에서 popup.layer_order 사용. compare 시 탭별로 동일 구조 확장 가능.
# - 전체 한 줄: _build_global_row() 는 눈/반투명만 사용, 동일 규칙(눈=전체 끄기/켜기, 반투명=전체 반투명/해제).
# - 순서 변경: _on_layer_reorder(dragged, target, after) 로 저장 후 set_vowels(ordered). 삽입 위치 미리 보기는 _set_drop_indicator_between / _hide_drop_indicator.

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QTabWidget,
    QButtonGroup,
    QSizePolicy,
    QApplication,
    QSplitter,
)
from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QPointF,
    QEvent,
    QObject,
    QMimeData,
    QByteArray,
)
from PyQt6.QtGui import QFont, QFontMetrics, QPainter, QPen, QColor, QDrag

import json
import os
import config
import app_logger
from .layer_logic import (
    LAYER_ROW_MIME_TYPE as _LAYER_ROW_MIME_TYPE,
    DRAW_ROW_MIME_TYPE as _DRAW_ROW_MIME_TYPE,
    apply_global_eye,
    apply_global_semi,
    toggle_item_visibility,
    compute_order_after_drop,
    get_children_indices,
    sync_parent_lock_to_children,
)
from .design_panel import ColorPalette
from .display_utils import strip_gichan_prefix
from .icon_widgets import (
    LinePreviewButton,
    MarkerShapeButton,
    LayerEyeButton,
    LayerLockButton,
)
from . import layout_constants as lc


# design_panel과 동일 매핑
MARKER_IDS = {"o": 0, "s": 1, "^": 2, "D": 3}
MARKER_VALS = ["o", "s", "^", "D"]
MARKER_LABELS = {"o": "동그라미", "s": "사각형", "^": "삼각형", "D": "다이아몬드"}
# 디자인 설정과 동일: 얇게=0.5, 보통=1.0, 두껍게=2.0
THICK_VALS = [0.5, 1.0, 2.0]
THICK_LABELS = {0.5: "얇게", 1.0: "보통", 2.0: "두껍게"}
# 실선 '-', 긴 점선 '---'(긴 대시), 짧은 점선 '--'(중간 대시, 기존 긴 점선에 나오던 모양)
STYLE_IDS = {"-": 0, "---": 1, "--": 2}
STYLE_VALS = ["-", "---", "--"]
STYLE_LABELS = {"-": "실선", "---": "긴 점선", "--": "짧은 점선"}

COLOR_NAMES = {
    "#E64A19": "Red",
    "#F57C00": "Orange",
    "#FFEB3B": "Yellow",
    "#388E3C": "Green",
    "#00BCD4": "Cyan",
    "#1976D2": "Blue",
    "#7B1FA2": "Purple",
    "#E91E63": "Pink",
    "#000000": "Black",
    "#606060": "Dark Gray",
    "#AAAAAA": "Light Gray",
    "#795548": "Brown",
    "#009688": "Teal",
    "#FF9800": "Amber",
    "transparent": "Transparent",
    "custom": "Custom Color",
}


class _RowClickForwarder(QObject):
    """행의 이름 열 등 빈 영역 클릭 시 선택 토글으로 전달."""

    def __init__(self, callback, parent=None):
        super().__init__(parent)
        self._callback = callback

    def eventFilter(self, obj, event):
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            if self._callback:
                self._callback()
        return False


class _LayerRowFrame(QFrame):
    """레이어 한 행용 프레임. 드래그로 순서 변경 가능."""

    def __init__(self, dock, vowel, parent=None):
        super().__init__(parent)
        self._dock = dock
        self._vowel = vowel
        self._drag_start_pos_global = None
        self._drag_start_pos_local = None
        self._drag_pending = False
        self.setAcceptDrops(False)

    def register_drag_child(self, widget):
        widget.installEventFilter(self)

    def _build_drag_payload(self):
        dock = self._dock
        if self._vowel in dock._selected_vowels and len(dock._selected_vowels) > 1:
            ordered = dock._get_ordered_vowels_for_display(
                list(dock._layer_rows.keys())
            )
            drag_list = sorted(dock._selected_vowels, key=lambda v: ordered.index(v))
            return json.dumps(drag_list).encode("utf-8")
        return self._vowel.encode("utf-8")

    def _start_drag(self):
        self._drag_pending = False
        mime = QMimeData()
        mime.setData(_LAYER_ROW_MIME_TYPE, QByteArray(self._build_drag_payload()))
        drag = QDrag(self)
        drag.setMimeData(mime)
        pix = self.grab()
        drag.setPixmap(pix)
        if self._drag_start_pos_local is not None:
            drag.setHotSpot(self._drag_start_pos_local)
        else:
            drag.setHotSpot(QPointF(pix.width() / 2, pix.height() / 2).toPoint())
        self._dock._hide_drop_indicator()
        drag.exec(Qt.DropAction.MoveAction)
        self._dock._hide_drop_indicator()

    def eventFilter(self, obj, event):
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._drag_start_pos_global = event.globalPosition().toPoint()
            self._drag_start_pos_local = self.mapFromGlobal(
                event.globalPosition().toPoint()
            )
        elif (
            event.type() == QEvent.Type.MouseMove
            and self._drag_start_pos_global is not None
        ):
            if event.buttons() & Qt.MouseButton.LeftButton:
                current_pos = event.globalPosition().toPoint()
                if (current_pos - self._drag_start_pos_global).manhattanLength() >= 8:
                    self._drag_start_pos_global = None
                    self._start_drag()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos_global = event.globalPosition().toPoint()
            self._drag_start_pos_local = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos_global is None:
            super().mouseMoveEvent(event)
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        if (
            event.globalPosition().toPoint() - self._drag_start_pos_global
        ).manhattanLength() >= 8:
            self._drag_start_pos_global = None
            self._start_drag()
        else:
            super().mouseMoveEvent(event)


class _LayerListDropArea(QWidget):
    """레이어 목록 전체 영역에서 드롭 수락. 파란 선을 레이아웃 변형 없이 위에 덧그립니다."""

    def __init__(self, dock, parent=None):
        super().__init__(parent)
        self._dock = dock
        self.setAcceptDrops(True)
        self.setStyleSheet("background: #FFFFFF;")

    def paintEvent(self, event):
        super().paintEvent(event)
        if getattr(self._dock, "_drop_target", None) is not None:
            vowel, after = self._dock._drop_target
            row = self._dock._layer_rows.get(vowel)
            if row:
                rect = row.geometry()
                y = rect.bottom() if after else rect.top()
                painter = QPainter(self)
                painter.setPen(QPen(QColor("#409EFF"), 3))
                painter.drawLine(rect.left(), y, rect.right(), y)
                painter.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(_LAYER_ROW_MIME_TYPE):
            event.acceptProposedAction()
            self._update_indicator(event.position().toPoint())

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(_LAYER_ROW_MIME_TYPE):
            event.acceptProposedAction()
            self._update_indicator(event.position().toPoint())

    def dragLeaveEvent(self, event):
        self._dock._hide_drop_indicator()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(_LAYER_ROW_MIME_TYPE):
            self._dock._hide_drop_indicator()
            return
        data = event.mimeData().data(_LAYER_ROW_MIME_TYPE)
        if not data or data.isEmpty():
            self._dock._hide_drop_indicator()
            return
        try:
            raw = bytes(data).decode("utf-8")
            dragged_list = json.loads(raw) if raw.startswith("[") else [raw]
        except Exception:
            self._dock._hide_drop_indicator()
            return
        vowel, after = self._dock._get_drop_target_at_pos(event.position().toPoint())
        if vowel is not None and (len(dragged_list) > 1 or dragged_list[0] != vowel):
            self._dock._on_layer_reorder(dragged_list, vowel, after=after)
        else:
            self._dock._hide_drop_indicator()
        event.acceptProposedAction()

    def _update_indicator(self, pos):
        vowel, after = self._dock._get_drop_target_at_pos(pos)
        if vowel is not None:
            self._dock._set_drop_indicator_between(vowel, after)


class _DrawLayerRowFrame(QFrame):
    """그리기 레이어 한 행. 드래그로 순서 변경 가능."""

    def __init__(self, dock, draw_index, parent=None):
        super().__init__(parent)
        self._dock = dock
        self._draw_index = draw_index
        self._drag_start_pos_global = None
        self._drag_start_pos_local = None
        self.setAcceptDrops(False)

    def register_drag_child(self, widget):
        widget.installEventFilter(self)

    def _build_drag_payload(self):
        dock = self._dock
        sel = getattr(dock, "_selected_draw_indices", set())
        if self._draw_index in sel and len(sel) > 1:
            ordered = list(range(len(dock.popup._get_current_draw_objects())))
            drag_list = sorted(sel, key=lambda i: ordered.index(i))
            return json.dumps(drag_list).encode("utf-8")
        return str(self._draw_index).encode("utf-8")

    def _start_drag(self):
        mime = QMimeData()
        mime.setData(_DRAW_ROW_MIME_TYPE, QByteArray(self._build_drag_payload()))
        drag = QDrag(self)
        drag.setMimeData(mime)
        pix = self.grab()
        drag.setPixmap(pix)
        if self._drag_start_pos_local is not None:
            drag.setHotSpot(self._drag_start_pos_local)
        else:
            drag.setHotSpot(QPointF(pix.width() / 2, pix.height() / 2).toPoint())
        self._dock._hide_draw_drop_indicator()
        drag.exec(Qt.DropAction.MoveAction)
        self._dock._hide_draw_drop_indicator()

    def eventFilter(self, obj, event):
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._drag_start_pos_global = event.globalPosition().toPoint()
            self._drag_start_pos_local = self.mapFromGlobal(
                event.globalPosition().toPoint()
            )
        elif (
            event.type() == QEvent.Type.MouseMove
            and self._drag_start_pos_global is not None
        ):
            if event.buttons() & Qt.MouseButton.LeftButton:
                current_pos = event.globalPosition().toPoint()
                if (current_pos - self._drag_start_pos_global).manhattanLength() >= 8:
                    self._drag_start_pos_global = None
                    self._start_drag()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos_global = event.globalPosition().toPoint()
            self._drag_start_pos_local = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos_global is None:
            super().mouseMoveEvent(event)
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        if (
            event.globalPosition().toPoint() - self._drag_start_pos_global
        ).manhattanLength() >= 8:
            self._drag_start_pos_global = None
            self._start_drag()
        else:
            super().mouseMoveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        # 그리기 레이어 선택 시 파란 선(Selection Indicator) — 라벨 레이어와 동일한 #4A90E2
        if self.property("selected") in (True, "true"):
            rect = self.rect()
            painter = QPainter(self)
            painter.setPen(QPen(QColor("#4A90E2"), 3))
            painter.drawLine(rect.left(), rect.top(), rect.left(), rect.bottom())
            painter.end()


class _DrawListDropArea(QWidget):
    """그리기 레이어 목록 드롭 영역. 파란 선으로 삽입 위치 표시."""

    def __init__(self, dock, parent=None):
        super().__init__(parent)
        self._dock = dock
        self.setAcceptDrops(True)
        self.setStyleSheet("background: #FFFFFF;")

    def paintEvent(self, event):
        super().paintEvent(event)
        if getattr(self._dock, "_draw_drop_target", None) is not None:
            idx, after = self._dock._draw_drop_target
            rows = getattr(self._dock, "_draw_layer_rows", None) or []
            if 0 <= idx < len(rows):
                row = rows[idx]
                rect = row.geometry()
                y = rect.bottom() if after else rect.top()
                painter = QPainter(self)
                painter.setPen(QPen(QColor("#409EFF"), 3))
                painter.drawLine(rect.left(), y, rect.right(), y)
                painter.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(_DRAW_ROW_MIME_TYPE):
            event.acceptProposedAction()
            self._update_indicator(event.position().toPoint())

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(_DRAW_ROW_MIME_TYPE):
            event.acceptProposedAction()
            self._update_indicator(event.position().toPoint())

    def dragLeaveEvent(self, event):
        self._dock._hide_draw_drop_indicator()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(_DRAW_ROW_MIME_TYPE):
            self._dock._hide_draw_drop_indicator()
            return
        data = event.mimeData().data(_DRAW_ROW_MIME_TYPE)
        if not data or data.isEmpty():
            self._dock._hide_draw_drop_indicator()
            return
        try:
            raw = bytes(data).decode("utf-8")
            dragged_list = json.loads(raw) if raw.startswith("[") else [int(raw)]
            if not isinstance(dragged_list, list):
                dragged_list = [dragged_list]
        except Exception:
            self._dock._hide_draw_drop_indicator()
            return
        target_idx, after = self._dock._get_draw_drop_target_at_pos(
            event.position().toPoint()
        )
        if target_idx is not None and (
            len(dragged_list) > 1 or dragged_list[0] != target_idx
        ):
            self._dock._on_draw_reorder(dragged_list, target_idx, after=after)
        else:
            self._dock._hide_draw_drop_indicator()
        event.acceptProposedAction()

    def _update_indicator(self, pos):
        idx, after = self._dock._get_draw_drop_target_at_pos(pos)
        if idx is not None:
            self._dock._set_draw_drop_indicator_between(idx, after)


def _draw_object_display_name(draw_objects, index):
    """그리기 객체의 레이어 목록 표시명. 선 N : a-e-o, 영역 N : o-e-a-o, 참조선 X/Y=..."""
    if not draw_objects or index < 0 or index >= len(draw_objects):
        return ""
    obj = draw_objects[index]
    t = getattr(obj, "type", "")
    if t == "line":
        n = 1 + sum(
            1 for i in range(index) if getattr(draw_objects[i], "type", "") == "line"
        )
        labels = getattr(obj, "point_labels", None) or []
        suffix = " : " + "-".join(labels) if labels else ""
        return f"선 {n}{suffix}"
    if t == "polygon":
        n = 1 + sum(
            1 for i in range(index) if getattr(draw_objects[i], "type", "") == "polygon"
        )
        labels = getattr(obj, "point_labels", None) or []
        if labels:
            suffix = " : " + "-".join(labels) + "-" + labels[0]
        else:
            suffix = ""
        return f"영역 {n}{suffix}"
    if t == "reference":
        v = getattr(obj, "value", 0)  # 단위(Unit) 기준 순수 데이터 값
        axis_name = getattr(obj, "axis_name", None) or ""
        if not axis_name and getattr(obj, "mode", "") == "horizontal":
            axis_name = "F1"
        if not axis_name:
            axis_name = "F2"
        unit = (getattr(obj, "axis_units", "Hz") or "Hz").strip().lower()
        if unit == "norm" or "norm" in unit:
            s = f"{v:.2f}"
        elif unit in ("bk", "bark"):
            s = f"{v:.1f}"
        else:
            s = str(int(v))
        return f"참조선 : {axis_name}={s}"
    if t == "area_label":
        v = getattr(obj, "value", 0)
        unit = (getattr(obj, "axis_units", "Hz") or "Hz").strip().lower()
        if unit == "norm" or "norm" in unit:
            s = f"{v:.2f}"
        else:
            s = str(int(round(v)))
        return f"넓이 : {s}"
    return f"그리기 {index + 1}"


def _format_color_display(color_hex):
    if not color_hex or color_hex == "transparent":
        return "Transparent"
    key = color_hex if color_hex in COLOR_NAMES else color_hex.upper()
    name = COLOR_NAMES.get(key, "Custom Color")
    if name == "Custom Color":
        return f"Custom ({color_hex})"
    return f"{name} ({color_hex})"


def _create_visual_button_group(parent, options, default_idx):
    group = QButtonGroup(parent)
    frame = QFrame()
    frame.setStyleSheet(
        "QFrame { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; }"
    )
    row_layout = QHBoxLayout(frame)
    row_layout.setContentsMargins(2, 2, 2, 2)
    row_layout.setSpacing(0)
    for i, opt in enumerate(options):
        w, s, r, tooltip = opt[:4]
        dash = opt[4] if len(opt) > 4 else None
        btn = LinePreviewButton(
            line_width=w, line_style=s, radius_css=r, tooltip=tooltip, dash_pattern=dash
        )
        group.addButton(btn, i)
        row_layout.addWidget(btn)
    group.button(default_idx).setChecked(True)
    return frame, group


class LayerDockWidget(QWidget):
    filter_state_changed = pyqtSignal(dict)
    overrides_changed = pyqtSignal(dict)
    compare_switch_requested = pyqtSignal(
        int
    )  # compare 모드에서 파일 A(0)/B(1) 전환 요청
    splitter_sizes_changed = pyqtSignal(
        list
    )  # 다중플롯에서 두 도크 스플리터 비율 공유용
    order_changed = pyqtSignal(list)

    def __init__(
        self,
        parent_popup,
        ui_font_name="Malgun Gothic",
        state_key=None,
        compare_mode=False,
        file_a_name="",
        file_b_name="",
        get_default_design=None,
    ):
        """state_key: None=단일 플롯, 'blue'/'red'=compare_plot 쪽 탭별 상태. compare_mode 시 레이어 탭 내에 파일 선택 행 표시.
        get_default_design: compare_plot용. None이면 popup.design_settings 사용, callable이면 호출해 해당 시리즈(Blue/Red) 기본값 사용."""
        super().__init__(parent_popup)
        self.popup = parent_popup
        self.ui_font_name = ui_font_name
        self._state_key = state_key  # None | 'blue' | 'red'
        self._compare_mode = compare_mode
        self._file_a_name = file_a_name
        self._file_b_name = file_b_name
        self._get_default_design = get_default_design  # callable() -> dict | None
        self._selected_vowels = set()
        self._layer_rows = {}
        self._updating = False
        self._semi_memory = {}
        self._setup_ui()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        font_normal = QFont(self.ui_font_name, 9)
        font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)

        # 상단: 모음 레이어 디자인용 단일 컨테이너 (삭제/clear 없이 show/hide만 사용)
        self._design_scroll = QScrollArea()
        top_scroll = self._design_scroll
        top_scroll.setWidgetResizable(True)
        top_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        top_scroll.setFrameShape(QFrame.Shape.NoFrame)
        top_scroll.setStyleSheet("QScrollArea { background-color: #FFFFFF; }")
        self.vowel_design_container = QWidget()
        self.vowel_design_container.setStyleSheet(
            "QWidget { background-color: #FFFFFF; }"
        )
        top_layout = QVBoxLayout(self.vowel_design_container)
        top_layout.setContentsMargins(12, 12, 12, 12)
        top_layout.setSpacing(14)

        top_layout.addWidget(QLabel("라벨과 중심점", font=font_bold))
        color_layout = QVBoxLayout()
        color_layout.setSpacing(6)
        color_layout.addWidget(QLabel("라벨 텍스트 색상:", font=font_normal))
        self.lbl_color_picker = ColorPalette(
            default_color="#FF0000",
            allow_transparent=True,
            parent=self.vowel_design_container,
        )
        color_layout.addWidget(self.lbl_color_picker)
        top_layout.addLayout(color_layout)
        centroid_layout = QHBoxLayout()
        centroid_layout.setSpacing(0)
        lbl_centroid = QLabel("모음 중심점 모양:", font=font_normal)
        lbl_centroid.setMinimumWidth(120)
        centroid_layout.addWidget(lbl_centroid)
        centroid_layout.addStretch()
        self.group_centroid_marker = QButtonGroup(self.vowel_design_container)
        for i, (mk, tip) in enumerate(
            [("o", "동그라미"), ("s", "사각형"), ("^", "삼각형"), ("D", "다이아몬드")]
        ):
            btn = MarkerShapeButton(mk, tooltip=tip)
            self.group_centroid_marker.addButton(btn, i)
            centroid_layout.addWidget(btn)
        self.group_centroid_marker.button(0).setChecked(True)
        top_layout.addLayout(centroid_layout)

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color: #EBEEF5;")
        top_layout.addWidget(line1)

        top_layout.addWidget(QLabel("신뢰 타원", font=font_bold))
        thicks = [
            (1.0, Qt.PenStyle.SolidLine, "4px 0 0 4px", "얇게"),
            (2.0, Qt.PenStyle.SolidLine, "0px", "보통"),
            (3.5, Qt.PenStyle.SolidLine, "0 4px 4px 0", "두껍게"),
        ]
        thick_frame, self.group_ell_thick = _create_visual_button_group(
            self.vowel_design_container, thicks, 1
        )
        styles = [
            (2.0, Qt.PenStyle.SolidLine, "4px 0 0 4px", "실선"),
            (2.0, Qt.PenStyle.DashLine, "0px", "긴 점선"),
            (2.0, Qt.PenStyle.DotLine, "0 4px 4px 0", "짧은 점선"),
        ]
        style_frame, self.group_ell_style = _create_visual_button_group(
            self.vowel_design_container, styles, 2
        )
        ell_type_row = QVBoxLayout()
        ell_type_row.setSpacing(4)
        ell_type_row.addWidget(QLabel("타원 선 타입:", font=font_normal))
        ell_type_row.addWidget(thick_frame)
        ell_type_row.addWidget(style_frame)
        top_layout.addLayout(ell_type_row)
        ell_line_color_layout = QVBoxLayout()
        ell_line_color_layout.setSpacing(6)
        ell_line_color_layout.addWidget(QLabel("타원 선 색상:", font=font_normal))
        self.ell_color_picker = ColorPalette(
            default_color="#606060",
            allow_transparent=True,
            parent=self.vowel_design_container,
        )
        ell_line_color_layout.addWidget(self.ell_color_picker)
        top_layout.addLayout(ell_line_color_layout)
        ell_fill_layout = QVBoxLayout()
        ell_fill_layout.setSpacing(6)
        ell_fill_layout.addWidget(QLabel("타원 내부 색상:", font=font_normal))
        self.ell_fill_picker = ColorPalette(
            default_color="transparent",
            allow_transparent=True,
            parent=self.vowel_design_container,
        )
        ell_fill_layout.addWidget(self.ell_fill_picker)
        top_layout.addLayout(ell_fill_layout)

        top_layout.addStretch()
        top_scroll.setWidget(self.vowel_design_container)
        top_scroll.setMinimumHeight(80)

        self.tab_widget = QTabWidget()
        self.tab_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border-top: 1px solid #E4E7ED;
                background: #FFFFFF;
            }
            QTabBar::tab {
                background: #E4E7ED;
                border: 1px solid #DCDFE6;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: %dpx;
                padding: 6px 0px;
                color: #606266;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #303133;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #EBEEF5;
                color: #409EFF;
            }
        """
            % config.TAB_BAR_MIN_WIDTH_PX
        )
        layer_tab = QWidget()
        data_layout = QVBoxLayout(layer_tab)
        data_layout.setContentsMargins(0, 0, 0, 0)

        tab_underline = QFrame()
        tab_underline.setFrameShape(QFrame.Shape.HLine)
        tab_underline.setFixedHeight(1)
        tab_underline.setStyleSheet(
            "background-color: #E4E7ED; margin: 0; border: none;"
        )
        data_layout.addWidget(tab_underline)
        data_layout.setSpacing(0)

        # compare 모드: 레이어 목록(전체 눈/반투명 행) 바로 위에 파일 선택 행
        self._compare_file_switch_row = None
        self._compare_file_btn_a = None
        self._compare_file_btn_b = None
        self._compare_file_group = None
        if self._compare_mode:
            _max = 20  # 레이어 목록 위 파일 선택 버튼용 글자 수 제한

            def _trunc(s):
                return s if len(s) <= _max else s[: _max - 3] + "..."

            name_a = os.path.splitext(self._file_a_name)[0]
            name_b = os.path.splitext(self._file_b_name)[0]
            btn_label_a = _trunc(strip_gichan_prefix(name_a))
            btn_label_b = _trunc(strip_gichan_prefix(name_b))
            self._compare_file_switch_row = QFrame()
            self._compare_file_switch_row.setFixedHeight(32)
            self._compare_file_switch_row.setStyleSheet(
                "background-color: #F5F7FA; border-bottom: 1px solid #EBEEF5;"
            )
            switch_layout = QHBoxLayout(self._compare_file_switch_row)
            switch_layout.setContentsMargins(0, 0, 0, 0)
            switch_layout.setSpacing(0)
            self._compare_file_btn_a = QPushButton(btn_label_a)
            self._compare_file_btn_b = QPushButton(btn_label_b)
            self._compare_file_btn_a.setCheckable(True)
            self._compare_file_btn_b.setCheckable(True)
            self._compare_file_group = QButtonGroup(self)
            self._compare_file_group.addButton(self._compare_file_btn_a, 0)
            self._compare_file_group.addButton(self._compare_file_btn_b, 1)
            self._compare_file_btn_a.setChecked(True)
            for btn in (self._compare_file_btn_a, self._compare_file_btn_b):
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                btn.setFixedHeight(32)
                btn.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                )
                btn.setStyleSheet(
                    "QPushButton { background: transparent; border: none; color: #606266; font-size: 11px; padding: 4px 2px; }"
                    "QPushButton:checked { background: #E6F0F9; color: #409EFF; font-weight: bold; }"
                    "QPushButton:hover:!checked { background: #EBEEF5; }"
                )
            switch_layout.addWidget(self._compare_file_btn_a, 1)
            sep_v = QFrame()
            sep_v.setFrameShape(QFrame.Shape.VLine)
            sep_v.setFixedWidth(1)
            sep_v.setStyleSheet("background-color: #E4E7ED; margin: 0; border: none;")
            switch_layout.addWidget(sep_v)
            switch_layout.addWidget(self._compare_file_btn_b, 1)
            self._compare_file_group.buttonClicked.connect(
                lambda b: self.compare_switch_requested.emit(
                    self._compare_file_group.id(b)
                )
            )
            data_layout.addWidget(self._compare_file_switch_row)

        self.layer_scroll = QScrollArea()
        self.layer_scroll.setWidgetResizable(True)
        self.layer_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.layer_scroll.setStyleSheet(
            "QScrollArea { border: none; background: #FFFFFF; }"
        )

        self._layer_list_widget = _LayerListDropArea(self)
        self._layer_list_layout = QVBoxLayout(self._layer_list_widget)
        self._layer_list_layout.setContentsMargins(0, 0, 0, 0)
        self._layer_list_layout.setSpacing(0)
        self._layer_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layer_scroll.setWidget(self._layer_list_widget)
        self._global_row = None  # 전체 눈/반투명 한 줄 (레이어 목록 위)
        # 드래그 시 삽입 위치 미리 보기: 레이아웃 변형 없이 paintEvent에서 위에 덧그리기만 함.
        self._drop_target = None
        data_layout.addWidget(self.layer_scroll)
        self.tab_widget.addTab(layer_tab, "라벨")

        draw_tab = QWidget()
        draw_tab_layout = QVBoxLayout(draw_tab)
        draw_tab_layout.setContentsMargins(0, 0, 0, 0)
        draw_tab_layout.setSpacing(0)
        draw_tab_underline = QFrame()
        draw_tab_underline.setFrameShape(QFrame.Shape.HLine)
        draw_tab_underline.setFixedHeight(1)
        draw_tab_underline.setStyleSheet(
            "background-color: #E4E7ED; margin: 0; border: none;"
        )
        draw_tab_layout.addWidget(draw_tab_underline)
        self._draw_global_row = self._build_draw_global_row()
        draw_tab_layout.addWidget(self._draw_global_row)
        self._draw_layer_scroll = QScrollArea()
        self._draw_layer_scroll.setWidgetResizable(True)
        self._draw_layer_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._draw_layer_scroll.setStyleSheet(
            "QScrollArea { border: none; background: #FFFFFF; }"
        )
        self._draw_list_placeholder = _DrawListDropArea(self)
        self._draw_list_placeholder.setStyleSheet("background: #FFFFFF;")
        self._draw_list_placeholder.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._draw_drop_target = None
        self._draw_layer_rows = []
        self._selected_draw_indices = set()
        self._draw_list_layout = QVBoxLayout(self._draw_list_placeholder)
        self._draw_list_layout.setContentsMargins(0, 0, 0, 0)
        self._draw_list_layout.setSpacing(0)
        self._draw_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        draw_tab_layout.addWidget(self._draw_layer_scroll, 1)
        self._draw_layer_scroll.setWidget(self._draw_list_placeholder)
        self._draw_list_placeholder.installEventFilter(self)
        self.tab_widget.addTab(draw_tab, "그리기")
        self.tab_widget.currentChanged.connect(self._on_layer_tab_index_changed)

        bottom_sep = QFrame()
        bottom_sep.setFrameShape(QFrame.Shape.HLine)
        bottom_sep.setFixedHeight(1)
        bottom_sep.setStyleSheet("background-color: #E4E7ED; margin: 0; border: none;")

        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(8, 4, 8, 4)
        reset_row.setSpacing(12)
        reset_row.addStretch()

        # 레이어 순서 초기화 버튼 (파일을 넘겨도 유지되는 전역 순서를 기본값으로 되돌림)
        self.btn_reset_order = QPushButton("순서 초기화")
        self.btn_reset_order.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_order.setStyleSheet(
            "QPushButton { background-color: #F5F7FA; border: 1px solid #DCDFE6; border-radius: 4px; color: #606266; padding: 4px 10px; }"
            "QPushButton:hover { background-color: #EBEEF5; }"
        )
        self.btn_reset_order.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_reset_order.clicked.connect(self._on_reset_order_clicked)
        reset_row.addWidget(self.btn_reset_order)

        self.btn_reset_layers = QPushButton("레이어 설정 초기화")
        self.btn_reset_layers.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_layers.setStyleSheet(
            "QPushButton { background-color: #F5F7FA; border: 1px solid #DCDFE6; border-radius: 4px; color: #606266; padding: 4px 10px; }"
            "QPushButton:hover { background-color: #EBEEF5; }"
        )
        self.btn_reset_layers.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_reset_layers.clicked.connect(self._on_reset_layers_clicked)
        reset_row.addWidget(self.btn_reset_layers)

        self.btn_batch_delete_draw = QPushButton("일괄 삭제")
        self.btn_batch_delete_draw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_delete_draw.setStyleSheet(
            "QPushButton { background-color: #F5F7FA; border: 1px solid #DCDFE6; border-radius: 4px; color: #606266; padding: 4px 10px; }"
            "QPushButton:hover { background-color: #FDE2E2; color: #E64A19; }"
        )
        self.btn_batch_delete_draw.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_batch_delete_draw.clicked.connect(self._on_batch_delete_draw_clicked)
        reset_row.addWidget(self.btn_batch_delete_draw)
        self.btn_batch_delete_draw.hide()

        lower_widget = QWidget()
        lower_layout = QVBoxLayout(lower_widget)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(0)
        lower_layout.addWidget(self.tab_widget, 1)
        lower_layout.addWidget(bottom_sep)
        lower_layout.addLayout(reset_row)
        lower_widget.setMinimumHeight(80)

        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.addWidget(top_scroll)
        self._splitter.addWidget(lower_widget)
        saved = getattr(self.popup, "layer_dock_splitter_sizes", None)
        if saved and len(saved) == 2 and all(s > 0 for s in saved):
            self._splitter.setSizes(list(saved))
        else:
            self._splitter.setSizes([lc.DOCK_WIDTH_PX, 400])

        def _on_splitter_moved():
            self.splitter_sizes_changed.emit(self._splitter.sizes())

        self._splitter.splitterMoved.connect(_on_splitter_moved)
        root_layout.addWidget(self._splitter)

        def make_apply(key, get_value):
            def apply():
                if self.tab_widget.currentIndex() != 0:
                    return
                if self._updating or not self._selected_vowels:
                    return
                overrides = self._get_layer_overrides()
                if not isinstance(overrides, dict):
                    overrides = {}
                val = get_value()
                for v in self._selected_vowels:
                    overrides.setdefault(v, {})
                    overrides[v][key] = val
                self._set_layer_overrides(overrides)
                self.overrides_changed.emit(overrides)
                self._rebuild_effects()

            return apply

        self.lbl_color_picker.color_changed.connect(
            make_apply("lbl_color", lambda: self.lbl_color_picker.current_color)
        )
        self.ell_color_picker.color_changed.connect(
            make_apply(
                "ell_color",
                lambda: (
                    self.ell_color_picker.current_color
                    if self.ell_color_picker.current_color != "transparent"
                    else None
                ),
            )
        )
        self.ell_fill_picker.color_changed.connect(
            make_apply(
                "ell_fill_color",
                lambda: (
                    self.ell_fill_picker.current_color
                    if self.ell_fill_picker.current_color != "transparent"
                    else None
                ),
            )
        )

        def on_centroid_toggled():
            if self._updating:
                return
            bid = self.group_centroid_marker.checkedId()
            if bid >= 0:
                make_apply("centroid_marker", lambda: MARKER_VALS[bid])()

        def on_ell_thick_toggled():
            if self._updating:
                return
            bid = self.group_ell_thick.checkedId()
            if bid >= 0:
                make_apply("ell_thick", lambda: THICK_VALS[bid])()

        def on_ell_style_toggled():
            if self._updating:
                return
            bid = self.group_ell_style.checkedId()
            if bid >= 0:
                make_apply("ell_style", lambda: STYLE_VALS[bid])()

        self.group_centroid_marker.buttonToggled.connect(on_centroid_toggled)
        self.group_ell_thick.buttonToggled.connect(on_ell_thick_toggled)
        self.group_ell_style.buttonToggled.connect(on_ell_style_toggled)

    def _get_current_filter_state(self):
        if self._state_key:
            return getattr(self.popup, "vowel_filter_state_" + self._state_key, {})
        return getattr(self.popup, "vowel_filter_state", {})

    def _set_filter_state(self, state):
        if self._state_key:
            setattr(self.popup, "vowel_filter_state_" + self._state_key, state)
        else:
            self.popup.vowel_filter_state = state
        self.filter_state_changed.emit(state)
        self._update_global_row_state()

    def _get_layer_overrides(self):
        if self._state_key:
            return getattr(self.popup, "layer_design_overrides_" + self._state_key, {})
        return getattr(self.popup, "layer_design_overrides", {})

    def _set_layer_overrides(self, overrides):
        if self._state_key:
            setattr(self.popup, "layer_design_overrides_" + self._state_key, overrides)
        else:
            self.popup.layer_design_overrides = overrides

    def _build_global_row(self):
        """레이어 목록 위 한 줄: 전체 눈(가시성) + 전체 반투명만. 높이를 약간 낮게.
        - 눈: 클릭 시 모두 끄기. 모든 레이어가 꺼져 있으면 클릭 시 모두 켜기.
        - 반투명: 클릭 시 모두 반투명. 모두 반투명이면 클릭 시 반투명 해제.
        compare_plot 이식 시 동일 로직을 탭별로 재사용할 수 있도록 상태는 _get_current_filter_state/_set_filter_state로만 접근.
        """
        row = QFrame()
        row.setFixedHeight(26)
        # 아래쪽 1px 경계선만 사용해 다른 구분선과 동일한 두께로 보이도록 함
        row.setStyleSheet(
            "background-color: #F5F7FA; border-top: none; border-left: none; border-right: none; border-bottom: 1px solid #EBEEF5;"
        )
        main_h = QHBoxLayout(row)
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        col_eye = QFrame()
        col_eye.setFixedSize(32, 26)
        col_eye.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED;"
        )
        eye_layout = QVBoxLayout(col_eye)
        eye_layout.setContentsMargins(0, 0, 0, 0)
        eye_btn = LayerEyeButton()
        eye_btn.setFixedSize(32, 26)
        eye_layout.addWidget(eye_btn)
        main_h.addWidget(col_eye)

        col_semi = QFrame()
        col_semi.setFixedSize(54, 26)
        col_semi.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED;"
        )
        semi_layout = QVBoxLayout(col_semi)
        semi_layout.setContentsMargins(0, 0, 0, 0)
        semi_btn = QPushButton("반투명")
        semi_btn.setCheckable(True)
        semi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        semi_btn.setFixedHeight(22)
        semi_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; color: #C0C4CC; font-size: 11px; }
            QPushButton:checked { color: #409EFF; font-weight: bold; }
            QPushButton:hover { color: #66B1FF; }
        """)
        semi_layout.addWidget(semi_btn)
        main_h.addWidget(col_semi)

        main_h.addStretch()

        def on_global_eye_clicked():
            st = self._get_current_filter_state()
            vowels = list(self._layer_rows.keys())
            if not vowels:
                return
            all_off = all(st.get(v) == "OFF" for v in vowels)
            new_st = apply_global_eye(st, vowels, turn_on=all_off)
            self._updating = True
            try:
                self._set_filter_state(new_st)
                for v in vowels:
                    self._layer_rows[v].eye_btn.blockSignals(True)
                    self._layer_rows[v].eye_btn.setChecked(new_st.get(v) != "OFF")
                    self._layer_rows[v].eye_btn.blockSignals(False)
            finally:
                self._updating = False
            self._update_global_row_state()

        def on_global_semi_clicked():
            st = self._get_current_filter_state()
            vowels = list(self._layer_rows.keys())
            if not vowels:
                return
            all_semi = all(
                self._layer_rows[v].semi_btn.isChecked() and st.get(v) != "OFF"
                for v in vowels
            )
            new_st = apply_global_semi(st, vowels, semi=not all_semi)
            self._updating = True
            try:
                for v in vowels:
                    self._layer_rows[v].semi_btn.blockSignals(True)
                    self._layer_rows[v].semi_btn.setChecked(new_st.get(v) == "SEMI")
                    self._layer_rows[v].semi_btn.blockSignals(False)
                    self._semi_memory[v] = new_st.get(v) == "SEMI"
                self._set_filter_state(new_st)
            finally:
                self._updating = False
            self._update_global_row_state()

        eye_btn.clicked.connect(on_global_eye_clicked)
        semi_btn.clicked.connect(on_global_semi_clicked)
        row.eye_btn = eye_btn
        row.semi_btn = semi_btn
        return row

    def _build_draw_global_row(self):
        """그리기 탭용 일괄 눈/반투명 행. 레이어 탭과 동일한 외형, 목록 비어 있으면 no-op."""
        row = QFrame()
        row.setFixedHeight(26)
        row.setStyleSheet(
            "background-color: #F5F7FA; border-top: none; border-left: none; border-right: none; border-bottom: 1px solid #EBEEF5;"
        )
        main_h = QHBoxLayout(row)
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        col_eye = QFrame()
        col_eye.setFixedSize(32, 26)
        col_eye.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED;"
        )
        eye_layout = QVBoxLayout(col_eye)
        eye_layout.setContentsMargins(0, 0, 0, 0)
        eye_btn = LayerEyeButton()
        eye_btn.setFixedSize(32, 26)
        eye_btn.setChecked(True)
        eye_layout.addWidget(eye_btn)
        main_h.addWidget(col_eye)

        col_semi = QFrame()
        col_semi.setFixedSize(54, 26)
        col_semi.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED;"
        )
        semi_layout = QVBoxLayout(col_semi)
        semi_layout.setContentsMargins(0, 0, 0, 0)
        semi_btn = QPushButton("반투명")
        semi_btn.setCheckable(True)
        semi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        semi_btn.setFixedHeight(22)
        semi_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; color: #C0C4CC; font-size: 11px; }
            QPushButton:checked { color: #409EFF; font-weight: bold; }
            QPushButton:hover { color: #66B1FF; }
        """)
        semi_layout.addWidget(semi_btn)
        main_h.addWidget(col_semi)

        main_h.addStretch()

        def on_eye():
            rows = getattr(self, "_draw_layer_rows", None) or []
            objs = self.popup._get_current_draw_objects()
            if not rows or len(objs) != len(rows):
                return
            all_off = all(not getattr(o, "visible", True) for o in objs)
            for i, o in enumerate(objs):
                o.visible = not all_off
            for i, r in enumerate(rows):
                if hasattr(r, "eye_btn"):
                    r.eye_btn.blockSignals(True)
                    r.eye_btn.setChecked(objs[i].visible)
                    r.eye_btn.blockSignals(False)
            if hasattr(self.popup, "_redraw_draw_layer"):
                self.popup._redraw_draw_layer()
            self._update_draw_global_row_state()

        def on_semi():
            rows = getattr(self, "_draw_layer_rows", None) or []
            objs = self.popup._get_current_draw_objects()
            if not rows or len(objs) != len(rows):
                return
            all_semi = all(getattr(o, "semi", False) for o in objs)
            for i, o in enumerate(objs):
                o.semi = not all_semi
            for i, r in enumerate(rows):
                if hasattr(r, "semi_btn"):
                    r.semi_btn.blockSignals(True)
                    r.semi_btn.setChecked(objs[i].semi)
                    r.semi_btn.blockSignals(False)
            if hasattr(self.popup, "_redraw_draw_layer"):
                self.popup._redraw_draw_layer()
            self._update_draw_global_row_state()

        eye_btn.clicked.connect(on_eye)
        semi_btn.clicked.connect(on_semi)
        row.eye_btn = eye_btn
        row.semi_btn = semi_btn
        return row

    def _build_draw_layer_row(self, draw_index, obj, draw_objects):
        """그리기 레이어 한 행. 라벨 행과 동일 구조: 눈(32), 반투명(54), 이름, X(삭제)(32), 잠금(32)."""
        row = _DrawLayerRowFrame(self, draw_index)
        row.setProperty("drawRow", True)
        row.setProperty("drawIndex", draw_index)
        row.setProperty(
            "selected", draw_index in getattr(self, "_selected_draw_indices", set())
        )
        row.setStyleSheet("""
            QFrame[drawRow="true"] { background-color: transparent; }
            QFrame[drawRow="true"]:hover { background-color: #F5F7FA; }
            QFrame[drawRow="true"][selected="true"] {
                background-color: #E6F0F9;
                border-left: 3px solid #409EFF;
            }
        """)
        row_vbox = QVBoxLayout(row)
        row_vbox.setContentsMargins(0, 0, 0, 0)
        row_vbox.setSpacing(0)
        main_h = QHBoxLayout()
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        col_eye = QFrame()
        col_eye.setFixedSize(32, 32)
        col_eye.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED; border-bottom: none; border-top: none; border-left: none;"
        )
        eye_layout = QVBoxLayout(col_eye)
        eye_layout.setContentsMargins(0, 0, 0, 0)
        eye_btn = LayerEyeButton()
        eye_btn.setChecked(getattr(obj, "visible", True))
        eye_layout.addWidget(eye_btn)
        main_h.addWidget(col_eye)

        col_semi = QFrame()
        col_semi.setFixedSize(54, 32)
        col_semi.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED; border-bottom: none; border-top: none; border-left: none;"
        )
        semi_layout = QVBoxLayout(col_semi)
        semi_layout.setContentsMargins(0, 0, 0, 0)
        semi_btn = QPushButton("반투명")
        semi_btn.setCheckable(True)
        semi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        semi_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; color: #C0C4CC; font-size: 11px; }
            QPushButton:checked { color: #409EFF; font-weight: bold; }
            QPushButton:hover { color: #66B1FF; }
        """)
        semi_btn.setChecked(getattr(obj, "semi", False))
        semi_layout.addWidget(semi_btn)
        main_h.addWidget(col_semi)

        col_name = QFrame()
        col_name.setStyleSheet("border: none; background: transparent;")
        name_layout = QHBoxLayout(col_name)
        name_layout.setContentsMargins(8, 0, 4, 0)
        name_layout.setSpacing(4)
        font_name = QFont(self.ui_font_name)
        font_name.setPointSizeF(8)
        font_name.setBold(True)
        full_name = _draw_object_display_name(draw_objects, draw_index)
        name_btn = QPushButton()
        name_btn.setFont(font_name)
        _elide_width = 200
        name_btn.setText(
            QFontMetrics(font_name).elidedText(
                full_name, Qt.TextElideMode.ElideRight, _elide_width
            )
        )
        name_btn.setToolTip("")
        name_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        name_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        name_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; text-align: left; color: #303133; }"
        )
        name_btn.setCheckable(True)
        name_btn.setChecked(
            draw_index in getattr(self, "_selected_draw_indices", set())
        )
        name_layout.addWidget(name_btn, 1)
        main_h.addWidget(col_name, 1)

        col_x = QFrame()
        col_x.setFixedSize(32, 32)
        col_x.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED; border-bottom: none; border-top: none; border-left: none;"
        )
        x_layout = QVBoxLayout(col_x)
        x_layout.setContentsMargins(0, 0, 0, 0)
        x_btn = QPushButton("✕")
        x_btn.setFixedSize(28, 28)
        x_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        x_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; color: #909399; font-size: 12px; }"
            "QPushButton:hover { color: #E64A19; }"
        )
        x_layout.addWidget(x_btn)
        main_h.addWidget(col_x)

        col_lock = QFrame()
        col_lock.setFixedSize(32, 32)
        col_lock.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED; border-bottom: none; border-top: none; border-left: none;"
        )
        lock_layout = QVBoxLayout(col_lock)
        lock_layout.setContentsMargins(0, 0, 0, 0)
        lock_btn = LayerLockButton()
        lock_btn.setChecked(getattr(obj, "locked", False))
        lock_layout.addWidget(lock_btn)
        main_h.addWidget(col_lock)

        row_vbox.addLayout(main_h)

        idx = draw_index
        popup = self.popup

        def _sync_area_labels_to_parent(objs, parent_idx, attr, value):
            o = objs[parent_idx] if 0 <= parent_idx < len(objs) else None
            if not o or getattr(o, "type", "") != "polygon":
                return
            pid = getattr(o, "id", None)
            if not pid:
                return
            for child in objs:
                if (
                    getattr(child, "type", "") == "area_label"
                    and getattr(child, "parent_id", None) == pid
                ):
                    setattr(child, attr, value)

        def on_eye_toggled(checked):
            objs = popup._get_current_draw_objects()
            if 0 <= idx < len(objs):
                objs[idx].visible = checked
                _sync_area_labels_to_parent(objs, idx, "visible", checked)
                if hasattr(popup, "_redraw_draw_layer"):
                    popup._redraw_draw_layer()
                self.update_draw_layer_list(objs)

        def on_semi_toggled(checked):
            objs = popup._get_current_draw_objects()
            if 0 <= idx < len(objs):
                objs[idx].semi = checked
                _sync_area_labels_to_parent(objs, idx, "semi", checked)
                if hasattr(popup, "_redraw_draw_layer"):
                    popup._redraw_draw_layer()
                self.update_draw_layer_list(objs)

        def on_name_clicked():
            self._last_modifier = QApplication.keyboardModifiers()
            self._selected_vowels = set()
            for r in self._layer_rows.values():
                r.setProperty("selected", False)
                if hasattr(r, "name_btn"):
                    r.name_btn.setChecked(False)
                r.style().unpolish(r)
                r.style().polish(r)
            self._toggle_select_draw_index(draw_index, name_btn)

        def on_x_clicked():
            self._selected_draw_indices = {idx}
            self._on_draw_delete()

        def on_lock_toggled(checked):
            objs = popup._get_current_draw_objects()
            if 0 <= idx < len(objs):
                objs[idx].locked = checked
                sync_parent_lock_to_children(objs, idx, checked)
                for child_idx in get_children_indices(objs, idx):
                    if 0 <= child_idx < len(getattr(self, "_draw_layer_rows", [])):
                        r = self._draw_layer_rows[child_idx]
                        if hasattr(r, "lock_btn"):
                            r.lock_btn.blockSignals(True)
                            r.lock_btn.setChecked(checked)
                            r.lock_btn.blockSignals(False)

        row._click_forwarder = _RowClickForwarder(on_name_clicked, col_name)
        col_name.installEventFilter(row._click_forwarder)

        eye_btn.toggled.connect(on_eye_toggled)
        semi_btn.toggled.connect(on_semi_toggled)
        name_btn.clicked.connect(on_name_clicked)
        x_btn.clicked.connect(on_x_clicked)
        lock_btn.toggled.connect(on_lock_toggled)

        row.register_drag_child(row)
        row.register_drag_child(col_name)
        row.register_drag_child(eye_btn)
        row.register_drag_child(semi_btn)
        row.register_drag_child(name_btn)
        row.register_drag_child(x_btn)
        row.register_drag_child(lock_btn)

        row.eye_btn = eye_btn
        row.semi_btn = semi_btn
        row.name_btn = name_btn
        row.x_btn = x_btn
        row.lock_btn = lock_btn
        row.draw_index = draw_index
        return row

    def _update_global_row_state(self):
        """전체 눈/반투명 행의 체크 상태를 현재 레이어 상태에 맞춤."""
        if self._global_row is None or not self._layer_rows:
            return
        st = self._get_current_filter_state()
        vowels = list(self._layer_rows.keys())
        any_visible = any(st.get(v) != "OFF" for v in vowels)
        all_semi = all(
            st.get(v) == "SEMI" for v in vowels if st.get(v) != "OFF"
        ) and any(st.get(v) != "OFF" for v in vowels)
        self._global_row.eye_btn.blockSignals(True)
        self._global_row.semi_btn.blockSignals(True)
        self._global_row.eye_btn.setChecked(any_visible)
        self._global_row.semi_btn.setChecked(bool(all_semi))
        self._global_row.eye_btn.blockSignals(False)
        self._global_row.semi_btn.blockSignals(False)

    def _get_ordered_vowels_for_display(self, vowels):
        """표시 순서용 모음 리스트. 저장된 순서가 있으면 사용하고, 없으면 정렬 순.
        compare_plot 이식 시에는 popup 대신 탭별 layer_order를 사용할 수 있도록 확장 가능.
        """
        vowels_set = set(vowels)
        ordered = getattr(self.popup, "layer_order", None) or []
        # 저장된 순서 중 현재 모음 집합에 포함되는 것만 유지
        stored = [v for v in ordered if v in vowels_set]
        if stored and set(stored) == vowels_set:
            return list(stored)
        return sorted(vowels)

    def _set_drop_indicator_between(self, vowel, after):
        """그려야 할 목표 위치만 저장하고 화면(DropArea)을 다시 그리도록 요청합니다."""
        ordered = self._get_ordered_vowels_for_display(list(self._layer_rows.keys()))
        if vowel not in ordered:
            self._hide_drop_indicator()
            return
        self._drop_target = (vowel, after)
        self._layer_list_widget.update()

    def _hide_drop_indicator(self):
        """파란 선을 숨깁니다."""
        self._drop_target = None
        self._layer_list_widget.update()

    def _get_drop_target_at_pos(self, pos):
        """레이어 목록 위젯 내 pos(좌표)에 대응하는 (vowel, after) 반환. 행 밖이면 맨 위/맨 아래로."""
        ordered = self._get_ordered_vowels_for_display(list(self._layer_rows.keys()))
        if not ordered:
            return (None, False)
        rows = [self._layer_rows[v] for v in ordered]
        for i, row in enumerate(rows):
            geom = row.geometry()
            if geom.contains(pos):
                return (ordered[i], pos.y() > geom.center().y())
        if pos.y() < rows[0].geometry().top():
            return (ordered[0], False)
        return (ordered[-1], True)

    def _on_layer_reorder(self, dragged_list, drop_target_vowel, after=False):
        """드래그한 레이어(단일 또는 다중 선택)를 드롭 대상 행 위/아래로 이동"""
        if not isinstance(dragged_list, list):
            dragged_list = [dragged_list]
        ordered = self._get_ordered_vowels_for_display(list(self._layer_rows.keys()))
        new_order = compute_order_after_drop(
            ordered, dragged_list, drop_target_vowel, after
        )
        if new_order is None:
            return

        self.popup.layer_order = list(new_order)
        self._hide_drop_indicator()

        # 1. 화면 새로고침 (에러나던 유령 함수를 지우고 정상 함수 사용)
        self.set_vowels(new_order)

        # 2. 이동한 레이어 파란색 선택 효과 확실하게 칠하기
        self._selected_vowels = set(dragged_list)
        for v, r in self._layer_rows.items():
            r.setProperty("selected", v in self._selected_vowels)
            r.name_btn.setChecked(v in self._selected_vowels)
            r.style().unpolish(r)
            r.style().polish(r)

        # 3. 하단 디자인 패널 동기화
        self._sync_design_controls_to_selection()

        # 4. 다중 플롯 시그널 동기화 및 그래프 갱신
        if hasattr(self, "order_changed"):
            self.order_changed.emit(new_order)
        if hasattr(self.popup, "on_apply"):
            self.popup.on_apply()

    def _hide_draw_drop_indicator(self):
        self._draw_drop_target = None
        self._draw_list_placeholder.update()

    def _set_draw_drop_indicator_between(self, draw_index, after):
        objs = self.popup._get_current_draw_objects()
        if 0 <= draw_index < len(objs):
            self._draw_drop_target = (draw_index, after)
            self._draw_list_placeholder.update()

    def _get_draw_drop_target_at_pos(self, pos):
        rows = getattr(self, "_draw_layer_rows", None) or []
        if not rows:
            return (None, False)
        for i, row in enumerate(rows):
            geom = row.geometry()
            if geom.contains(pos):
                return (i, pos.y() > geom.center().y())
        if pos.y() < rows[0].geometry().top():
            return (0, False)
        return (len(rows) - 1, True)

    def _on_draw_reorder(self, dragged_indices, target_index, after=False):
        objs = self.popup._get_current_draw_objects()
        if not objs or target_index is None:
            return
        dragged_list = [objs[i] for i in sorted(dragged_indices) if 0 <= i < len(objs)]
        drop_target = objs[target_index]
        new_order = compute_order_after_drop(objs, dragged_list, drop_target, after)
        if new_order is None:
            return
        self.popup._set_current_draw_objects(new_order)
        self._hide_draw_drop_indicator()
        self._selected_draw_indices = set()
        if hasattr(self.popup, "_redraw_draw_layer"):
            self.popup._redraw_draw_layer()
        self.update_draw_layer_list(new_order)

    def _toggle_select_draw_index(self, draw_index, name_btn):
        mod = getattr(self, "_last_modifier", None)
        objs = self.popup._get_current_draw_objects()
        n = len(objs)
        if mod == Qt.KeyboardModifier.ControlModifier:
            if draw_index in self._selected_draw_indices:
                self._selected_draw_indices.discard(draw_index)
            else:
                self._selected_draw_indices.add(draw_index)
        elif mod == Qt.KeyboardModifier.ShiftModifier:
            anchor = getattr(self, "_anchor_draw_index", None)
            if anchor is None:
                anchor = draw_index
            start, end = min(anchor, draw_index), max(anchor, draw_index)
            self._selected_draw_indices = set(range(start, end + 1))
        else:
            if self._selected_draw_indices == {draw_index}:
                self._selected_draw_indices = set()
            else:
                self._selected_draw_indices = {draw_index}
                self._anchor_draw_index = draw_index
        self._last_modifier = None
        rows = getattr(self, "_draw_layer_rows", None) or []
        for i, r in enumerate(rows):
            sel = i in self._selected_draw_indices
            r.setProperty("selected", sel)
            if hasattr(r, "name_btn"):
                r.name_btn.setChecked(sel)
            r.style().unpolish(r)
            r.style().polish(r)

    def _on_draw_delete(self):
        objs = self.popup._get_current_draw_objects()
        if not objs:
            return
        to_remove = sorted(self._selected_draw_indices, reverse=True)
        if not to_remove:
            return
        removed_parent_ids = {
            getattr(objs[i], "id", None)
            for i in to_remove
            if 0 <= i < len(objs) and getattr(objs[i], "type", "") == "polygon"
        }
        removed_parent_ids.discard(None)
        min_idx = min(to_remove)
        for i in to_remove:
            if 0 <= i < len(objs):
                objs.pop(i)
        new_list = [
            o
            for o in objs
            if not (
                getattr(o, "type", "") == "area_label"
                and getattr(o, "parent_id", None) in removed_parent_ids
            )
        ]
        self.popup._set_current_draw_objects(new_list)
        if new_list:
            new_idx = min(min_idx, len(new_list) - 1)
            self._selected_draw_indices = {new_idx}
        else:
            self._selected_draw_indices = set()
        if hasattr(self.popup, "_redraw_draw_layer"):
            self.popup._redraw_draw_layer()
        self.update_draw_layer_list(new_list)
        self._draw_list_placeholder.setFocus(Qt.FocusReason.OtherFocusReason)

    def _update_draw_global_row_state(self):
        objs = self.popup._get_current_draw_objects()
        row = getattr(self, "_draw_global_row", None)
        if row is None or not objs:
            return
        any_visible = any(getattr(o, "visible", True) for o in objs)
        all_semi = all(getattr(o, "semi", False) for o in objs)
        row.eye_btn.blockSignals(True)
        row.semi_btn.blockSignals(True)
        row.eye_btn.setChecked(any_visible)
        row.semi_btn.setChecked(bool(all_semi))
        row.eye_btn.blockSignals(False)
        row.semi_btn.blockSignals(False)

    def set_vowels(self, vowels):
        """현재 파일의 모음 레이어 목록을 표시. 순서는 저장된 값이 있으면 사용, 없으면 정렬.
        맨 위에 전체 눈/반투명 한 줄을 두고, 각 레이어 행 사이에 1px 구분선을 넣는다.
        """
        self._layer_rows.clear()
        while self._layer_list_layout.count():
            item = self._layer_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        ordered_vowels = self._get_ordered_vowels_for_display(vowels)
        if not ordered_vowels:
            self._global_row = None
            self._rebuild_effects()
            return

        filter_state = self._get_current_filter_state()
        # 전체 눈/반투명 한 줄 (높이 낮게, 자체 border-bottom 1px 만 사용)
        self._global_row = self._build_global_row()
        self._layer_list_layout.addWidget(self._global_row)

        for idx, v in enumerate(ordered_vowels):
            row = self._build_layer_row(str(v), filter_state.get(v, "ON"))
            row.setProperty("vowel", v)
            self._layer_list_layout.addWidget(row)
            self._layer_rows[v] = row
            if idx < len(ordered_vowels) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setFixedHeight(1)
                sep.setStyleSheet("background-color: #EBEEF5; margin: 0; border: none;")
                self._layer_list_layout.addWidget(sep)
        self._rebuild_effects()
        self._update_global_row_state()

    def set_compare_file_index(self, index):
        """compare 모드에서 어느 파일이 선택됐는지 동기화 (0=파일A, 1=파일B)."""
        if not self._compare_mode or self._compare_file_group is None:
            return
        btn = self._compare_file_group.button(index)
        if btn and not btn.isChecked():
            btn.setChecked(True)

    def set_splitter_sizes(self, sizes):
        """다중플롯에서 다른 도크와 스플리터 비율 동기화. sizes: [상단, 하단] 픽셀."""
        if getattr(self, "_splitter", None) is not None and sizes and len(sizes) == 2:
            self._splitter.setSizes(list(sizes))

    def _build_layer_row(self, vowel, state):
        row = _LayerRowFrame(self, vowel)
        row.setProperty("layerRow", True)
        row.setProperty("vowel", vowel)

        # 행 전체에 hover 및 선택 효과 적용 (밑줄은 행 사이 separator로만 처리)
        row.setStyleSheet("""
            QFrame[layerRow="true"] {
                background-color: transparent;
            }
            QFrame[layerRow="true"]:hover {
                background-color: #F5F7FA;
            }
            QFrame[layerRow="true"][selected="true"] {
                background-color: #E6F0F9;
            }
        """)

        row_vbox = QVBoxLayout(row)
        row_vbox.setContentsMargins(0, 0, 0, 0)
        row_vbox.setSpacing(0)

        # 메인 가로 레이아웃 (테이블 구조: 여백과 간격을 0으로)
        main_h = QHBoxLayout()
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        # 1. 눈 (Eye) 열
        col_eye = QFrame()
        col_eye.setFixedSize(32, 32)
        # 오른쪽 1px 세로선으로 칸을 구분 (배경은 투명으로 두어 행 hover/선택 색이 그대로 비치도록 함)
        col_eye.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED; border-bottom: none; border-top: none; border-left: none;"
        )
        eye_layout = QVBoxLayout(col_eye)
        eye_layout.setContentsMargins(0, 0, 0, 0)
        eye_btn = LayerEyeButton()
        eye_layout.addWidget(eye_btn)

        # 2. 반투명 (Semi) 열
        col_semi = QFrame()
        col_semi.setFixedSize(54, 32)
        col_semi.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED; border-bottom: none; border-top: none; border-left: none;"
        )
        semi_layout = QVBoxLayout(col_semi)
        semi_layout.setContentsMargins(0, 0, 0, 0)
        semi_btn = QPushButton("반투명")
        semi_btn.setCheckable(True)
        semi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        semi_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; color: #C0C4CC; font-size: 11px; }
            QPushButton:checked { color: #409EFF; font-weight: bold; }
            QPushButton:hover { color: #66B1FF; }
        """)
        semi_layout.addWidget(semi_btn)

        # 상태 연동 로직 (가장 중요한 독립성 보장 영역)
        was_semi = self._semi_memory.get(vowel, False)
        if state == "SEMI":
            was_semi = True
            self._semi_memory[vowel] = True

        eye_btn.setChecked(state != "OFF")
        semi_btn.setChecked(was_semi)

        # 3. 레이어 이름 & 확장 (Name) 열
        col_name = QFrame()
        col_name.setStyleSheet("border: none; background: transparent;")
        name_layout = QHBoxLayout(col_name)
        name_layout.setContentsMargins(8, 0, 4, 0)
        name_layout.setSpacing(4)

        font_name = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        name_btn = QPushButton(vowel)
        name_btn.setFont(font_name)
        # 줄 전체에서 최대한 넓게 클릭 가능한 영역을 확보하기 위해 가로 방향으로 확장
        name_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        name_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        name_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; text-align: left; color: #303133; }"
        )

        expand_btn = QPushButton("▼")
        expand_btn.setFixedSize(22, 22)
        expand_btn.setCheckable(True)
        expand_btn.setChecked(True)
        expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        expand_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; color: #909399; font-size: 10px; } QPushButton:hover { color: #409EFF; }"
        )

        name_layout.addWidget(name_btn, 1)
        name_layout.addWidget(expand_btn)

        # 4. 자물쇠(잠금) 열 — 잠금 시 레이어 설정 초기화에서 제외
        col_lock = QFrame()
        col_lock.setFixedSize(32, 32)
        col_lock.setStyleSheet(
            "background: transparent; border-right: 1px solid #E4E7ED; border-bottom: none; border-top: none; border-left: none;"
        )
        lock_layout = QVBoxLayout(col_lock)
        lock_layout.setContentsMargins(0, 0, 0, 0)
        lock_btn = LayerLockButton()
        lock_layout.addWidget(lock_btn)

        if self._state_key:
            locked_attr = "layer_locked_vowels_" + self._state_key
            if not hasattr(self.popup, locked_attr):
                setattr(self.popup, locked_attr, set())
            locked_set = getattr(self.popup, locked_attr)
            lock_btn.setChecked(vowel in locked_set)

            def on_lock_toggled(checked):
                s = getattr(self.popup, locked_attr)
                if checked:
                    s.add(vowel)
                else:
                    s.discard(vowel)
        else:
            idx = getattr(
                self.popup,
                "current_idx",
                getattr(self.popup.controller, "current_idx", 0),
            )
            by_file = getattr(self.popup, "layer_locked_vowels_by_file", None)
            if by_file is None:
                self.popup.layer_locked_vowels_by_file = {}
                by_file = self.popup.layer_locked_vowels_by_file
            locked_set = by_file.setdefault(idx, set())
            lock_btn.setChecked(vowel in locked_set)

            def on_lock_toggled(checked):
                s = by_file.setdefault(idx, set())
                if checked:
                    s.add(vowel)
                else:
                    s.discard(vowel)

        lock_btn.toggled.connect(on_lock_toggled)

        # 행에 각 열 합체
        main_h.addWidget(col_eye)
        main_h.addWidget(col_semi)
        main_h.addWidget(col_name, 1)
        main_h.addWidget(col_lock)
        row_vbox.addLayout(main_h)

        # 4. 효과 레이어 표시 컨테이너 (여백 최소화로 "두툼한 공백" 감소)
        row.effects_container = QWidget()
        row.effects_container.setStyleSheet("background-color: transparent;")
        row.effects_layout = QVBoxLayout(row.effects_container)
        row.effects_layout.setContentsMargins(40, 2, 8, 2)
        row.effects_layout.setSpacing(0)
        row_vbox.addWidget(row.effects_container)

        # 드래그 시작 영역 확장: 행 전체와 주요 클릭 영역(이름/토글 버튼들/효과 영역)에서 드래그 가능
        row.register_drag_child(row)
        row.register_drag_child(col_name)
        row.register_drag_child(row.effects_container)
        row.register_drag_child(eye_btn)
        row.register_drag_child(semi_btn)
        row.register_drag_child(name_btn)
        row.register_drag_child(expand_btn)
        row.register_drag_child(lock_btn)

        # --- 시그널 함수 정의 ---
        def on_eye_toggled(checked):
            st = self._get_current_filter_state()
            st[vowel] = toggle_item_visibility(checked, semi_btn.isChecked())
            self._set_filter_state(st)

        def on_semi_toggled(checked):
            self._semi_memory[vowel] = checked
            if eye_btn.isChecked():
                st = self._get_current_filter_state()
                st[vowel] = toggle_item_visibility(True, checked)
                self._set_filter_state(st)

        def on_name_clicked():
            self._last_modifier = QApplication.keyboardModifiers()
            self._toggle_select_vowel(vowel, name_btn)
            self._sync_design_controls_to_selection()

        # 이름 열 빈 영역 클릭 시에도 선택 토글 (두툼한 공백 대응: 클릭 가능 영역 확대)
        row._click_forwarder = _RowClickForwarder(on_name_clicked, col_name)
        col_name.installEventFilter(row._click_forwarder)

        def on_expand_toggled(checked):
            row.effects_container.setVisible(checked)
            expand_btn.setText("▼" if checked else "▶")

        eye_btn.toggled.connect(on_eye_toggled)
        semi_btn.toggled.connect(on_semi_toggled)
        name_btn.clicked.connect(on_name_clicked)
        expand_btn.toggled.connect(on_expand_toggled)

        row.eye_btn = eye_btn
        row.semi_btn = semi_btn
        row.name_btn = name_btn
        row.expand_btn = expand_btn

        return row

    def _toggle_select_vowel(self, vowel, name_btn):
        mod = getattr(self, "_last_modifier", None)
        if mod == Qt.KeyboardModifier.ControlModifier:
            if vowel in self._selected_vowels:
                self._selected_vowels.discard(vowel)
            else:
                self._selected_vowels.add(vowel)
        elif mod == Qt.KeyboardModifier.ShiftModifier:
            vowels = self._get_ordered_vowels_for_display(list(self._layer_rows.keys()))
            if vowel in vowels:
                anchor = getattr(self, "_anchor_vowel", None) or vowel
                if anchor in vowels:
                    i1 = vowels.index(anchor)
                    i2 = vowels.index(vowel)
                    start, end = (i1, i2) if i1 <= i2 else (i2, i1)
                    self._selected_vowels = set(vowels[start : end + 1])
        else:
            # 수정키 없이 클릭: 이미 이 모음만 선택된 상태면 선택 해제, 아니면 이 모음만 선택
            if self._selected_vowels == {vowel}:
                self._selected_vowels = set()
            else:
                self._selected_vowels = {vowel}
                self._anchor_vowel = vowel

        self._last_modifier = None

        for v, r in self._layer_rows.items():
            r.setProperty("selected", v in self._selected_vowels)
            if hasattr(r, "name_btn"):
                r.name_btn.setChecked(v in self._selected_vowels)
            r.style().unpolish(r)
            r.style().polish(r)
        self._sync_design_controls_to_selection()

    def refresh_design_ui(self):
        """좌측 디자인 설정(기본값)이 바뀌었을 때 호출. 개별 오버라이드 없는 컨트롤을 새 기본값에 맞춰 갱신."""
        self._sync_design_controls_to_selection()

    def keyPressEvent(self, event):
        self._last_modifier = event.modifiers()
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if (
            obj == self._draw_list_placeholder
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Delete
        ):
            self._on_draw_delete()
            return True
        return super().eventFilter(obj, event)

    def _on_layer_tab_index_changed(self, index: int):
        """탭 전환 시 라벨 탭의 레이어 선택 해제. 그리기 탭일 때 순서/레이어 초기화 버튼 숨김."""
        self._selected_vowels = set()
        for r in self._layer_rows.values():
            r.setProperty("selected", False)
            if hasattr(r, "name_btn"):
                r.name_btn.setChecked(False)
            r.style().unpolish(r)
            r.style().polish(r)
        self._sync_design_controls_to_selection()
        if index == 1:
            self.btn_reset_order.hide()
            self.btn_reset_layers.hide()
            self.btn_batch_delete_draw.show()
            self._draw_list_placeholder.setFocus(Qt.FocusReason.OtherFocusReason)
            self._selected_vowels = set()
            for r in self._layer_rows.values():
                r.setProperty("selected", False)
                if hasattr(r, "name_btn"):
                    r.name_btn.setChecked(False)
                r.style().unpolish(r)
                r.style().polish(r)
            self.vowel_design_container.hide()
        else:
            self.btn_reset_order.show()
            self.btn_reset_layers.show()
            self.btn_batch_delete_draw.hide()
            self.vowel_design_container.show()

    def update_draw_layer_list(self, draw_objects):
        """그리기 탭 목록을 현재 파일의 그리기 객체와 동기화. 라벨과 동일 구조(눈/반투명/이름/X/잠금)."""
        self._draw_layer_rows = []
        while self._draw_list_layout.count():
            child = self._draw_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        draw_objects = draw_objects or []
        for i, obj in enumerate(draw_objects):
            row = self._build_draw_layer_row(i, obj, draw_objects)
            self._draw_list_layout.addWidget(row)
            self._draw_layer_rows.append(row)
            if i < len(draw_objects) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setFixedHeight(1)
                sep.setStyleSheet("background-color: #EBEEF5; margin: 0; border: none;")
                self._draw_list_layout.addWidget(sep)
        self._update_draw_global_row_state()

    def _sync_design_controls_to_selection(self):
        if self.tab_widget.currentIndex() != 0:
            return
        self._updating = True
        try:
            overrides = self._get_layer_overrides()
            if self._get_default_design is not None:
                ds = self._get_default_design() or {}
            else:
                ds = getattr(self.popup, "design_settings", {}) or {}
            if len(self._selected_vowels) == 1:
                v = next(iter(self._selected_vowels))
                o = overrides.get(v, {})
                self.lbl_color_picker.set_color(
                    o.get("lbl_color", ds.get("lbl_color", "#FF0000"))
                )
                idx = MARKER_IDS.get(
                    o.get("centroid_marker", ds.get("centroid_marker", "o")), 0
                )
                btn_c = self.group_centroid_marker.button(idx)
                if btn_c:
                    btn_c.setChecked(True)
                thick_val = o.get("ell_thick") or ds.get("ell_thick", 2.0)
                tid = next(
                    (
                        i
                        for i, t in enumerate(THICK_VALS)
                        if abs(t - float(thick_val)) < 0.01
                    ),
                    1,
                )
                btn_thick = self.group_ell_thick.button(tid)
                if btn_thick:
                    btn_thick.setChecked(True)
                sid = STYLE_IDS.get(o.get("ell_style", ds.get("ell_style", ":")), 2)
                btn_style = self.group_ell_style.button(sid)
                if btn_style:
                    btn_style.setChecked(True)
                self.ell_color_picker.set_color(
                    o.get("ell_color") or ds.get("ell_color") or "#606060"
                )
                self.ell_fill_picker.set_color(
                    o.get("ell_fill_color") or ds.get("ell_fill_color") or "transparent"
                )
            else:
                self.lbl_color_picker.set_color(ds.get("lbl_color", "#FF0000"))
                self.group_centroid_marker.button(0).setChecked(True)
                self.group_ell_thick.button(1).setChecked(True)
                self.group_ell_style.button(2).setChecked(True)
                self.ell_color_picker.set_color(ds.get("ell_color") or "#606060")
                self.ell_fill_picker.set_color(
                    ds.get("ell_fill_color") or "transparent"
                )
        finally:
            self._updating = False

    def _effect_display_text(self, key, value):
        if value is None:
            return ""
        if key == "lbl_color":
            return _format_color_display(value)
        if key == "centroid_marker":
            return MARKER_LABELS.get(value, str(value))
        if key == "ell_thick":
            return THICK_LABELS.get(value, str(value))
        if key == "ell_style":
            return STYLE_LABELS.get(value, str(value))
        if key in ["ell_color", "ell_fill_color"]:
            return _format_color_display(value)
        return str(value)[:20]

    def _effect_label(self, key):
        labels = {
            "lbl_color": "라벨 색",
            "centroid_marker": "중심점 모양",
            "ell_thick": "타원 선 두께",
            "ell_style": "타원 선 모양",
            "ell_color": "타원 선 색",
            "ell_fill_color": "타원 내부 색",
        }
        return labels.get(key, key)

    def _rebuild_effects(self):
        overrides = self._get_layer_overrides()
        font_effect = QFont(self.ui_font_name, 8)
        for vowel, row in self._layer_rows.items():
            while row.effects_layout.count():
                item = row.effects_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            o = overrides.get(vowel, {})
            if not o:
                row.expand_btn.setVisible(False)
                continue
            row.expand_btn.setVisible(True)
            first = True
            for key in [
                "lbl_color",
                "centroid_marker",
                "ell_thick",
                "ell_style",
                "ell_color",
                "ell_fill_color",
            ]:
                if key not in o:
                    continue
                if not first:
                    sep = QFrame()
                    sep.setFrameShape(QFrame.Shape.HLine)
                    sep.setStyleSheet(
                        "color: #F0F2F5; margin-left: 4px; margin-right: 4px; margin-top: 1px; margin-bottom: 1px;"
                    )
                    row.effects_layout.addWidget(sep)
                first = False
                eff_row = QHBoxLayout()
                eff_row.setContentsMargins(0, 0, 0, 0)
                eff_row.setSpacing(4)
                lbl = QLabel(
                    f"  {self._effect_label(key)}: {self._effect_display_text(key, o[key])}",
                    font=font_effect,
                )
                lbl.setStyleSheet("color: #606266;")
                eff_row.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
                eff_row.addStretch()
                x_btn = QPushButton("✕")
                x_btn.setFixedSize(18, 18)
                x_btn.setStyleSheet(
                    "QPushButton { border: none; color: #909399; font-size: 11px; } QPushButton:hover { color: #E64A19; }"
                )
                x_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                k, v = key, vowel

                # 버그 수정 반영: (checked=False 추가)
                def remove_key(checked=False, kk=k, vv=v):
                    if self.tab_widget.currentIndex() != 0:
                        return
                    ov = self._get_layer_overrides()
                    if not isinstance(ov, dict):
                        return
                    if vv not in ov or kk not in ov[vv]:
                        return
                    new_overrides = {}
                    for v_key, o_dict in ov.items():
                        if v_key != vv:
                            new_overrides[v_key] = dict(o_dict)
                        else:
                            no = {
                                k_sub: val
                                for k_sub, val in o_dict.items()
                                if k_sub != kk
                            }
                            if no:
                                new_overrides[v_key] = no
                    self._set_layer_overrides(new_overrides)
                    if not self._state_key:
                        idx = getattr(
                            getattr(self.popup, "controller", None), "current_idx", None
                        )
                        if idx is not None and hasattr(
                            self.popup, "layer_design_overrides_by_file"
                        ):
                            self.popup.layer_design_overrides_by_file[idx] = {
                                v_key: dict(o_dict)
                                for v_key, o_dict in new_overrides.items()
                            }
                    self.overrides_changed.emit(new_overrides)
                    self._rebuild_effects()
                    if hasattr(self.popup, "on_apply"):
                        self.popup.on_apply()

                x_btn.clicked.connect(remove_key)
                eff_row.addWidget(x_btn)
                w = QWidget()
                w.setFixedHeight(24)
                w.setLayout(eff_row)
                row.effects_layout.addWidget(w)

    def _reset_layers_for_current_file(self):
        if self._state_key:
            locked_set = getattr(
                self.popup, "layer_locked_vowels_" + self._state_key, set()
            )
            ov_attr = "layer_design_overrides_" + self._state_key
            st_attr = "vowel_filter_state_" + self._state_key
            current_ov = getattr(self.popup, ov_attr, {}) or {}
            current_st = getattr(self.popup, st_attr, {}) or {}
            setattr(
                self.popup,
                ov_attr,
                {v: dict(ov) for v, ov in current_ov.items() if v in locked_set},
            )
            setattr(
                self.popup,
                st_attr,
                {v: st for v, st in current_st.items() if v in locked_set},
            )
        else:
            idx = getattr(
                self.popup,
                "current_idx",
                getattr(self.popup.controller, "current_idx", None),
            )
            if idx is None:
                return
            locked_set = getattr(self.popup, "layer_locked_vowels_by_file", {}).get(
                idx, set()
            )
            self.popup.layer_design_overrides = {
                v: dict(ov)
                for v, ov in (self.popup.layer_design_overrides or {}).items()
                if v in locked_set
            }
            if hasattr(self.popup, "layer_design_overrides_by_file"):
                self.popup.layer_design_overrides_by_file[idx] = {
                    v: dict(ov)
                    for v, ov in (
                        self.popup.layer_design_overrides_by_file.get(idx) or {}
                    ).items()
                    if v in locked_set
                }
            self.popup.vowel_filter_state = {
                v: st
                for v, st in (self.popup.vowel_filter_state or {}).items()
                if v in locked_set
            }
            if hasattr(self.popup, "vowel_filter_state_by_file"):
                self.popup.vowel_filter_state_by_file[idx] = {
                    v: st
                    for v, st in (
                        self.popup.vowel_filter_state_by_file.get(idx) or {}
                    ).items()
                    if v in locked_set
                }

        for v in list(self._semi_memory.keys()):
            if v not in locked_set:
                del self._semi_memory[v]

        vowel_names = list(self._layer_rows.keys())
        self._rebuild_effects()
        self.set_vowels(vowel_names)
        app_logger.info(config.LOG_MSG["LAYER_SETTINGS_RESET"])
        if hasattr(self.popup, "on_apply"):
            self.popup.on_apply()

    def _on_reset_order_clicked(self):
        """순서 초기화 버튼: 현재 탭에 따라 레이어/그리기 순서 초기화."""
        if self.tab_widget.currentIndex() == 0:
            self._reset_layer_order()
        else:
            self._reset_draw_order()

    def _on_reset_layers_clicked(self):
        """레이어 설정 초기화 버튼: 현재 탭에 따라 레이어/그리기 설정 초기화."""
        if self.tab_widget.currentIndex() == 0:
            self._reset_layers_for_current_file()
        else:
            self._reset_draw_layers()

    def _on_batch_delete_draw_clicked(self):
        """일괄 삭제: locked가 False인 그리기 객체만 제거. 잠금된 객체와 그 자식(area_label 등)은 유지."""
        objs = self.popup._get_current_draw_objects()
        if not objs:
            return
        keep_ids = {
            getattr(o, "id", None)
            for o in objs
            if getattr(o, "locked", False) and getattr(o, "type", "") == "polygon"
        }
        keep_ids.discard(None)
        new_list = [
            o
            for o in objs
            if getattr(o, "locked", False)
            or (
                getattr(o, "type", "") == "area_label"
                and getattr(o, "parent_id", None) in keep_ids
            )
        ]
        self.popup._set_current_draw_objects(new_list)
        self._selected_draw_indices = set()
        if hasattr(self.popup, "_redraw_draw_layer"):
            self.popup._redraw_draw_layer()
        self.update_draw_layer_list(new_list)
        self._draw_list_placeholder.setFocus(Qt.FocusReason.OtherFocusReason)

    def _reset_draw_order(self):
        """그리기 탭 순서 초기화. 추후 _draw_layer_rows 등 연동 시 구현."""
        pass

    def _reset_draw_layers(self):
        """그리기 탭 레이어 설정 초기화. 추후 그리기 전용 overrides 연동 시 구현."""
        pass

    def _reset_layer_order(self):
        """레이어 표시 순서를 기본값(정렬)으로 초기화. 필터/디자인 설정은 그대로 유지."""
        # 전역 순서 저장소만 비우고, 현재 모음 목록을 다시 그리면 _get_ordered_vowels_for_display가 정렬 순서를 사용.
        if hasattr(self.popup, "layer_order"):
            self.popup.layer_order = []
        vowels = list(self._layer_rows.keys())
        self.set_vowels(vowels)
        if hasattr(self, "order_changed"):
            self.order_changed.emit(self._get_ordered_vowels_for_display(vowels))
        app_logger.info(config.LOG_MSG["LAYER_ORDER_RESET"])
