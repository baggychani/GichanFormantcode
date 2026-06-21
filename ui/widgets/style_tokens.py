"""UI 공통 스타일 토큰."""

# 공통 색상
COLOR_PRIMARY = "#409EFF"
COLOR_PRIMARY_HOVER = "#66B1FF"
COLOR_TEXT = "#333333"
COLOR_TEXT_MUTED = "#606266"
COLOR_BORDER = "#C0C4CC"
COLOR_BORDER_LIGHT = "#DCDFE6"
COLOR_BORDER_SOFT = "#DADDE3"
COLOR_BG_HOVER = "#F5F7FA"
COLOR_BG_SOFT = "#F3F4F6"
COLOR_BG_SOFT_HOVER = "#ECEFF4"

# PopupPlot 저장 영역 버튼 높이
EXPORT_BUTTON_HEIGHT_PX = 30
PROJECT_SAVE_BUTTON_HEIGHT_PX = 30
BATCH_SAVE_BUTTON_HEIGHT_PX = 38

# 스크롤바가 있는 분석 탭에서 스크롤 영역 밖 컨트롤이 맞춰 가져야 할 우측 여백
ANALYSIS_NON_SCROLL_RIGHT_MARGIN_PX = 12

PLOT_NAV_BUTTON_STYLE = f"""
    QPushButton {{ background-color: white; border: 1px solid {COLOR_BORDER_LIGHT}; border-radius: 4px; color: {COLOR_TEXT}; }}
    QPushButton:hover {{ background-color: {COLOR_BG_HOVER}; color: {COLOR_PRIMARY}; border-color: {COLOR_BORDER}; }}
    QPushButton:disabled {{ background-color: {COLOR_BG_HOVER}; color: {COLOR_BORDER}; border-color: #E4E7ED; }}
"""

PLOT_SECONDARY_BUTTON_STYLE = f"""
    QPushButton {{ background-color: white; border: 1px solid {COLOR_BORDER}; border-radius: 4px; }}
    QPushButton:hover {{ background-color: {COLOR_BG_HOVER}; border: 1px solid #909399; }}
"""

PLOT_PRIMARY_BUTTON_STYLE = f"""
    QPushButton {{ background-color: {COLOR_PRIMARY}; color: white; font-weight: bold; border-radius: 4px; }}
    QPushButton:hover {{ background-color: {COLOR_PRIMARY_HOVER}; }}
"""

PLOT_RANGE_APPLY_BUTTON_STYLE = f"""
    QPushButton {{ background-color: {COLOR_BG_SOFT}; color: {COLOR_TEXT_MUTED}; font-weight: 600; border-radius: 4px; border: 1px solid {COLOR_BORDER_SOFT}; }}
    QPushButton:hover {{ background-color: {COLOR_BG_SOFT_HOVER}; border-color: #C8CCD4; }}
"""

PLOT_RANGE_RESET_BUTTON_STYLE = """
    QPushButton { background-color: #F8F9FB; color: #606266; font-weight: 600; border-radius: 4px; border: 1px solid #DADDE3; }
    QPushButton:hover { background-color: #F1F3F6; border-color: #C8CCD4; }
"""

DESIGN_ICON_BUTTON_STYLE = f"""
    QPushButton {{ background-color: transparent; border: 1px solid transparent; border-radius: 3px; padding: 1px; }}
    QPushButton:hover {{ border-color: #CDD3DA; }}
    QPushButton:checked {{ border: 1px solid {COLOR_PRIMARY}; }}
"""

DESIGN_FONT_BUTTON_SIZE = (32, 26)
DESIGN_FONT_ICON_SIZE = (30, 20)
DESIGN_RAW_MARKER_BUTTON_SIZE = (30, 24)
DESIGN_RAW_MARKER_ICON_SIZE = (23, 23)

MAIN_WINDOW_STYLE = """
    QMainWindow { background-color: #f5f7fa; }
    QGroupBox {
        background-color: white; border: 1px solid #e4e7ed;
        border-radius: 8px; margin-top: 10px; padding-top: 10px;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #909399; font-weight: bold; }

    QPushButton {
        background-color: #ffffff; border: 1px solid #dcdfe6;
        border-radius: 6px; padding: 6px; color: #606266;
    }
    QPushButton:hover { background-color: #ecf5ff; color: #409eff; border-color: #c6e2ff; }
    QPushButton:checked {
        background-color: #409eff; color: white; border-color: #409eff; font-weight: bold;
    }
    QPushButton:disabled {
        background-color: #f5f5f5; color: #bbbbbb; border: 1px solid #eeeeee;
    }

    QMessageBox QPushButton { min-width: 80px; padding: 5px 15px; }

    QTableWidget {
        border: 1px solid #e4e7ed; border-radius: 6px;
        background: #fafafa; gridline-color: transparent;
    }
    QTableWidget::item { border-bottom: 1px solid #f0f2f5; }

    QHeaderView {
        background-color: #fafafa;
        border: none;
    }

    QHeaderView::section:vertical {
        border: none;
        border-bottom: 1px solid #f0f2f5;
        background-color: #fafafa;
        padding-left: 5px;
        padding-right: 5px;
        color: #909399;
        min-width: 25px;
    }

    QHeaderView::section:horizontal {
        background-color: #fafafa;
        border: none;
        border-bottom: 1px solid #e4e7ed;
        color: #909399;
    }

    QTableWidget QTableCornerButton::section {
        background-color: #fafafa;
        border: none;
    }
"""
