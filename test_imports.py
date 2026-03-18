import sys
print("Testing imports...")
try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from ui.windows.popup_plot import PlotPopup
    from ui.windows.compare_plot import ComparePlotPopup
    print("Imports successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
