from __future__ import annotations

from types import SimpleNamespace

from core.compare_render_service import CompareRenderService
from core.compare_series import CompareSession


class _Engine:
    def draw_compare_plot(self, _figure, _inputs, _params, **_kwargs):
        return SimpleNamespace(
            snapping_data=["snap"],
            label_data={0: ["label-a"], 1: ["label-b"]},
            label_text_artists={0: ["artist-a"], 1: ["artist-b"]},
        )


class _Host:
    plot_engine = _Engine()

    def __init__(self):
        self.custom_label_offsets = {}
        self.items = {
            0: {"name": "a", "df": object()},
            1: {"name": "b", "df": object()},
        }
        self.presented = False

    def _ensure_plot_engine(self):
        return None

    def _read_manual_ranges(self, _widgets):
        return {"x_min": "0", "x_max": "1"}

    def _get_current_plot_params(self, _popup):
        return {"type": "f1_f2"}

    def _get_default_design(self):
        return {}

    def get_data_item_at(self, index):
        return self.items[index]

    def _present_popup_canvas(self, _popup, _canvas):
        self.presented = True

    def _sync_popup_tool_contexts(self, *_args):
        pass


class _Popup:
    normalization = None

    def __init__(self):
        self.fixed_plot_params = {}

    @staticmethod
    def get_design_settings():
        return {}


def test_compare_render_service_builds_inputs_and_applies_result():
    host = _Host()
    popup = _Popup()

    CompareRenderService(host).refresh(
        object(), object(), {}, popup, CompareSession.from_data_indices(0, 1)
    )

    assert host.presented is True
    assert popup.snapping_data == ["snap"]
    assert popup.label_data_blue == ["label-a"]
    assert popup.label_data_red == ["label-b"]
