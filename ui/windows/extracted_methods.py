# ruff: noqa: F821

def _apply_pyqt6_icon(self):
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
        return isinstance(QApplication.focusWidget(), QLineEdit)

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
        QShortcut(
            QKeySequence(Qt.Key.Key_T), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_label_move)
        QShortcut(
            QKeySequence(Qt.Key.Key_M), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_compare_click)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(
            lambda: self._on_download_plot(False, "jpg")
        )

        QShortcut(
            QKeySequence("Esc"), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_cancel_ruler_or_draw)
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
            QKeySequence(Qt.Key.Key_P), self, context=Qt.ShortcutContext.WindowShortcut
        ).activated.connect(self._safe_toggle_draw)
        # 그리기 모드에서 도구 선택: 1=선, 2=영역, 3=수평 참조선, 4=수직 참조선
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
        """숫자 키(1~4)로 그리기 도구를 선택. 그리기 모드가 꺼져 있으면 무시."""
        if self._is_input_focused():
            return
        if not (getattr(self, "btn_draw", None) and self.btn_draw.isChecked()):
            return
        if hasattr(self, "draw_indicator") and self.draw_indicator is not None:
            # 인디케이터 버튼 체크 상태를 바꾸고, 실제 도구도 즉시 교체
            self.draw_indicator.set_mode(mode)
        # DrawModeIndicator.set_mode는 mode_changed를 emit하지 않으므로, 직접 도구를 교체해 준다.
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

def update_label_move_style(self, is_on):
        self.design_tab.btn_label_move.setChecked(is_on)
        self.design_tab.btn_label_move.setStyleSheet(
            "QPushButton#BtnLabelMove { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #333;} "
            "QPushButton#BtnLabelMove:checked { background-color: #E6A23C; color: white; font-weight: bold; border: none; }"
        )
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_label_move_on(is_on)

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
        if self.btn_draw.isChecked():
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

