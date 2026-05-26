import platform
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QCursor

from utils import icon_utils
from ui.widgets.scroll_styles import MODERN_SCROLLBAR_STYLE

_BODY_SIZE = 9
_NOTE_SIZE = 9
_CARD_TITLE_SIZE = 10
_RULES_NOTE_SPACING = 5
_BEFORE_EXAMPLE_GAP = 18

_COLUMN_EXAMPLES = (
    {
        "caption": "헤더 포함 · F1 · F2 · F3 · 라벨",
        "note": "1행에 F1, F2 등의 헤더가 있어도 자동으로 무시됩니다.",
        "headers": ("F1", "F2", "F3", "라벨"),
        "rows": (
            ("730", "1090", "2800", "/a/"),
            ("320", "2250", "3100", "/i/"),
            ("350", "950", "870", "/u/"),
            ("480", "1800", "2600", "/e/"),
        ),
        "show_header": True,
    },
    {
        "caption": "헤더 포함 · F1 · F2 · 라벨 (F3 열 없음)",
        "note": "F3를 쓰지 않을 때는 C열을 비워 두지 말고 라벨 열을 바로 붙이면 됩니다.",
        "headers": ("F1", "F2", "라벨"),
        "rows": (
            ("730", "1090", "/a/"),
            ("320", "2250", "/i/"),
            ("350", "950", "/u/"),
            ("480", "1800", "/e/"),
        ),
        "show_header": True,
    },
    {
        "caption": "소수점 포함 (전체 데이터에 일괄 적용)",
        "note": "소수점은 계산 시 자동으로 반올림됩니다. 모든 행에 동일하게 쓰면 됩니다.",
        "headers": ("F1", "F2", "라벨"),
        "rows": (
            ("730.4", "1089.7", "/a/"),
            ("320.2", "2248.5", "/i/"),
            ("350.8", "948.3", "/u/"),
            ("480.1", "1799.6", "/e/"),
        ),
        "show_header": True,
    },
    {
        "caption": "헤더 없이 · F1 · F2 · 라벨 (F3 열 생략)",
        "note": "첫 줄부터 데이터여도 되며, F3 열 없이 F2 다음에 라벨을 둘 수 있습니다.",
        "headers": ("F1", "F2", "라벨"),
        "rows": (
            ("730", "1090", "/a/"),
            ("320", "2250", "/i/"),
            ("350", "950", "/u/"),
            ("480", "1800", "/e/"),
        ),
        "show_header": False,
    },
)


