from unittest.mock import MagicMock

import pandas as pd

from core.preview_renderer import PreviewRenderer
from core.runtime_port import HeadlessRuntime


class _Figure:
    def __init__(self):
        self.cleared = False
        self.savefig_kwargs = None

    def clear(self):
        self.cleared = True

    def savefig(self, buffer, **kwargs):
        self.savefig_kwargs = kwargs
        buffer.write(b"png-data")


def test_preview_renderer_returns_png_without_presentation_types():
    engine = MagicMock()
    figure = _Figure()
    renderer = PreviewRenderer(engine, figure)
    data = {
        "name": "speaker.csv",
        "df": pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["a"]}),
    }

    png = renderer.render_png(
        data,
        {"type": "f1_f2", "normalization": None},
        {"x_min": "0", "x_max": "1", "y_min": "0", "y_max": "1"},
        {"show_grid": True},
    )

    assert png == b"png-data"
    assert figure.cleared is True
    assert figure.savefig_kwargs == {"format": "png", "facecolor": "white"}
    engine.draw_plot.assert_called_once()
    engine.draw_single_normalized.assert_not_called()


def test_headless_runtime_debouncer_is_deterministic():
    runtime = HeadlessRuntime(
        app_data="C:/app", documents="C:/docs", downloads="C:/downloads"
    )
    calls = []
    debouncer = runtime.create_debouncer(lambda: calls.append("render"))

    debouncer.trigger(150)
    assert calls == []
    debouncer.fire()

    assert calls == ["render"]
    assert runtime.app_data_dir() == "C:/app"
    assert runtime.documents_dir() == "C:/docs"
    assert runtime.downloads_dir() == "C:/downloads"