def _redraw_draw_layer(self):
        if not self.figure.axes:
            return
        ax = self.figure.axes[0]
        # 이전 그리기 레이어 아티스트 제거 (삭제/파일 전환 시 화면에서 사라지도록)
        for a in getattr(self, "_draw_layer_artists", []):
            try:
                a.remove()
            except Exception:
                pass
        self._draw_layer_artists = []
        self._draw_layer_area_label_refs = []

        def _line_style_to_mpl(s):
            """'-' | '---' | '--' -> matplotlib linestyle.

            신뢰타원(engine.plot_engine._to_mpl_linestyle)과 동일한 철학:
            - '---' : 긴 대시 (6pt dash, 3pt gap)
            - '--'  : Matplotlib 기본 dashed
            - '-'   : 실선
            """
            if s == "---":
                # 긴 점선: 신뢰타원과 동일하게 커스텀 긴 대시 패턴
                return (0, (6.0, 3.0))
            # 나머지는 Matplotlib 표준 스타일에 그대로 위임
            if s in ("-", "--", ":"):
                return s
            # 알 수 없는 값이면 짧은 점선과 동일하게 처리
            return "--"

        def _is_serif_font():
            ds = getattr(self, "design_settings", None) or {}
            if not isinstance(ds, dict):
                return False
            if ds.get("font_style") == "serif":
                return True
            common = ds.get("common", {})
            return isinstance(common, dict) and common.get("font_style") == "serif"

        for obj in self._get_current_draw_objects():
            if not getattr(obj, "visible", True):
                continue
            # semi: 확정 객체도 반투명 표시 (선/외곽선만 알파 조정)
            is_semi = getattr(obj, "semi", False)
            line_alpha = 0.5 if is_semi else 0.9
            try:
                if getattr(obj, "type", None) == "line" and hasattr(obj, "points"):
                    xs = [p[0] for p in obj.points]
                    ys = [p[1] for p in obj.points]
                    style = getattr(obj, "line_style", "-") or "-"
                    color_hex = getattr(obj, "line_color", "#000000") or "#000000"
                    rgba_color = mcolors.to_rgba(color_hex, float(line_alpha))
                    linewidth = 1.0
                    (line,) = ax.plot(
                        xs,
                        ys,
                        linestyle=_line_style_to_mpl(style),
                        color=rgba_color,
                        linewidth=linewidth,
                        zorder=1,
                        clip_on=False,
                    )
                    self._draw_layer_artists.append(line)

                    # 화살표 그리기 (arrow_mode, arrow_head에 따라)
                    arrow_mode = getattr(obj, "arrow_mode", "none") or "none"
                    arrow_head = getattr(obj, "arrow_head", "stealth") or "stealth"
                    if arrow_mode != "none" and len(obj.points) >= 2:
                        from matplotlib.patches import Polygon as MplPolygon

                        arrow_z = 4.0  # 선(z=1)은 아래 유지, centroid(z=3) 위 / 라벨(z=100) 아래

                        def _add_arrow(p_start, p_end):
                            # 기존 선 스타일(실선/점선)을 보존하기 위해 shaft를 덧그리지 않고,
                            # 끝점 근처에 head만 별도 렌더링한다.
                            # 화살촉 왜곡을 막기 위해 화면(px) 좌표에서 head를 만든 뒤 data 좌표로 역변환한다.
                            x0, y0 = float(p_start[0]), float(p_start[1])
                            x1, y1 = float(p_end[0]), float(p_end[1])
                            disp0 = ax.transData.transform((x0, y0))
                            disp1 = ax.transData.transform((x1, y1))
                            dx, dy = (
                                float(disp1[0] - disp0[0]),
                                float(disp1[1] - disp0[1]),
                            )
                            seg_len_px = (dx * dx + dy * dy) ** 0.5
                            if seg_len_px <= 1e-6:
                                return

                            ux, uy = dx / seg_len_px, dy / seg_len_px
                            px, py = -uy, ux  # 수직 단위벡터

                            # px 단위 head 크기: 선 두께 비례 + 최소 보장
                            head_len = max(12.0, 8.0 * max(linewidth, 1.0))
                            head_len = min(head_len, seg_len_px * 0.7)
                            head_w = head_len * 0.78

                            tx, ty = float(disp1[0]), float(disp1[1])
                            bx, by = tx - ux * head_len, ty - uy * head_len
                            lx, ly = bx + px * head_w * 0.5, by + py * head_w * 0.5
                            rx, ry = bx - px * head_w * 0.5, by - py * head_w * 0.5

                            inv = ax.transData.inverted().transform
                            tip_d = tuple(inv((tx, ty)))
                            left_d = tuple(inv((lx, ly)))
                            right_d = tuple(inv((rx, ry)))

                            if arrow_head == "open":
                                # Open head: V자 head 두 선만 그림
                                (l1,) = ax.plot(
                                    [tip_d[0], left_d[0]],
                                    [tip_d[1], left_d[1]],
                                    color=rgba_color,
                                    linewidth=max(0.9, linewidth * 0.9),
                                    zorder=arrow_z,
                                    clip_on=False,
                                )
                                (l2,) = ax.plot(
                                    [tip_d[0], right_d[0]],
                                    [tip_d[1], right_d[1]],
                                    color=rgba_color,
                                    linewidth=max(0.9, linewidth * 0.9),
                                    zorder=arrow_z,
                                    clip_on=False,
                                )
                                self._draw_layer_artists.extend([l1, l2])
                            elif arrow_head == "latex":
                                # Latex head: 꽉 찬 3점 이등변 삼각형
                                poly = MplPolygon(
                                    [tip_d, left_d, right_d],
                                    closed=True,
                                    facecolor=rgba_color,
                                    edgecolor=rgba_color,
                                    linewidth=max(0.5, linewidth * 0.5),
                                    zorder=arrow_z,
                                    clip_on=False,
                                )
                                ax.add_patch(poly)
                                self._draw_layer_artists.append(poly)
                            else:
                                # Stealth head: latex 삼각형 기반 + 꼬리 중앙 안쪽 indent
                                indent = head_len * (3.6 / 8.5)
                                mx, my = bx + ux * indent, by + uy * indent
                                mid_d = tuple(inv((mx, my)))
                                poly = MplPolygon(
                                    [tip_d, left_d, mid_d, right_d],
                                    closed=True,
                                    facecolor=rgba_color,
                                    edgecolor=rgba_color,
                                    linewidth=max(0.5, linewidth * 0.5),
                                    zorder=arrow_z,
                                    clip_on=False,
                                )
                                ax.add_patch(poly)
                                self._draw_layer_artists.append(poly)

                        pts = obj.points
                        if arrow_mode == "end":
                            _add_arrow(pts[-2], pts[-1])
                        elif arrow_mode == "all":
                            for j in range(len(pts) - 1):
                                _add_arrow(pts[j], pts[j + 1])
                elif getattr(obj, "type", None) == "polygon" and hasattr(obj, "points"):
                    from matplotlib.patches import Polygon as MplPolygon

                    # semi: 내부·테두리 모두 반투명, 확정 외곽선은 진하게
                    face_alpha = 0.15 if not is_semi else 0.06
                    edge_alpha = 1.0 if not is_semi else 0.4

                    border_style = getattr(obj, "border_style", "-") or "-"
                    border_hex = getattr(obj, "border_color", "#000000") or "#000000"
                    fill_hex = getattr(obj, "fill_color", "#3366CC") or "#3366CC"

                    if str(fill_hex).lower() == "transparent":
                        face_rgba = (0.0, 0.0, 0.0, 0.0)
                    else:
                        face_rgba = mcolors.to_rgba(fill_hex, float(face_alpha))
                    edge_rgba = mcolors.to_rgba(border_hex, float(edge_alpha))

                    poly = MplPolygon(
                        obj.points,
                        facecolor=face_rgba,
                        edgecolor=edge_rgba,
                        linestyle=_line_style_to_mpl(border_style),
                        linewidth=1.0,
                        zorder=1,
                    )
                    ax.add_patch(poly)
                    self._draw_layer_artists.append(poly)
                elif getattr(obj, "type", None) == "reference" and hasattr(obj, "mode"):
                    # 참조선은 아래 별도 루프에서 그림
                    pass
                elif getattr(obj, "type", None) == "area_label":
                    # 넓이 텍스트: 값/좌표가 잘못되어도 전체 루프가 죽지 않도록 try 블록 안에서 처리
                    v = getattr(obj, "value", 0)
                    u = (getattr(obj, "axis_units", "Hz") or "Hz").strip().lower()
                    if u == "norm" or "norm" in u:
                        txt = f"{v:.2f}"
                    else:
                        txt = str(int(round(v)))
                    font_family = ["DejaVu Sans", "Malgun Gothic"]
                    if _is_serif_font():
                        font_family = [
                            "Times New Roman",
                            "Noto Serif KR",
                            "DejaVu Serif",
                        ]
                    text_alpha = 0.3 if getattr(obj, "semi", False) else 1.0
                    txt_artist = ax.text(
                        getattr(obj, "x", 0),
                        getattr(obj, "y", 0),
                        txt,
                        fontsize=10,
                        fontfamily=font_family,
                        color="#303133",
                        alpha=text_alpha,
                        va="center",
                        ha="center",
                        zorder=2,
                        clip_on=True,
                    )
                    self._draw_layer_artists.append(txt_artist)
                    self._draw_layer_area_label_refs.append((txt_artist, obj))
            except Exception:
                # 한 객체에서 에러가 나더라도 나머지 객체는 계속 그리도록 방어
                continue

        # 참조선은 별도 루프에서 기존 로직 유지 (가독성을 위해 위 try/except에서 분리)
        for obj in self._get_current_draw_objects():
            if not getattr(obj, "visible", True):
                continue
            if getattr(obj, "type", None) != "reference" or not hasattr(obj, "mode"):
                continue

            from draw.draw_reference import (
                REF_LINE_COLOR,
                REF_LINE_ALPHA,
                format_ref_label,
            )

            xlim, ylim = ax.get_xlim(), ax.get_ylim()
            v = obj.value  # 단위(Unit) 기준 순수 데이터 값 (Hz 등)
            axis_units = getattr(obj, "axis_units", "") or "Hz"
            axis_scale = getattr(obj, "axis_scale", "linear")
            if axis_scale == "bark" and (axis_units or "").strip().lower() == "hz":
                plot_v = float(hz_to_bark(v))
            else:
                plot_v = v
            lbl = format_ref_label(v, axis_units)
            font_family = ["DejaVu Sans", "Malgun Gothic"]
            if _is_serif_font():
                font_family = ["Times New Roman", "Noto Serif KR", "DejaVu Serif"]
            style = getattr(obj, "line_style", "-") or "-"
            color_override = getattr(obj, "line_color", None)
            base_color = color_override or REF_LINE_COLOR
            ref_alpha = 0.3 if getattr(obj, "semi", False) else REF_LINE_ALPHA
            rgba_line = mcolors.to_rgba(base_color, float(ref_alpha))
            text_alpha = 0.3 if getattr(obj, "semi", False) else 1.0
            if obj.mode == "horizontal":
                (ref_line,) = ax.plot(
                    xlim,
                    [plot_v, plot_v],
                    color=rgba_line,
                    linestyle=_line_style_to_mpl(style),
                    linewidth=1,
                    zorder=1.5,
                    clip_on=True,
                )
                ref_txt = ax.text(
                    xlim[0],
                    plot_v,
                    lbl,
                    fontsize=12,
                    fontfamily=font_family,
                    color="#303133",
                    alpha=text_alpha,
                    va="center",
                    zorder=2,
                    clip_on=False,
                )
                self._draw_layer_artists.append(ref_line)
                self._draw_layer_artists.append(ref_txt)
            else:
                (ref_line,) = ax.plot(
                    [plot_v, plot_v],
                    ylim,
                    color=rgba_line,
                    linestyle=_line_style_to_mpl(style),
                    linewidth=1,
                    zorder=1.5,
                    clip_on=True,
                )
                ref_txt = ax.text(
                    plot_v,
                    ylim[0],
                    lbl,
                    fontsize=12,
                    fontfamily=font_family,
                    color="#303133",
                    alpha=text_alpha,
                    va="bottom",
                    ha="center",
                    zorder=2,
                    clip_on=False,
                )
                self._draw_layer_artists.append(ref_line)
                self._draw_layer_artists.append(ref_txt)
        if self.canvas:
            self._ensure_area_label_drag_connected()
            self.canvas.draw_idle()