def _make_rules_note_box(ui_font_name: str, lines: tuple[str, ...]) -> QFrame:
    box = QFrame()
    box.setStyleSheet(
        """
        QFrame {
            background-color: #FAFBFC;
            border: 1px solid #EBEEF5;
            border-radius: 6px;
        }
        """
    )
    layout = QVBoxLayout(box)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(_RULES_NOTE_SPACING)
    for text in lines:
        lbl = QLabel(text)
        lbl.setFont(QFont(ui_font_name, _NOTE_SIZE))
        lbl.setStyleSheet("color: #606266; border: none;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
    return box


def _make_vertical_gap(height: int) -> QWidget:
    gap = QWidget()
    gap.setFixedHeight(height)
    gap.setStyleSheet("background: transparent; border: none;")
    return gap


def _column_layout_table_html() -> str:
    return f"""
    <table width="100%" cellpadding="10" cellspacing="0"
           style="background-color: #FFFFFF; border: 1px solid #EBEEF5;
                  border-radius: 6px; font-size: {_BODY_SIZE + 1}pt; color: #606266;">
        <tr style="background-color: #F5F7FA; color: #909399; font-size: {_NOTE_SIZE}pt;">
            <td align="center" width="25%"><b>1열 (A열)</b></td>
            <td align="center" width="25%"><b>2열 (B열)</b></td>
            <td align="center" width="25%"><b>3열 (C열)</b></td>
            <td align="center" width="25%"><b>4열 (D열)</b></td>
        </tr>
        <tr style="color: #303133;">
            <td align="center"><b>F1</b></td>
            <td align="center"><b>F2</b></td>
            <td align="center"><b>F3</b>
                <span style="color:#909399; font-weight:normal;"> (선택)</span></td>
            <td align="center"><b>라벨</b></td>
        </tr>
    </table>
    """


def _format_label_cell(value: str) -> str:
    return f'<b><font color="#303133">{value}</font></b>'


def _example_table_html(example: dict) -> str:
    headers = example["headers"]
    label_idx = len(headers) - 1
    header_row = ""
    if example["show_header"]:
        cells = "".join(
            f'<td align="center">{h}</td>' for h in headers
        )
        header_row = (
            f'<tr style="color: #909399; font-size: {_NOTE_SIZE + 1}pt;">'
            f"{cells}</tr>"
        )
    body_rows = []
    for row in example["rows"]:
        cells = []
        for idx, value in enumerate(row):
            if idx == label_idx:
                cells.append(
                    f'<td align="center">{_format_label_cell(value)}</td>'
                )
            else:
                cells.append(f'<td align="center">{value}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"""
    <table width="100%" cellpadding="8" cellspacing="0"
           style="background-color: #F5F7FA; border: 1px solid #EBEEF5;
                  border-radius: 6px; font-size: {_BODY_SIZE + 1}pt;">
        {header_row}
        {''.join(body_rows)}
    </table>
    """


class _FormatExampleCarousel(QWidget):
    _NAV_BTN_STYLE = """
        QPushButton {
            background-color: #FFFFFF;
            border: 1px solid #DCDFE6;
            border-radius: 15px;
            color: #606266;
            font-size: 11px;
            font-weight: bold;
            min-width: 30px;
            max-width: 30px;
            min-height: 30px;
            max-height: 30px;
            padding: 0px;
        }
        QPushButton:hover {
            background-color: #409EFF;
            border-color: #409EFF;
            color: #FFFFFF;
        }
        QPushButton:pressed { background-color: #3A8EE6; }
        QPushButton:disabled {
            background-color: #F5F7FA;
            border-color: #EBEEF5;
            color: #C0C4CC;
        }
        QPushButton:hover:disabled {
            background-color: #F5F7FA;
            border-color: #EBEEF5;
            color: #C0C4CC;
        }
    """

    def __init__(self, ui_font_name: str, parent=None):
        super().__init__(parent)
        self._ui_font_name = ui_font_name
        self._index = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(8)

        self._caption = QLabel()
        self._caption.setFont(
            QFont(self._ui_font_name, _BODY_SIZE, QFont.Weight.Bold)
        )
        self._caption.setStyleSheet("color: #303133; border: none;")
        self._caption.setWordWrap(True)
        layout.addWidget(self._caption)

        self._note = QLabel()
        self._note.setFont(QFont(self._ui_font_name, _NOTE_SIZE))
        self._note.setStyleSheet("color: #909399; border: none;")
        self._note.setWordWrap(True)
        layout.addWidget(self._note)

        self._table = QLabel()
        self._table.setStyleSheet("border: none; margin: 0;")
        self._table.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._table)

        nav = QHBoxLayout()
        nav.setContentsMargins(0, 2, 0, 0)
        nav.setSpacing(10)

        self._prev_btn = QPushButton("◀")
        self._prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._prev_btn.setStyleSheet(self._NAV_BTN_STYLE)
        self._prev_btn.clicked.connect(self._show_prev)

        self._page_lbl = QLabel()
        self._page_lbl.setFont(QFont(self._ui_font_name, _NOTE_SIZE))
        self._page_lbl.setStyleSheet("color: #909399; border: none;")
        self._page_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_lbl.setMinimumWidth(48)

        self._next_btn = QPushButton("▶")
        self._next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._next_btn.setStyleSheet(self._NAV_BTN_STYLE)
        self._next_btn.clicked.connect(self._show_next)

        nav.addStretch()
        nav.addWidget(self._prev_btn)
        nav.addWidget(self._page_lbl)
        nav.addWidget(self._next_btn)
        nav.addStretch()
        layout.addLayout(nav)

        self._render()

    def _render(self):
        example = _COLUMN_EXAMPLES[self._index]
        total = len(_COLUMN_EXAMPLES)
        self._caption.setText(example["caption"])
        self._note.setText(example["note"])
        self._table.setText(_example_table_html(example))
        self._page_lbl.setText(f"{self._index + 1} / {total}")
        at_first = self._index <= 0
        at_last = self._index >= total - 1
        self._prev_btn.setEnabled(not at_first)
        self._next_btn.setEnabled(not at_last)
        self._prev_btn.setCursor(
            Qt.CursorShape.ArrowCursor
            if at_first
            else QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self._next_btn.setCursor(
            Qt.CursorShape.ArrowCursor
            if at_last
            else QCursor(Qt.CursorShape.PointingHandCursor)
        )

    def _show_prev(self):
        if self._index > 0:
            self._index -= 1
            self._render()

    def _show_next(self):
        if self._index < len(_COLUMN_EXAMPLES) - 1:
            self._index += 1
            self._render()


class DataGuidePopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("데이터 파일 준비 가이드")
        self.setFixedSize(600, 560)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._apply_window_icon()
        self.ui_font_name = (
            "Malgun Gothic" if platform.system() == "Windows" else "AppleGothic"
        )
        self._setup_ui()

    def _apply_window_icon(self):
        try:
            self.setWindowIcon(icon_utils.get_app_icon())
        except Exception:
            pass

    def _setup_ui(self):
        self.setStyleSheet(
            f"""
            QDialog {{ background-color: #F5F7FA; }}
            {MODERN_SCROLLBAR_STYLE}
        """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 16)
        main_layout.setSpacing(0)

        title_lbl = QLabel("데이터 파일 준비 가이드")
        title_lbl.setFont(QFont(self.ui_font_name, 15, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #303133; margin-bottom: 4px;")
        main_layout.addWidget(title_lbl)

        subtitle = QLabel("아래 형식에 맞춰 파일을 준비해 주세요.")
        subtitle.setFont(QFont(self.ui_font_name, _BODY_SIZE))
        subtitle.setStyleSheet("color: #909399; margin-bottom: 12px;")
        main_layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 4, 0)
        content_layout.setSpacing(12)

        def create_card(title, widget_items):
            card = QFrame()
            card.setStyleSheet(
                """
                QFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #EBEEF5;
                    border-radius: 8px;
                }
                """
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 16, 18, 16)
            card_layout.setSpacing(10)

            t_lbl = QLabel(title)
            t_lbl.setFont(
                QFont(self.ui_font_name, _CARD_TITLE_SIZE, QFont.Weight.Bold)
            )
            t_lbl.setStyleSheet("color: #409EFF; border: none; padding-bottom: 2px;")
            card_layout.addWidget(t_lbl)

            for w in widget_items:
                card_layout.addWidget(w)

            return card

        def make_lbl(text, color="#606266", size=_BODY_SIZE, bold=False):
            lbl = QLabel(text)
            weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
            lbl.setFont(QFont(self.ui_font_name, size, weight))
            lbl.setStyleSheet(f"color: {color}; border: none;")
            lbl.setWordWrap(True)
            lbl.setTextFormat(Qt.TextFormat.RichText)
            return lbl

        # 1. 지원 파일
        sec1_lbl1 = make_lbl(
            "GichanFormant는 <b>.txt, .xlsx, .csv, .tsv</b> 파일을 지원합니다."
        )
        sec1_lbl2 = make_lbl(
            "여러 파일을 동시에 클릭 또는 드래그 앤 드롭으로 로드할 수 있습니다."
        )
        sec1_lbl3 = make_lbl(
            "한 번에 수백 개의 파일을 넣으면 성능이 저하될 수 있습니다.",
            "#909399",
            _NOTE_SIZE,
        )

        content_layout.addWidget(
            create_card(
                "1. 지원 파일 및 로드",
                [sec1_lbl1, sec1_lbl2, sec1_lbl3],
            )
        )

        # 2. 열 구성
        sec2_cols_table = QLabel(_column_layout_table_html())
        sec2_cols_table.setTextFormat(Qt.TextFormat.RichText)
        sec2_cols_table.setStyleSheet("border: none;")
        sec2_cols_note = make_lbl(
            "F3 없이 F2 다음 열(<b>C열</b>)에 <b>라벨</b>을 바로 둬도 됩니다.",
            "#F56C6C",
            _NOTE_SIZE,
        )
        sec2_rules = _make_rules_note_box(
            self.ui_font_name,
            (
                "F1~F3까지만 포먼트 데이터로 인식하며 F4부터는 지원하지 않습니다.",
                '첫 번째 줄(1행)에 헤더(예: "F1", "F2" 등)가 있어도 자동으로 무시됩니다.',
                "F1이 F2보다 큰 논리적 오류 데이터는 자동으로 제외됩니다.",
            ),
        )
        sec2_before_examples = _make_vertical_gap(_BEFORE_EXAMPLE_GAP)
        sec2_carousel = _FormatExampleCarousel(self.ui_font_name)

        content_layout.addWidget(
            create_card(
                "2. 열(Column) 구성 및 처리 규칙",
                [
                    sec2_cols_table,
                    sec2_cols_note,
                    sec2_rules,
                    sec2_before_examples,
                    sec2_carousel,
                ],
            )
        )

        # 3. 모음 기호 규칙
        sec3_lbl1 = make_lbl(
            "모음 기호는 반드시 <b style='color: #409EFF;'>슬래시 / /</b> 기호로 감싸야 합니다."
        )

        ex_box = QFrame()
        ex_box.setStyleSheet(
            """
            QFrame {
                background-color: #FAFBFC;
                border: 1px solid #EBEEF5;
                border-radius: 6px;
            }
            """
        )
        ex_layout = QVBoxLayout(ex_box)
        ex_layout.setContentsMargins(14, 10, 14, 10)
        ex_layout.setSpacing(8)

        ex_bad = make_lbl(
            "<span style='color: #F56C6C; font-weight: bold;'>✕ 잘못된 예</span>"
            "&nbsp;&nbsp;<b>a, i, u, ㅏ, ʌ, \"e\", [ㅜ]</b>",
            size=_BODY_SIZE,
        )
        ex_good = make_lbl(
            "<span style='color: #409EFF; font-weight: bold;'>✓ 올바른 예</span>"
            "&nbsp;&nbsp;<b>/a/, /i/, /u/, /ㅏ/, /ʌ/, /e/, /aː/</b>",
            size=_BODY_SIZE,
        )
        ex_layout.addWidget(ex_bad)
        ex_layout.addWidget(ex_good)

        sec3_lbl2 = make_lbl(
            "기호는 로마자, 한글, IPA, 장음(ː) 등 다양한 표기를 사용할 수 있습니다.",
            "#909399",
            _NOTE_SIZE,
        )
        sec3_lbl3 = make_lbl(
            "슬래시가 없는 데이터는 분석에서 제외됩니다.", "#909399", _NOTE_SIZE
        )

        content_layout.addWidget(
            create_card(
                "3. 모음 기호(Label) 규칙",
                [sec3_lbl1, ex_box, sec3_lbl2, sec3_lbl3],
            )
        )

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 14, 0, 0)
        close_btn = QPushButton("확인")
        close_btn.setFixedWidth(160)
        close_btn.setFixedHeight(36)
        close_btn.setFont(QFont(self.ui_font_name, 10, QFont.Weight.Bold))
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #409EFF;
                color: white;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover { background-color: #66B1FF; }
            QPushButton:pressed { background-color: #3A8EE6; }
            """
        )
        close_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        else:
            super().keyPressEvent(event)
