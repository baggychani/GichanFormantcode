# ui/vowel_analysis_dialog.py — 모음 상세 분석 결과 창

import os
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QMessageBox,
    QFileDialog,
    QWidget,
    QLabel,
    QStyledItemDelegate,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, QStandardPaths, QSize, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPen, QKeySequence, QIcon
import itertools
import pandas as pd
from utils.pillai_stats import calculate_pillai_score
from utils.icon_utils import get_app_icon
from utils.math_utils import calc_f2_prime
from ui.widgets.display_utils import truncate_display_name, MAX_DISPLAY_NAME_LEN
from utils.vowel_stats import (
    analyze_vowels,
    calculate_point_distances_from_centroid,
    calculate_point_distances_from_centroid_bark,
)

# 열 너비 (px)
VOWEL_COL_WIDTH = 58
DATA_COL_WIDTH = 92
# 테이블 전체 너비 + 레이아웃 좌우 마진(16*2) + 여유(스크롤/테두리) = 창 최소/초기 가로
TABLE_TOTAL_WIDTH = VOWEL_COL_WIDTH + 8 * DATA_COL_WIDTH
DIALOG_WIDTH = TABLE_TOTAL_WIDTH + 32 + 24


class CopyableTableWidget(QTableWidget):
    """데이터 복사(Tab-separated) 기능을 제공하는 테이블 위젯."""

    def _copy_selection(self):
        selection = self.selectedIndexes()
        if not selection:
            return

        # 선택된 인덱스들을 행/열 기준으로 정렬
        rows = sorted(list(set(idx.row() for idx in selection)))
        cols = sorted(list(set(idx.column() for idx in selection)))

        lines = []
        for r in rows:
            row_data = []
            for c in cols:
                it = self.item(r, c)
                # 실제로 선택된 셀인 경우에만 텍스트 포함 (아니면 공백)
                if it and it.isSelected():
                    row_data.append(it.text())
                else:
                    row_data.append("")
            lines.append("\t".join(row_data))

        text_to_copy = "\n".join(lines)
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(text_to_copy)

    def mousePressEvent(self, event):
        """이미 선택된 셀을 다시 누르면 선택을 해제합니다."""
        item = self.itemAt(event.pos())
        if item and item.isSelected():
            self.setCurrentItem(None)
            item.setSelected(False)
        else:
            super().mousePressEvent(event)


# 데이터 행에만 세로 구분선 (헤더 행에는 그리지 않음)
class _DataRowVerticalLineDelegate(QStyledItemDelegate):
    def __init__(self, first_data_row, parent=None):
        super().__init__(parent)
        self._first_data_row = first_data_row

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if index.row() >= self._first_data_row and index.column() < 8:
            painter.save()
            painter.setPen(QPen(QColor("#E4E7ED"), 1))
            r = option.rect
            painter.drawLine(r.right(), r.top(), r.right(), r.bottom())
            painter.restore()


# X축 타입 → 표시 라벨 (controller와 동일)
X_AXIS_LABELS = {
    "f1_f2": "F2",
    "f1_f3": "F3",
    "f1_f2_prime": "F2'",
    "f1_f2_minus_f1": "F2 - F1",
    "f1_f2_prime_minus_f1": "F2' - F1",
}
# 정규화 시 n 접두사
X_AXIS_LABELS_NORM = {
    "f1_f2": "nF2",
    "f1_f3": "nF3",
    "f1_f2_prime": "nF2'",
    "f1_f2_minus_f1": "nF2 - nF1",
    "f1_f2_prime_minus_f1": "nF2' - nF1",
}


def _build_x_hz(df, plot_type):
    """plot_type에 따라 Hz 단위 X축 벡터 반환. 실패 시 None."""
    if plot_type == "f1_f2":
        return df["F2"].values if "F2" in df.columns else None
    if plot_type == "f1_f3":
        return df["F3"].values if "F3" in df.columns else None
    if plot_type == "f1_f2_prime":
        if "F3" not in df.columns:
            return None
        f2p = calc_f2_prime(df["F1"].values, df["F2"].values, df["F3"].values)
        return f2p
    if plot_type == "f1_f2_minus_f1":
        return df["F2"].values - df["F1"].values
    if plot_type == "f1_f2_prime_minus_f1":
        if "F3" not in df.columns:
            return None
        f2p = calc_f2_prime(df["F1"].values, df["F2"].values, df["F3"].values)
        return f2p - df["F1"].values
    return df["F2"].values if "F2" in df.columns else None


