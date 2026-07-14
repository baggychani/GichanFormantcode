"""Persist and recover the file-open and export directories."""

from __future__ import annotations

import os

from utils import path_prefs


class PathPreferenceService:
    def __init__(self, host) -> None:
        self.host = host

    def initial_open_dir(self) -> str:
        return self.host.last_open_dir if self.host.last_open_dir and os.path.isdir(self.host.last_open_dir) else self.host.runtime.documents_dir() or ""

    def set_open_dir(self, path: str) -> None:
        if path and os.path.isdir(path):
            self.host.last_open_dir = path
            self.save()

    def set_save_dir(self, path: str) -> None:
        if path and os.path.isdir(path):
            self.host.last_save_dir = path
            self.save()

    def save(self) -> None:
        base = self.host.runtime.app_data_dir()
        if base:
            path_prefs.save_path_prefs(base, {
                "last_open_dir": self.host.last_open_dir,
                "last_save_dir": self.host.last_save_dir,
            })
