"""Combined txt 저장 UI 어댑터."""

from PySide6.QtWidgets import QFileDialog, QMessageBox


def prompt_save_combined_txt(
    controller, parent_window=None, parent_widget=None
) -> bool:
    """현재 Combined 항목을 입력 형식 txt로 저장하는 UI 흐름."""
    item, _ = controller._get_plot_item_at(parent_window)
    if not item or not item.get("is_combined"):
        QMessageBox.information(
            parent_widget,
            "Combined txt",
            "Combined 항목에서만 사용할 수 있습니다.",
        )
        return False

    initial_path, _ = controller.get_default_combined_txt_path(parent_window)
    path, _ = QFileDialog.getSaveFileName(
        parent_widget,
        "Combined 데이터 txt 저장",
        initial_path,
        "Text Files (*.txt);;All Files (*.*)",
    )
    if not path:
        return False
    if not path.lower().endswith(".txt"):
        path += ".txt"

    ok, msg = controller.export_combined_txt(path, parent_window, parent_widget)
    if ok:
        QMessageBox.information(
            parent_widget,
            "저장 완료",
            f"Combined 데이터를 저장했습니다.\n{path}",
        )
        return True

    QMessageBox.warning(parent_widget, "저장 실패", msg or "저장에 실패했습니다.")
    return False
