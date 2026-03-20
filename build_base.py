from pathlib import Path

repo_root = Path(__file__).resolve().parent

base_code = """import os
import platform
from PySide6.QtWidgets import QMainWindow, QApplication, QLineEdit, QMessageBox, QFileDialog
from PySide6.QtGui import QIcon, QShortcut, QKeySequence
from PySide6.QtCore import Qt

import matplotlib.colors as mcolors
import config
import app_logger
from utils import icon_utils
from draw import DrawMode
from draw.draw_common import polygon_area, AreaLabelObject
from utils.math_utils import hz_to_bark, bark_to_hz
from draw import draw_line, draw_polygon, draw_reference

class BasePlotWindow(QMainWindow):
    \"\"\"
    popup_plot.py와 compare_plot.py의 공통 로직을 담는 부모 클래스입니다.
    \"\"\"
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_label_move_active_flag = False

    def _is_label_move_active(self):
        btn_on = False
        if hasattr(self, "design_tab") and hasattr(self.design_tab, "btn_label_move"):
            btn_on = self.design_tab.btn_label_move.isChecked()
        return btn_on

"""

# Let's read the AST again and generate the file properly to avoid indentation issues.
import ast

file_path = repo_root / "ui" / "windows" / "popup_plot.py"
methods_to_extract = [
    "_apply_window_icon",
    "_is_ruler_active",
    "_is_input_focused",
    "_is_draw_active",
    "_redraw_draw_layer",
    "_get_current_draw_objects",
    "_set_current_draw_objects",
    "_on_draw_object_complete",
    "_safe_toggle_draw",
    "_safe_toggle_ruler",
    "_safe_draw_complete",
    "_safe_draw_rollback",
    "_safe_cancel_ruler_point",
    "_safe_set_draw_mode",
    "_rebind_draw_tool_if_active",
    "_on_draw_mode_changed",
    "_on_toggle_draw",
    "_draw_tool_deactivate",
    "_bind_shortcuts",
    "update_ruler_style",
    "update_unit_labels",
    "update_x_label",
    "update_label_move_style",
    "_on_download_plot",
    "show_warning",
    "show_critical",
    "closeEvent",
]

with open(file_path, "r", encoding="utf-8") as f:
    source = f.read()

tree = ast.parse(source)

out_code = []
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == "PlotPopup":
        for body_item in node.body:
            if (
                isinstance(body_item, ast.FunctionDef)
                and body_item.name in methods_to_extract
            ):
                segment = ast.get_source_segment(source, body_item)

                # Fix indentation
                lines = segment.splitlines()
                # first line `def ...` has no indentation in segment.
                lines[0] = "    " + lines[0]
                # the rest of the lines might need adjustment if they are indented correctly relative to def.
                # Actually, in ast.get_source_segment, the raw source string's exact substring is returned.
                # Since the original file had `    def`, get_source_segment starts at `def` and includes the rest verbatim.
                # So `lines[0]` is `def ...`, `lines[1]` has 8 spaces.
                # Let's just prepend 4 spaces ONLY to the first line, so it aligns with 4 spaces.
                # Wait, if `lines[1]` has 8 spaces, and `lines[0]` has 4 spaces, they are perfectly aligned!

                out_code.append("\n".join(lines))

with open(
    repo_root / "ui" / "windows" / "base_plot_window.py", "w", encoding="utf-8"
) as f:
    f.write(base_code)
    f.write("\n\n".join(out_code))
    f.write("\n")
