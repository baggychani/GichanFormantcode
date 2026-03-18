import ast

filepath = "c:/Users/woori/Desktop/GichanFormant/ui/windows/compare_plot.py"
with open(filepath, "r", encoding="utf-8") as f:
    source = f.read()

tree = ast.parse(source)
class_methods = []
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == "ComparePlotPopup":
        for body_item in node.body:
            if isinstance(body_item, ast.FunctionDef):
                class_methods.append(body_item.name)

print("Methods in ComparePlotPopup:", class_methods)
