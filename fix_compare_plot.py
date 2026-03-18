def fix_compare_plot():
    filepath = "c:/Users/woori/Desktop/GichanFormant/ui/windows/compare_plot.py"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "self._safe_cancel_ruler_point" in content:
        content = content.replace("self._safe_cancel_ruler_point", "self._safe_cancel_ruler_or_draw")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print("Fixed compare_plot.py!")
    elif "self._safe_cancel_ruler_or_draw" in content:
        print("Already fixed compare_plot.py!")
    else:
        print("Could not find the target string in compare_plot.py.")

if __name__ == "__main__":
    fix_compare_plot()
