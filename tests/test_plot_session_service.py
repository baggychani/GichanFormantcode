from __future__ import annotations

from core.interactive_plot_state import PlotSessionState
from core.plot_session_service import PlotSessionService


class _Popup:
    current_idx = 2
    fixed_plot_params = {"type": "f1_f2"}
    layer_locked_vowels_by_file = {2: {"a"}}
    layer_order = ["a", "i"]
    _draw_objects_by_file = {2: ["line"]}

    @staticmethod
    def get_sigma():
        return 2.5


def test_session_service_syncs_popup_edits_and_rehydrates_popup():
    popup = _Popup()
    session = PlotSessionState()

    PlotSessionService.sync_from_popup(
        session,
        popup,
        fallback_index=0,
        manual_ranges={"y_min": 200, "y_max": 1000},
        design_settings={"lbl_size": 20},
        filter_state={"a": "ON"},
        layer_overrides={"a": {"lbl_size": 24}},
    )
    target = _Popup()
    target.fixed_plot_params = {}
    PlotSessionService.apply_to_popup(session, target, index=2)

    assert session.current_idx == 2
    assert session.sigma == "2.5"
    assert session.layer_locked_vowels_by_file[2] == ["a"]
    assert target.fixed_plot_params["sigma"] == 2.5
    assert target.layer_order == ["a", "i"]
