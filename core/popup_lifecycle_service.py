"""Cleanup and shared interaction shutdown for legacy popup windows."""

from __future__ import annotations

import config
from core.compare_service import clear_compare_label_offsets
from utils import app_logger


class PopupLifecycleService:
    def __init__(self, host) -> None:
        self.host = host

    def clear_offsets(self, popup) -> None:
        key = getattr(popup, "_plot_key", None)
        if key:
            self.host.custom_label_offsets.pop(key, None)
        compare_key = getattr(popup, "_plot_key_compare", None)
        if compare_key:
            self.clear_compare_offsets(compare_key, popup)

    def remove(self, popup) -> None:
        self.host.legacy_windows.remove(popup, before_remove=self.clear_offsets)

    def clear_compare_offsets(self, plot_key, popup=None) -> None:
        clear_compare_label_offsets(
            self.host.custom_label_offsets,
            plot_key,
            session=getattr(popup, "compare_session", None),
        )

    def disable_ruler(self) -> None:
        tool = self.host.ruler_tool
        if not tool.active:
            return
        tool.active = False
        tool.detach()
        tool.clear_all()
        for popup in self.host.open_popups:
            if hasattr(popup, "update_ruler_style"):
                popup.update_ruler_style(False)
        app_logger.info(config.LOG_MSG["RULER_OFF_INFO"])

    def disable_label_move(self) -> None:
        tool = self.host.label_move_tool
        if not (tool and tool.active):
            return
        tool.active = False
        tool.detach()
        for popup in self.host.open_popups:
            if hasattr(popup, "update_label_move_style"):
                popup.update_label_move_style(False)
        app_logger.info(config.LOG_MSG["LABEL_MOVE_OFF"])
