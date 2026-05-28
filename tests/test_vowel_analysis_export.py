from ui.dialogs.vowel_analysis_dialog import _result_to_dataframe


def test_result_to_dataframe_non_normalized_includes_hz_and_bark():
    result = {
        "statistics": {
            "a": {
                "y_mean": 500.0,
                "y_std": 10.0,
                "y_range": 20.0,
                "x_mean": 1500.0,
                "x_std": 15.0,
                "x_range": 30.0,
            }
        },
        "point_distances_hz": {
            "a": {"distance_mean": 50.0, "distance_std": 5.0},
        },
        "point_distances_bark": {
            "a": {"distance_mean": 0.5, "distance_std": 0.05},
        },
    }
    df = _result_to_dataframe(result, "F2", normalized=False)
    assert "중심-개별 거리(Hz) 평균" in df.columns
    assert "중심-개별 거리(Bark) 평균" in df.columns
    assert df.loc[0, "중심-개별 거리(Hz) 평균"] == 50.0
    assert df.loc[0, "중심-개별 거리(Bark) 평균"] == 0.5


def test_result_to_dataframe_normalized_single_distance_columns():
    result = {
        "statistics": {
            "a": {
                "y_mean": 0.1,
                "y_std": 0.01,
                "y_range": 0.02,
                "x_mean": 0.2,
                "x_std": 0.02,
                "x_range": 0.04,
            }
        },
        "point_distances": {
            "a": {"distance_mean": 0.03, "distance_std": 0.004},
        },
    }
    df = _result_to_dataframe(result, "nF2", normalized=True)
    assert "중심-개별 거리 평균" in df.columns
    assert "중심-개별 거리(Bark) 평균" not in df.columns
