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
                out_code.append(segment)

with open("c:/Users/woori/Desktop/GichanFormant/ui/windows/extracted_methods.py", "w", encoding="utf-8") as f:
    f.write("\n\n".join(out_code))

print(f"Extracted {len(out_code)} methods.")
