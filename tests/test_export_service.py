import pandas as pd

from core.data_loading_service import load_plot_item_from_file
from core.export_service import export_combined_txt_file


def test_export_combined_txt_file_writes_input_format(tmp_path):
    item = {
        "is_combined": True,
        "has_f3": False,
        "df": pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["a"]}),
    }
    path = tmp_path / "combined.txt"

    ok, msg = export_combined_txt_file(item, str(path))

    assert ok is True
    assert msg == str(path)
    assert path.read_text(encoding="utf-8").strip() == "500\t1500\t/a/"


def test_export_combined_txt_file_rejects_non_combined(tmp_path):
    ok, msg = export_combined_txt_file({"is_combined": False}, str(tmp_path / "x.txt"))

    assert ok is False
    assert "Combined" in msg


def test_export_combined_txt_file_round_trips_pre_lobanov_z_scores(tmp_path):
    item = {
        "is_combined": True,
        "is_pre_lobanov": True,
        "has_f3": True,
        "df": pd.DataFrame(
            {
                "F1": [1.2, -0.8, -0.4],
                "F2": [-0.5, 1.1, -0.6],
                "F3": [0.0, None, -0.7],
                "Label": ["a", "i", "u"],
            }
        ),
    }
    path = tmp_path / "combined.txt"

    ok, _msg = export_combined_txt_file(item, str(path))
    loaded = load_plot_item_from_file(str(path))

    assert ok is True
    assert path.read_text(encoding="utf-8").splitlines()[0] == "Lobanov"
    assert loaded["success"], loaded["errors"]
    assert loaded["is_pre_lobanov"]
    reloaded = loaded["item"]["df"]
    assert reloaded["F1"].tolist() == [1.2, -0.8, -0.4]
    assert reloaded["F3"].iloc[0] == 0.0
    assert pd.isna(reloaded["F3"].iloc[1])
