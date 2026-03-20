import itertools
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QStackedWidget,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QEvent
from PyQt6.QtGui import QColor, QFont
from utils.pillai_stats import calculate_pillai_score
from utils.vowel_sorting import get_vowel_sort_key

# Scrollbar style (copied from vowel_analysis_dialog.py or move to a separate theme file later)
MODERN_SCROLLBAR_STYLE = """
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #DCDFE6;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical:hover {
        background: #C0C4CC;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        background: transparent;
        height: 8px;
        margin: 0px;
    }
    QScrollBar::handle:horizontal {
        background: #DCDFE6;
        min-width: 20px;
        border-radius: 4px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #C0C4CC;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
"""


class PillaiHelpTooltip(QWidget):
    """Pillai Score 설명을 위한 커스텀 고퀄리티 툴팁 위젯."""

    def __init__(self, parent=None):
        super().__init__(
            parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Layout & Content
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # 그림자 여유 공간

        self.container = QWidget()
        self.container.setObjectName("TooltipContainer")
        self.container.setStyleSheet("""
            QWidget#TooltipContainer {
                background-color: white;
                border: 1px solid #DCDFE6;
                border-radius: 12px;
            }
        """)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 16, 16, 16)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setText(
            """
            <div style="font-family: 'Malgun Gothic', sans-serif; line-height: 1.6; color: #303133;">
                <p style="font-size: 15px; font-weight: bold; margin-bottom: 10px; color: #2c3e50;">Pillai Score란 무엇인가요?</p>
                <p style="margin-bottom: 10px; font-size: 13px;">다변량 통계 분석(MANOVA)을 기반으로, 화자가 두 모음(예: /i:/ 와 /ɪ/)을 얼마나 명확하게 구분해서 발음하고 있는지 수치화해 주는 지표입니다. 점수는 <b>0부터 1 사이</b>의 값으로 나옵니다.</p>
                <ul style="margin-left: -20px; margin-bottom: 0; font-size: 13px;">
                    <li style="margin-bottom: 8px;"><b>0에 가까울수록 (겹침):</b> 두 모음 데이터가 산점도 상에서 심하게 겹쳐 있습니다. 아직 두 모음을 구별하는 음운 카테고리가 명확히 잡히지 않아 비슷한 소리로 발음되고 있다는 뜻입니다.</li>
                    <li><b>1에 가까울수록 (분리):</b> 두 모음 데이터가 산점도 상에서 뚜렷하게 나뉘어 있습니다. 화자가 두 모음을 명확히 다른 소리에 해당하게 분리해서 발음하고 있다는 뜻입니다.</li>
                </ul>
            </div>
            """
        )
        self.label.setFixedWidth(320)
        container_layout.addWidget(self.label)

        layout.addWidget(self.container)

        # Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        # Animation
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def show_at(self, pos):
        # 화면 경계 처리 (Windows 상단/하단 등에서 잘리지 않게)
        screen = self.screen().availableGeometry()
        w, h = self.sizeHint().width(), self.sizeHint().height()

        x = pos.x()
        y = pos.y() + 15

        if x + w > screen.right():
            x = screen.right() - w - 10
        if y + h > screen.bottom():
            y = pos.y() - h - 10

        self.move(int(x), int(y))
        self.setWindowOpacity(0)
        self.show()
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def hide_tooltip(self):
        self.hide()


