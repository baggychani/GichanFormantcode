from __future__ import annotations

import pandas as pd

from core.workspace_service import WorkspaceService
from core.workspace_state import WorkspaceState


def _loader(path: str, **_kwargs):
    return {
        "success": True,
        "name": path,
        "item": {
            "name": path,
            "df": pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["a"]}),
            "df_original": pd.DataFrame(
                {"F1": [500.0], "F2": [1500.0], "Label": ["a"]}
            ),
            "has_f3": False,
            "is_pre_lobanov": False,
        },
        "errors": [],
        "row_dropped": [],
    }


def test_workspace_service_owns_derived_combined_item_and_cursor():
    state = WorkspaceState()
    service = WorkspaceService(state)

    result = service.add_files(["a.csv", "b.csv"], loader=_loader)

    assert result["success_count"] == 2
    assert len(state.filepaths) == 2
    assert state.plot_data_list[-1]["is_combined"] is True
    assert service.set_current_index(999) == len(state.plot_data_list) - 1


def test_workspace_service_removal_rebuilds_derived_item():
    state = WorkspaceState()
    service = WorkspaceService(state)
    service.add_files(["a.csv", "b.csv"], loader=_loader)

    removed = service.remove_file(0)

    assert removed and removed["name"] == "a.csv"
    assert state.filepaths == ["b.csv"]
    assert all(not item.get("is_combined") for item in state.plot_data_list)
