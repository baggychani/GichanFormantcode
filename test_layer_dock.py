import sys
import traceback

print("Testing layer_dock.py imports...")
try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from ui.widgets.layer_dock import LayerDockWidget
    print("LayerDockWidget imported successfully!")
except Exception as e:
    print("Error importing LayerDockWidget:")
    traceback.print_exc()
    sys.exit(1)
