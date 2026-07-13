from PySide6.QtWidgets import QApplication

from ui.widgets.design_panel import CompareDesignSettingsPanel


def test_compare_design_panel_applies_saved_settings():
    app = QApplication.instance() or QApplication([])
    panel = CompareDesignSettingsPanel(name_blue="A", name_red="B")
    settings = panel.get_current_settings()
    settings["common"]["show_raw"] = False
    settings["common"]["show_grid"] = True
    settings["blue"]["ell_color"] = "#123456"
    settings["series"]["0"]["ell_color"] = "#123456"

    panel.apply_settings(settings, emit=False)
    restored = panel.get_current_settings()

    assert restored["common"]["show_raw"] is False
    assert restored["common"]["show_grid"] is True
    assert restored["blue"]["ell_color"] == "#123456"
    panel.deleteLater()
    app.processEvents()
