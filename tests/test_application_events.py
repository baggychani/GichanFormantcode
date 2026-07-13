from core.application_events import (
    ApplicationError,
    ApplicationEventBus,
)
from core.workspace_state import WorkspaceState


def test_workspace_state_clears_data_but_keeps_path_preferences():
    state = WorkspaceState(
        filepaths=["a.csv"],
        plot_data_list=[{"name": "a.csv"}],
        current_idx=1,
        last_outlier_mode="tukey_iqr",
        last_open_dir="C:/open",
        last_save_dir="C:/save",
        custom_label_offsets={(0, "f1_f2"): {"a": (1.0, 2.0)}},
    )

    state.clear_data()

    assert state.filepaths == []
    assert state.plot_data_list == []
    assert state.current_idx == 0
    assert state.custom_label_offsets == {}
    assert state.last_open_dir == "C:/open"
    assert state.last_save_dir == "C:/save"


def test_event_bus_isolates_subscriber_failures_and_can_unsubscribe():
    bus = ApplicationEventBus()
    received = []
    unsubscribe = bus.subscribe("state_changed", received.append)
    bus.subscribe("state_changed", lambda _event: 1 / 0)
    bus.subscribe("*", received.append)

    failures = bus.emit("state_changed", {"value": 1})
    unsubscribe()
    bus.emit("state_changed", {"value": 2})

    assert len(failures) == 1
    assert [event.payload["value"] for event in received] == [1, 1, 2]


def test_application_error_is_json_safe():
    error = ApplicationError(
        code="invalid_request",
        message="잘못된 요청",
        details={"field": "source_groups"},
    )

    assert str(error) == "잘못된 요청"
    assert error.to_dict() == {
        "code": "invalid_request",
        "message": "잘못된 요청",
        "details": {"field": "source_groups"},
    }
