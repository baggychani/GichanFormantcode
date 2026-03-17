from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QButtonGroup,
    QStackedWidget,
    QPushButton,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QCursor

from .design_panel import ToggleSwitch, ColorPalette
from .icon_widgets import LinePreviewButton, create_trajectory_icon


# design_panel / layer_dock 과 동일한 선 스타일 매핑을 사용한다.
_STYLE_ID_TO_VALUE = {0: "-", 1: "---", 2: "--"}  # 실선, 긴 점선, 짧은 점선
_STYLE_VALUE_TO_ID = {"-": 0, "---": 1, "--": 2}


class DrawDesignPanel(QWidget):
    """
    그리기 레이어(선 / 영역 / 참조선) 전용 디자인 패널.

    - 레이어 타입에 따라 완전히 다른 UI 세트를 보여준다.
    - settings_changed(layer_id, settings_dict)를 통해 현재 UI 상태를 외부로 알린다.
    - 실제 캔버스 반영/레이어 생성·삭제 로직은 포함하지 않는다.
    """

    settings_changed = pyqtSignal(str, dict)

    def __init__(self, parent=None, ui_font_name="Malgun Gothic"):
        super().__init__(parent)
        self.ui_font_name = ui_font_name
        self._loading = False
        self._current_layer_id = ""
        self._current_layer_type = None  # "line" | "area" | "reference" | None

        self._setup_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # 내부 UI 생성 유틸
    # ------------------------------------------------------------------
    def _create_line_style_group(self, parent, default_idx: int):
        """
        실선 / 긴 점선 / 짧은 점선 선택용 시각 버튼 그룹을 생성한다.
        반환값: (frame_widget, button_group)
        """
        group = QButtonGroup(parent)

        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; }"
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        # design_panel / layer_dock 의 스타일 정의를 그대로 따른다.
        options = [
            (2.0, Qt.PenStyle.SolidLine, "4px 0 0 4px", "실선"),
            (2.0, Qt.PenStyle.DashLine, "0px", "긴 점선"),
            (2.0, Qt.PenStyle.DotLine, "0 4px 4px 0", "짧은 점선"),
        ]

        for i, opt in enumerate(options):
            w, s, r, tooltip = opt
            btn = LinePreviewButton(
                line_width=w,
                line_style=s,
                radius_css=r,
                tooltip=tooltip,
            )
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            group.addButton(btn, i)
            layout.addWidget(btn)

        if group.button(default_idx) is not None:
            group.button(default_idx).setChecked(True)
        return frame, group

    def _add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #EBEEF5;")
        layout.addWidget(line)

    # ------------------------------------------------------------------
    # 페이지별 UI
    # ------------------------------------------------------------------
    def _build_line_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        font_normal = QFont(self.ui_font_name, 9)

        layout.addWidget(QLabel("선 레이어", font=font_bold))

        # 선 타입
        row_style = QVBoxLayout()
        row_style.setSpacing(4)
        row_style.addWidget(QLabel("선 타입:", font=font_normal))
        frame, group = self._create_line_style_group(page, default_idx=0)
        row_style.addWidget(frame)
        layout.addLayout(row_style)

        # 화살표 타입 (2줄 구성: 1줄=none/end/all, 2줄=stealth/open/latex)
        arrow_mode_layout = QVBoxLayout()
        arrow_mode_layout.setSpacing(4)
        arrow_mode_layout.addWidget(QLabel("화살표 타입:", font=font_normal))
        arrow_mode_frame = QFrame()
        arrow_mode_frame.setStyleSheet(
            "QFrame { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; }"
        )
        arrow_mode_h = QHBoxLayout(arrow_mode_frame)
        arrow_mode_h.setContentsMargins(2, 2, 2, 2)
        arrow_mode_h.setSpacing(0)
        group_arrow_mode = QButtonGroup(self)
        # none / end / all 버튼
        for i, mode in enumerate(["none", "end", "all"]):
            btn = QPushButton()
            btn.setIcon(create_trajectory_icon(arrow_mode=mode, head_style="stealth"))
            btn.setIconSize(QSize(54, 24))
            btn.setToolTip(
                {"none": "화살표 없음", "end": "끝점", "all": "점마다"}[mode]
            )
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(
                "QPushButton { background-color: transparent; border: none; padding: 2px 4px; }"
                "QPushButton:checked { background-color: #ECF5FF; border-radius: 3px; }"
            )
            group_arrow_mode.addButton(btn, i)
            arrow_mode_h.addWidget(btn)
        if group_arrow_mode.button(0) is not None:
            group_arrow_mode.button(0).setChecked(True)
        arrow_mode_layout.addWidget(arrow_mode_frame)

        arrow_head_frame = QFrame()
        arrow_head_frame.setStyleSheet(
            "QFrame { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; }"
        )
        arrow_head_h = QHBoxLayout(arrow_head_frame)
        arrow_head_h.setContentsMargins(2, 2, 2, 2)
        arrow_head_h.setSpacing(0)
        group_arrow_head = QButtonGroup(self)
        for i, head in enumerate(["stealth", "open", "latex"]):
            btn = QPushButton()
            btn.setIcon(create_trajectory_icon(arrow_mode="end", head_style=head))
            btn.setIconSize(QSize(54, 24))
            btn.setToolTip(
                {"stealth": "stealth", "open": "open", "latex": "latex"}[head]
            )
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(
                "QPushButton { background-color: transparent; border: none; padding: 2px 4px; }"
                "QPushButton:checked { background-color: #ECF5FF; border-radius: 3px; }"
            )
            group_arrow_head.addButton(btn, i)
            arrow_head_h.addWidget(btn)
        if group_arrow_head.button(0) is not None:
            group_arrow_head.button(0).setChecked(True)
        arrow_mode_layout.addWidget(arrow_head_frame)
        layout.addLayout(arrow_mode_layout)

        # 선 색상 (투명 불가)
        color_layout = QVBoxLayout()
        color_layout.setSpacing(6)
        color_layout.addWidget(QLabel("선 색상:", font=font_normal))
        color_picker = ColorPalette(
            default_color="#000000", allow_transparent=False, parent=page
        )
        color_layout.addWidget(color_picker)
        layout.addLayout(color_layout)

        layout.addStretch()

        self._line_controls = {
            "group_style": group,
            "color_picker": color_picker,
            "group_arrow_mode": group_arrow_mode,
            "group_arrow_head": group_arrow_head,
            "arrow_head_frame": arrow_head_frame,
        }
        self._update_line_arrow_head_enabled()
        return page

    def _update_line_arrow_head_enabled(self):
        """arrow_mode가 none이면 화살표 모양 줄을 시각적으로 비활성화."""
        if not hasattr(self, "_line_controls"):
            return
        g_mode = self._line_controls["group_arrow_mode"]
        mode_idx = g_mode.checkedId()
        if mode_idx < 0:
            btn_mode = g_mode.checkedButton()
            mode_idx = g_mode.id(btn_mode) if btn_mode else 0
        mode_val = {0: "none", 1: "end", 2: "all"}.get(mode_idx, "none")
        enabled = mode_val != "none"
        self._line_controls["arrow_head_frame"].setEnabled(enabled)
        # 요구사항: 화살표 X(none)면 모양 줄은 사라지고 클릭 불가
        self._line_controls["arrow_head_frame"].setVisible(enabled)

    def _build_area_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        font_normal = QFont(self.ui_font_name, 9)

        layout.addWidget(QLabel("영역 레이어", font=font_bold))

        # 영역 넓이 표시 라벨 (읽기 전용)
        self._area_value_label = QLabel("영역 넓이 : —", font=font_normal)
        layout.addWidget(self._area_value_label)

        # 넓이 텍스트 레이어 토글 (상단 정보 블록으로 묶어서 들여쓰기)
        info_frame = QFrame()
        # 넓이 텍스트 토글 주변의 얇은 선(테두리)을 없애고 배경만 살린다.
        info_frame.setStyleSheet(
            "QFrame { background-color: #F9FAFB; border: none; border-radius: 0px; }"
        )
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 6, 8, 6)
        info_layout.setSpacing(4)

        row = QHBoxLayout()
        lbl = QLabel("넓이 텍스트 레이어 켜기", font=font_normal)
        # 기본값: OFF
        switch = ToggleSwitch(checked=False)
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(switch)

        info_layout.addLayout(row)
        layout.addWidget(info_frame)

        self._add_separator(layout)

        # 외곽선 타입
        row_style = QVBoxLayout()
        row_style.setSpacing(4)
        row_style.addWidget(QLabel("외곽선 타입:", font=font_normal))
        frame_style, group_style = self._create_line_style_group(page, default_idx=0)
        row_style.addWidget(frame_style)
        layout.addLayout(row_style)

        # 외곽선 색상 (투명 불가)
        border_color_layout = QVBoxLayout()
        border_color_layout.setSpacing(6)
        border_color_layout.addWidget(QLabel("외곽선 색상:", font=font_normal))
        border_color_picker = ColorPalette(
            default_color="#000000", allow_transparent=False, parent=page
        )
        border_color_layout.addWidget(border_color_picker)
        layout.addLayout(border_color_layout)

        # 영역 내부 색상 (투명 허용, 기본값은 실제 폴리곤 기본 색상과 유사한 파란색)
        fill_color_layout = QVBoxLayout()
        fill_color_layout.setSpacing(6)
        fill_color_layout.addWidget(QLabel("영역 내부 색상:", font=font_normal))
        fill_color_picker = ColorPalette(
            default_color="#3366CC", allow_transparent=True, parent=page
        )
        fill_color_layout.addWidget(fill_color_picker)
        layout.addLayout(fill_color_layout)

        layout.addStretch()

        self._area_controls = {
            "switch_area_label": switch,
            "group_border_style": group_style,
            "border_color_picker": border_color_picker,
            "fill_color_picker": fill_color_picker,
        }
        return page

    def _build_reference_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        font_bold = QFont(self.ui_font_name, 10, QFont.Weight.Bold)
        font_normal = QFont(self.ui_font_name, 9)

        layout.addWidget(QLabel("참조선 레이어", font=font_bold))

        # 참조선 타입
        row_style = QVBoxLayout()
        row_style.setSpacing(4)
        row_style.addWidget(QLabel("참조선 타입:", font=font_normal))
        frame_style, group_style = self._create_line_style_group(page, default_idx=0)
        row_style.addWidget(frame_style)
        layout.addLayout(row_style)

        # 참조선 색상 (투명 불가, 기본 회색)
        color_layout = QVBoxLayout()
        color_layout.setSpacing(6)
        color_layout.addWidget(QLabel("참조선 색상:", font=font_normal))
        color_picker = ColorPalette(
            default_color="#AAAAAA", allow_transparent=False, parent=page
        )
        color_layout.addWidget(color_picker)
        layout.addLayout(color_layout)

        layout.addStretch()

        self._reference_controls = {
            "group_style": group_style,
            "color_picker": color_picker,
        }
        return page

    # ------------------------------------------------------------------
    # 전체 레이아웃
    # ------------------------------------------------------------------
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setStyleSheet("QWidget { background-color: white; }")

        # 포커스 없을 때 안내 라벨
        placeholder = QLabel("그리기 레이어를 선택하면 디자인 옵션이 표시됩니다.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_font = QFont(self.ui_font_name, 9)
        ph_font.setItalic(True)
        placeholder.setFont(ph_font)
        placeholder.setStyleSheet("color: #909399;")
        placeholder.setWordWrap(True)

        stacked = QStackedWidget()
        page_line = self._build_line_page()
        page_area = self._build_area_page()
        page_reference = self._build_reference_page()

        stacked.addWidget(page_line)  # index 0
        stacked.addWidget(page_area)  # index 1
        stacked.addWidget(page_reference)  # index 2

        self._placeholder = placeholder
        self._stacked = stacked
        self._page_indices = {"line": 0, "area": 1, "reference": 2}

        main_layout.addWidget(placeholder)
        main_layout.addWidget(stacked)
        main_layout.addStretch()

        # 기본 상태: 포커스 없음
        self._set_focus_none_ui()

    def _connect_signals(self):
        # 선/영역/참조선 선 타입: buttonClicked 사용 (buttonToggled는 해제+선택 두 번 발화해 _loading과 꼬임)
        for ctrl in [
            self._line_controls["group_style"],
            self._line_controls["group_arrow_mode"],
            self._line_controls["group_arrow_head"],
        ]:
            ctrl.buttonClicked.connect(self._on_any_control_changed)
        self._line_controls["color_picker"].color_changed.connect(
            self._on_any_control_changed
        )

        self._area_controls["switch_area_label"].toggled.connect(
            self._on_any_control_changed
        )
        self._area_controls["group_border_style"].buttonClicked.connect(
            self._on_any_control_changed
        )
        self._area_controls["border_color_picker"].color_changed.connect(
            self._on_any_control_changed
        )
        self._area_controls["fill_color_picker"].color_changed.connect(
            self._on_any_control_changed
        )

        self._reference_controls["group_style"].buttonClicked.connect(
            self._on_any_control_changed
        )
        self._reference_controls["color_picker"].color_changed.connect(
            self._on_any_control_changed
        )

    # ------------------------------------------------------------------
    # 퍼블릭 API
    # ------------------------------------------------------------------
    def clear_selection(self):
        """어떤 그리기 레이어도 선택되지 않았을 때 호출."""
        self._current_layer_id = ""
        self._current_layer_type = None
        self._set_focus_none_ui()
        # 포커스 없음일 때는 settings_changed를 보내지 않는다.

    def set_current_layer(self, layer_id: str, layer_type: str, settings: dict | None):
        """
        외부(레이어 도크 등)에서 현재 선택된 그리기 레이어 정보를 전달한다.

        layer_type: "line" | "area" | "reference"
        settings: 타입별 설정 딕셔너리 (없으면 기본값 사용)
        """
        self._current_layer_id = layer_id or ""
        self._current_layer_type = layer_type
        self._set_focus_active_ui(layer_type)

        self._loading = True
        try:
            settings = settings or {}
            if layer_type == "line":
                self._apply_line_settings(settings)
            elif layer_type == "area":
                self._apply_area_settings(settings)
            elif layer_type == "reference":
                self._apply_reference_settings(settings)
        finally:
            self._loading = False

    def get_current_settings(self) -> dict:
        """현재 UI 상태를 타입별 설정 딕셔너리로 반환."""
        if self._current_layer_type is None:
            return {}
        if self._current_layer_type == "line":
            return self._collect_line_settings()
        if self._current_layer_type == "area":
            return self._collect_area_settings()
        if self._current_layer_type == "reference":
            return self._collect_reference_settings()
        return {}

    # ------------------------------------------------------------------
    # 내부 상태 적용/수집
    # ------------------------------------------------------------------
    def _apply_line_settings(self, settings: dict):
        style_val = settings.get("line_style", "-")
        style_id = _STYLE_VALUE_TO_ID.get(style_val, 0)
        group = self._line_controls["group_style"]
        btn = group.button(style_id)
        if btn:
            btn.setChecked(True)

        # 화살표 타입
        mode_val = settings.get("arrow_mode", "none")
        mode_idx = {"none": 0, "end": 1, "all": 2}.get(mode_val, 0)
        g_mode = self._line_controls["group_arrow_mode"]
        btn_mode = g_mode.button(mode_idx)
        if btn_mode:
            btn_mode.setChecked(True)

        # 화살표 모양
        head_val = settings.get("arrow_head", "stealth")
        head_idx = {"stealth": 0, "open": 1, "latex": 2}.get(head_val, 0)
        g_head = self._line_controls["group_arrow_head"]
        btn_head = g_head.button(head_idx)
        if btn_head:
            btn_head.setChecked(True)

        # mode가 none이면 모양 프레임 비활성화
        self._line_controls["arrow_head_frame"].setEnabled(mode_val != "none")

        color = settings.get("line_color", "#000000") or "#000000"
        # 투명은 지원하지 않으므로 transparent가 들어오면 기본값으로 되돌린다.
        if str(color).lower() == "transparent":
            color = "#000000"
        self._line_controls["color_picker"].set_color(color)

    def _apply_area_settings(self, settings: dict):
        sw = self._area_controls["switch_area_label"]
        sw.setChecked(bool(settings.get("area_label_visible", True)))

        # 넓이 값 표시 (없으면 대시)
        area_val = settings.get("area_value", None)
        if area_val is None:
            self._area_value_label.setText("영역 넓이 : —")
        else:
            try:
                self._area_value_label.setText(f"영역 넓이 : {float(area_val):.2f}")
            except (TypeError, ValueError):
                self._area_value_label.setText("영역 넓이 : —")

        style_val = settings.get("border_style", "-")
        style_id = _STYLE_VALUE_TO_ID.get(style_val, 0)
        group = self._area_controls["group_border_style"]
        btn = group.button(style_id)
        if btn:
            btn.setChecked(True)

        border_color = settings.get("border_color", "#000000") or "#000000"
        if str(border_color).lower() == "transparent":
            border_color = "#000000"
        self._area_controls["border_color_picker"].set_color(border_color)

        # fill_color: None/transparent는 투명으로, 키 자체가 없으면 기본 파란색
        if "fill_color" in settings:
            fill_color = settings["fill_color"]
            if fill_color is None or str(fill_color).lower() == "transparent":
                self._area_controls["fill_color_picker"].set_color("transparent")
            else:
                self._area_controls["fill_color_picker"].set_color(fill_color)
        else:
            self._area_controls["fill_color_picker"].set_color("#3366CC")

    def _apply_reference_settings(self, settings: dict):
        style_val = settings.get("line_style", "-")
        style_id = _STYLE_VALUE_TO_ID.get(style_val, 0)
        group = self._reference_controls["group_style"]
        btn = group.button(style_id)
        if btn:
            btn.setChecked(True)

        color = settings.get("line_color", "#606060") or "#606060"
        if str(color).lower() == "transparent":
            color = "#606060"
        self._reference_controls["color_picker"].set_color(color)

    def _collect_line_settings(self) -> dict:
        group = self._line_controls["group_style"]
        style_id = group.checkedId()
        if style_id < 0:
            # checkedId가 -1일 때는 현재 checkedButton으로 보정
            btn = group.checkedButton()
            style_id = group.id(btn) if btn else 0
        style_val = _STYLE_ID_TO_VALUE.get(style_id, "-")
        color = self._line_controls["color_picker"].current_color
        # 화살표 타입
        g_mode = self._line_controls["group_arrow_mode"]
        mode_idx = g_mode.checkedId()
        if mode_idx < 0:
            btn_mode = g_mode.checkedButton()
            mode_idx = g_mode.id(btn_mode) if btn_mode else 0
        mode_val = {0: "none", 1: "end", 2: "all"}.get(mode_idx, "none")
        # 화살표 모양
        g_head = self._line_controls["group_arrow_head"]
        head_idx = g_head.checkedId()
        if head_idx < 0:
            btn_head = g_head.checkedButton()
            head_idx = g_head.id(btn_head) if btn_head else 0
        head_val = {0: "stealth", 1: "open", 2: "latex"}.get(head_idx, "stealth")

        out = {
            "line_style": style_val,
            "line_color": color,
            "arrow_mode": mode_val,
        }
        # mode가 none이면 화살표 모양 설정을 보내지 않는다 (요약에서도 사라지게)
        if mode_val != "none":
            out["arrow_head"] = head_val
        return out

    def _collect_area_settings(self) -> dict:
        group = self._area_controls["group_border_style"]
        style_id = group.checkedId()
        if style_id < 0:
            btn = group.checkedButton()
            style_id = group.id(btn) if btn else 0
        style_val = _STYLE_ID_TO_VALUE.get(style_id, "-")

        border_color = self._area_controls["border_color_picker"].current_color
        # 필 색상: transparent는 문자열 그대로 "transparent"로 저장해, 렌더링/요약에서 명시적으로 처리
        fill_color = self._area_controls["fill_color_picker"].current_color

        return {
            "border_style": style_val,
            "border_color": border_color,
            "fill_color": fill_color,
            "area_label_visible": self._area_controls["switch_area_label"].isChecked(),
        }

    def _collect_reference_settings(self) -> dict:
        group = self._reference_controls["group_style"]
        style_id = group.checkedId()
        if style_id < 0:
            btn = group.checkedButton()
            style_id = group.id(btn) if btn else 0
        style_val = _STYLE_ID_TO_VALUE.get(style_id, "-")
        color = self._reference_controls["color_picker"].current_color
        return {
            "line_style": style_val,
            "line_color": color,
        }

    # ------------------------------------------------------------------
    # 포커스 상태 UI 전환
    # ------------------------------------------------------------------
    def _set_focus_none_ui(self):
        self._placeholder.setVisible(True)
        self._stacked.setVisible(False)

    def _set_focus_active_ui(self, layer_type: str):
        self._placeholder.setVisible(False)
        self._stacked.setVisible(True)
        idx = self._page_indices.get(layer_type, 0)
        self._stacked.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # 시그널 처리
    # ------------------------------------------------------------------
    def _on_any_control_changed(self, *args):
        if self._loading:
            return
        if self._current_layer_type is None or not self._current_layer_id:
            return
        if self._current_layer_type == "line":
            self._update_line_arrow_head_enabled()
        self._emit_settings()

    def _emit_settings(self):
        if self._current_layer_type is None or not self._current_layer_id:
            return
        settings = self.get_current_settings()
        # #region agent log
        try:
            import json

            with open("debug-61ea09.log", "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "sessionId": "61ea09",
                            "message": "emit_settings",
                            "data": {
                                "layer_id": self._current_layer_id,
                                "layer_type": str(self._current_layer_type),
                            },
                            "hypothesisId": "H1",
                            "timestamp": __import__("time").time() * 1000,
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        self.settings_changed.emit(self._current_layer_id, settings)