def _on_draw_mode_changed(self, mode):
        if mode is None:
            self._draw_tool_deactivate()
            return
        if self.btn_ruler.isChecked():
            self.controller.toggle_ruler(self)
        if self.design_tab.btn_label_move.isChecked():
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
        x_name = getattr(self, "x_axis_label", None) or "F2"
        y_name = "F1"
        if ax is None:
            return
        self._draw_tool_deactivate()
        font_family = ["DejaVu Sans", "Malgun Gothic"]
        if (
            getattr(self, "design_settings", None)
            and self.design_settings.get("font_style") == "serif"
        ):
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
        self.btn_ruler.setStyleSheet(
            """
            QPushButton#BtnRuler { background-color: #F0F2F5; border: 1px solid #DCDFE6; border-radius: 4px; color: #333; }
            QPushButton#BtnRuler:hover:!checked { background-color: #E4E7ED; border: 1px solid #C0C4CC; }
            QPushButton#BtnRuler:checked { background-color: #67C23A; color: white; font-weight: bold; border: none; }
            """
        )
        if hasattr(self, "tool_indicator") and self.tool_indicator is not None:
            self.tool_indicator.set_ruler_on(is_on)
        if is_on and getattr(self, "btn_draw", None) and self.btn_draw.isChecked():
            self.btn_draw.setChecked(False)
            if hasattr(self, "draw_indicator") and self.draw_indicator is not None:
                self.draw_indicator.hide()
            self._draw_tool_deactivate()