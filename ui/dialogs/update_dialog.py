# ui/dialogs/update_dialog.py

import html

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

import config
from ui.widgets.icon_widgets import create_github_mark_icon

_UPDATE_DIALOG_TITLE = "업데이트가 준비되었습니다!"


class CustomUpdateDialog(QDialog):
    """업데이트 알림 다이얼로그."""

    def __init__(self, parent, version, url, notes, ui_font_name="Malgun Gothic"):
        super().__init__(parent)
        self.setWindowTitle(_UPDATE_DIALOG_TITLE)
        self.setFixedWidth(440)

        font_title = QFont(ui_font_name, 13, QFont.Weight.Bold)
        font_body = QFont(ui_font_name, 9)
        font_caption = QFont(ui_font_name, 9)
        font_badge = QFont(ui_font_name, 10, QFont.Weight.DemiBold)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(0)

        title = QLabel(_UPDATE_DIALOG_TITLE)
        title.setFont(font_title)
        title.setStyleSheet("color: #303133;")
        layout.addWidget(title)
        layout.addSpacing(4)

        subtitle = QLabel("GitHub Releases에서 최신 설치 파일을 받을 수 있습니다.")
        subtitle.setFont(font_caption)
        subtitle.setStyleSheet("color: #909399;")
        layout.addWidget(subtitle)

        layout.addSpacing(18)

        version_row = QHBoxLayout()
        version_row.setSpacing(10)
        lbl_current = QLabel(f"현재  {config.APP_VERSION}")
        lbl_current.setFont(font_badge)
        lbl_current.setStyleSheet(
            "color: #606266; background: #f5f7fa; border: 1px solid #e4e7ed;"
            "border-radius: 4px; padding: 6px 10px;"
        )
        arrow = QLabel("→")
        arrow.setFont(font_badge)
        arrow.setStyleSheet("color: #c0c4cc;")
        lbl_latest = QLabel(f"최신  {version}")
        lbl_latest.setFont(font_badge)
        lbl_latest.setStyleSheet(
            "color: #409eff; background: #ecf5ff; border: 1px solid #b3d8ff;"
            "border-radius: 4px; padding: 6px 10px;"
        )
        version_row.addWidget(lbl_current)
        version_row.addWidget(arrow)
        version_row.addWidget(lbl_latest)
        version_row.addStretch()
        layout.addLayout(version_row)

        if notes:
            layout.addSpacing(16)
            notes_title = QLabel("릴리스 노트")
            notes_title.setFont(font_body)
            notes_title.setStyleSheet("color: #606266;")
            layout.addWidget(notes_title)
            layout.addSpacing(6)

            notes_frame = QFrame()
            notes_frame.setObjectName("release_notes_frame")
            notes_frame_layout = QVBoxLayout(notes_frame)
            notes_frame_layout.setContentsMargins(0, 0, 0, 0)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            scroll.setMaximumHeight(132)

            notes_body = html.escape(notes.strip()).replace("\n", "<br>")
            notes_area = QLabel(
                f'<div style="line-height: 148%; color: #606266;">{notes_body}</div>'
            )
            notes_area.setFont(font_body)
            notes_area.setWordWrap(True)
            notes_area.setTextFormat(Qt.TextFormat.RichText)
            notes_area.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            notes_area.setContentsMargins(12, 10, 12, 10)
            scroll.setWidget(notes_area)
            notes_frame_layout.addWidget(scroll)
            layout.addWidget(notes_frame)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ebeef5;")
        layout.addSpacing(18)
        layout.addWidget(sep)
        layout.addSpacing(14)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch(1)

        btn_later = QPushButton("나중에")
        btn_later.setObjectName("btn_later")
        btn_later.setMinimumSize(88, 36)
        btn_later.setFont(font_body)
        btn_later.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_later.clicked.connect(self.reject)

        btn_update = QPushButton("지금 업데이트")
        btn_update.setObjectName("btn_update")
        btn_update.setMinimumSize(148, 36)
        btn_update.setFont(font_body)
        btn_update.setIcon(
            create_github_mark_icon(size=16, color="#ffffff", gap_after=6)
        )
        btn_update.setIconSize(QSize(22, 16))
        btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_update.setDefault(True)
        btn_update.clicked.connect(self.accept)

        btn_layout.addWidget(btn_later)
        btn_layout.addWidget(btn_update)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QFrame#release_notes_frame {
                background-color: #f5f7fa;
                border: 1px solid #e4e7ed;
                border-radius: 6px;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
                margin: 4px 2px 4px 0;
            }
            QScrollBar::handle:vertical {
                background: #c0c4cc;
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #909399;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QPushButton#btn_later {
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                background-color: #ffffff;
                color: #606266;
                font-weight: 500;
                padding: 0 14px;
            }
            QPushButton#btn_later:hover {
                background-color: #f5f7fa;
                border-color: #c0c4cc;
            }
            QPushButton#btn_update {
                border: 1px solid #409eff;
                border-radius: 4px;
                background-color: #409eff;
                color: #ffffff;
                font-weight: 500;
                padding: 0 16px 0 12px;
            }
            QPushButton#btn_update:hover {
                background-color: #66b1ff;
                border-color: #66b1ff;
            }
        """)
