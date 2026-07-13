import pandas as pd
from PySide6.QtWidgets import QApplication

from core.controller import MainController


def test_desktop_coordinator_opens_and_closes_single_plot():
    app = QApplication.instance() or QApplication([])
    controller = MainController(render_initial_preview=False)
    dataframe = pd.DataFrame(
        {
            "F1": [500.0, 510.0, 520.0, 530.0],
            "F2": [1500.0, 1510.0, 1520.0, 1530.0],
            "Label": ["a", "a", "a", "a"],
        }
    )
    controller.filepaths = ["C:/data/speaker.csv"]
    controller.plot_data_list = [
        {
            "name": "speaker.csv",
            "df": dataframe.copy(),
            "df_original": dataframe.copy(),
            "has_f3": False,
            "is_pre_lobanov": False,
        }
    ]
    controller.view.update_file_status(1)

    try:
        controller.application_service.open_single_plot()
        app.processEvents()

        assert len(controller.open_popups) == 1
        assert controller.open_popups[0].isVisible()
    finally:
        for popup in list(controller.open_popups):
            popup.close()
        controller.ui.close()
        app.processEvents()
