from unittest.mock import MagicMock, patch

from ui.dialogs.combined_txt_save_dialog import prompt_save_combined_txt


def test_prompt_save_combined_txt_rejects_non_combined_item():
    controller = MagicMock()
    controller._get_plot_item_at.return_value = ({"is_combined": False}, 0)

    with patch("ui.dialogs.combined_txt_save_dialog.QMessageBox") as msg_box:
        assert not prompt_save_combined_txt(controller)

    msg_box.information.assert_called_once()
    controller.export_combined_txt.assert_not_called()


def test_prompt_save_combined_txt_exports_selected_path():
    controller = MagicMock()
    controller._get_plot_item_at.return_value = ({"is_combined": True}, 0)
    controller.get_default_combined_txt_path.return_value = ("C:/tmp/out.txt", "C:/tmp")
    controller.export_combined_txt.return_value = (True, "")

    with (
        patch(
            "ui.dialogs.combined_txt_save_dialog.QFileDialog.getSaveFileName",
            return_value=("C:/tmp/out", ""),
        ),
        patch("ui.dialogs.combined_txt_save_dialog.QMessageBox") as msg_box,
    ):
        assert prompt_save_combined_txt(controller)

    controller.export_combined_txt.assert_called_once()
    assert controller.export_combined_txt.call_args.args[0] == "C:/tmp/out.txt"
    msg_box.information.assert_called_once()
