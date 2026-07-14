from __future__ import annotations

from types import SimpleNamespace

from core.plot_interaction_service import PlotInteractionService


class _Tool:
    def __init__(self):
        self.active = False
        self.context = None

    def detach(self):
        self.active = False

    def clear_all(self):
        pass

    def set_context(self, *args, **kwargs):
        self.context = (args, kwargs)

    def toggle(self):
        self.active = not self.active
        return self.active


class _Popup:
    def __init__(self):
        self.figure = SimpleNamespace(axes=[object()])
        self.canvas = object()
        self.fixed_plot_params = {}
        self.snapping_data = []
        self.label_data = []
        self.label_text_artists = []
        self.ruler_styles = []
        self.label_styles = []

    def get_design_settings(self):
        return {}

    def update_ruler_style(self, enabled):
        self.ruler_styles.append(enabled)

    def update_label_move_style(self, enabled):
        self.label_styles.append(enabled)


class _Host:
    def __init__(self):
        self.ruler_tool = _Tool()
        self.label_move_tool = _Tool()
        self.presented = 0

    def _present_popup_canvas(self, *_args):
        self.presented += 1

    def _save_label_offset(self, *_args):
        pass

    def _clear_label_offset(self, *_args):
        pass


def test_interaction_service_enforces_ruler_label_mode_exclusion():
    host = _Host()
    popup = _Popup()
    service = PlotInteractionService(host)

    service.toggle_single_label_move(popup)
    service.toggle_ruler(popup)

    assert host.label_move_tool.active is False
    assert host.ruler_tool.active is True
    assert popup.label_styles == [True, False]
    assert popup.ruler_styles == [True]
