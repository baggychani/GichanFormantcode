import base64
import platform
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon, QPixmap

from utils import icon_utils


class DataGuidePopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("데이터 파일 준비 가이드")
        self.setFixedSize(580, 550)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._apply_pyqt6_icon()
        self.ui_font_name = (
            "Malgun Gothic" if platform.system() == "Windows" else "AppleGothic"
        )
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
        self.setStyleSheet("background-color: #F9FAFB;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 15)
        main_layout.setSpacing(0)

        title_lbl = QLabel("데이터 파일 준비 가이드")
        title_lbl.setFont(QFont(self.ui_font_name, 16, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #2c3e50; margin-bottom: 15px;")
        main_layout.addWidget(title_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(10)

        def create_card(title, widget_items):
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background-color: white; border: 1px solid #E5E7EB; border-radius: 10px; padding: 2px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 20, 20, 20)
            card_layout.setSpacing(5)

            t_lbl = QLabel(title)
            t_lbl.setFont(QFont(self.ui_font_name, 11, QFont.Weight.Bold))
            t_lbl.setStyleSheet("color: #1565C0; border: none;")
            card_layout.addWidget(t_lbl)

            for w in widget_items:
                card_layout.addWidget(w)

            return card

        def make_lbl(text, color="#374151", size=10):
            lbl = QLabel(text)
            lbl.setFont(QFont(self.ui_font_name, size))
            lbl.setStyleSheet(f"color: {color}; border: none; line-height: 1.5;")
            lbl.setWordWrap(True)
            return lbl

        # 1. 지원 파일
        sec1_lbl1 = make_lbl(
            "GichanFormant는 <b>.txt, .xlsx, .csv, .tsv</b> 파일을 지원합니다."
        )
        sec1_lbl2 = make_lbl(
            "여러 파일을 동시에 클릭 또는 드래그 앤 드롭으로 로드할 수 있습니다."
        )
        sec1_lbl3 = make_lbl(
            "(단, 한 번에 수백 개의 파일을 무리하게 넣으면 성능이 저하될 수 있습니다.)",
            "#666666",
            9,
        )

        content_layout.addWidget(
            create_card(
                "1. 지원 파일 및 로드 가이드", [sec1_lbl1, sec1_lbl2, sec1_lbl3]
            )
        )

        # 2. 열 구성 및 예외 처리
        sec2_lbl1 = make_lbl("• 1열 (A열): <b>F1</b>")
        sec2_lbl2 = make_lbl("• 2열 (B열): <b>F2</b>")
        sec2_lbl3 = make_lbl("• 3열 (C열): <b>F3</b> (선택), 그 다음 열: <b>라벨</b>.")
        sec2_lbl3_sub = make_lbl(
            "  F1~F3까지만 포먼트 데이터로 인식하며 F4부터는 지원하지 않습니다."
        )
        sec2_lbl4 = make_lbl(
            '- 첫 번째 줄(1행)에 헤더(예: "F1", "F2" 등)가 있어도 자동으로 무시됩니다.',
            "#666666",
            9,
        )

        table_html = """
        <table width="100%" cellpadding="6" cellspacing="0" style="background-color: #F3F4F6; border-radius: 6px;">
            <tr><td align="center">730</td><td align="center">1090</td><td align="center"></td><td align="center"><b><font color="#1f2937">/a/</font></b></td></tr>
            <tr><td align="center">320</td><td align="center">2250</td><td align="center"></td><td align="center"><b><font color="#1f2937">/i/</font></b></td></tr>
            <tr><td align="center">350</td><td align="center">950</td><td align="center"></td><td align="center"><b><font color="#1f2937">/u/</font></b></td></tr>
            <tr><td align="center">480</td><td align="center">1800</td><td align="center"></td><td align="center"><b><font color="#1f2937">/e/</font></b></td></tr>
        </table>
        """
        sec2_table = QLabel(table_html)
        sec2_table.setStyleSheet("border: none;")

        sec2_lbl5 = make_lbl(
            "- 데이터의 소수점은 계산 시 자동으로 반올림 처리됩니다.", "#666666", 9
        )
        sec2_lbl6 = make_lbl(
            "- F1이 F2보다 큰 논리적 오류 데이터는 자동으로 제외됩니다.", "#666666", 9
        )

        content_layout.addWidget(
            create_card(
                "2. 열(Column) 구성 및 처리 규칙",
                [
                    sec2_lbl1,
                    sec2_lbl2,
                    sec2_lbl3,
                    sec2_lbl3_sub,
                    sec2_lbl4,
                    sec2_table,
                    sec2_lbl5,
                    sec2_lbl6,
                ],
            )
        )

        # 3. 모음 기호 규칙
        sec3_lbl1 = make_lbl(
            "• 모음 기호는 반드시 <b style='color: #1976d2;'>슬래시 / /</b> 기호로 감싸야 합니다."
        )

        ex_box = QFrame()
        ex_box.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB; 
                border: 1px solid #E5E7EB; 
                border-radius: 6px;
                margin-top: 10px;
                margin-bottom: 10px;
            }
        """)
        ex_layout = QVBoxLayout(ex_box)
        ex_layout.setContentsMargins(15, 15, 15, 15)
        ex_layout.setSpacing(12)

        ex_bad = make_lbl(
            "<b><span style='color: #d32f2f;'>X 잘못된 예:</span></b>&nbsp;&nbsp;&nbsp;<b>a, i, u, ㅏ, ʌ, \"e\", [ㅜ]</b>",
            size=11,
        )
        ex_good = make_lbl(
            "<b><span style='color: #1976d2;'>O 올바른 예:</span></b>&nbsp;&nbsp;&nbsp;<b>/a/, /i/, /u/, /ㅏ/, /ʌ/, /aː/</b> (ː=장음 기호)",
            size=11,
        )
        ex_layout.addWidget(ex_bad)
        ex_layout.addWidget(ex_good)

        sec3_lbl2 = make_lbl(
            "- 기호는 로마자, 한글, IPA, 장음 기호(ː) 등 모두 사용 가능합니다.",
            "#666666",
            9,
        )
        sec3_lbl3 = make_lbl(
            "- 슬래시가 없는 데이터는 분석에서 제외됩니다.", "#666666", 9
        )

        content_layout.addWidget(
            create_card(
                "3. 모음 기호(Label) 규칙", [sec3_lbl1, ex_box, sec3_lbl2, sec3_lbl3]
            )
        )

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 15, 0, 5)
        close_btn = QPushButton("가이드 확인 완료")
        close_btn.setFixedWidth(200)
        close_btn.setFixedHeight(40)
        close_btn.setFont(QFont(self.ui_font_name, 10, QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background-color: #2c3e50; color: white; border-radius: 20px; border: none; }
            QPushButton:hover { background-color: #34495e; }
        """)
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
