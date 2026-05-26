from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QPlainTextEdit,
    QAbstractSpinBox,
    QMessageBox,
    QFileDialog,
)
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import Qt

import config
from utils import app_logger
from utils import icon_utils
from draw import DrawMode
from draw.draw_common import polygon_area, AreaLabelObject, LegendObject, TextObject
from draw.legend_helpers import (
    create_legend_object,
    find_legend_object,
    has_legend_object,
)
from draw.draw_layer_render import render_draw_objects
from tools.transform_box import TransformBoxTool
from ui.dialogs.legend_text_dialog import LegendTextDialog
from ui.dialogs.draw_text_dialog import DrawTextDialog
from draw import draw_line, draw_polygon, draw_reference, draw_text
from engine.plot_engine import PlotEngine


class BasePlotWindow(QMainWindow):
    """
    popup_plot.py와 compare_plot.py의 공통 로직을 담는 부모 클래스입니다.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_legend_id = None
        self._selected_text_id = None
        self._legend_transform_tool = None
        self._draw_layer_text_refs = []
        self._text_drag_cids = None
        self._dragging_text_obj = None
        self._text_cursor_changed = False
        self._export_render_depth = 0
        self._is_label_move_active_flag = False

    def _is_label_move_active(self):
        btn_on = False
        if hasattr(self, "design_tab") and hasattr(self.design_tab, "btn_label_move"):
            btn_on = self.design_tab.btn_label_move.isChecked()
        return btn_on

    def _apply_window_icon(self):
        try:
            self.setWindowIcon(icon_utils.get_app_icon())
        except Exception:
            pass

    def closeEvent(self, event):
        if (
            hasattr(self, "_click_clear_focus_filter")
            and self._click_clear_focus_filter is not None
        ):
            try:
                QApplication.instance().removeEventFilter(
                    self._click_clear_focus_filter
                )
            except Exception:
                pass
            self._click_clear_focus_filter = None
        try:
            # 창이 닫힐 때 이 팝업과 연결된 모든 라벨 오프셋을 완전히 제거
            if hasattr(self.controller, "clear_label_offsets_for_popup"):
                self.controller.clear_label_offsets_for_popup(self)

            if self.filter_panel is not None and self.filter_panel.isVisible():
                self.filter_panel.close()

            if hasattr(self, "dock_widget") and self.dock_widget:
                self.dock_widget.close()
                self.dock_widget.deleteLater()
                self.dock_widget = None
            if hasattr(self, "layer_dock_widget") and self.layer_dock_widget:
                # 플로팅 여부와 관계없이 메인 창과 함께 정리되도록 보장
                try:
                    self.layer_dock_widget.setParent(self)
                except Exception:
                    pass
                self.layer_dock_widget.close()
                self.layer_dock_widget.deleteLater()
                self.layer_dock_widget = None

            if hasattr(self.controller, "remove_popup"):
                self.controller.remove_popup(self)

            # Matplotlib Figure/Canvas 명시적 해제로 메모리 누수 방지
            if hasattr(self, "figure") and self.figure is not None:
                self.figure.clear()
                self.figure = None
            if hasattr(self, "canvas") and self.canvas is not None:
                self.canvas.deleteLater()
                self.canvas = None
        except Exception:
            pass

        event.accept()

    def _is_input_focused(self):
        """텍스트·선택 입력 위젯 포커스 시 창 단축키가 발동하지 않도록 한다."""
        fw = QApplication.focusWidget()
        if fw is None:
            return False
        if isinstance(
            fw,
            (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QComboBox),
        ):
            return True
        return False

    def _bind_shortcuts(self):
        QShortcut(
            QKeySequence(Qt.Key.Key_A), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_switch_to_tab(0))
        QShortcut(
            QKeySequence(Qt.Key.Key_D), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_switch_to_tab(1))
        QShortcut(QKeySequence(Qt.Key.Key_Tab), self).activated.connect(
            self._toggle_panels_visibility
        )

        QShortcut(QKeySequence("Left"), self).activated.connect(self._safe_nav_prev)
        QShortcut(QKeySequence("Right"), self).activated.connect(self._safe_nav_next)

        QShortcut(
            QKeySequence(Qt.Key.Key_R), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_ruler)
        # T키는 서브클래스(popup_plot / compare_plot)에서 각자의 방식으로 등록한다.
        # base에서 등록하면 compare_plot이 T를 재등록할 때 PySide6 Ambiguous Shortcut이
        # 발생해 두 핸들러 모두 무반응이 되므로 여기서는 등록하지 않는다.
        QShortcut(
            QKeySequence(Qt.Key.Key_M), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_compare_click)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Save), self).activated.connect(
            lambda: self._on_download_plot(False, "jpg")
        )

        QShortcut(
            QKeySequence("Esc"), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_cancel_ruler_or_draw)
        self._shortcut_draw_return = QShortcut(
            QKeySequence(Qt.Key.Key_Return),
            self,
            context=Qt.ShortcutContext.WindowShortcut,
        )
        self._shortcut_draw_return.activated.connect(self._safe_draw_complete)
        self._shortcut_draw_return.setEnabled(False)
        self._shortcut_draw_enter = QShortcut(
            QKeySequence(Qt.Key.Key_Enter),
            self,
            context=Qt.ShortcutContext.WindowShortcut,
        )
        self._shortcut_draw_enter.activated.connect(self._safe_draw_complete)
        self._shortcut_draw_enter.setEnabled(False)
        QShortcut(
            QKeySequence(QKeySequence.StandardKey.Undo),
            self,
            context=Qt.ShortcutContext.WindowShortcut,
        ).activated.connect(self._safe_draw_rollback)
        QShortcut(
            QKeySequence(Qt.Key.Key_P), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_draw)
        # 그리기 모드에서 도구 선택: 1=선, 2=영역, 3=텍스트, 4=수평 참조선, 5=수직 참조선
        QShortcut(
            QKeySequence(Qt.Key.Key_1), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.LINE))
        QShortcut(
            QKeySequence(Qt.Key.Key_2), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.POLYGON))
        QShortcut(
            QKeySequence(Qt.Key.Key_3), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.TEXT))
        QShortcut(
            QKeySequence(Qt.Key.Key_4), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.REF_H))
        QShortcut(
            QKeySequence(Qt.Key.Key_5), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.REF_V))
        # L: 설정 유지 토글
        QShortcut(
            QKeySequence(Qt.Key.Key_L), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_design_lock)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(
            self._safe_batch_save
        )
        QShortcut(
            QKeySequence("Ctrl+B"), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_bold)
        QShortcut(
            QKeySequence("Ctrl+I"), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_italic)

    def _safe_draw_complete(self):
        if self._is_input_focused():
            return
        if (
            getattr(self, "btn_draw", None)
            and self.btn_draw.isChecked()
            and getattr(self, "_draw_tool", None)
        ):
            self._draw_tool.complete()

    def _safe_draw_rollback(self):
        if self._is_input_focused():
            return
        if (
            getattr(self, "btn_draw", None)
            and self.btn_draw.isChecked()
            and getattr(self, "_draw_tool", None)
        ):
            self._draw_tool.rollback()

    def _safe_set_draw_mode(self, mode):
        """숫자 키(1~5)로 그리기 도구를 선택. 그리기 모드가 꺼져 있으면 무시."""
        if self._is_input_focused():
            return
        if not (getattr(self, "btn_draw", None) and self.btn_draw.isChecked()):
            return
        if hasattr(self, "draw_indicator") and self.draw_indicator is not None:
            mode = self.draw_indicator.toggle_or_select(mode)
        self._on_draw_mode_changed(mode)

    def _safe_toggle_draw(self):
        if self._is_input_focused():
            return
        if getattr(self, "btn_draw", None):
            # 눈금자 또는 라벨 이동 모드가 켜져 있으면 그리기 모드를 켤 수 없다 (배타 모드)
            if not self.btn_draw.isChecked() and (
                self._is_ruler_active() or self._is_label_move_active()
            ):
                return
            self.btn_draw.setChecked(not self.btn_draw.isChecked())
            self._on_toggle_draw()

    def _safe_toggle_ruler(self):
        if self._is_input_focused():
            return
        next_state = not self.btn_ruler.isChecked()
        # 배타 모드: 눈금자를 켜려면 draw/label_move가 모두 꺼져 있어야 한다.
        if next_state and (
            (getattr(self, "btn_draw", None) and self.btn_draw.isChecked())
            or self._is_label_move_active()
        ):
            return
        self.btn_ruler.setChecked(next_state)
        self.on_toggle_ruler()

    def _is_ruler_active(self):
        btn_on = bool(getattr(self, "btn_ruler", None) and self.btn_ruler.isChecked())
        tool_on = bool(
            getattr(getattr(self, "controller", None), "ruler_tool", None)
            and self.controller.ruler_tool.active
        )
        return btn_on or tool_on

    def _is_draw_active(self):
        return bool(getattr(self, "btn_draw", None) and self.btn_draw.isChecked())

    def on_toggle_ruler(self):
        # 버튼 직접 클릭 시에도 진입 가능하므로 배타 모드 강제
        if self.btn_ruler.isChecked() and (
            self._is_draw_active() or self._is_label_move_active()
        ):
            self.btn_ruler.setChecked(False)
            self.update_ruler_style(False)
            return

        self.setFocus()
        self.controller.toggle_ruler(self)
        self.update_ruler_style(self.controller.ruler_tool.active)

    def update_label_move_style(self, is_on):
        self.design_tab.btn_label_move.setChecked(is_on)
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_label_move_on(is_on)

    def _safe_cancel_ruler_or_draw(self):
        """ESC 키: 눈금자 측정 중단 또는 그리기 도구 취소"""
        if self._is_input_focused():
            return
        if getattr(self, "btn_draw", None) and self.btn_draw.isChecked():
            if getattr(self, "_draw_tool", None) is not None:
                self._draw_tool.cancel()
            return
        if hasattr(self.controller, "ruler_tool") and self.controller.ruler_tool.active:
            self.controller.ruler_tool._cancel_current_drawing()

    def _safe_toggle_design_lock(self):
        """L 키: 디자인 설정 유지 토글"""
        if self._is_input_focused():
            return
        if hasattr(self, "design_tab") and hasattr(self.design_tab, "btn_lock"):
            self.design_tab.btn_lock.setChecked(
                not self.design_tab.btn_lock.isChecked()
            )

    def _safe_switch_to_tab(self, index):
        """A/D 키: 탭 전환"""
        if self._is_input_focused():
            return
        if hasattr(self, "tab_widget") and self.tab_widget.currentIndex() != index:
            self.tab_widget.setCurrentIndex(index)

    def _safe_toggle_bold(self):
        """Ctrl+B: 굵게 토글"""
        if self._is_input_focused():
            return
        if hasattr(self, "design_tab") and hasattr(self.design_tab, "btn_bold"):
            # PlotPopup 방식 (단일 버튼)
            self.design_tab.btn_bold.setChecked(
                not self.design_tab.btn_bold.isChecked()
            )

    def _safe_toggle_italic(self):
        """Ctrl+I: 기울임 토글"""
        if self._is_input_focused():
            return
        if hasattr(self, "design_tab") and hasattr(self.design_tab, "btn_italic"):
            # PlotPopup 방식 (단일 버튼)
            self.design_tab.btn_italic.setChecked(
                not self.design_tab.btn_italic.isChecked()
            )

    def _toggle_panels_visibility(self):
        """Tab 키: 패널 가시성 토글 (자식 개별 구현)"""
        pass

    def _safe_nav_prev(self):
        """Left 키 (PlotPopup 전용)"""
        pass

    def _safe_nav_next(self):
        """Right 키 (PlotPopup 전용)"""
        pass

    def _safe_batch_save(self):
        """Ctrl+Shift+S (PlotPopup 전용)"""
        pass

    def _safe_compare_click(self):
        """M 키 (PlotPopup 전용)"""
        pass

    def _safe_toggle_label_move(self):
        """T 키: 라벨 이동 모드 토글"""
        if self._is_input_focused():
            return
        if hasattr(self, "design_tab") and hasattr(self.design_tab, "btn_label_move"):
            self.design_tab.btn_label_move.setChecked(
                not self.design_tab.btn_label_move.isChecked()
            )
            self.controller.toggle_label_move(self)

    def _draw_tool_deactivate(self):
        if getattr(self, "_draw_tool", None) is not None:
            try:
                self._draw_tool.deactivate()
            except Exception:
                pass
            self._draw_tool = None
        if getattr(self, "canvas", None) is not None:
            self.canvas.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _on_toggle_draw(self):
        # 버튼 직접 클릭으로 진입했을 때도 배타 모드를 강제한다.
        if self.btn_draw.isChecked() and (
            self._is_ruler_active() or self._is_label_move_active()
        ):
            self.btn_draw.setChecked(False)
            if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
                self.tool_indicator.set_draw_mode_on(False)
            return
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_draw_mode_on(self.btn_draw.isChecked())
        draw_on = self.btn_draw.isChecked()
        for sc in (
            getattr(self, "_shortcut_draw_return", None),
            getattr(self, "_shortcut_draw_enter", None),
        ):
            if sc is not None:
                sc.setEnabled(draw_on)
        if draw_on:
            self.draw_indicator.show()
            self.draw_indicator.set_mode(None)
            # 인디케이터가 키보드 포커스를 갖지 않도록 캔버스 또는 메인 창으로 포커스 이동
            if getattr(self, "canvas", None) is not None:
                self.canvas.setFocus()
            else:
                self.setFocus()
            app_logger.info(config.LOG_MSG["DRAW_ON"])
        else:
            self._draw_tool_deactivate()
            self.draw_indicator.hide()
            app_logger.info(config.LOG_MSG["DRAW_OFF_INFO"])

    def _get_current_draw_objects(self):
        """현재 파일 인덱스에 해당하는 그리기 객체 리스트 (파일별 분리)."""
        idx = getattr(self, "current_idx", None)
        if (
            idx is None
            and hasattr(self, "controller")
            and hasattr(self.controller, "get_current_index")
        ):
            idx = self.controller.get_current_index()
        if idx is None:
            idx = 0
        return getattr(self, "_draw_objects_by_file", {}).setdefault(idx, [])

    def _set_current_draw_objects(self, lst):
        """현재 파일의 그리기 객체 리스트를 교체."""
        idx = getattr(self, "current_idx", None)
        if (
            idx is None
            and hasattr(self, "controller")
            and hasattr(self.controller, "get_current_index")
        ):
            idx = self.controller.get_current_index()
        if idx is None:
            idx = 0
        if not hasattr(self, "_draw_objects_by_file"):
            self._draw_objects_by_file = {}
        self._draw_objects_by_file[idx] = list(lst)

    def _on_draw_object_complete(self, obj):
        objs = self._get_current_draw_objects()
        if getattr(obj, "type", "") == "text" and not getattr(obj, "name", ""):
            n = sum(1 for o in objs if getattr(o, "type", "") == "text") + 1
            obj.name = f"텍스트 {n}"
        objs.append(obj)
        if (
            getattr(obj, "type", "") == "polygon"
            and getattr(obj, "points", None)
            and len(obj.points) >= 3
            and getattr(obj, "id", "")
            and getattr(obj, "show_area_label", False)
        ):
            area = polygon_area(obj.points)
            xs = [p[0] for p in obj.points]
            ys = [p[1] for p in obj.points]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            area_label = AreaLabelObject(
                parent_id=obj.id,
                value=area,
                x=cx,
                y=cy,
                axis_units=getattr(obj, "axis_units", "Hz"),
                visible=obj.visible,
                locked=obj.locked,
                semi=obj.semi,
            )
            objs.append(area_label)
        self._set_current_draw_objects(objs)
        self._redraw_draw_layer()
        if (
            hasattr(self, "_layer_dock_content")
            and self._layer_dock_content is not None
        ):
            self._layer_dock_content.update_draw_layer_list(
                self._get_current_draw_objects()
            )
        if self.canvas:
            self.canvas.draw_idle()

    def show_warning(self, title, text):
        QMessageBox.warning(self, title, text)

    def show_critical(self, title, text):
        QMessageBox.critical(self, title, text)

    def is_compare_plot_popup(self) -> bool:
        return (
            getattr(self, "idx_blue", None) is not None
            and getattr(self, "idx_red", None) is not None
        )

    def legend_deletable(self) -> bool:
        return True

    def _refresh_draw_layer_list(self) -> None:
        objs = self._get_current_draw_objects()
        for attr in ("_layer_dock_content", "_layer_dock_blue", "_layer_dock_red"):
            dock = getattr(self, attr, None)
            if dock is not None and hasattr(dock, "update_draw_layer_list"):
                dock.update_draw_layer_list(objs)

    def add_legend_object(self):
        objs = self._get_current_draw_objects()
        if has_legend_object(objs):
            return find_legend_object(objs)
        legend = create_legend_object(self, is_compare=self.is_compare_plot_popup())
        objs.append(legend)
        self._set_current_draw_objects(objs)
        self._selected_legend_id = legend.id
        self._redraw_draw_layer()
        self._refresh_draw_layer_list()
        return legend

    def ensure_legend_object(self):
        if has_legend_object(self._get_current_draw_objects()):
            return find_legend_object(self._get_current_draw_objects())
        return self.add_legend_object()

    def get_legend_object(self):
        return find_legend_object(self._get_current_draw_objects())

    def select_legend_object(self, legend_id: str | None) -> None:
        self._selected_legend_id = legend_id
        if legend_id is not None:
            self._selected_text_id = None
        self._sync_legend_transform_tool()
        self._redraw_draw_layer()

    def select_text_object(self, text_id: str | None) -> None:
        self._selected_text_id = text_id
        if text_id is not None:
            self._selected_legend_id = None
        self._sync_legend_transform_tool()
        self._redraw_draw_layer()

    def _active_draw_layer_dock(self):
        return getattr(self, "_layer_dock_content", None)

    def _find_draw_object_index(self, obj) -> int | None:
        objs = self._get_current_draw_objects()
        obj_id = getattr(obj, "id", None)
        for i, o in enumerate(objs):
            if o is obj:
                return i
            if obj_id and getattr(o, "id", None) == obj_id:
                return i
        return None

    def _focus_draw_text_layer(self, text_obj, *, switch_tab: bool = True) -> None:
        if getattr(text_obj, "type", "") != "text":
            return
        idx = self._find_draw_object_index(text_obj)
        if idx is None:
            return
        dock = self._active_draw_layer_dock()
        if dock is not None and hasattr(dock, "focus_draw_index"):
            dock.focus_draw_index(idx, switch_to_draw_tab=switch_tab)
        self.select_text_object(getattr(text_obj, "id", None))

    def _clear_draw_text_focus(self) -> None:
        dock = self._active_draw_layer_dock()
        if dock is not None and hasattr(dock, "focus_draw_index"):
            dock.focus_draw_index(None)
        self.select_text_object(None)

    def open_legend_text_dialog(self, legend: LegendObject | None = None) -> None:
        target = legend or self.get_legend_object()
        if target is None:
            return
        dlg = LegendTextDialog(
            target,
            ui_font_name=getattr(self, "ui_font_name", "Malgun Gothic"),
            parent=self,
        )
        if dlg.exec():
            dlg.apply_to_legend()
            self._redraw_draw_layer()

    def open_draw_text_dialog(self, text_obj: TextObject | None = None) -> None:
        target = text_obj
        if target is None and self._selected_text_id:
            for obj in self._get_current_draw_objects():
                if (
                    getattr(obj, "type", "") == "text"
                    and getattr(obj, "id", None) == self._selected_text_id
                ):
                    target = obj
                    break
        if target is None:
            return
        dlg = DrawTextDialog(
            initial_text=str(getattr(target, "text", "") or ""),
            ui_font_name=getattr(self, "ui_font_name", "Malgun Gothic"),
            parent=self,
        )
        if dlg.exec():
            dlg.apply_to_text_object(target)
            self._redraw_draw_layer()
            self._refresh_draw_layer_list()

    def _sync_legend_transform_tool(self) -> None:
        if not self.figure.axes:
            return
        ax = self.figure.axes[0]
        legend = None
        if self._selected_legend_id:
            for obj in self._get_current_draw_objects():
                if (
                    getattr(obj, "type", "") == "legend"
                    and getattr(obj, "id", None) == self._selected_legend_id
                ):
                    legend = obj
                    break
        if self._legend_transform_tool is None:
            self._legend_transform_tool = TransformBoxTool(
                self.canvas,
                ax,
                on_changed=self._on_legend_transform_changed,
            )
        else:
            self._legend_transform_tool.ax = ax
        self._legend_transform_tool.set_target(legend)
        if legend is not None and not getattr(legend, "locked", False):
            self._legend_transform_tool.activate()
        else:
            self._legend_transform_tool.deactivate()

    def _on_legend_transform_changed(self) -> None:
        self._redraw_draw_layer()

    def _text_hit_at_px(self, x_px, y_px, pad_px=14):
        refs = getattr(self, "_draw_layer_text_refs", []) or []
        if not self.canvas or not refs:
            return None
        try:
            renderer = self.canvas.get_renderer()
        except Exception:
            renderer = None
        if renderer is None:
            return None
        for arts, obj, _bounds in refs:
            if getattr(obj, "type", "") != "text":
                continue
            art_list = arts if isinstance(arts, list) else [arts]
            for art in art_list:
                try:
                    bbox = art.get_window_extent(renderer)
                    x0, x1 = (
                        min(bbox.x0, bbox.x1) - pad_px,
                        max(bbox.x0, bbox.x1) + pad_px,
                    )
                    y0, y1 = (
                        min(bbox.y0, bbox.y1) - pad_px,
                        max(bbox.y0, bbox.y1) + pad_px,
                    )
                    if x0 <= x_px <= x1 and y0 <= y_px <= y1:
                        return obj
                except Exception:
                    continue
        return None

    def _is_text_focused(self, obj) -> bool:
        text_id = getattr(obj, "id", None)
        if not text_id or text_id != getattr(self, "_selected_text_id", None):
            return False
        dock = self._active_draw_layer_dock()
        if dock is None:
            return False
        sel = getattr(dock, "_selected_draw_indices", set())
        if len(sel) != 1:
            return False
        objs = self._get_current_draw_objects()
        sel_idx = next(iter(sel))
        if not (0 <= sel_idx < len(objs)):
            return False
        sel_obj = objs[sel_idx]
        return (
            getattr(sel_obj, "type", "") == "text"
            and getattr(sel_obj, "id", None) == text_id
        )

    def _ensure_text_drag_connected(self):
        if getattr(self, "_text_drag_cids", None) is not None:
            return
        if not getattr(self, "canvas", None):
            return
        c = self.canvas
        try:
            cid_bp = c.mpl_connect("button_press_event", self._on_canvas_text_press)
            cid_mv = c.mpl_connect("motion_notify_event", self._on_canvas_text_move)
            cid_br = c.mpl_connect("button_release_event", self._on_canvas_text_release)
            self._text_drag_cids = (cid_bp, cid_mv, cid_br)
            self._dragging_text_obj = None
            self._text_cursor_changed = False
        except Exception:
            self._text_drag_cids = ()

    def _on_canvas_text_press(self, event):
        if getattr(event, "dblclick", False):
            return
        if event.button != 1:
            return
        hit = self._text_hit_at_px(event.x, event.y)
        if hit is not None:
            self._focus_draw_text_layer(hit)
            if (
                not getattr(hit, "locked", False)
                and event.inaxes is not None
                and event.xdata is not None
                and event.ydata is not None
            ):
                self._dragging_text_obj = hit
                self._text_drag_offset = (
                    float(hit.x) - float(event.xdata),
                    float(hit.y) - float(event.ydata),
                )
            return
        if event.inaxes is not None:
            self._clear_draw_text_focus()

    def _on_canvas_text_move(self, event):
        obj = getattr(self, "_dragging_text_obj", None)
        if obj is not None:
            if (
                event.inaxes is not None
                and event.xdata is not None
                and event.ydata is not None
            ):
                ox, oy = getattr(self, "_text_drag_offset", (0.0, 0.0))
                obj.x = float(event.xdata) + ox
                obj.y = float(event.ydata) + oy
                self._redraw_draw_layer()
            return
        hit = (
            self._text_hit_at_px(event.x, event.y) if event.inaxes is not None else None
        )
        try:
            if hit is not None and not getattr(hit, "locked", False):
                cursor = (
                    Qt.CursorShape.SizeAllCursor
                    if self._is_text_focused(hit)
                    else Qt.CursorShape.PointingHandCursor
                )
                if not getattr(self, "_text_cursor_changed", False):
                    self.canvas.setCursor(cursor)
                    self._text_cursor_changed = True
                elif getattr(self, "_text_hover_cursor", None) != cursor:
                    self.canvas.setCursor(cursor)
                self._text_hover_cursor = cursor
            elif getattr(self, "_text_cursor_changed", False):
                self.canvas.unsetCursor()
                self._text_cursor_changed = False
                self._text_hover_cursor = None
        except Exception:
            pass

    def _on_canvas_text_release(self, event):
        if getattr(self, "_dragging_text_obj", None) is not None:
            self._dragging_text_obj = None
            self._text_drag_offset = (0.0, 0.0)
        if getattr(self, "_text_cursor_changed", False):
            try:
                self.canvas.unsetCursor()
            except Exception:
                pass
            self._text_cursor_changed = False
            self._text_hover_cursor = None

    def begin_export_render(self) -> None:
        """이미지 저장 등 내보내기 직전: 편집 UI(선택 핸들 등)를 숨긴다."""
        self._export_render_depth = getattr(self, "_export_render_depth", 0) + 1
        if self._export_render_depth == 1:
            self._redraw_draw_layer()
            if self.canvas:
                self.canvas.draw()

    def end_export_render(self) -> None:
        """내보내기 완료 후 편집 UI 복원."""
        depth = getattr(self, "_export_render_depth", 0)
        self._export_render_depth = max(0, depth - 1)
        if self._export_render_depth == 0:
            self._redraw_draw_layer()
            if self.canvas:
                self.canvas.draw_idle()

    def _show_editor_chrome(self) -> bool:
        return getattr(self, "_export_render_depth", 0) == 0

    def _redraw_draw_layer(self):
        if not self.figure.axes:
            return
        ax = self.figure.axes[0]
        for a in getattr(self, "_draw_layer_artists", []):
            try:
                a.remove()
            except Exception:
                pass
        self._draw_layer_artists = []
        self._draw_layer_area_label_refs = []
        self._draw_layer_text_refs = []
        self._draw_layer_artists = render_draw_objects(
            ax,
            self._get_current_draw_objects(),
            self,
            show_editor_chrome=self._show_editor_chrome(),
            selected_legend_id=getattr(self, "_selected_legend_id", None),
            selected_text_id=getattr(self, "_selected_text_id", None),
            area_label_refs=self._draw_layer_area_label_refs,
            text_layer_refs=self._draw_layer_text_refs,
        )
        self._sync_legend_transform_tool()
        if self.canvas:
            self._ensure_area_label_drag_connected()
            self._ensure_text_drag_connected()
            self.canvas.draw_idle()

    def _on_draw_mode_changed(self, mode):
        if mode is None:
            self._draw_tool_deactivate()
            return
        if self._is_ruler_active():
            self.controller.toggle_ruler(self)
        if self._is_label_move_active():
            self.controller.toggle_label_move(self)
        ax = self.figure.axes[0] if self.figure.axes else None
        snapping_data = getattr(self, "snapping_data", None) or []
        # Scale과 Unit 완전 분리: 그리기 도구에는 실제 눈금 단위(Unit)만 전달. 스케일이 Bark여도 단위가 Hz면 Hz.
        params = getattr(self, "fixed_plot_params", None) or {}
        if params.get("normalization"):
            x_unit = y_unit = "norm"
        else:
            x_unit = (params.get("f2_unit") or "Hz").strip()
            y_unit = (params.get("f1_unit") or "Hz").strip()
        x_scale = (params.get("f2_scale") or "linear").strip().lower()
        y_scale = (params.get("f1_scale") or "linear").strip().lower()
        norm = getattr(self, "normalization", None) or params.get("normalization")
        if norm:
            ptype = params.get("type") or "f1_f2"
            x_name = PlotEngine.normalized_x_axis_label(ptype)
            y_name = "nF1"
        else:
            x_name = getattr(self, "x_axis_label", None) or "F2"
            y_name = "F1"
        if ax is None:
            return
        self._draw_tool_deactivate()
        # font_style 읽기: popup_plot은 flat dict, compare_plot은 nested {"common": {...}, ...}
        font_family = ["DejaVu Sans", "Malgun Gothic"]
        ds = getattr(self, "design_settings", None) or {}
        font_style = (
            ds.get("font_style")  # popup_plot: flat
            or (ds.get("common") or {}).get("font_style")  # compare_plot: nested
        )
        if font_style == "serif":
            font_family = ["Times New Roman", "Noto Serif KR", "DejaVu Serif"]

        def _on_draw_cancel():
            self.draw_indicator.set_mode(None)

        if mode == DrawMode.LINE:
            self._draw_tool = draw_line.DrawLineTool(
                self.canvas,
                ax,
                snapping_data,
                axis_units=y_unit,
                on_complete=self._on_draw_object_complete,
                on_cancel=_on_draw_cancel,
                font_family=["DejaVu Sans", "Malgun Gothic"],
            )
        elif mode == DrawMode.POLYGON:
            self._draw_tool = draw_polygon.DrawPolygonTool(
                self.canvas,
                ax,
                snapping_data,
                axis_units=y_unit,
                on_complete=self._on_draw_object_complete,
                on_cancel=_on_draw_cancel,
                font_family=["DejaVu Sans", "Malgun Gothic"],
            )
        elif mode == DrawMode.TEXT:
            self._draw_tool = draw_text.DrawTextTool(
                self.canvas,
                ax,
                axis_units=y_unit,
                parent_window=self,
                ui_font_name=getattr(self, "ui_font_name", "Malgun Gothic"),
                hit_text_at=self._text_hit_at_px,
                on_complete=self._on_draw_object_complete,
                on_cancel=_on_draw_cancel,
            )
        elif mode in (DrawMode.REF_H, DrawMode.REF_V):
            self._draw_tool = draw_reference.DrawReferenceTool(
                self.canvas,
                ax,
                horizontal=(mode == DrawMode.REF_H),
                snapping_data=snapping_data,
                x_unit=x_unit,
                y_unit=y_unit,
                x_scale=x_scale,
                y_scale=y_scale,
                x_name=x_name,
                y_name=y_name,
                on_complete=self._on_draw_object_complete,
                on_cancel=_on_draw_cancel,
                font_family=font_family,
                tick_color="#303133",
                normalization=norm,
            )
        else:
            return
        self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.canvas.setFocus()
        self._draw_tool.activate()

    def _on_download_plot(self, checked, fmt):
        if self._is_input_focused():
            return
        initial_path, _ = self.controller.get_default_save_path(fmt, self)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"플롯 이미지 저장({fmt.upper()})",
            initial_path,
            f"{fmt.upper()} Image (*.{fmt})",
        )
        if file_path:
            try:
                self.controller.save_plot_to_file(self.figure, file_path, fmt, self)
                QMessageBox.information(
                    self, "저장 완료", "이미지가 성공적으로 저장되었습니다."
                )
            except Exception as e:
                import traceback

                traceback.print_exc()
                QMessageBox.critical(
                    self, "저장 실패", f"저장 중 오류가 발생했습니다:\n{e}"
                )

    def _rebind_draw_tool_if_active(self):
        if not getattr(self, "btn_draw", None) or not self.btn_draw.isChecked():
            return
        if not getattr(self, "draw_indicator", None):
            return
        mode = self.draw_indicator.get_mode()
        if mode is None:
            return
        self._on_draw_mode_changed(mode)

    def _apply_normalization_axis_ui(self, reset_ranges=False):
        """정규화 플롯일 때 좌표축 레이블/단위/범위 적용. Gerstman만 읽기 전용."""
        norm = getattr(self, "normalization", None)
        if hasattr(self, "norm_section_widget"):
            self.norm_section_widget.setVisible(False)
        if hasattr(self, "lbl_norm_value"):
            self.lbl_norm_value.setText(norm or "없음")
        if not getattr(self, "range_widgets", None):
            return
        if not norm:
            params = getattr(self, "fixed_plot_params", None) or {}
            if hasattr(self, "lbl_f1_axis"):
                self.lbl_f1_axis.setText("F1:")
            if hasattr(self, "lbl_x_axis"):
                ptype = params.get("type", "f1_f2")

                x_names = {
                    "f1_f2": "F2",
                    "f1_f3": "F3",
                    "f1_f2_prime": "F2'",
                    "f1_f2_minus_f1": "F2 - F1",
                    "f1_f2_prime_minus_f1": "F2' - F1",
                }
                self.x_axis_label = x_names.get(ptype, "F2")
                self.lbl_x_axis.setText(f"{self.x_axis_label}:")
            use_bark = params.get("use_bark_units", False)
            f1_scale = params.get("f1_scale", "linear")
            f2_scale = params.get("f2_scale", "linear")
            u1 = "Bark" if (f1_scale == "bark" and use_bark) else "Hz"
            u2 = "Bark" if (f2_scale == "bark" and use_bark) else "Hz"
            if hasattr(self, "lbl_f1_unit"):
                self.lbl_f1_unit.setText(f"({u1})")
            if hasattr(self, "lbl_f2_unit"):
                self.lbl_f2_unit.setText(f"({u2})")
            for key in ["y_min", "y_max", "x_min", "x_max"]:
                self.range_widgets[key].setReadOnly(False)
            return
        r = PlotEngine.NORM_RANGES.get(norm, PlotEngine.NORM_RANGES["Lobanov"])
        if hasattr(self, "lbl_f1_axis"):
            self.lbl_f1_axis.setText("nF1:")
        if hasattr(self, "lbl_x_axis"):
            ptype = (getattr(self, "fixed_plot_params", None) or {}).get(
                "type", "f1_f2"
            )
            self.x_axis_label = PlotEngine.normalized_x_axis_label(ptype)
            self.lbl_x_axis.setText(f"{self.x_axis_label}:")
        if hasattr(self, "lbl_f1_unit"):
            self.lbl_f1_unit.setText("")
        if hasattr(self, "lbl_f2_unit"):
            self.lbl_f2_unit.setText("")
        r = PlotEngine.NORM_RANGES.get(norm, PlotEngine.NORM_RANGES["Lobanov"])
        if reset_ranges:
            for key in ["y_min", "y_max", "x_min", "x_max"]:
                self.range_widgets[key].setText(str(r[key]))
        for key in ["y_min", "y_max", "x_min", "x_max"]:
            self.range_widgets[key].setReadOnly(norm == "Gerstman")

    def update_unit_labels(self, f1_unit, f2_unit=None):
        if f2_unit is None:
            f2_unit = f1_unit

        self.lbl_f1_axis.setText("F1:")
        self.lbl_x_axis.setText(f"{self.x_axis_label}:")

        self.lbl_f1_unit.setText(f"({f1_unit})")
        self.lbl_f2_unit.setText(f"({f2_unit})")

    def update_x_label(self, new_label):
        self.x_axis_label = new_label
        self.lbl_x_axis.setText(f"{new_label}:")

    def update_ruler_style(self, is_on):
        self.btn_ruler.setChecked(is_on)
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_ruler_on(is_on)
        if is_on and getattr(self, "btn_draw", None) and self.btn_draw.isChecked():
            self.btn_draw.setChecked(False)
            if hasattr(self, "draw_indicator") and self.draw_indicator is not None:
                self.draw_indicator.hide()
            self._draw_tool_deactivate()
