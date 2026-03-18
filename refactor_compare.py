import ast

def remove_methods(filepath, class_name, methods_to_remove):
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    lines = source.splitlines()
    tree = ast.parse(source)

    ranges_to_remove = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for body_item in node.body:
                if isinstance(body_item, ast.FunctionDef) and body_item.name in methods_to_remove:
                    start = body_item.lineno - 1
                    end = body_item.end_lineno
                    if body_item.decorator_list:
                        start = body_item.decorator_list[0].lineno - 1
                    ranges_to_remove.append((start, end))

    ranges_to_remove.sort(key=lambda x: x[0], reverse=True)
    
    for start, end in ranges_to_remove:
        del lines[start:end]

    return "\n".join(lines) + "\n"

# Only remove methods that are 100% identical and moved to BasePlotWindow
compare_remove = [
    "_apply_pyqt6_icon",
    "_is_ruler_active",
    "_is_input_focused",
    "_is_draw_active",
    "_redraw_draw_layer",
    "_get_current_draw_objects",
    "_set_current_draw_objects",
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
    "update_ruler_style",
    "update_unit_labels",
    "update_x_label",
    "update_label_move_style",
    "show_warning",
    "show_critical",
    "_on_download_plot", # Manually verified as identical
]

compare_source = remove_methods("c:/Users/woori/Desktop/GichanFormant/ui/windows/compare_plot.py", "ComparePlotPopup", compare_remove)

if "from ui.windows.base_plot_window import BasePlotWindow" not in compare_source:
    compare_source = compare_source.replace("from PyQt6.QtWidgets import (", "from ui.windows.base_plot_window import BasePlotWindow\nfrom PyQt6.QtWidgets import (")
compare_source = compare_source.replace("class ComparePlotPopup(QMainWindow):", "class ComparePlotPopup(BasePlotWindow):")

with open("c:/Users/woori/Desktop/GichanFormant/ui/windows/compare_plot.py", "w", encoding="utf-8") as f:
    f.write(compare_source)
print("compare_plot.py refactored.")
