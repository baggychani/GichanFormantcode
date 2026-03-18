import ast

file_path = "c:/Users/woori/Desktop/GichanFormant/ui/windows/compare_plot.py"
methods_to_extract = [
    "_on_draw_object_complete",
    "_bind_shortcuts",
    "_on_download_plot",
    "closeEvent"
]

with open(file_path, "r", encoding="utf-8") as f:
    source = f.read()

tree = ast.parse(source)

out_code = []
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == "ComparePlotPopup":
        for body_item in node.body:
            if isinstance(body_item, ast.FunctionDef) and body_item.name in methods_to_extract:
                segment = ast.get_source_segment(source, body_item)
                out_code.append(segment)

with open("c:/Users/woori/Desktop/GichanFormant/ui/windows/extracted_compare.py", "w", encoding="utf-8") as f:
    f.write("\n\n".join(out_code))

print(f"Extracted {len(out_code)} methods from compare_plot.py")