def _outlier_suffix_from_params(plot_params):
    """fixed_plot_params에서 이상치 접미사 문자열 반환."""
    sigma = float(plot_params.get("sigma", 2.0))
    if sigma <= 1.0:
        return "_이상치 제거 1σ"
    return "_이상치 제거 2σ"


def _analysis_base_name(file_name, plot_params, is_pillai=False):
    """저장 시 사용할 기본 이름 (확장자 제거 + 이상치 접미사 + 정규화 접미사 + _analysis/_pillai_analysis)."""
    base = os.path.splitext(file_name)[0]
    base += _outlier_suffix_from_params(plot_params)
    norm = (plot_params or {}).get("normalization")
    if norm:
        base += f"_{norm}"
    suffix = "_pillai_analysis" if is_pillai else "_analysis"
    return base + suffix


class VowelAnalysisDialog(QDialog):
    """모음 상세 분석 결과를 표로 보여주고, 엑셀/CSV 저장을 제공하는 다이얼로그."""

    def __init__(
        self,
        parent,
        controller,
        plot_data_snapshot,
        fixed_plot_params,
        title_suffix,
        initial_tab_idx=0,
    ):
        super().__init__(parent)
        self.controller = controller
        self.plot_data_snapshot = plot_data_snapshot
        self.fixed_plot_params = dict(fixed_plot_params) if fixed_plot_params else {}
        self.title_suffix = title_suffix
        self._initial_tab_idx = initial_tab_idx
        self._analysis_results = []  # list of (file_name, result_dict) per tab
        self._stacked_widgets = []  # list of QStackedWidget per tab
        self._normalization = self.fixed_plot_params.get("normalization")
        plot_type = self.fixed_plot_params.get("type", "f1_f2")
        if self._normalization:
            self._x_axis_label = X_AXIS_LABELS_NORM.get(plot_type, "nF2")
        else:
            self._x_axis_label = X_AXIS_LABELS.get(plot_type, "F2")
        self.setWindowTitle(f"Analysis - {title_suffix}")
        self.setMinimumWidth(DIALOG_WIDTH)
        self.setMinimumHeight(460)
        self.resize(DIALOG_WIDTH, 480)
        self._apply_icon()
        self._build_ui()
        self._run_analysis()
        self._set_initial_tab()
        self._update_save_buttons_state()  # 초기 상태 반영
        # 탭 변경 시 디폴트(포먼트) 화면으로 리셋
        self.tabs.currentChanged.connect(lambda: self._switch_page(0))

    def keyPressEvent(self, event):
        """창 레벨에서 CTRL+C를 감지하여 현재 탭의 테이블 데이터를 복사합니다."""
        if event.matches(QKeySequence.StandardKey.Copy):
            current_tab = self.tabs.currentWidget()
            if current_tab:
                table = current_tab.findChild(CopyableTableWidget)
                if table:
                    table._copy_selection()
        else:
            super().keyPressEvent(event)

    def _apply_icon(self):
        try:
            self.setWindowIcon(get_app_icon())
        except Exception:
            pass

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #FAFAFA; }
            QTabWidget::pane {
                border: none;
                border-top: 1px solid #E4E7ED;
                background: white;
                margin-top: 0;
                padding: 0;
            }
            QTabBar::tab {
                background: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                padding: 10px 18px;
                color: #606266;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: white;
                color: #303133;
                font-weight: bold;
                border-bottom: 2px solid #409EFF;
            }
            QTabBar::tab:hover:!selected {
                color: #409EFF;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        btn_row = QHBoxLayout()

        # Page navigation buttons (Bottom Left)
        self.btn_page_formant = QPushButton()
        self.btn_page_formant.setIcon(QIcon(os.path.join("assets", "formant.png")))
        self.btn_page_formant.setIconSize(QSize(32, 28))
        self.btn_page_formant.setFixedSize(40, 36)
        self.btn_page_formant.setToolTip("포먼트 및 중심-개별 유클리드 거리")
        self.btn_page_formant.setStyleSheet("""
            QPushButton { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; }
            QPushButton:hover { background-color: #F5F7FA; border-color: #409EFF; }
        """)
        self.btn_page_formant.clicked.connect(lambda: self._switch_page(0))

        self.btn_page_pillai = QPushButton()
        self.btn_page_pillai.setIcon(QIcon(os.path.join("assets", "pillai.png")))
        self.btn_page_pillai.setIconSize(QSize(32, 28))
        self.btn_page_pillai.setFixedSize(40, 36)
        self.btn_page_pillai.setToolTip("Pillai Score")
        self.btn_page_pillai.setStyleSheet("""
            QPushButton { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; }
            QPushButton:hover { background-color: #F5F7FA; border-color: #409EFF; }
        """)
        self.btn_page_pillai.clicked.connect(lambda: self._switch_page(1))

        btn_row.addWidget(self.btn_page_formant)
        btn_row.addWidget(self.btn_page_pillai)

        btn_row.addStretch()
        self.btn_excel = QPushButton("엑셀 저장")
        self.btn_excel.setStyleSheet("""
            QPushButton { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; color: #333333; padding: 6px 14px; }
            QPushButton:hover { background-color: #F5F7FA; color: #409EFF; border-color: #C0C4CC; }
            QPushButton:disabled { background-color: #F9FAFB; color: #C0C4CC; border-color: #EBEEF5; }
        """)
        self.btn_excel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_excel.clicked.connect(self._save_excel)
        self.btn_csv = QPushButton("CSV 저장")
        self.btn_csv.setStyleSheet("""
            QPushButton { background-color: white; border: 1px solid #DCDFE6; border-radius: 4px; color: #333333; padding: 6px 14px; }
            QPushButton:hover { background-color: #F5F7FA; color: #409EFF; border-color: #C0C4CC; }
            QPushButton:disabled { background-color: #F9FAFB; color: #C0C4CC; border-color: #EBEEF5; }
        """)
        self.btn_csv.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_csv.clicked.connect(self._save_csv)
        btn_row.addWidget(self.btn_excel)
        btn_row.addWidget(self.btn_csv)
        layout.addLayout(btn_row)

    def _switch_page(self, index):
        """모든 탭의 페이지를 전환합니다."""
        for stack in self._stacked_widgets:
            stack.setCurrentIndex(index)
            # 탭(파일) 전환 시 기존 선택/포커스 초기화
            table = stack.widget(0)
            if isinstance(table, QTableWidget):
                table.clearSelection()
                table.setCurrentCell(-1, -1)
        self._update_save_buttons_state()

    def _update_save_buttons_state(self):
        """현재 페이지와 선택 상태에 따라 저장 버튼의 활성/비활성 상태를 업데이트합니다."""
        current_tab_idx = self.tabs.currentIndex()
        if current_tab_idx < 0 or current_tab_idx >= len(self._stacked_widgets):
            return

        stack = self._stacked_widgets[current_tab_idx]
        if stack.currentIndex() == 0:
            # Formant 페이지는 항상 활성화
            self.btn_excel.setEnabled(True)
            self.btn_csv.setEnabled(True)
            self.btn_excel.setToolTip("")
            self.btn_csv.setToolTip("")
        else:
            # Pillai 페이지는 3개 이상 선택 시에만 활성화
            pillai_page = stack.currentWidget()
            if isinstance(pillai_page, PillaiScorePage):
                is_valid = pillai_page.selection_count >= 3
                self.btn_excel.setEnabled(is_valid)
                self.btn_csv.setEnabled(is_valid)
                if not is_valid:
                    msg = "모음을 3개 이상 선택해야 저장할 수 있습니다."
                    self.btn_excel.setToolTip(msg)
                    self.btn_csv.setToolTip(msg)
                else:
                    self.btn_excel.setToolTip("")
                    self.btn_csv.setToolTip("")

    def _run_analysis(self):
        """비정규화: Hz df로 F1·X축 통계, Bark 기준 중심-개별 거리. 정규화: 정규화 df로 nF1·nX축 통계, 정규화 단위 기준 중심-개별 거리."""
        if not self.plot_data_snapshot:
            return
        plot_type = self.fixed_plot_params.get("type", "f1_f2")
        norm = self._normalization
        for data in self.plot_data_snapshot:
            name = data.get("name", "")
            df_raw = data.get("df")
            if df_raw is None or df_raw.empty:
                self._add_empty_tab(name, "데이터 없음")
                self._analysis_results.append((name, None))
                continue
            label_col = "Label" if "Label" in df_raw.columns else "label"
            if (
                label_col not in df_raw.columns
                or "F1" not in df_raw.columns
                or "F2" not in df_raw.columns
            ):
                self._add_empty_tab(name, "필수 컬럼(F1, F2, Label) 없음")
                self._analysis_results.append((name, None))
                continue
            if norm and getattr(self.controller, "_apply_normalization", None):
                df = self.controller._apply_normalization(df_raw, norm)
            else:
                df = df_raw
            x_vals = _build_x_hz(df, plot_type)
            if x_vals is None:
                self._add_empty_tab(name, "X축 계산 실패")
                self._analysis_results.append((name, None))
                continue
            if norm:
                df_work = df[[label_col, "F1", "F2"]].copy()
                df_work["x_norm"] = x_vals
                result = analyze_vowels(
                    df_work,
                    x_col="x_norm",
                    y_col="F1",
                    label_col=label_col,
                )
                result["point_distances"] = calculate_point_distances_from_centroid(
                    df_work, x_col="x_norm", y_col="F1", label_col=label_col
                )
            else:
                df_hz = df[[label_col, "F1", "F2"]].copy()
                df_hz["x_hz"] = x_vals
                result = analyze_vowels(
                    df_hz,
                    x_col="x_hz",
                    y_col="F1",
                    label_col=label_col,
                )
                result["point_distances"] = (
                    calculate_point_distances_from_centroid_bark(
                        df, label_col=label_col, x_hz=x_vals
                    )
                )
            self._analysis_results.append((name, result))
            stack = self._add_table_tab(name, result, df_hz if not norm else df_work)
            if stack:
                # 페이지 전환 시 상태 업데이트
                stack.currentChanged.connect(self._update_save_buttons_state)

        # 탭 전환 시에도 상태 업데이트
        self.tabs.currentChanged.connect(self._update_save_buttons_state)

    def _set_initial_tab(self):
        """Plot 창에서 보고 있던 파일 탭을 Analysis 창에서도 선택."""
        idx = min(max(0, self._initial_tab_idx), self.tabs.count() - 1)
        if idx >= 0:
            self.tabs.setCurrentIndex(idx)

    def _add_empty_tab(self, tab_label, message):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel(message))
        self.tabs.addTab(w, truncate_display_name(tab_label, MAX_DISPLAY_NAME_LEN))

    def _add_table_tab(self, tab_label, result, df):
        if not result or not result.get("statistics"):
            self._add_empty_tab(tab_label, "분석 결과 없음")
            return
        stats = result["statistics"]
        point_dist = result.get("point_distances") or {}
        vowels = sorted(stats.keys())
        widths = [VOWEL_COL_WIDTH] + [DATA_COL_WIDTH] * 8
        n_data_rows = len(vowels)
        n_header_rows = 2
        table = CopyableTableWidget(n_header_rows + n_data_rows, 9)
        table.horizontalHeader().setVisible(False)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Focus Rect 제거
        table.setCurrentCell(-1, -1)  # 초기 포커스 셀 제거
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #E4E7ED; border-radius: 4px; gridline-color: transparent; }
            QTableWidget::item { padding: 6px 4px; color: #303133; border: none; }
        """)
        table.setItemDelegate(_DataRowVerticalLineDelegate(n_header_rows, table))
        hh = table.horizontalHeader()
        for c, w in enumerate(widths):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            hh.resizeSection(c, w)

        header_bg = QBrush(QColor("#F5F7FA"))
        header_font = QFont()
        header_font.setBold(True)

        def set_header_item(row, col, text):
            it = QTableWidgetItem(text)
            it.setBackground(header_bg)
            it.setFont(header_font)
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, col, it)
            return it

        # Row 0: 빈칸 | F1 또는 nF1 | X축 라벨 | 중심-개별 거리 (정규화 시 (Bark) 생략)
        norm = getattr(self, "_normalization", None)
        y_label = "nF1" if norm else "F1"
        dist_label = "중심-개별 거리" if norm else "중심-개별 거리(Bark)"
        set_header_item(0, 0, "")
        set_header_item(0, 1, y_label)
        set_header_item(0, 4, self._x_axis_label)
        set_header_item(0, 7, dist_label)
        table.setSpan(0, 1, 1, 3)
        table.setSpan(0, 4, 1, 3)
        table.setSpan(0, 7, 1, 2)
        # Row 1: 빈칸 | 평균 SD range | 평균 SD range | 평균 SD
        set_header_item(1, 0, "")
        for c, text in enumerate(
            ["평균", "SD", "range", "평균", "SD", "range", "평균", "SD"]
        ):
            set_header_item(1, c + 1, text)

        # Gerstman: 큰 수 → .1f mean/SD, 정수 range. 그 외 정규화: 소수 넷째 자리. 비정규화: 기존
        is_gerstman = norm == "Gerstman"
        if norm and not is_gerstman:
            fmt_y, fmt_x, fmt_r, fmt_d = (
                _fmt_norm_small,
                _fmt_norm_small,
                _fmt_norm_small,
                _fmt_norm_small,
            )
        elif is_gerstman:
            fmt_y, fmt_x, fmt_r, fmt_d = (
                _fmt_mean_sd,
                _fmt_mean_sd,
                _fmt_range,
                _fmt_mean_sd,
            )
        else:
            fmt_y, fmt_x, fmt_r, fmt_d = (
                _fmt_mean_sd,
                _fmt_mean_sd,
                _fmt_range,
                _fmt_bark,
            )
        for row, v in enumerate(vowels):
            s = stats[v]
            pd_v = point_dist.get(v, {})
            r = row + n_header_rows
            table.setItem(r, 0, QTableWidgetItem(str(v)))
            table.setItem(r, 1, QTableWidgetItem(fmt_y(s["y_mean"])))
            table.setItem(r, 2, QTableWidgetItem(fmt_y(s["y_std"])))
            table.setItem(r, 3, QTableWidgetItem(fmt_r(s["y_range"])))
            table.setItem(r, 4, QTableWidgetItem(fmt_x(s["x_mean"])))
            table.setItem(r, 5, QTableWidgetItem(fmt_x(s["x_std"])))
            table.setItem(r, 6, QTableWidgetItem(fmt_r(s["x_range"])))
            table.setItem(r, 7, QTableWidgetItem(fmt_d(pd_v.get("distance_mean"))))
            table.setItem(r, 8, QTableWidgetItem(fmt_d(pd_v.get("distance_std"))))

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        stack = QStackedWidget()
        stack.addWidget(table)  # Page 0: Formant Table

        # Page 1: Pillai Score Interactive Page
        pillai_page = PillaiScorePage(
            df,
            x_col="x_norm" if norm else "x_hz",
            y_col="F1",
            label_col="Label" if "Label" in df.columns else "label",
        )
        pillai_page.selectionStateChanged.connect(self._update_save_buttons_state)
        stack.addWidget(pillai_page)

        layout.addWidget(stack)
        self._stacked_widgets.append(stack)
        self.tabs.addTab(w, truncate_display_name(tab_label, MAX_DISPLAY_NAME_LEN))
        return stack

    def _current_file_name_and_result(self):
        """현재 선택된 탭의 (file_name, result_dict) 반환."""
        tab_idx = self.tabs.currentIndex()
        if tab_idx < 0 or tab_idx >= len(self._analysis_results):
            return None, None

        stack = self._stacked_widgets[tab_idx]
        if stack.currentIndex() == 1:
            # Pillai Score 결과 저장을 위해 특수 데이터 반환 예정 (후속 작업에서 보완 가능)
            # 여기서는 일단 기존 result를 반환하되, Pillai 전용 저장 로직이 _save_excel 내부에 필요함
            pass

        return self._analysis_results[tab_idx]

    def _initial_save_dir(self):
        if getattr(self.controller, "last_save_dir", None):
            return self.controller.last_save_dir
        return (
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DownloadLocation
            )
            or ""
        )

    def _save_excel(self):
        name, result = self._current_file_name_and_result()
        if not name or result is None:
            QMessageBox.information(self, "저장", "저장할 분석 데이터가 없습니다.")
            return

        current_tab_idx = self.tabs.currentIndex()
        stack = self._stacked_widgets[current_tab_idx]
        is_pillai = stack.currentIndex() == 1

        if is_pillai:
            # Pillai Score 조합 결과 저장
            pillai_page = stack.currentWidget()
            if (
                isinstance(pillai_page, PillaiScorePage)
                and pillai_page.selection_count >= 3
            ):
                data = pillai_page.get_combination_results()
                df = pd.DataFrame(data, columns=["모음 조합", "Pillai Score"])

                # Suffix: _pillai_analysis
                base_name = _analysis_base_name(
                    name, self.fixed_plot_params, is_pillai=True
                )
                path, _ = QFileDialog.getSaveFileName(
                    self,
                    "엑셀 저장",
                    os.path.join(self._initial_save_dir(), base_name + ".xlsx"),
                    "Excel Files (*.xlsx)",
                )
                if path:
                    df.to_excel(path, index=False)
                    if hasattr(self.controller, "set_last_save_dir"):
                        self.controller.set_last_save_dir(os.path.dirname(path))
                    QMessageBox.information(
                        self, "저장 완료", f"저장되었습니다:\n{path}"
                    )
                return

        # Suffix: _analysis
        base_name = _analysis_base_name(name, self.fixed_plot_params, is_pillai=False)
        initial_dir = self._initial_save_dir()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "엑셀 저장",
            os.path.join(initial_dir, base_name + ".xlsx"),
            "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            _export_to_excel(
                result, path, self._x_axis_label, normalized=bool(self._normalization)
            )
            if hasattr(self.controller, "set_last_save_dir"):
                self.controller.set_last_save_dir(os.path.dirname(path))
            QMessageBox.information(self, "저장 완료", f"저장되었습니다:\n{path}")
        except ImportError:
            QMessageBox.warning(
                self,
                "엑셀 저장",
                "엑셀 저장을 위해 openpyxl이 필요합니다.\npip install openpyxl",
            )
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", str(e))

    def _save_csv(self):
        name, result = self._current_file_name_and_result()
        if not name or result is None:
            QMessageBox.information(self, "저장", "저장할 분석 데이터가 없습니다.")
            return

        current_tab_idx = self.tabs.currentIndex()
        stack = self._stacked_widgets[current_tab_idx]
        is_pillai = stack.currentIndex() == 1

        if is_pillai:
            # Pillai Score 조합 결과 저장
            pillai_page = stack.currentWidget()
            if (
                isinstance(pillai_page, PillaiScorePage)
                and pillai_page.selection_count >= 3
            ):
                data = pillai_page.get_combination_results()
                df = pd.DataFrame(data, columns=["모음 조합", "Pillai Score"])

                # Suffix: _pillai_analysis
                base_name = _analysis_base_name(
                    name, self.fixed_plot_params, is_pillai=True
                )
                path, _ = QFileDialog.getSaveFileName(
                    self,
                    "CSV 저장",
                    os.path.join(self._initial_save_dir(), base_name + ".csv"),
                    "CSV Files (*.csv)",
                )
                if path:
                    df.to_csv(path, index=False, encoding="utf-8-sig")
                    if hasattr(self.controller, "set_last_save_dir"):
                        self.controller.set_last_save_dir(os.path.dirname(path))
                    QMessageBox.information(
                        self, "저장 완료", f"저장되었습니다:\n{path}"
                    )
                return

        # Suffix: _analysis
        base_name = _analysis_base_name(name, self.fixed_plot_params, is_pillai=False)
        initial_dir = self._initial_save_dir()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "CSV 저장",
            os.path.join(initial_dir, base_name + ".csv"),
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            _export_to_csv(
                result, path, self._x_axis_label, normalized=bool(self._normalization)
            )
            if hasattr(self.controller, "set_last_save_dir"):
                self.controller.set_last_save_dir(os.path.dirname(path))
            QMessageBox.information(self, "저장 완료", f"저장되었습니다:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", str(e))


def _fmt_mean_sd(val):
    """평균·SD: 소수점 첫째 자리까지 고정 (예: 851 -> 851.0)."""
    if val is None:
        return ""
    try:
        return f"{float(val):.1f}"
    except (TypeError, ValueError):
        return str(val)


def _fmt_range(val):
    """Range: 정수만 표기."""
    if val is None:
        return ""
    try:
        return f"{int(round(float(val)))}"
    except (TypeError, ValueError):
        return str(val)


def _fmt_bark(val):
    """중심-개별 거리(Bark) 평균·SD: 소수점 넷째 자리까지."""
    if val is None:
        return ""
    try:
        return f"{float(val):.4f}"
    except (TypeError, ValueError):
        return str(val)


def _fmt_norm_small(val):
    """정규화(비-Gerstman) 값: 소수점 넷째 자리까지."""
    if val is None:
        return ""
    try:
        return f"{float(val):.4f}"
    except (TypeError, ValueError):
        return str(val)


def _result_to_dataframe(result, x_axis_label, normalized=False):
    """analyze_vowels 결과를 표와 동일한 열 구조의 DataFrame으로 만든다. 정규화 시 nF1/nF2·거리 컬럼명."""
    import pandas as pd

    stats = result.get("statistics") or {}
    point_dist = result.get("point_distances") or {}
    vowels = sorted(stats.keys())
    y_pre = "nF1" if normalized else "F1"
    dist_mean_col = "중심-개별 거리 평균" if normalized else "중심-개별 거리(Bark) 평균"
    dist_sd_col = "중심-개별 거리 SD" if normalized else "중심-개별 거리(Bark) SD"
    rows = []
    for v in vowels:
        s = stats[v]
        pd_v = point_dist.get(v, {})
        rows.append(
            {
                "모음": v,
                f"{y_pre} 평균": s["y_mean"],
                f"{y_pre} SD": s["y_std"],
                f"{y_pre} range": s["y_range"],
                f"{x_axis_label} 평균": s["x_mean"],
                f"{x_axis_label} SD": s["x_std"],
                f"{x_axis_label} range": s["x_range"],
                dist_mean_col: pd_v.get("distance_mean"),
                dist_sd_col: pd_v.get("distance_std"),
            }
        )
    return pd.DataFrame(rows)


def _export_to_excel(result, path, x_axis_label="F2", normalized=False):

    try:
        import openpyxl  # noqa: F401
    except ImportError:
        raise ImportError("openpyxl")
    df = _result_to_dataframe(result, x_axis_label, normalized=normalized)
    df.to_excel(path, index=False, engine="openpyxl")


def _export_to_csv(result, path, x_axis_label, normalized=False):

    df = _result_to_dataframe(result, x_axis_label, normalized=normalized)
    df.to_csv(path, index=False, encoding="utf-8-sig")


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
            "font-size: 16px; font-weight: bold; color: #303133; border: none;"
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

        # 1. 모음 선택 테이블 (2열 배치)
        vowel_counts = self.df[self.label_col].value_counts().to_dict()
        self._vowel_list = sorted(list(vowel_counts.keys()))

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
            list(set(it.data(Qt.ItemDataRole.UserRole) for it in selected_items))
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
