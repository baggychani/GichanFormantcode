import itertools
from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QStackedWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from utils.formant_pair_distance import format_pair_distance
from utils.vowel_sorting import get_vowel_sort_key
from ui.widgets.pillai_score_page import MODERN_SCROLLBAR_STYLE


class EuclideanResultTable(QTableWidget):
    """선택된 셀을 다시 누르면 선택 해제."""

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item and item.isSelected():
            self.setCurrentItem(None)
            item.setSelected(False)
        else:
            super().mousePressEvent(event)


class EuclideanDistancePage(QWidget):
    """모음 무게중심 쌍별 유클리드 거리."""

    selectionStateChanged = Signal()

    def __init__(
        self,
        df,
        x_col: str,
        y_col: str,
        label_col: str,
        fixed_plot_params: Optional[Dict[str, Any]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.df = df
        self.x_col = x_col
        self.y_col = y_col
        self.label_col = label_col
        self.fixed_plot_params = dict(fixed_plot_params or {})
        self._norm = bool(self.fixed_plot_params.get("normalization"))
        self.distance_label = "유클리드 거리" if self._norm else "유클리드 거리(Bark)"
        self._vowel_list = []
        self.selection_count = 0
        self._setup_ui()

    # --- 거리 계산 ---

    def _centroid_dict(self, vowel) -> Optional[Dict[str, Any]]:
        sub = self.df[self.df[self.label_col] == vowel]
        if sub.empty:
            return None
        if self._norm:
            return {
                "x": float(sub[self.x_col].mean()),
                "y": float(sub[self.y_col].mean()),
            }
        return {
            "raw_f1": float(sub[self.y_col].mean()),
            "raw_f2": float(sub[self.x_col].mean()),
        }

    def _pair_distance_str(self, v1, v2) -> str:
        p1 = self._centroid_dict(v1)
        p2 = self._centroid_dict(v2)
        if p1 is None or p2 is None:
            return "—"
        return format_pair_distance(p1, p2, self.fixed_plot_params)

    # --- UI ---

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(12)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 0, 16, 0)

        header = QLabel("무게중심 간 유클리드 거리")
        header.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #303133; border: none; background: transparent;"
        )
        header_layout.addWidget(header)
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

        vowel_counts = self.df[self.label_col].value_counts().to_dict()
        self._vowel_list = sorted(list(vowel_counts.keys()), key=get_vowel_sort_key)

        self.vowel_table = QTableWidget()
        self.vowel_table.setColumnCount(2)
        self.vowel_table.horizontalHeader().setVisible(False)
        self.vowel_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.vowel_table.verticalHeader().setVisible(False)
        self.vowel_table.setShowGrid(False)
        self.vowel_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.vowel_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectItems
        )
        self.vowel_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.vowel_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.vowel_table.setCurrentCell(-1, -1)
        self.vowel_table.setStyleSheet(
            f"QTableWidget {{ border: none; background-color: transparent; outline: none; }} QTableWidget::item:selected {{ background-color: #F0F7FF; color: #409EFF; border: none; }} {MODERN_SCROLLBAR_STYLE}"
        )
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
            cell_layout.setSpacing(10)

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
        content_layout.addWidget(self.vowel_table, 1)

        self.result_stack = QStackedWidget()
        self.result_stack.setStyleSheet(
            "background-color: #F8FAFB; border: none; border-radius: 12px;"
        )

        self.prompt_page = QLabel(
            "분석할 모음을 2개 이상 선택하세요.\n(조합별 거리가 자동 계산됩니다)"
        )
        self.prompt_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prompt_page.setStyleSheet(
            "color: #909399; font-style: italic; background: transparent; border: none;"
        )
        self.result_stack.addWidget(self.prompt_page)

        self.single_page = QWidget()
        self.single_page.setStyleSheet("background: transparent; border: none;")
        single_layout = QVBoxLayout(self.single_page)
        single_layout.addStretch(2)

        self.lbl_vowels_2 = QLabel("-")
        self.lbl_vowels_2.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #303133; background: transparent; border: none;"
        )
        self.lbl_vowels_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        single_layout.addWidget(self.lbl_vowels_2)
        single_layout.addSpacing(10)
        lbl_dist_title = QLabel(self.distance_label)
        lbl_dist_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_dist_title.setStyleSheet(
            "color: #606266; background: transparent; border: none;"
        )
        single_layout.addWidget(lbl_dist_title)
        self.lbl_dist_val = QLabel("-")
        self.lbl_dist_val.setStyleSheet(
            "font-size: 28px; font-weight: bold; color: #303133; background: transparent; border: none;"
        )
        self.lbl_dist_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_dist_val.setWordWrap(True)
        single_layout.addWidget(self.lbl_dist_val)
        single_layout.addStretch(3)

        self.result_stack.addWidget(self.single_page)

        self.multi_page = QWidget()
        self.multi_page.setStyleSheet("background: transparent; border: none;")
        multi_layout = QVBoxLayout(self.multi_page)
        multi_layout.setContentsMargins(12, 12, 12, 12)

        self.lbl_multi_header = QLabel(f"모음 조합별 {self.distance_label}")
        self.lbl_multi_header.setStyleSheet(
            "font-weight: bold; color: #303133; padding-bottom: 4px; background: transparent; border: none;"
        )
        multi_layout.addWidget(self.lbl_multi_header)

        self.multi_table = EuclideanResultTable()
        self.multi_table.setColumnCount(2)
        self.multi_table.setHorizontalHeaderLabels(["모음 조합", self.distance_label])
        self.multi_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.multi_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Interactive
        )
        self.multi_table.horizontalHeader().resizeSection(1, 200)
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
        self.multi_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.multi_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.multi_table.setCurrentCell(-1, -1)
        self.multi_table.setShowGrid(True)
        self.multi_table.setGridStyle(Qt.PenStyle.SolidLine)
        self.multi_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E4E7ED;
                background-color: transparent;
                outline: none;
                gridline-color: #E4E7ED;
            }
            QTableWidget::item { padding: 6px 4px; }
            QTableWidget::item:hover, QTableWidget::item:selected {
                background-color: #F5F9FF;
            }
        """ + MODERN_SCROLLBAR_STYLE)
        multi_layout.addWidget(self.multi_table)
        self.result_stack.addWidget(self.multi_page)

        content_layout.addWidget(self.result_stack, 1)

    # --- 저장 / 선택 ---

    def get_combination_results(self):
        rows = self.multi_table.rowCount()
        data = []
        for r in range(rows):
            pair = self.multi_table.item(r, 0).text()
            dist = self.multi_table.item(r, 1).text()
            data.append([pair, dist])
        return data

    def get_distance_column_name(self) -> str:
        return self.distance_label

    def _reset_selection(self):
        self.vowel_table.clearSelection()

    def _on_selection_changed(self):
        selected_items = self.vowel_table.selectedItems()
        selected_vowels = sorted(
            list(set(it.data(Qt.ItemDataRole.UserRole) for it in selected_items)),
            key=get_vowel_sort_key,
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
        self.lbl_dist_val.setText(self._pair_distance_str(v1, v2))

    def _handle_multi_pairs(self, vowels):
        pairs = list(itertools.combinations(vowels, 2))
        self.multi_table.setRowCount(len(pairs))
        for i, (v1, v2) in enumerate(pairs):
            pair_text = f"{v1} - {v2}"
            dist_text = self._pair_distance_str(v1, v2)
            it_pair = QTableWidgetItem(pair_text)
            it_pair.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_dist = QTableWidgetItem(dist_text)
            it_dist.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_dist.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.multi_table.setItem(i, 0, it_pair)
            self.multi_table.setItem(i, 1, it_dist)
