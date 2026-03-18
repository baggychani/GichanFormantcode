import os

base_code = """import os
import platform
from PyQt6.QtWidgets import QMainWindow, QApplication, QLineEdit, QMessageBox, QFileDialog
from PyQt6.QtGui import QIcon, QShortcut, QKeySequence
from PyQt6.QtCore import Qt

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

with open("c:/Users/woori/Desktop/GichanFormant/ui/windows/extracted_methods.py", "r", encoding="utf-8") as f:
    methods_code = f.read()

fixed_methods = []
for line in methods_code.splitlines():
    if line.startswith("def "):
        fixed_methods.append("    " + line)
    elif line.strip() == "":
        fixed_methods.append("")
    else:
        # The body lines in extracted_methods.py already have 8 spaces because they were 8 spaces in popup_plot.py. Wait, if `def ` had 4 spaces, then body had 8. The ast removed 4 spaces from the first line? Let's assume ast.get_source_segment stripped leading whitespace from the first line ONLY.
        if line.startswith("        ") or line.startswith("    "):
            fixed_methods.append("    " + line)  # This might add 4 spaces, so body gets 12. Let's look at line 2: "        try:"
            # If line 2 is "        try:", then it has 8 spaces. If we add 4, it becomes 12. That's wrong.
            # Alternatively, let's just use Python's textwrap.indent
            pass

import textwrap
# Let's read the AST again and generate the file properly to avoid indentation issues.
import ast

file_path = "c:/Users/woori/Desktop/GichanFormant/ui/windows/popup_plot.py"
methods_to_extract = [
    "_apply_pyqt6_icon",
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
            if isinstance(body_item, ast.FunctionDef) and body_item.name in methods_to_extract:
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

with open("c:/Users/woori/Desktop/GichanFormant/ui/windows/base_plot_window.py", "w", encoding="utf-8") as f:
    f.write(base_code)
    f.write("\n\n".join(out_code))
    f.write("\n")

