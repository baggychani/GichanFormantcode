# ui/dialogs/update_dialog.py

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import Qt

import config


class CustomUpdateDialog(QDialog):
    """
    업데이트 알림 커스텀 다이얼로그
    main.py 내부에 있던 로직을 분리한 클래스입니다.
    """

    def __init__(self, parent, version, url, notes):
        super().__init__(parent)
        self.setWindowTitle("업데이트 알림")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(12)

        # 제목
        title_label = QLabel(
            f"<span style='font-size: 11pt;'><b>새로운 버전({version})이 준비되었습니다!</b></span>"
        )
        layout.addWidget(title_label)

        # 버전 정보
        info_text = (
            f"<div style='margin-bottom: 8px;'>현재 버전: {config.APP_VERSION}</div>"
            f"<div>최신 버전: <b>{version}</b></div>"
        )
        info_label = QLabel(info_text)
        layout.addWidget(info_label)

        # 릴리스 노트
        if notes:
            notes_title = QLabel("<b>[릴리스 노트]</b>")
            notes_title.setStyleSheet("color: #555;")
            layout.addWidget(notes_title)

            notes_area = QLabel(notes.strip())
            notes_area.setWordWrap(True)
            notes_area.setStyleSheet("""
                background-color: #f5f7fa; 
                padding: 12px; 
                border: 1px solid #e4e7ed;
                border-radius: 4px;
                color: #606266;
            """)
            layout.addWidget(notes_area)

        # 버튼 레이아웃
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        btn_update = QPushButton("지금 업데이트")
        btn_update.setMinimumSize(120, 36)
        btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_update.setDefault(True)
        btn_update.clicked.connect(self.accept)

        btn_later = QPushButton("나중에")
        btn_later.setMinimumSize(100, 36)
        btn_later.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_later.clicked.connect(self.reject)

        btn_layout.addWidget(btn_update)
        btn_layout.addWidget(btn_later)
        btn_layout.addStretch(1)

        layout.addLayout(btn_layout)

        # 스타일시트 적용
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel { color: #303133; }
            QPushButton { 
                border: 1px solid #dcdfe6; 
                border-radius: 4px; 
                background-color: #ffffff;
                font-weight: 500;
            }
            QPushButton:hover { 
                background-color: #f5f7fa; 
                border-color: #c0c4cc; 
            }
            QPushButton:default {
                background-color: #409eff;
                color: white;
                border-color: #409eff;
            }
            QPushButton:default:hover {
                background-color: #66b1ff;
            }
        """)
