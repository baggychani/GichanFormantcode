from __future__ import annotations

import json

from PySide6.QtCore import QByteArray, QEvent, QMimeData, QObject, QPointF, Qt
from PySide6.QtGui import QColor, QDrag, QPainter, QPen
from PySide6.QtWidgets import QFrame, QWidget

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
            # 자식 위젯(버튼 등)이 없는 빈 공간을 클릭했을 때만 처리
            if (
                hasattr(obj, "childAt")
                and obj.childAt(event.position().toPoint()) is None
            ):
                if self._callback:
                    # 클릭이 발생한 "그 순간"의 키보드 상태를 캡처하여 전달
                    self._callback(event.modifiers())
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
        payload = self._build_drag_payload()
        mime.setData(LAYER_ROW_MIME_TYPE, QByteArray(payload))
        drag = QDrag(self)
        drag.setMimeData(mime)

        # 1. 다중 선택 여부에 따라 스택 이미지 생성
        dock = self._dock
        selected_vowels = list(dock._selected_vowels)
        if self._vowel in selected_vowels and len(selected_vowels) > 1:
            # 표시 순서대로 정렬하여 상위 3개만 시각적으로 겹침 표시
            ordered = dock._get_ordered_vowels_for_display(
                list(dock._layer_rows.keys())
            )
            drag_items = sorted(selected_vowels, key=lambda v: ordered.index(v))
            show_items = drag_items[:3]  # 최대 3개까지만 겹침 표시

            # 스택용 Pixmap 크기 계산 (개당 6px씩 어긋남)
            base_pix = self.grab()
            dpr = self.devicePixelRatio()
            offset = 6
            stack_w = base_pix.width() / dpr + (len(show_items) - 1) * offset
            stack_h = base_pix.height() / dpr + (len(show_items) - 1) * offset
            from PySide6.QtGui import QPixmap

            # 장치 픽셀 비유(DPR) 반영하여 물리 픽셀 크기로 생성
            out_pix = QPixmap(int(stack_w * dpr), int(stack_h * dpr))
            out_pix.setDevicePixelRatio(dpr)
            out_pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(out_pix)

            # 뒤에서부터 앞으로 그림 (0번이 가장 위에 오도록)
            for i, v in enumerate(reversed(show_items)):
                idx = len(show_items) - 1 - i
                row_frame = dock._layer_rows.get(v)
                if row_frame:
                    p = row_frame.grab()
                    # 논리적 좌표로 그리기 (Painter가 DPR을 인식함)
                    painter.drawPixmap(idx * offset, idx * offset, p)
                    # 구분을 위한 얇은 테두리 추가 (논리적 크기 기준)
                    painter.setPen(QPen(QColor("#DCDFE6"), 1))
                    painter.drawRect(
                        idx * offset,
                        idx * offset,
                        int(p.width() / dpr) - 1,
                        int(p.height() / dpr) - 1,
                    )

            # 전체 반투명 처리
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_DestinationIn
            )
            # rect()는 논리적 크기를 반환함
            painter.fillRect(out_pix.rect(), QColor(0, 0, 0, 180))
            painter.end()
        else:
            # 단일 선택: 기존 로직 유지
            pix = self.grab()
            out_pix = pix.copy()
            painter = QPainter(out_pix)
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_DestinationIn
            )
            painter.fillRect(out_pix.rect(), QColor(0, 0, 0, 180))
            painter.end()

        drag.setPixmap(out_pix)
        if self._drag_start_pos_local is not None:
            drag.setHotSpot(self._drag_start_pos_local)
        else:
            drag.setHotSpot(
                QPointF(out_pix.width() / 2, out_pix.height() / 2).toPoint()
            )

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
        # 파란 선 그리기 로직 제거 (오버레이 위젯 방식 사용)

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
        payload = self._build_drag_payload()
        mime.setData(DRAW_ROW_MIME_TYPE, QByteArray(payload))
        drag = QDrag(self)
        drag.setMimeData(mime)

        # 1. 다중 선택 여부에 따라 스택 이미지 생성
        dock = self._dock
        sel = getattr(dock, "_selected_draw_indices", set())
        if self._draw_index in sel and len(sel) > 1:
            # 인덱스 순서대로 정렬하여 상위 3개만 시각적으로 겹침 표시
            drag_items = sorted(list(sel))
            show_items = drag_items[:3]
            rows = getattr(dock, "_draw_layer_rows", [])

            base_pix = self.grab()
            dpr = self.devicePixelRatio()
            offset = 6
            stack_w = base_pix.width() / dpr + (len(show_items) - 1) * offset
            stack_h = base_pix.height() / dpr + (len(show_items) - 1) * offset
            from PySide6.QtGui import QPixmap

            out_pix = QPixmap(int(stack_w * dpr), int(stack_h * dpr))
            out_pix.setDevicePixelRatio(dpr)
            out_pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(out_pix)

            # 뒤에서부터 앞으로 그림
            for i, idx in enumerate(reversed(show_items)):
                # idx에 해당하는 row_frame 찾기
                row_frame = None
                for r in rows:
                    if getattr(r, "_draw_index", -1) == idx:
                        row_frame = r
                        break

                if row_frame:
                    p = row_frame.grab()
                    offset_idx = len(show_items) - 1 - i
                    painter.drawPixmap(offset_idx * offset, offset_idx * offset, p)
                    # 구분을 위한 얇은 테두리 추가 (논리적 크기 기준)
                    painter.setPen(QPen(QColor("#DCDFE6"), 1))
                    painter.drawRect(
                        offset_idx * offset,
                        offset_idx * offset,
                        int(p.width() / dpr) - 1,
                        int(p.height() / dpr) - 1,
                    )

            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_DestinationIn
            )
            painter.fillRect(out_pix.rect(), QColor(0, 0, 0, 180))
            painter.end()
        else:
            # 단일 선택: 기존 로직
            pix = self.grab()
            out_pix = pix.copy()
            painter = QPainter(out_pix)
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_DestinationIn
            )
            painter.fillRect(out_pix.rect(), QColor(0, 0, 0, 180))
            painter.end()

        drag.setPixmap(out_pix)
        if self._drag_start_pos_local is not None:
            drag.setHotSpot(self._drag_start_pos_local)
        else:
            drag.setHotSpot(
                QPointF(out_pix.width() / 2, out_pix.height() / 2).toPoint()
            )

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


class _DrawListDropArea(QWidget):
    """그리기 레이어 목록 드롭 영역. 파란 선으로 삽입 위치 표시."""

    def __init__(self, dock, parent=None):
        super().__init__(parent)
        self._dock = dock
        self.setAcceptDrops(True)
        self.setStyleSheet("background: #FFFFFF;")

    def paintEvent(self, event):
        super().paintEvent(event)
        # 파란 선 그리기 로직 제거 (오버레이 위젯 방식 사용)

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
        if idx is not None:
            self._dock._set_draw_drop_indicator_between(idx, after)
