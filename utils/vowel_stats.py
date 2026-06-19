"""
모음 분석 통계 계산 모듈

모음별 F1/F2 (또는 선택된 축) 통계 및 Centroid까지의 유클리드 거리를 계산합니다.
단일 플롯과 다중 플롯(compare plot) 모두에서 사용 가능하도록 설계되었습니다.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, Any

from utils.math_utils import hz_to_bark


def calculate_vowel_statistics(
    df: pd.DataFrame, x_col: str = "F2", y_col: str = "F1", label_col: str = "Label"
) -> Dict[str, Dict[str, Any]]:
    """
    모음별 기본 통계량 계산 (평균, 표준편차, 범위)

    Parameters:
        df: 포먼트 데이터 DataFrame
        x_col: X축 컬럼명 (기본값: 'F2')
        y_col: Y축 컬럼명 (기본값: 'F1')
        label_col: 모음 라벨 컬럼명 (기본값: 'Label')

    Returns:
        dict: {
            vowel: {
                'x_mean': float, 'x_std': float, 'x_min': float, 'x_max': float, 'x_range': float,
                'y_mean': float, 'y_std': float, 'y_min': float, 'y_max': float, 'y_range': float,
                'count': int
            }
        }
    """
    if df.empty or label_col not in df.columns:
        return {}

    if x_col not in df.columns or y_col not in df.columns:
        return {}

    stats = {}
    for vowel, group in df.groupby(label_col):
        x_vals = group[x_col].dropna()
        y_vals = group[y_col].dropna()

        if len(x_vals) == 0 or len(y_vals) == 0:
            continue

        stats[vowel] = {
            "x_mean": float(x_vals.mean()),
            "x_std": float(x_vals.std()) if len(x_vals) > 1 else 0.0,
            "x_min": float(x_vals.min()),
            "x_max": float(x_vals.max()),
            "x_range": float(x_vals.max() - x_vals.min()),
            "y_mean": float(y_vals.mean()),
            "y_std": float(y_vals.std()) if len(y_vals) > 1 else 0.0,
            "y_min": float(y_vals.min()),
            "y_max": float(y_vals.max()),
            "y_range": float(y_vals.max() - y_vals.min()),
            "count": len(group),
        }

    return stats


def calculate_global_centroid(
    df: pd.DataFrame, x_col: str = "F2", y_col: str = "F1", label_col: str = "Label"
) -> Tuple[Optional[float], Optional[float]]:
    """
    전체 모음의 중심점(Centroid) 계산
    각 모음의 평균점을 구한 뒤, 그 평균점들의 중심을 계산합니다.

    Parameters:
        df: 포먼트 데이터 DataFrame
        x_col: X축 컬럼명
        y_col: Y축 컬럼명
        label_col: 모음 라벨 컬럼명

    Returns:
        (centroid_x, centroid_y) 또는 (None, None)
    """
    stats = calculate_vowel_statistics(df, x_col, y_col, label_col)

    if not stats:
        return None, None

    x_means = [s["x_mean"] for s in stats.values()]
    y_means = [s["y_mean"] for s in stats.values()]

    centroid_x = np.mean(x_means)
    centroid_y = np.mean(y_means)

    return float(centroid_x), float(centroid_y)


def calculate_centroid_distances(
    df: pd.DataFrame, x_col: str = "F2", y_col: str = "F1", label_col: str = "Label"
) -> Dict[str, Dict[str, float]]:
    """
    각 모음 중심에서 전체 Centroid까지의 유클리드 거리 계산

    Parameters:
        df: 포먼트 데이터 DataFrame
        x_col: X축 컬럼명
        y_col: Y축 컬럼명
        label_col: 모음 라벨 컬럼명

    Returns:
        dict: {
            vowel: {
                'distance_to_centroid': float,
                'vowel_center_x': float,
                'vowel_center_y': float
            }
        }
    """
    stats = calculate_vowel_statistics(df, x_col, y_col, label_col)
    centroid_x, centroid_y = calculate_global_centroid(df, x_col, y_col, label_col)

    if centroid_x is None or centroid_y is None:
        return {}

    distances = {}
    for vowel, s in stats.items():
        vx, vy = s["x_mean"], s["y_mean"]
        dist = np.sqrt((vx - centroid_x) ** 2 + (vy - centroid_y) ** 2)
        distances[vowel] = {
            "distance_to_centroid": float(dist),
            "vowel_center_x": vx,
            "vowel_center_y": vy,
        }

    return distances


def calculate_pairwise_mahalanobis_distances(
    df: pd.DataFrame,
    x_col: str = "F2",
    y_col: str = "F1",
    label_col: str = "Label",
    *,
    min_group_size: int = 2,
) -> Dict[Tuple[str, str], Dict[str, float]]:
    """모음 중심 쌍별 Mahalanobis distance를 계산한다.

    각 모음 쌍의 중심 차이를 두 모음 데이터의 pooled covariance로 스케일링한다.
    공분산이 singular인 경우에도 연구 데이터에서 자주 발생하는 작은 표본 문제를
    견딜 수 있도록 pseudo-inverse를 사용한다.
    """
    if df.empty or label_col not in df.columns:
        return {}
    if x_col not in df.columns or y_col not in df.columns:
        return {}

    result: Dict[Tuple[str, str], Dict[str, float]] = {}
    labels = list(pd.unique(df[label_col].dropna()))
    for i, label_a in enumerate(labels):
        group_a = df[df[label_col] == label_a][[x_col, y_col]].dropna()
        if len(group_a) < min_group_size:
            continue
        for label_b in labels[i + 1 :]:
            group_b = df[df[label_col] == label_b][[x_col, y_col]].dropna()
            if len(group_b) < min_group_size:
                continue

            coords_a = group_a.to_numpy(dtype=float)
            coords_b = group_b.to_numpy(dtype=float)
            pooled = np.vstack([coords_a, coords_b])
            cov = np.cov(pooled.T)
            if cov.ndim != 2 or cov.shape != (2, 2):
                continue
            cov_inv = np.linalg.pinv(cov)
            diff = coords_a.mean(axis=0) - coords_b.mean(axis=0)
            distance_sq = float(diff.T @ cov_inv @ diff)
            distance = float(np.sqrt(max(distance_sq, 0.0)))
            result[(str(label_a), str(label_b))] = {
                "distance": distance,
                "x_mean_diff": float(diff[0]),
                "y_mean_diff": float(diff[1]),
                "n_a": int(len(coords_a)),
                "n_b": int(len(coords_b)),
            }
    return result


def calculate_point_distances_from_centroid(
    df: pd.DataFrame, x_col: str = "F2", y_col: str = "F1", label_col: str = "Label"
) -> Dict[str, Dict[str, float]]:
    """
    각 모음 내 개별 데이터 포인트들에서 해당 모음의 중심까지의 거리 통계

    Parameters:
        df: 포먼트 데이터 DataFrame
        x_col: X축 컬럼명
        y_col: Y축 컬럼명
        label_col: 모음 라벨 컬럼명

    Returns:
        dict: {
            vowel: {
                'distance_mean': float,
                'distance_std': float,
                'distance_min': float,
                'distance_max': float
            }
        }
    """
    stats = calculate_vowel_statistics(df, x_col, y_col, label_col)

    if not stats:
        return {}

    result = {}
    for vowel, group in df.groupby(label_col):
        if vowel not in stats:
            continue

        cx, cy = stats[vowel]["x_mean"], stats[vowel]["y_mean"]
        x_vals = group[x_col].values
        y_vals = group[y_col].values

        distances = np.sqrt((x_vals - cx) ** 2 + (y_vals - cy) ** 2)

        result[vowel] = {
            "distance_mean": float(np.mean(distances)),
            "distance_std": float(np.std(distances)) if len(distances) > 1 else 0.0,
            "distance_min": float(np.min(distances)),
            "distance_max": float(np.max(distances)),
        }

    return result


def calculate_point_distances_from_centroid_bark(
    df: pd.DataFrame,
    label_col: str = "Label",
    x_hz=None,
) -> Dict[str, Dict[str, float]]:
    """
    각 모음 내 개별 포인트에서 해당 모음의 중심(Bark 공간)까지의 유클리드 거리 통계.
    F1과 X축(Hz)을 Bark로 변환한 (F1_bark, x_bark) 공간에서 centroid와 거리 계산.
    플롯 X축(Hz) 배열 x_hz를 넘기면 해당 축 기준 Bark 거리로 계산. None이면 df['F2'] 사용.
    """
    if df.empty or label_col not in df.columns:
        return {}
    if "F1" not in df.columns:
        return {}
    x_vals = np.asarray(x_hz) if x_hz is not None else df["F2"].values
    if x_hz is None and "F2" not in df.columns:
        return {}
    if len(x_vals) != len(df):
        return {}
    f1_bark = hz_to_bark(df["F1"].values)
    x_bark = hz_to_bark(x_vals)
    labels = df[label_col].values
    result = {}
    for vowel in pd.unique(labels):
        mask = labels == vowel
        if not np.any(mask):
            continue
        cx = float(np.mean(f1_bark[mask]))
        cy = float(np.mean(x_bark[mask]))
        dists = np.sqrt((f1_bark[mask] - cx) ** 2 + (x_bark[mask] - cy) ** 2)
        result[vowel] = {
            "distance_mean": float(np.mean(dists)),
            "distance_std": float(np.std(dists)) if np.sum(mask) > 1 else 0.0,
            "distance_min": float(np.min(dists)),
            "distance_max": float(np.max(dists)),
        }
    return result


def analyze_vowels(
    df: pd.DataFrame,
    x_col: str = "F2",
    y_col: str = "F1",
    label_col: str = "Label",
    normalization: Optional[str] = None,
) -> Dict[str, Any]:
    """
    종합 모음 분석 함수

    단일 플롯 및 compare_plot 확장을 위한 통합 인터페이스입니다.

    Parameters:
        df: 포먼트 데이터 DataFrame
        x_col: X축 컬럼명 (예: 'F2', 'nF2')
        y_col: Y축 컬럼명 (예: 'F1', 'nF1')
        label_col: 모음 라벨 컬럼명
        normalization: 정규화 방법 (None, 'Lobanov', 'Gerstman' 등)

    Returns:
        dict: {
            'statistics': { vowel: {...} },
            'centroid': (x, y),
            'centroid_distances': { vowel: {...} },
            'point_distances': { vowel: {...} },
            'metadata': {
                'x_col': str,
                'y_col': str,
                'normalization': str or None,
                'total_points': int,
                'vowel_count': int
            }
        }
    """
    statistics = calculate_vowel_statistics(df, x_col, y_col, label_col)
    centroid = calculate_global_centroid(df, x_col, y_col, label_col)
    centroid_distances = calculate_centroid_distances(df, x_col, y_col, label_col)
    point_distances = calculate_point_distances_from_centroid(
        df, x_col, y_col, label_col
    )

    return {
        "statistics": statistics,
        "centroid": centroid,
        "centroid_distances": centroid_distances,
        "point_distances": point_distances,
        "metadata": {
            "x_col": x_col,
            "y_col": y_col,
            "normalization": normalization,
            "total_points": len(df),
            "vowel_count": len(statistics),
        },
    }


def analyze_vowels_compare(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    x_col: str = "F2",
    y_col: str = "F1",
    label_col: str = "Label",
    normalization: Optional[str] = None,
) -> Dict[str, Any]:
    """
    다중 플롯(compare plot)용 종합 모음 분석 함수

    두 데이터셋을 비교 분석합니다.

    Parameters:
        df_a: 첫 번째 데이터셋 (Blue)
        df_b: 두 번째 데이터셋 (Red)
        x_col: X축 컬럼명
        y_col: Y축 컬럼명
        label_col: 모음 라벨 컬럼명
        normalization: 정규화 방법

    Returns:
        dict: {
            'data_a': analyze_vowels() 결과,
            'data_b': analyze_vowels() 결과,
            'comparison': { vowel: { 'x_diff', 'y_diff', 'distance_diff' } }
        }
    """
    analysis_a = analyze_vowels(df_a, x_col, y_col, label_col, normalization)
    analysis_b = analyze_vowels(df_b, x_col, y_col, label_col, normalization)

    comparison = {}
    common_vowels = set(analysis_a["statistics"].keys()) & set(
        analysis_b["statistics"].keys()
    )

    for vowel in common_vowels:
        stat_a = analysis_a["statistics"][vowel]
        stat_b = analysis_b["statistics"][vowel]

        comparison[vowel] = {
            "x_mean_diff": stat_a["x_mean"] - stat_b["x_mean"],
            "y_mean_diff": stat_a["y_mean"] - stat_b["y_mean"],
            "x_std_diff": stat_a["x_std"] - stat_b["x_std"],
            "y_std_diff": stat_a["y_std"] - stat_b["y_std"],
        }

        if (
            vowel in analysis_a["centroid_distances"]
            and vowel in analysis_b["centroid_distances"]
        ):
            dist_a = analysis_a["centroid_distances"][vowel]["distance_to_centroid"]
            dist_b = analysis_b["centroid_distances"][vowel]["distance_to_centroid"]
            comparison[vowel]["centroid_distance_diff"] = dist_a - dist_b

    return {"data_a": analysis_a, "data_b": analysis_b, "comparison": comparison}
