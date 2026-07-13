from dataclasses import replace

from PySide6.QtWidgets import QApplication

from core.controller import MainController
from core.view_port import MainViewPort


def test_default_controller_uses_pyside_view_port():
    app = QApplication.instance() or QApplication([])
    controller = MainController(render_initial_preview=False)
    try:
        assert isinstance(controller.view, MainViewPort)
        assert controller.view.native_window is controller.ui
        assert controller.ui.application is controller.application_service

        settings = replace(
            controller.get_analysis_settings(),
            origin="bottom_left",
        )
        controller.apply_analysis_settings(settings)

        assert controller.sync_analysis_settings_from_view().origin == "bottom_left"
    finally:
        controller.ui.close()
        app.processEvents()
