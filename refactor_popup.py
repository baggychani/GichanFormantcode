import ast

def remove_methods(filepath, class_name, methods_to_remove):
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    lines = source.splitlines()
    tree = ast.parse(source)

    # find line ranges for methods to remove
    ranges_to_remove = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for body_item in node.body:
                if isinstance(body_item, ast.FunctionDef) and body_item.name in methods_to_remove:
                    # Find end line. End_lineno is available in Python 3.8+
                    start = body_item.lineno - 1
                    end = body_item.end_lineno
                    
                    # Look for decorators if any
                    if body_item.decorator_list:
                        start = body_item.decorator_list[0].lineno - 1
                    
                    ranges_to_remove.append((start, end))

    ranges_to_remove.sort(key=lambda x: x[0], reverse=True)
    
    for start, end in ranges_to_remove:
        del lines[start:end]

    return "\n".join(lines) + "\n"

# Remove exact methods from popup_plot that are now in base_plot_window
popup_remove = [
    "_apply_pyqt6_icon",
    "_is_ruler_active",
    "_is_input_focused",
    "_is_draw_active",  # not in popup_plot maybe?
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
    "closeEvent"
]

popup_source = remove_methods("c:/Users/woori/Desktop/GichanFormant/ui/windows/popup_plot.py", "PlotPopup", popup_remove)

# add import and change QMainWindow to BasePlotWindow
if "from ui.windows.base_plot_window import BasePlotWindow" not in popup_source:
    popup_source = popup_source.replace("from PyQt6.QtWidgets import (", "from ui.windows.base_plot_window import BasePlotWindow\nfrom PyQt6.QtWidgets import (")
popup_source = popup_source.replace("class PlotPopup(QMainWindow):", "class PlotPopup(BasePlotWindow):")

with open("c:/Users/woori/Desktop/GichanFormant/ui/windows/popup_plot.py", "w", encoding="utf-8") as f:
    f.write(popup_source)
print("popup_plot.py refactored.")
