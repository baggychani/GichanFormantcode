# ruff: noqa: F821

def closeEvent(self, event):
        if self.controller.ruler_tool.active:
            self.controller.toggle_ruler(self)
        if getattr(self, "btn_draw", None) and self.btn_draw.isChecked():
            self.btn_draw.setChecked(False)
        self._draw_tool_deactivate()
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
            if hasattr(self, "layer_dock_widget") and self.layer_dock_widget:
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
        QShortcut(
            QKeySequence(Qt.Key.Key_R), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_ruler)
        QShortcut(
            QKeySequence(Qt.Key.Key_P), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_draw)
        QShortcut(
            QKeySequence(Qt.Key.Key_1), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.LINE))
        QShortcut(
            QKeySequence(Qt.Key.Key_2), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.POLYGON))
        QShortcut(
            QKeySequence(Qt.Key.Key_3), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.REF_H))
        QShortcut(
            QKeySequence(Qt.Key.Key_4), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(lambda: self._safe_set_draw_mode(DrawMode.REF_V))
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(
            lambda: self._on_download_plot(False, "jpg")
        )
        QShortcut(
            QKeySequence("Esc"), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_cancel_ruler_point)
        QShortcut(
            QKeySequence(Qt.Key.Key_Return),
            self,
            context=Qt.ShortcutContext.WindowShortcut,
        ).activated.connect(self._safe_draw_complete)
        QShortcut(
            QKeySequence(Qt.Key.Key_Enter),
            self,
            context=Qt.ShortcutContext.WindowShortcut,
        ).activated.connect(self._safe_draw_complete)
        QShortcut(
            QKeySequence(QKeySequence.StandardKey.Undo),
            self,
            context=Qt.ShortcutContext.WindowShortcut,
        ).activated.connect(self._safe_draw_rollback)
        QShortcut(
            QKeySequence("Ctrl+B"), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_bold)
        QShortcut(
            QKeySequence("Ctrl+I"), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_italic)

def _on_draw_object_complete(self, obj):
        setattr(obj, "series", self._active_draw_series)
        if hasattr(obj, "point_labels"):
            obj.point_labels = self._normalize_compare_point_labels(
                getattr(obj, "point_labels", None) or []
            )
        objs = self._get_current_draw_objects()
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
            setattr(area_label, "series", self._active_draw_series)
            objs.append(area_label)

        self._redraw_draw_layer()
        if hasattr(self, "_layer_dock_blue") and self._layer_dock_blue is not None:
            self._layer_dock_blue.update_draw_layer_list(
                self._get_current_draw_objects()
            )
        if hasattr(self, "_layer_dock_red") and self._layer_dock_red is not None:
            self._layer_dock_red.update_draw_layer_list(
                self._get_current_draw_objects()
            )
        if self.canvas:
            self.canvas.draw_idle()

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