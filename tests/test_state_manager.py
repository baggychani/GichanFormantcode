from core.state_manager import StateManager


def test_state_manager_stores_design_and_filter_state():
    StateManager.reset_instance()
    state = StateManager.instance()

    state.emit_design_changed({"ell_style": "-", "lbl_bold": True})
    state.emit_filter_changed({"a": "ON", "e": "SEMI"})

    assert state.get_design_state() == {"ell_style": "-", "lbl_bold": True}
    assert state.get_filter_state() == {"a": "ON", "e": "SEMI"}


def test_state_manager_returns_copies():
    StateManager.reset_instance()
    state = StateManager.instance()
    state.emit_filter_changed({"a": "ON"})

    copied = state.get_filter_state()
    copied["a"] = "OFF"

    assert state.get_filter_state() == {"a": "ON"}
