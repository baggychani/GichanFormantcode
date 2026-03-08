# ui_filter.py

import os
import platform
import base64
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QButtonGroup, QScrollArea,
                             QWidget, QFrame, QSizePolicy, QTabWidget)
from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6.QtGui import QFont, QIcon, QPixmap

from utils import icon_utils
from .display_utils import strip_gichan_prefix


class LiveVowelFilterPanel(QDialog):
    """
    플롯에 표시될 모음의 가시성을 실시간으로 조절하는 라이브 필터링 패널입니다.
    """

    def __init__(self, parent, vowels, current_state, file_name, on_change_callback):
        super().__init__(parent)
        self.vowels = sorted(list(vowels))
        self.file_name = file_name
        self.on_change_callback = on_change_callback

        self.current_state = current_state.copy()
        for v in self.vowels:
            if v not in self.current_state:
                self.current_state[v] = 'ON'

        self.button_groups = {}

        clean_name = os.path.splitext(self.file_name)[0]
        self.setWindowTitle(f"표시 모음 필터링 - {clean_name}")

        self.setFixedWidth(395)
        self.setMinimumHeight(400)

        self.setWindowModality(Qt.WindowModality.NonModal)

        self.ui_font_name = "Malgun Gothic" if platform.system() == "Windows" else "AppleGothic"

        self._apply_pyqt6_icon()
        self._setup_ui()

    def _apply_pyqt6_icon(self):
        try:
            icon_data = base64.b64decode(icon_utils.ICON_BASE64)
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.setWindowIcon(QIcon(pixmap))
        except Exception:
            pass

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #F5F7FA; }
            QLabel { color: #333333; }
            QScrollArea { border: 1px solid #DCDFE6; border-radius: 4px; background-color: white; }
            QWidget#ScrollContent { background-color: white; }

            QPushButton.seg-btn {
                background-color: #FFFFFF;
                color: #909399;
                border: 1px solid #DCDFE6;
                font-weight: bold;
                padding: 5px 0px; 
                font-size: 11px;
            }
            QPushButton.seg-btn:hover { background-color: #F0F2F5; color: #606266; }

            QPushButton.seg-left {
                border-top-left-radius: 4px; border-bottom-left-radius: 4px;
                border-top-right-radius: 0px; border-bottom-right-radius: 0px;
                border-right: none;
            }
            QPushButton.seg-left:checked { background-color: #67C23A; color: white; border-color: #67C23A; }

            QPushButton.seg-mid {
                border-radius: 0px;
            }
            QPushButton.seg-mid:checked { background-color: #73767A; color: white; border-color: #73767A; }

            QPushButton.seg-right {
                border-top-left-radius: 0px; border-bottom-left-radius: 0px;
                border-top-right-radius: 4px; border-bottom-right-radius: 4px;
                border-left: none;
            }
            QPushButton.seg-right:checked { background-color: #E6A23C; color: white; border-color: #E6A23C; }

            QPushButton#btn_close { 
                background-color: #ffffff; border: 1px solid #dcdfe6; 
                border-radius: 4px; padding: 6px; color: #606266; font-weight: bold;
            }
            QPushButton#btn_close:hover { background-color: #ecf5ff; color: #409eff; border-color: #c6e2ff; }

            QPushButton[property="all_on"] {
                background-color: #F0F9EB; border: 1px solid #C2E7B0; 
                border-radius: 4px; color: #67C23A; font-weight: bold;
            }
            QPushButton[property="all_on"]:hover { background-color: #67C23A; color: white; border-color: #67C23A; }

            QPushButton[property="all_off"] {
                background-color: #F4F4F5; border: 1px solid #E9E9EB; 
                border-radius: 4px; color: #909399; font-weight: bold;
            }
            QPushButton[property="all_off"]:hover { background-color: #909399; color: white; border-color: #909399; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title_vlayout = QVBoxLayout()
        title_vlayout.setSpacing(2)

        lbl_title = QLabel("모음 가시성 설정")
        lbl_title.setFont(QFont(self.ui_font_name, 12, QFont.Weight.Bold))

        lbl_subtitle = QLabel(strip_gichan_prefix(os.path.splitext(self.file_name)[0]))
        lbl_subtitle.setFont(QFont(self.ui_font_name, 9))
        lbl_subtitle.setStyleSheet("color: #909399;")

        title_vlayout.addWidget(lbl_title)
        title_vlayout.addWidget(lbl_subtitle)

        header_layout.addLayout(title_vlayout)
        header_layout.addStretch()

        btn_all_on = QPushButton("모두 ON")
        btn_all_on.setProperty("property", "all_on")
        btn_all_on.setFixedSize(70, 28)
        btn_all_on.clicked.connect(self._set_all_on)
        header_layout.addWidget(btn_all_on, alignment=Qt.AlignmentFlag.AlignBottom)

        btn_all_off = QPushButton("모두 OFF")
        btn_all_off.setProperty("property", "all_off")
        btn_all_off.setFixedSize(70, 28)
        btn_all_off.clicked.connect(self._set_all_off)
        header_layout.addWidget(btn_all_off, alignment=Qt.AlignmentFlag.AlignBottom)

        layout.addLayout(header_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(6)

        font_vowel = QFont(self.ui_font_name, 11, QFont.Weight.Bold)

        for vowel in self.vowels:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            lbl_v = QLabel(vowel)
            lbl_v.setFont(font_vowel)
            lbl_v.setFixedWidth(50)
            lbl_v.setStyleSheet("color: #333333;")
            row_layout.addWidget(lbl_v)

            btn_on = QPushButton("ON")
            btn_off = QPushButton("OFF")
            btn_semi = QPushButton("반투명")

            btn_on.setProperty("class", "seg-btn seg-left")
            btn_off.setProperty("class", "seg-btn seg-mid")
            btn_semi.setProperty("class", "seg-btn seg-right")

            bg = QButtonGroup(self)
            bg.setExclusive(True)

            for i, btn in enumerate([btn_on, btn_off, btn_semi]):
                btn.setCheckable(True)
                btn.setFixedHeight(26)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                bg.addButton(btn, i + 1)

            state = self.current_state.get(vowel, 'ON')
            if state == 'ON':
                btn_on.setChecked(True)
            elif state == 'OFF':
                btn_off.setChecked(True)
            else:
                btn_semi.setChecked(True)

            bg.idClicked.connect(self._on_switch_changed)
            self.button_groups[vowel] = bg

            seg_layout = QHBoxLayout()
            seg_layout.setSpacing(0)
            seg_layout.addWidget(btn_on)
            seg_layout.addWidget(btn_off)
            seg_layout.addWidget(btn_semi)

            row_layout.addLayout(seg_layout)
            self.scroll_layout.addWidget(row_widget)

            if vowel != self.vowels[-1]:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet("color: #EBEEF5;")
                self.scroll_layout.addWidget(line)

        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_close = QPushButton("닫기")
        btn_close.setObjectName("btn_close")
        btn_close.setFixedSize(80, 30)
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _set_all_on(self):
        for bg in self.button_groups.values():
            bg.button(1).setChecked(True)
        self._on_switch_changed()

    def _set_all_off(self):
        for bg in self.button_groups.values():
            bg.button(2).setChecked(True)
        self._on_switch_changed()

    def _on_switch_changed(self, btn_id=None):
        new_state = {}
        for vowel, bg in self.button_groups.items():
            checked_id = bg.checkedId()
            if checked_id == 1:
                new_state[vowel] = 'ON'
            elif checked_id == 2:
                new_state[vowel] = 'OFF'
            else:
                new_state[vowel] = 'SEMI'

        self.current_state = new_state
        if self.on_change_callback:
            self.on_change_callback(new_state)

    def get_filter_state(self):
        return self.current_state


class MultiVowelFilterPanel(QDialog):
    """
    다중 플롯(비교 모드)에 특화된 듀얼 탭 기반 라이브 필터링 패널입니다.
    두 파일의 모음 표시 상태를 독립적으로 관리합니다.
    """

    def __init__(self, parent, file1_name, vowels1, state1, file2_name, vowels2, state2, on_change_callback):
        super().__init__(parent)
        self.file1_name = file1_name
        self.vowels1 = sorted(list(vowels1))
        self.state1 = state1.copy() if state1 else {}

        self.file2_name = file2_name
        self.vowels2 = sorted(list(vowels2))
        self.state2 = state2.copy() if state2 else {}

        self.on_change_callback = on_change_callback

        for v in self.vowels1:
            if v not in self.state1:
                self.state1[v] = 'ON'
        for v in self.vowels2:
            if v not in self.state2:
                self.state2[v] = 'ON'

        # 1: 탭1 (파란색 데이터), 2: 탭2 (빨간색 데이터)
        self.button_groups = {1: {}, 2: {}}
        self._multi_row_map = {}

        self.setWindowTitle("다중 플롯 모음 필터링")
        self.setFixedWidth(410)
        self.setMinimumHeight(450)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self.ui_font_name = "Malgun Gothic" if platform.system() == "Windows" else "AppleGothic"

        self._apply_pyqt6_icon()
        self._setup_ui()

    def _apply_pyqt6_icon(self):
        try:
            icon_data = base64.b64decode(icon_utils.ICON_BASE64)
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.setWindowIcon(QIcon(pixmap))
        except Exception:
            pass

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #F5F7FA; }
            QLabel { color: #333333; }
            QScrollArea { border: 1px solid #DCDFE6; border-radius: 4px; background-color: white; }
            QWidget#ScrollContent { background-color: white; }

            QTabWidget::pane { border: 1px solid #DCDFE6; border-radius: 4px; background: white; top: -1px; }
            QTabBar::tab {
                background: #E4E7ED; border: 1px solid #DCDFE6; border-bottom: none;
                border-top-left-radius: 4px; border-top-right-radius: 4px;
                min-width: 130px; padding: 8px 0px; color: #606266; font-weight: bold;
            }
            QTabBar::tab:selected { background: #FFFFFF; color: #303133; }
            QTabBar::tab:hover:!selected { background: #EBEEF5; color: #409EFF; }

            QPushButton.seg-btn {
                background-color: #FFFFFF; color: #909399; border: 1px solid #DCDFE6;
                font-weight: bold; padding: 5px 0px; font-size: 11px;
            }
            QPushButton.seg-btn:hover { background-color: #F0F2F5; color: #606266; }
            QPushButton.seg-left {
                border-top-left-radius: 4px; border-bottom-left-radius: 4px;
                border-top-right-radius: 0px; border-bottom-right-radius: 0px; border-right: none;
            }
            QPushButton.seg-left:checked { background-color: #67C23A; color: white; border-color: #67C23A; }
            QPushButton.seg-mid { border-radius: 0px; }
            QPushButton.seg-mid:checked { background-color: #73767A; color: white; border-color: #73767A; }
            QPushButton.seg-right {
                border-top-left-radius: 0px; border-bottom-left-radius: 0px;
                border-top-right-radius: 4px; border-bottom-right-radius: 4px; border-left: none;
            }
            QPushButton.seg-right:checked { background-color: #E6A23C; color: white; border-color: #E6A23C; }

            QPushButton#btn_close { 
                background-color: #ffffff; border: 1px solid #dcdfe6; 
                border-radius: 4px; padding: 6px; color: #606266; font-weight: bold;
            }
            QPushButton#btn_close:hover { background-color: #ecf5ff; color: #409eff; border-color: #c6e2ff; }

            QPushButton[property="all_on"] {
                background-color: #F0F9EB; border: 1px solid #C2E7B0; 
                border-radius: 4px; color: #67C23A; font-weight: bold;
            }
            QPushButton[property="all_on"]:hover { background-color: #67C23A; color: white; border-color: #67C23A; }

            QPushButton[property="all_off"] {
                background-color: #F4F4F5; border: 1px solid #E9E9EB; 
                border-radius: 4px; color: #909399; font-weight: bold;
            }
            QPushButton[property="all_off"]:hover { background-color: #909399; color: white; border-color: #909399; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        lbl_title = QLabel("다중 플롯 모음 가시성 설정")
        lbl_title.setFont(QFont(self.ui_font_name, 12, QFont.Weight.Bold))
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.tab_widget = QTabWidget()
        self.tab_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        name1 = os.path.splitext(self.file1_name)[0]
        name2 = os.path.splitext(self.file2_name)[0]
        name1_display = strip_gichan_prefix(name1)
        name2_display = strip_gichan_prefix(name2)

        tab1 = self._create_tab_page(name1_display, self.vowels1, self.state1, 1)
        tab2 = self._create_tab_page(name2_display, self.vowels2, self.state2, 2)

        self.tab_widget.addTab(tab1, name1_display)
        self.tab_widget.addTab(tab2, name2_display)

        layout.addWidget(self.tab_widget)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("닫기")
        btn_close.setObjectName("btn_close")
        btn_close.setFixedSize(80, 30)
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _create_tab_page(self, file_name, vowels, current_state, tab_id):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 15, 10, 10)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        lbl_subtitle = QLabel(f"대상 파일: {file_name}")
        lbl_subtitle.setFont(QFont(self.ui_font_name, 9))
        lbl_subtitle.setStyleSheet("color: #909399;")
        header_layout.addWidget(lbl_subtitle)
        header_layout.addStretch()

        btn_all_on = QPushButton("모두 ON")
        btn_all_on.setProperty("property", "all_on")
        btn_all_on.setFixedSize(70, 26)
        btn_all_on.clicked.connect(lambda: self._set_all_on(tab_id))
        header_layout.addWidget(btn_all_on)

        btn_all_off = QPushButton("모두 OFF")
        btn_all_off.setProperty("property", "all_off")
        btn_all_off.setFixedSize(70, 26)
        btn_all_off.clicked.connect(lambda: self._set_all_off(tab_id))
        header_layout.addWidget(btn_all_off)

        layout.addLayout(header_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(6)

        self._multi_row_map[tab_id] = {}

        font_vowel = QFont(self.ui_font_name, 11, QFont.Weight.Bold)

        for vowel in vowels:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            lbl_v = QLabel(vowel)
            lbl_v.setFont(font_vowel)
            lbl_v.setFixedWidth(50)
            lbl_v.setStyleSheet("color: #333333;")
            row_layout.addWidget(lbl_v)

            btn_on = QPushButton("ON")
            btn_off = QPushButton("OFF")
            btn_semi = QPushButton("반투명")

            btn_on.setProperty("class", "seg-btn seg-left")
            btn_off.setProperty("class", "seg-btn seg-mid")
            btn_semi.setProperty("class", "seg-btn seg-right")

            bg = QButtonGroup(self)
            bg.setExclusive(True)

            for i, btn in enumerate([btn_on, btn_off, btn_semi]):
                btn.setCheckable(True)
                btn.setFixedHeight(26)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                bg.addButton(btn, i + 1)

            state = current_state.get(vowel, 'ON')
            if state == 'ON':
                btn_on.setChecked(True)
            elif state == 'OFF':
                btn_off.setChecked(True)
            else:
                btn_semi.setChecked(True)

            bg.idClicked.connect(self._on_switch_changed)
            self.button_groups[tab_id][vowel] = bg

            seg_layout = QHBoxLayout()
            seg_layout.setSpacing(0)
            seg_layout.addWidget(btn_on)
            seg_layout.addWidget(btn_off)
            seg_layout.addWidget(btn_semi)

            row_layout.addLayout(seg_layout)
            scroll_layout.addWidget(row_widget)
            self._multi_row_map[tab_id][id(row_widget)] = vowel

            if vowel != vowels[-1]:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet("color: #EBEEF5;")
                scroll_layout.addWidget(line)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        return page

    def _set_all_on(self, tab_id):
        for bg in self.button_groups[tab_id].values():
            bg.button(1).setChecked(True)
        self._on_switch_changed()

    def _set_all_off(self, tab_id):
        for bg in self.button_groups[tab_id].values():
            bg.button(2).setChecked(True)
        self._on_switch_changed()

    def _on_switch_changed(self, btn_id=None):
        new_state1 = {}
        for vowel, bg in self.button_groups[1].items():
            checked_id = bg.checkedId()
            if checked_id == 1: new_state1[vowel] = 'ON'
            elif checked_id == 2: new_state1[vowel] = 'OFF'
            else: new_state1[vowel] = 'SEMI'

        new_state2 = {}
        for vowel, bg in self.button_groups[2].items():
            checked_id = bg.checkedId()
            if checked_id == 1: new_state2[vowel] = 'ON'
            elif checked_id == 2: new_state2[vowel] = 'OFF'
            else: new_state2[vowel] = 'SEMI'

        self.state1 = new_state1
        self.state2 = new_state2

        if self.on_change_callback:
            self.on_change_callback(self.state1, self.state2)

    def get_filter_state(self):
        return self.state1, self.state2