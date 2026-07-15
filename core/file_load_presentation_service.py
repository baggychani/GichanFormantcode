"""Presentation updates after a workspace file-load operation."""

from __future__ import annotations

from typing import Any

import config
from utils import app_logger


class FileLoadPresentationService:
    def __init__(self, host: Any) -> None:
        self.host = host

    def apply(self, result: dict) -> None:
        if result["success_count"]:
            app_logger.info(config.LOG_MSG["FILE_LOAD_NEW_SUCCESS"].format(
                success_count=result["success_count"], total_files=result["total_files"]
            ))
            for name, report in result.get("row_dropped", []):
                if report:
                    detail = ", ".join(f"{label}: {count}개" for label, count in report.items())
                    app_logger.info(config.LOG_MSG["FILE_ROW_DROPPED"].format(name=name, detail=detail))
        if result["failed"]:
            names = ", ".join(name for name, _errors in result["failed"])
            app_logger.warning(config.LOG_MSG["FILE_LOAD_FAILED_SUMMARY"].format(
                fail_count=len(result["failed"]), names=names
            ))
            for name, errors in result["failed"][:3]:
                if errors:
                    app_logger.debug(config.LOG_MSG["FILE_LOAD_FAILED_DEBUG"].format(
                        name=name, msg=errors[0][1]
                    ))
        host = self.host
        host.view.update_file_status(result["total_files"])
        host.view.toggle_f3_options(result["has_f3_all"])
        if result["success_count"]:
            if host.all_real_items_pre_lobanov():
                app_logger.info(config.LOG_MSG["LOBANOV_FILE_DETECTED"])
            host._sync_pre_lobanov_ui()
            if getattr(host.view, "native_window", None) is None:
                return
            host.update_live_preview()
