import pandas as pd

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
