import sys
import traceback

print("Testing popup_plot.py imports after Phase 3-C...")
try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication( sys.argv)
    from ui.windows.popup_plot import PlotPopup
    print("PlotPopup imported successfully!")
except Exception as e:
    with open("error_log.txt", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
    sys.exit(1)
