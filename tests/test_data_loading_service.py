import pandas as pd

import config
from core.data_loading_service import load_plot_item_from_file, make_plot_item


class _FakeProcessor:
    is_pre_lobanov = False
    row_drops = []

    def load_files(self, _paths):
        return True, False, []

    def get_data(self, copy=True):
        return pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["a"]})


class _FakePreLobanovProcessor(_FakeProcessor):
    is_pre_lobanov = True


def test_make_plot_item_uses_dataframe_snapshot_copies():
    df = pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["a"]})
    item = make_plot_item(name="a.txt", df=df)

    assert item["name"] == "a.txt"
    assert item["has_f3"] is False
    df.loc[0, "F1"] = 999.0
    assert item["df"].loc[0, "F1"] == 500.0


def test_load_plot_item_from_file_success():
    result = load_plot_item_from_file("C:/tmp/a.txt", processor_cls=_FakeProcessor)

    assert result["success"] is True
    assert result["item"]["name"] == "a.txt"
    assert result["item"]["df"].loc[0, "Label"] == "a"


def test_load_plot_item_rejects_mixed_lobanov_mode():
    result = load_plot_item_from_file(
        "C:/tmp/a.txt",
        existing_pre_lobanov=False,
        processor_cls=_FakePreLobanovProcessor,
    )

    assert result["success"] is False
    assert result["errors"][0][1] == config.PARSE_ERR_LOBANOV_MIXED
