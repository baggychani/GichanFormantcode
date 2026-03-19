from __future__ import annotations

import json

from PyQt6.QtCore import QByteArray, QEvent, QMimeData, QObject, QPointF, Qt
from PyQt6.QtGui import QColor, QDrag, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QWidget

from ui.widgets.layer_logic import DRAW_ROW_MIME_TYPE, LAYER_ROW_MIME_TYPE


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
        mime.setData(LAYER_ROW_MIME_TYPE, QByteArray(self._build_drag_payload()))
        drag = QDrag(self)
        drag.setMimeData(mime)
        
        # 원본 스냅샷 획득
        pix = self.grab()
        
        # 반투명 처리된 새 Pixmap 생성
        transparent_pix = QColor(0, 0, 0, 0)
        out_pix = pix.copy()
        painter = QPainter(out_pix)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.fillRect(out_pix.rect(), QColor(0, 0, 0, 180)) # 약 70% 불투명도
        painter.end()
        
        drag.setPixmap(out_pix)
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
        if event.mimeData().hasFormat(LAYER_ROW_MIME_TYPE):
            event.acceptProposedAction()
            self._update_indicator(event.position().toPoint())

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(LAYER_ROW_MIME_TYPE):
            event.acceptProposedAction()
            self._update_indicator(event.position().toPoint())

    def dragLeaveEvent(self, event):
        self._dock._hide_drop_indicator()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(LAYER_ROW_MIME_TYPE):
            self._dock._hide_drop_indicator()
            return
        data = event.mimeData().data(LAYER_ROW_MIME_TYPE)
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
            ordered = list(range(len(dock.draw_manager.get_draw_objects())))
            drag_list = sorted(sel, key=lambda i: ordered.index(i))
            return json.dumps(drag_list).encode("utf-8")
        return str(self._draw_index).encode("utf-8")

    def _start_drag(self):
        mime = QMimeData()
        mime.setData(DRAW_ROW_MIME_TYPE, QByteArray(self._build_drag_payload()))
        drag = QDrag(self)
        drag.setMimeData(mime)
        
        # 원본 스냅샷 획득
        pix = self.grab()
        
        # 반투명 처리
        out_pix = pix.copy()
        painter = QPainter(out_pix)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.fillRect(out_pix.rect(), QColor(0, 0, 0, 180))
        painter.end()
        
        drag.setPixmap(out_pix)
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
        if event.mimeData().hasFormat(DRAW_ROW_MIME_TYPE):
            event.acceptProposedAction()
            self._update_indicator(event.position().toPoint())

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(DRAW_ROW_MIME_TYPE):
            event.acceptProposedAction()
            self._update_indicator(event.position().toPoint())

    def dragLeaveEvent(self, event):
        self._dock._hide_draw_drop_indicator()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(DRAW_ROW_MIME_TYPE):
            self._dock._hide_draw_drop_indicator()
            return
        data = event.mimeData().data(DRAW_ROW_MIME_TYPE)
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
