"""Error-contained refresh entry points for legacy plot popups."""

from __future__ import annotations

from typing import Any

import config
from utils import app_logger
from engine.plot_engine import kor_font


class PlotRenderWorkflowService:
    def __init__(self, host: Any) -> None:
        self.host = host

    def refresh_single(self, figure, canvas, range_widgets, label, popup) -> None:
        try:
            self.host.single_plot_service.refresh(figure, canvas, range_widgets, label, popup)
        except Exception as error:
            app_logger.error(config.LOG_MSG["PLOT_APPLY_FAIL"].format(e=error))
            self._show_error(figure, canvas, "플롯 렌더링 오류")

    def refresh_compare(self, figure, canvas, range_widgets, popup, session) -> None:
        if figure is None or canvas is None or range_widgets is None or popup is None:
            return
        try:
            self.host.compare_render_service.refresh(figure, canvas, range_widgets, popup, session)
        except Exception as error:
            app_logger.error(config.LOG_MSG["PLOT_REFRESH_FAIL"].format(e=error))
            self._show_error(figure, canvas, "다중 플롯 렌더링 오류")

    @staticmethod
    def _show_error(figure, canvas, message: str) -> None:
        try:
            figure.clear()
            axis = figure.add_subplot(111)
            axis.text(0.5, 0.5, message, ha="center", va="center", fontfamily=kor_font, fontsize=11)
            axis.set_axis_off()
            canvas.draw()
        except Exception as error:
            app_logger.debug(f"[plot refresh] fallback failed: {error}")
