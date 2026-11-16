"""Per-file session state and cached analyses must stay tied to their data."""

import numpy as np
import pandas as pd
import pytest

from core.controller import MainController
from core.data_loading_service import make_plot_item
from core.runtime_port import HeadlessRuntime
from core.view_port import NullMainView


@pytest.fixture
def service():
    controller = MainController(
        view_factory=lambda *_args: NullMainView(),
        runtime=HeadlessRuntime(),
        render_initial_preview=False,
    )
    result = controller.application_service
    try:
        yield result
    finally:
        result.close()


def _write_sources(directory, count: int) -> list[str]:
    paths = []
    for number in range(1, count + 1):
        path = directory / f"s{number}.txt"
        path.write_text(
            "400\t2200\t/i/\n700\t1300\t/a/\n450\t900\t/u/\n", encoding="utf-8"
        )
        paths.append(str(path))
    return paths


def _mark_current_source(service, note: str) -> None:
    service.update_interactive_session(
        {
            "filter_state": {"i": "OFF"},
            "draw_objects": [
                {"type": "text", "id": note, "text": note, "x": 1500, "y": 500}
            ],
        }
    )


def _prepared_notes(service, index: int) -> tuple[str, list[str], dict | None]:
    service.set_current_index(index)
    prepared = service.prepare_interactive_preview({})
    notes = [obj["text"] for obj in prepared["draw_objects"]]
    return prepared["filename"], notes, prepared["filter_state"]


def test_loading_a_file_does_not_hand_combined_state_to_it(service, tmp_path):
    paths = _write_sources(tmp_path, 3)
    service.load_files(paths[:2])
    service.set_current_index(2)  # Combined
    _mark_current_source(service, "on combined")

    service.load_files(paths[2:])

    name, notes, filters = _prepared_notes(service, 2)
    assert name == "s3.txt"
    assert notes == []
    assert filters is None
    name, notes, filters = _prepared_notes(service, 3)
    assert "Combined" in name
    assert notes == ["on combined"]
    assert filters == {"i": "OFF"}


def test_removing_a_file_keeps_combined_state_or_drops_it_with_combined(
    service, tmp_path
):
    paths = _write_sources(tmp_path, 3)
    service.load_files(paths)
    service.set_current_index(3)  # Combined
    _mark_current_source(service, "on combined")

    service.remove_file(0)
    name, notes, _filters = _prepared_notes(service, 2)
    assert "Combined" in name
    assert notes == ["on combined"]

    # One file left: Combined disappears and must not leave state behind for
    # the next file that takes its index.
    service.remove_file(0)
    service.load_files(paths[:1])
    for index in (0, 1):
        _name, notes, filters = _prepared_notes(service, index)
        assert notes == []
        assert filters is None


def test_vowel_analysis_follows_outlier_filter_changes(service):
    rng = np.random.default_rng(2)
    df = pd.DataFrame(
        {
            "F1": np.r_[500 + rng.normal(0, 5, 20), 900.0],
            "F2": np.r_[1500 + rng.normal(0, 5, 20), 2600.0],
            "Label": ["a"] * 21,
        }
    )
    controller = service.controller
    controller.filepaths = ["a.txt"]
    controller.plot_data_list = [make_plot_item(name="a.txt", df=df)]

    for step in range(60):
        mode = [None, "mahalanobis_2sigma", "tukey_iqr"][step % 3]
        service.set_analysis_settings({"outlier_mode": mode})
        count = service.get_vowel_analysis(0)["statistics"]["a"]["count"]
        assert count == len(controller.plot_data_list[0]["df"]), (step, mode)
