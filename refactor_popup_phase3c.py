import ast

def replace_popup_plot():
    filepath = "c:/Users/woori/Desktop/GichanFormant/ui/windows/popup_plot.py"
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    lines = source.splitlines()
    tree = ast.parse(source)

    class_start = None
    class_end = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "BatchSaveDialog":
            class_start = node.lineno - 1
            class_end = node.end_lineno
            break

    if class_start is not None and class_end is not None:
        # Keep empty lines and decorators associated by simple range exclusion
        del lines[class_start:class_end]
        
    new_source = "\n".join(lines)
    
    # Add import statement
    import_stmt = "from ui.dialogs.batch_save_dialog import BatchSaveDialog"
    if import_stmt not in new_source:
        parts = new_source.split("from ui.windows.base_plot_window import BasePlotWindow")
        if len(parts) == 2:
            new_source = parts[0] + "from ui.windows.base_plot_window import BasePlotWindow\n" + import_stmt + parts[1]
        else:
            new_source = import_stmt + "\n" + new_source

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_source)

    print("Successfully removed BatchSaveDialog from popup_plot.py and added import!")

if __name__ == "__main__":
    replace_popup_plot()
