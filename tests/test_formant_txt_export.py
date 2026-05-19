"""formant_txt_export 테스트."""

import pandas as pd

from model.formant_txt_export import formant_dataframe_to_txt


def test_formant_dataframe_to_txt_with_f3_and_labels():
    df = pd.DataFrame(
        {
            "F1": [730.0, 320.0],
            "F2": [1090.0, 2250.0],
            "F3": [float("nan"), 2400.0],
            "Label": ["a", "/i/"],
        }
    )
    text = formant_dataframe_to_txt(df, include_f3=True)
    lines = text.strip().splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("/a/")
    assert "730" in lines[0] and "1090" in lines[0]
    assert lines[1].startswith("320") and "/i/" in lines[1]


def test_formant_dataframe_to_txt_without_f3():
    df = pd.DataFrame({"F1": [500.0], "F2": [1500.0], "Label": ["e"]})
    text = formant_dataframe_to_txt(df, include_f3=False)
    assert text.strip() == "500\t1500\t/e/"
