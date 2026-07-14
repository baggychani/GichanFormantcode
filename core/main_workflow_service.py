"""User-facing main-window commands composed from application services."""

from __future__ import annotations

import os

import config
from core.application_events import ApplicationError
from core.project_service import load_project, save_project
from model.data_processor import DataProcessor
from utils import app_logger


class MainWorkflowService:
    def __init__(self, host) -> None:
        self.host = host

    def handle_file_drop(self, files) -> None:
        self.host.application_service.load_files(files)

    def request_file_open(self) -> None:
        self.host.view.request_file_open(self.host.application_service.load_files)

    def prompt_save_project(self, popup=None) -> None:
        host = self.host
        if not host.plot_data_list:
            host.view.show_warning("데이터 없음", "저장할 프로젝트 데이터가 없습니다.")
            return
        source = popup or self._active_single_popup()
        host.view.request_project_save(lambda path: self.save_project_file(path, source), parent_window=source)

    def prompt_open_project(self) -> None:
        self.host.view.request_project_open(self.load_project_file, parent_window=self.host.ui)

    def save_project_file(self, path, popup=None) -> None:
        try:
            self.host.application_service.save_project(path, popup_window=popup)
        except ApplicationError as error:
            self.host.view.show_critical("프로젝트 저장 실패", str(error))
            app_logger.error(f"[Project] save failed: {error}")

    def save_project_document(self, path, popup=None) -> None:
        self.host.sync_analysis_settings_from_view()
        save_project(path, self.host, popup)
        app_logger.info(f"[Project] 프로젝트 저장 완료: {path}")

    def load_project_file(self, path) -> None:
        try:
            self.host.application_service.load_project(path)
        except ApplicationError as error:
            self.host.view.show_critical("프로젝트 열기 실패", str(error))
            app_logger.error(f"[Project] load failed: {error}")

    def load_project_document(self, path, *, restore_windows=True):
        project = load_project(path)
        self.host.project_restore_service.apply(project, restore_windows=restore_windows)
        self.host.set_last_open_dir(os.path.dirname(os.path.abspath(path)))
        app_logger.info(f"[Project] 프로젝트 불러오기 완료: {path}")
        return project

    def load_files(self, files):
        result = self.host.workspace_service.add_files(
            list(files), loader=self.host._load_file_item
        )
        self.host.file_load_presentation_service.apply(result)
        return result

    def remove_file(self, index: int) -> bool:
        removed = self.host.workspace_service.remove_file(index)
        if removed is None:
            app_logger.debug("[remove_file] ignored invalid or derived item index")
            return False
        self.host.view.update_file_status(removed["total_files"])
        self.host.view.toggle_f3_options(removed["has_f3_all"])
        app_logger.info(config.LOG_MSG["FILE_REMOVED"].format(removed_name=removed["name"]))
        self.host._sync_pre_lobanov_ui()
        self.host.update_live_preview()
        return True

    def reset(self) -> None:
        if not self.host.filepaths:
            return
        self.host.workspace.clear_data()
        self.host.data_processor = DataProcessor()
        self.host.view.reset()
        app_logger.info(config.LOG_MSG["RESET_ALL"])

    def _active_single_popup(self):
        for popup in reversed(self.host.open_popups):
            if getattr(popup, "plot_data_snapshot", None) is not None and not hasattr(popup, "compare_session"):
                return popup
        return None
