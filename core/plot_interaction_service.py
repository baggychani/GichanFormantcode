"""Legacy ruler and label-move tool coordination."""

from __future__ import annotations

from typing import Any

from core.compare_runtime import merged_label_move_context


class PlotInteractionService:
    """Exclusive interaction modes for single and compare legacy popups."""

    def __init__(self, host: Any) -> None:
        self.host = host

    def toggle_ruler(self, popup: Any) -> None:
        ruler = self.host.ruler_tool
        if ruler.active:
            ruler.active = False
            ruler.detach()
            ruler.clear_all()
            popup.update_ruler_style(False)
            return
        label_tool = self.host.label_move_tool
        if label_tool and label_tool.active:
            label_tool.active = False
            label_tool.detach()
            update = getattr(popup, "update_label_move_style", None) or getattr(
                popup, "update_compare_label_move_style", None
            )
            if callable(update):
                update(False)
            popup._label_move_series = None
        ruler.active = True
        if popup.figure.axes:
            design = self._design(popup)
            ruler.set_context(
                popup.canvas,
                popup.figure.axes[0],
                popup.fixed_plot_params,
                popup.snapping_data,
                design or None,
            )
        popup.update_ruler_style(True)

    def toggle_single_label_move(self, popup: Any) -> None:
        if self.host.ruler_tool.active:
            return
        tool = self._label_tool()
        tool.on_offset_saved = lambda dragging: self.host._save_label_offset(dragging, popup)
        tool.on_offset_cleared = lambda vowel: self.host._clear_label_offset(popup, vowel)
        if not tool.active and popup.figure.axes:
            tool.set_context(
                popup.canvas,
                popup.figure.axes[0],
                getattr(popup, "label_data", []),
                label_text_artists=getattr(popup, "label_text_artists", None),
            )
        enabled = tool.toggle()
        update = getattr(popup, "update_label_move_style", None)
        if callable(update):
            update(enabled)
        if enabled:
            self.host._present_popup_canvas(popup, popup.canvas)

    def toggle_compare_label_move(self, popup: Any) -> None:
        if self.host.ruler_tool.active:
            return
        tool = self._label_tool()
        tool.on_offset_saved = lambda dragging: self.host._save_compare_label_offset(dragging, popup)
        tool.on_offset_cleared = lambda value: self.host._clear_compare_label_offset_from_arg(popup, value)
        if not tool.active and popup.figure.axes:
            labels, artists = merged_label_move_context(popup)
            tool.set_context(
                popup.canvas, popup.figure.axes[0], labels, label_text_artists=artists
            )
        enabled = tool.toggle()
        popup._label_move_series = "all" if enabled else None
        update = getattr(popup, "update_compare_label_move_style", None)
        if callable(update):
            update(enabled)
        if enabled:
            self.host._present_popup_canvas(popup, popup.canvas)

    def sync_contexts(self, popup: Any, figure: Any, canvas: Any) -> None:
        if not figure.axes:
            return
        axis = figure.axes[0]
        ruler = self.host.ruler_tool
        if ruler.active:
            ruler.set_context(
                canvas, axis, popup.fixed_plot_params, popup.snapping_data,
                self._design(popup) or None,
            )
        tool = self.host.label_move_tool
        if tool and tool.active:
            if hasattr(popup, "label_data_by_series") or hasattr(popup, "label_data_blue"):
                labels, artists = merged_label_move_context(popup)
            else:
                labels = getattr(popup, "label_data", []) or []
                artists = getattr(popup, "label_text_artists", None)
            tool.set_context(canvas, axis, labels, label_text_artists=artists)

    def _label_tool(self) -> Any:
        if self.host.label_move_tool is None:
            self.host.label_move_tool = self.host.window_coordinator.create_label_move_tool()
        return self.host.label_move_tool

    @staticmethod
    def _design(popup: Any) -> dict:
        design = popup.get_design_settings() if hasattr(popup, "get_design_settings") else {}
        if not design and getattr(popup, "design_tab", None):
            design = getattr(popup.design_tab, "get_current_settings", lambda: {})()
        return design or {}