class PillaiScorePage(QWidget):
    """모음 여러 개를 선택하여 조합별 Pillai Score를 계산하는 페이지."""

    selectionStateChanged = pyqtSignal()

    def __init__(self, df, x_col, y_col, label_col, parent=None):
        super().__init__(parent)
        self.df = df
        self.x_col = x_col
        self.y_col = y_col
        self.label_col = label_col
        self._vowel_list = []
        self.selection_count = 0
        self.help_tooltip = PillaiHelpTooltip(self.window())
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)  # 가로를 넓게 쓰기 위해 좌우 마진 0
        layout.setSpacing(12)

        # Header with Reset Button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 0, 16, 0)

        header = QLabel("Pillai Score 분석")
        header.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #303133; border: none; background: transparent;"
        )
        header_layout.addWidget(header)

        # Help Icon (?)
        help_icon = QLabel("?")
        help_icon.setFixedSize(20, 20)
        help_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        help_icon.setStyleSheet("""
            QLabel {
                background-color: #F0F2F5;
                color: #909399;
                border: 1px solid #DCDFE6;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QLabel:hover {
                background-color: #E4E7ED;
                color: #409EFF;
                border-color: #409EFF;
            }
        """)
        help_icon.setToolTip("")  # 기본 툴팁 제거
        help_icon.installEventFilter(self)
        self.help_icon = help_icon

        header_layout.addWidget(help_icon)
        header_layout.addSpacing(4)
        header_layout.addStretch()

        self.btn_reset = QPushButton("전체 초기화")
        self.btn_reset.setStyleSheet("""
            QPushButton { background-color: #Fefefe; border: 1px solid #DCDFE6; border-radius: 4px; padding: 4px 12px; color: #606266; }
            QPushButton:hover { background-color: #F5F7FA; color: #F56C6C; border-color: #Fab6b6; }
        """)
        self.btn_reset.clicked.connect(self._reset_selection)
        header_layout.addWidget(self.btn_reset)
        layout.addWidget(header_widget)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(16, 0, 16, 0)
        layout.addLayout(content_layout)

        # 1. 모음 선택 테이블 (2열 배치)
        vowel_counts = self.df[self.label_col].value_counts().to_dict()
        self._vowel_list = sorted(list(vowel_counts.keys()), key=get_vowel_sort_key)

        self.vowel_table = QTableWidget()
        self.vowel_table.setColumnCount(2)
        self.vowel_table.horizontalHeader().setVisible(False)
        self.vowel_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )  # 가로로 넓게 확장
        self.vowel_table.verticalHeader().setVisible(False)
        self.vowel_table.setShowGrid(False)
        self.vowel_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.vowel_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectItems
        )
        self.vowel_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.vowel_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Focus Rect 제거
        self.vowel_table.setCurrentCell(-1, -1)  # 초기 포커스 셀 제거
        self.vowel_table.setStyleSheet(
            f"QTableWidget {{ border: none; background-color: transparent; outline: none; }} QTableWidget::item:selected {{ background-color: #F0F7FF; color: #409EFF; border: none; }} {MODERN_SCROLLBAR_STYLE}"
        )

        # 행 간격 조정
        self.vowel_table.verticalHeader().setDefaultSectionSize(42)

        n_vowels = len(self._vowel_list)
        n_rows = (n_vowels + 1) // 2
        self.vowel_table.setRowCount(n_rows)
        for i, v in enumerate(self._vowel_list):
            row, col = i // 2, i % 2
            count = vowel_counts.get(v, 0)

            container = QWidget()
            cell_layout = QHBoxLayout(container)
            cell_layout.setContentsMargins(12, 4, 8, 4)
            cell_layout.setSpacing(10)  # 8에서 10으로 확대 (스페이스 하나 더 느낌)

            lbl_v = QLabel(str(v))
            lbl_v.setStyleSheet(
                "font-size: 16px; color: #303133; border: none; background: transparent;"
            )
            lbl_count = QLabel(f"(데이터 포인트 {count}개)")
            lbl_count.setStyleSheet(
                "font-size: 10px; color: #909399; border: none; background: transparent;"
            )

            cell_layout.addWidget(lbl_v)
            cell_layout.addWidget(lbl_count)
            cell_layout.addStretch()

            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, v)
            self.vowel_table.setItem(row, col, item)
            self.vowel_table.setCellWidget(row, col, container)

        self.vowel_table.itemSelectionChanged.connect(self._on_selection_changed)
        content_layout.addWidget(self.vowel_table, 1)  # 비율 조정

        # 2. 결과 영역
        self.result_stack = QStackedWidget()
        self.result_stack.setStyleSheet(
            "background-color: #F8FAFB; border: none; border-radius: 12px;"
        )

        self.prompt_page = QLabel(
            "분석할 모음을 2개 이상 선택하세요.\n(조합별 점수가 자동 계산됩니다)"
        )
        self.prompt_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prompt_page.setStyleSheet(
            "color: #909399; font-style: italic; background: transparent; border: none;"
        )
        self.result_stack.addWidget(self.prompt_page)

        self.single_page = QWidget()
        self.single_page.setStyleSheet("background: transparent; border: none;")
        single_layout = QVBoxLayout(self.single_page)
        single_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vowels_2 = QLabel("-")
        self.lbl_vowels_2.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #303133; background: transparent; border: none;"
        )
        self.lbl_vowels_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        single_layout.addWidget(self.lbl_vowels_2)
        single_layout.addSpacing(10)
        lbl_pillai_title = QLabel("Pillai Score")
        lbl_pillai_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_pillai_title.setStyleSheet(
            "color: #606266; background: transparent; border: none;"
        )
        single_layout.addWidget(lbl_pillai_title)
        self.lbl_pillai_val = QLabel("-")
        self.lbl_pillai_val.setStyleSheet(
            "font-size: 48px; font-weight: bold; color: #409EFF; background: transparent; border: none;"
        )
        self.lbl_pillai_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        single_layout.addWidget(self.lbl_pillai_val)
        self.result_stack.addWidget(self.single_page)

        self.multi_page = QWidget()
        self.multi_page.setStyleSheet("background: transparent; border: none;")
        multi_layout = QVBoxLayout(self.multi_page)
        multi_layout.setContentsMargins(
            12, 12, 12, 12
        )  # 테이블 외곽선 잘림 방지 (8에서 12로 확대)

        self.lbl_multi_header = QLabel("모음 조합별 Pillai Score 분석 결과")
        self.lbl_multi_header.setStyleSheet(
            "font-weight: bold; color: #303133; padding-bottom: 4px; background: transparent; border: none;"
        )
        multi_layout.addWidget(self.lbl_multi_header)

        self.multi_table = QTableWidget()
        self.multi_table.setColumnCount(2)
        self.multi_table.setHorizontalHeaderLabels(["모음 조합", "Pillai Score"])
        self.multi_table.horizontalHeader().setStretchLastSection(True)
        self.multi_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section { 
                background-color: #F8FAFB; 
                border: none; 
                border-bottom: 1px solid #E4E7ED; 
                border-right: 1px solid #E4E7ED; 
                padding: 4px; 
            }
            QHeaderView::section:last { border-right: none; }
        """)
        self.multi_table.verticalHeader().setVisible(False)
        self.multi_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.multi_table.setAlternatingRowColors(True)
        self.multi_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Focus Rect 제거
        self.multi_table.setCurrentCell(-1, -1)  # 초기 포커스 셀 제거
        self.multi_table.setShowGrid(True)
        self.multi_table.setGridStyle(Qt.PenStyle.SolidLine)
        self.multi_table.setStyleSheet(f"""
            QTableWidget {{ 
                border: 1px solid #E4E7ED; 
                background-color: transparent; 
                outline: none; 
                gridline-color: #E4E7ED;
            }} 
            QTableWidget::item {{ 
                padding: 6px 4px; 
            }}
            QTableWidget::item:hover, QTableWidget::item:selected {{ 
                background-color: #F5F9FF; 
                color: #303133; 
            }} 
            {MODERN_SCROLLBAR_STYLE}
        """)
        multi_layout.addWidget(self.multi_table)
        self.result_stack.addWidget(self.multi_page)

        content_layout.addWidget(self.result_stack, 1)  # 좌우 비율 1:1로 조정

    def get_combination_results(self):
        """현재 멀티 테이블에 표시된 데이터를 리스트로 반환."""
        rows = self.multi_table.rowCount()
        data = []
        for r in range(rows):
            pair = self.multi_table.item(r, 0).text()
            score = self.multi_table.item(r, 1).text()
            data.append([pair, score])
        return data

    def _reset_selection(self):
        self.vowel_table.clearSelection()

    def _on_selection_changed(self):
        selected_items = self.vowel_table.selectedItems()
        selected_vowels = sorted(
            list(set(it.data(Qt.ItemDataRole.UserRole) for it in selected_items)),
            key=get_vowel_sort_key
        )
        self.selection_count = len(selected_vowels)
        self.selectionStateChanged.emit()

        if self.selection_count < 2:
            self.result_stack.setCurrentIndex(0)
        elif self.selection_count == 2:
            self._handle_single_pair(selected_vowels)
            self.result_stack.setCurrentIndex(1)
        else:
            self._handle_multi_pairs(selected_vowels)
            self.result_stack.setCurrentIndex(2)

    def _handle_single_pair(self, vowels):
        v1, v2 = vowels
        self.lbl_vowels_2.setText(f"{v1}  vs  {v2}")
        score = self._calc_pillai(v1, v2)
        if score is not None:
            self.lbl_pillai_val.setText(f"{score:.4f}")
        else:
            self.lbl_pillai_val.setText("N/A")

    def _handle_multi_pairs(self, vowels):
        pairs = list(itertools.combinations(vowels, 2))
        self.multi_table.setRowCount(len(pairs))
        for i, (v1, v2) in enumerate(pairs):
            pair_text = f"{v1} - {v2}"
            score = self._calc_pillai(v1, v2)
            score_text = f"{score:.4f}" if score is not None else "N/A"

            it_pair = QTableWidgetItem(pair_text)
            it_pair.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_score = QTableWidgetItem(score_text)
            it_score.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_score.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            if score is not None and score > 0.8:  # 분리도가 높은 경우 강조
                it_score.setForeground(QColor("#409EFF"))

            self.multi_table.setItem(i, 0, it_pair)
            self.multi_table.setItem(i, 1, it_score)

    def _calc_pillai(self, v1, v2):
        try:
            coords1 = self.df[self.df[self.label_col] == v1][
                [self.x_col, self.y_col]
            ].values
            coords2 = self.df[self.df[self.label_col] == v2][
                [self.x_col, self.y_col]
            ].values
            return calculate_pillai_score(coords1, coords2)
        except Exception:
            return None

    def eventFilter(self, obj, event):
        if obj == getattr(self, "help_icon", None):
            if event.type() == QEvent.Type.Enter:
                self.help_tooltip.show_at(event.globalPosition().toPoint())
            elif event.type() == QEvent.Type.Leave:
                self.help_tooltip.hide_tooltip()
        return super().eventFilter(obj, event)
