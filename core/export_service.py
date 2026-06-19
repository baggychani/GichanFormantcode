"""Export helpers for plot images and formant text files."""

from __future__ import annotations

import os

import config
from model.formant_txt_export import formant_dataframe_to_txt
from utils import app_logger


def export_combined_txt_file(item: dict, file_path: str) -> tuple[bool, str]:
    """Write a Combined item as GichanFormant input-style text."""
    if not item or not item.get("is_combined"):
        return False, "Combined 항목이 아닙니다."
    df = item.get("df")
    if df is None or df.empty:
        return False, "저장할 데이터가 없습니다."
    text = formant_dataframe_to_txt(df, include_f3=bool(item.get("has_f3", False)))
    if not text.strip():
        return False, "유효한 행이 없어 파일을 만들 수 없습니다."
    try:
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    except OSError as error:
        return False, str(error)
    app_logger.info(config.LOG_MSG["COMBINED_TXT_SAVE"].format(path=file_path))
    return True, file_path


def save_figure_file(figure, file_path: str, fmt: str, parent_window=None) -> None:
    """Save a Matplotlib figure with GichanFormant export conventions."""
    if parent_window:
        if getattr(parent_window, "_draw_tool", None) is not None:
            try:
                parent_window._draw_tool.cancel()
            except Exception as error:
                app_logger.debug(f"[save_plot_to_file] 그리기 도구 취소 실패: {error}")
        if hasattr(parent_window, "begin_export_render"):
            parent_window.begin_export_render()
    try:
        if parent_window and getattr(parent_window, "canvas", None) is not None:
            try:
                parent_window.canvas.draw()
            except Exception as error:
                app_logger.debug(
                    f"[save_plot_to_file] 캔버스 다시 그리기 실패: {error}"
                )
        figure.set_size_inches(6.5, 6.5)
        if fmt.lower() == "png":
            figure.savefig(file_path, format="png", dpi=300, transparent=True)
        else:
            figure.savefig(file_path, format=fmt, dpi=300, facecolor="white")
        app_logger.info(config.LOG_MSG["SAVE_SINGLE_SHORT"].format(path=file_path))
    finally:
        if parent_window and hasattr(parent_window, "end_export_render"):
            parent_window.end_export_render()


def save_dir_from_path(file_path: str) -> str:
    return os.path.dirname(file_path)
