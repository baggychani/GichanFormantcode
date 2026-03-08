# math_utils.py (utils 패키지)

from __future__ import annotations

import pandas as pd
import numpy as np
from scipy import stats
from typing import Union


def hz_to_linear(hz: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """리니어 스케일: 입력받은 Hz 값을 그대로 반환"""
    return hz


def hz_to_bark(hz: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """바크 스케일: Traunmuller(1990) 공식을 사용해 청각 척도로 변환"""
    hz_safe = np.maximum(hz, 0.1)  # 0 이하 값 방어
    return 26.81 / (1 + 1960 / hz_safe) - 0.53


def bark_to_hz(bark: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Bark -> Hz 역변환: 사용자 입력 범위를 연산용 Hz로 변환"""
    bark_safe = np.maximum(bark, 0.0)  # -0.53 미만 방어
    denom = (26.81 / (bark_safe + 0.53)) - 1
    return np.where(denom > 0, 1960 / denom, 20000)


def hz_to_log(hz: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """로그 스케일: 밑이 10인 상용로그 적용"""
    return np.log10(np.maximum(hz, 0.1))


def calc_f2_prime(
    f1: Union[float, np.ndarray],
    f2: Union[float, np.ndarray],
    f3: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """유효 제2포먼트(F2'): F2와 F3의 청각적 통합 현상을 보정 연산"""
    f3_safe = np.where(pd.isna(f3) | (f3 == 0), f2, f3)
    denom = np.where(f3_safe == f1, 0.1, f3_safe - f1)  # 분모 0 방지
    f2_prime = f2 + (f3_safe - f2) * ((f2 - f1) / denom)
    return np.clip(f2_prime, f2, f3_safe)  # F2~F3 범위 고정


# ---------------------------------------------------------
# 정규화 알고리즘 (Normalization Methods)
# ---------------------------------------------------------

def lobanov_normalization(df):
    """
    [로바노프 정규화 (Lobanov)]
    - 설명: 화자의 모음 공간의 가상 중심을 기준으로 값을 표현하는 방법으로, 통계학에서 널리 쓰이는 Z-score 변환과 유사합니다[cite: 70, 71]. 특정 포먼트 값에서 화자의 해당 포먼트 평균값을 뺀 후, 해당 포먼트의 표준 편차로 나누어 계산합니다[cite: 72, 73].
    - 원본 문헌: Lobanov, B.M. (1971). Classification of Russian vowels spoken by different speakers. JASA 49(2), 606-608. [cite: 177]
    """
    df_norm = df.copy()
    for col in ['F1', 'F2', 'F3']:
        if col in df_norm.columns:
            mu, sigma = df_norm[col].mean(), df_norm[col].std()
            if pd.isna(sigma) or sigma is None or (hasattr(sigma, '__float__') and sigma == 0):
                df_norm[col] = 0.0
            else:
                df_norm[col] = (df_norm[col] - mu) / sigma
            df_norm[col] = df_norm[col].replace([np.inf, -np.inf], np.nan).fillna(0)
    return df_norm


def gerstman_normalization(df):
    """
    [거스트만 정규화 (Gerstman)]
    - 설명: 모음 공간을 포먼트 주파수 범위의 양 끝점에 맞추어 정렬하는 방식입니다[cite: 67]. 각 포먼트의 양극단이 0과 1이 아닌 0과 999가 되도록 스케일링하여 모음 공간의 크기를 평준화합니다[cite: 68, 69]. (참고: Flynn 논문 11번 수식의 분모에 있는 더하기(+) 기호는 오타이며, 본 코드는 올바르게 뺄셈(-)으로 구현되었습니다.)
    - 원본 문헌: Gerstman, L. (1968). Classification of self-normalized vowels. IEEE Transactions of Audio Electroacoustics AU-16, 78-80. [cite: 173]
    """
    df_norm = df.copy()
    for col in ['F1', 'F2', 'F3']:
        if col in df_norm.columns:
            f_min, f_max = df_norm[col].min(), df_norm[col].max()
            if pd.isna(f_min) or pd.isna(f_max):
                df_norm[col] = 0.0
            else:
                denom = f_max - f_min
                if denom is None or (hasattr(denom, '__float__') and denom == 0):
                    df_norm[col] = 0.0
                else:
                    df_norm[col] = 999 * (df_norm[col] - f_min) / denom
            df_norm[col] = df_norm[col].replace([np.inf, -np.inf], np.nan).fillna(0)
    return df_norm


def watt_fabricius_normalization(df, variant='2m'):
    """
    [와트 & 파브리시우스 정규화 변형 (2mW&F)]
    - 설명: 화자의 모음 공간 중심점(centroid)을 기준으로 값을 표현하는 방식입니다[cite: 74]. 모음 공간을 삼각형으로 간주하며, F1과 F2의 최솟값 및 최댓값을 나타내는 지점들에 꼭짓점을 둡니다[cite: 75]. 2mW&F 변형 모델은 가상의 [u'] 지점을 구성할 때, 포인트 모음들의 평균값들 중 최솟값(lowest mean F1, F2 value of the point vowels)을 사용하도록 설정하여 더욱 현실적인 [u'] 배치를 제공합니다[cite: 85, 86].
    - 원본 문헌 (origW&F 기반): Watt, D.J.L., & Fabricius, A.H. (2002). Evaluation of a technique for improving the mapping of multiple speakers vowel spaces in the F1-F2 plane. Leeds Working Papers in Linguistics and Phonetics 9, 159-173. [cite: 186, 187]
    """
    df_norm = df.copy()
    try:
        vi = df['Vowel'] == 'i'
        va = df['Vowel'] == 'a'
        if not vi.any() or not va.any():
            return df_norm

        i_f1, i_f2 = df.loc[vi, 'F1'].mean(), df.loc[vi, 'F2'].mean()
        a_f1, a_f2 = df.loc[va, 'F1'].mean(), df.loc[va, 'F2'].mean()

        if np.isnan(i_f1) or np.isnan(i_f2) or np.isnan(a_f1) or np.isnan(a_f2):
            return df_norm

        if variant == '2m':
            mean_f1_by_vowel = df.groupby('Vowel')['F1'].mean()
            mean_f2_by_vowel = df.groupby('Vowel')['F2'].mean()
            u_p_f1 = mean_f1_by_vowel.min()
            u_p_f2 = mean_f2_by_vowel.min()
        else:
            u_p_f1 = i_f1
            u_p_f2 = i_f2

        s_f1 = (i_f1 + a_f1 + u_p_f1) / 3
        s_f2 = (i_f2 + u_p_f2) / 2 if variant == 'Im' else (i_f2 + a_f2 + u_p_f2) / 3

        if s_f1 is None or s_f1 == 0 or np.isnan(s_f1) or s_f2 is None or s_f2 == 0 or np.isnan(s_f2):
            return df_norm

        df_norm['F1'] = (df_norm['F1'] / s_f1).replace([np.inf, -np.inf], np.nan).fillna(0)
        df_norm['F2'] = (df_norm['F2'] / s_f2).replace([np.inf, -np.inf], np.nan).fillna(0)
    except Exception:
        return df_norm
    return df_norm


def bigham_normalization(df):
    """
    [비검 정규화 (Bigham)]
    - 설명: 기존 Watt & Fabricius 방식의 파생형으로, 중심점 S를 구설할 때 삼각형이 아닌 사각형(quadrilateral)의 무게중심을 사용합니다[cite: 86]. 화자의 최소 및 최대 F1, F2 주파수를 나타내는 점들로 꼭짓점을 구성합니다[cite: 87]. 수학적으로 각 포먼트 최솟값과 최댓값의 평균과 동일하게 연산됩니다. Flynn 논문의 실험 결과, 모음 공간 정렬(Alignment) 평가에서 전체 1위를 차지했습니다[cite: 135, 139].
    - 원본 문헌: Bigham, D.S. (2008). Dialect Contact and Accommodation among Emerging Adults in a University setting. PhD Dissertation, University of Texas at Austin. [cite: 152, 153]
    """
    df_norm = df.copy()
    try:
        for col in ['F1', 'F2']:
            if col not in df_norm.columns:
                continue
            f_min, f_max = df_norm[col].min(), df_norm[col].max()
            if np.isnan(f_min) or np.isnan(f_max):
                continue
            s_f = (f_min + f_max) / 2
            if s_f is None or s_f == 0 or np.isnan(s_f):
                continue
            df_norm[col] = (df_norm[col] / s_f).replace([np.inf, -np.inf], np.nan).fillna(0)
    except Exception:
        pass
    return df_norm


def nearey1_normalization(df):
    """
    [니어리 1 정규화 (Nearey1)]
    - 설명: 포먼트 내재적(formant-intrinsic) 공식입니다[cite: 92]. 포먼트 주파수에 로그 변환을 적용한 값에서, 해당 화자의 모든 모음에 대한 로그 변환 포먼트 평균값을 뺍니다[cite: 91, 93]. Flynn의 연구에서 모음 공간 정렬 시, Hz 원본 데이터보다 뚜렷한 개선 효과를 보여주었습니다[cite: 136].
    - 원본 문헌: Nearey, T.M. (1978). Phonetic Feature Systems for Vowels. PhD Dissertation, Indiana University. [cite: 177, 178]
    """
    df_norm = df.copy()
    for col in ['F1', 'F2', 'F3']:
        if col in df_norm.columns:
            # 0 이하의 값이 로그 연산에 들어가는 것을 막기 위한 방어 코드
            safe_vals = np.maximum(df_norm[col], 0.1)
            log_vals = np.log(safe_vals)
            mean_log = log_vals.mean()

            # 로그 변환 값에서 해당 포먼트의 평균 로그 값을 차감 (수식 18)
            df_norm[col] = log_vals - mean_log
            df_norm[col] = df_norm[col].replace([np.inf, -np.inf], np.nan).fillna(0)
    return df_norm


# ---------------------------------------------------------
# 이상치 제거 (Outlier Removal) - 마할라노비스 거리 기반
# ---------------------------------------------------------

def _ensure_xy_columns(df, plot_type):
    """plot_type에 따라 분석용 x, y 컬럼을 담은 DataFrame과 컬럼명 반환. (y, x) 순."""
    out = df[['F1', 'F2']].copy()
    out.columns = ['y_val', 'x_val']
    if plot_type == 'f1_f2':
        out['x_val'] = df['F2'].values
    elif plot_type == 'f1_f3':
        if 'F3' not in df.columns:
            return None, None, None
        out['x_val'] = df['F3'].values
    elif plot_type == 'f1_f2_prime':
        f2p = calc_f2_prime(df['F1'].values, df['F2'].values,
                            df['F3'].values if 'F3' in df.columns else df['F2'].values)
        out['x_val'] = f2p
    elif plot_type == 'f1_f2_minus_f1':
        out['x_val'] = (df['F2'] - df['F1']).values
    elif plot_type == 'f1_f2_prime_minus_f1':
        f2p = calc_f2_prime(df['F1'].values, df['F2'].values,
                            df['F3'].values if 'F3' in df.columns else df['F2'].values)
        out['x_val'] = (f2p - df['F1'].values)
    else:
        out['x_val'] = df['F2'].values
    label_col = 'Label' if 'Label' in df.columns else 'label'
    if label_col not in df.columns:
        return None, None, None
    out['_label'] = df[label_col].values
    return out, 'y_val', 'x_val'


def remove_outliers_mahalanobis(df, plot_type, sigma_option):
    """
    모음 라벨별로 마할라노비스 거리 기반 이상치 제거.
    - sigma_option: '1sigma' (68.27% 유지, 상위 ~31.73% 컷오프) 또는 '2sigma' (95.45% 유지, 상위 ~4.55% 컷오프).
    - 라벨당 5개 미만이면 해당 라벨은 건너뛰고 원본 유지.
    반환: (filtered_df, total_removed_count, per_label_removed_dict, meta_dict).
      * per_label_removed_dict: {label: removed_count}
      * meta_dict: {"labels_too_small": set([...]), "labels_tested": set([...])}
    """
    xy_df, y_col, x_col = _ensure_xy_columns(df, plot_type)
    if xy_df is None or y_col is None or x_col is None:
        return df.copy(), 0, {}, {"labels_too_small": set(), "labels_tested": set()}

    # 자유도 2 카이제곱 임계값
    if sigma_option == '1sigma':
        # 68.27% 포함 → 상위 31.73% 컷오프
        threshold = stats.chi2.ppf(0.6827, df=2)
    else:
        # 2sigma: 95.45% 포함 → 상위 4.55% 컷오프 (약 5.991)
        threshold = stats.chi2.ppf(0.9545, df=2)

    keep_mask = np.ones(len(xy_df), dtype=bool)
    per_label_removed = {}
    labels_too_small = set()
    labels_tested = set()

    for label, group in xy_df.groupby('_label'):
        g = group[[y_col, x_col]].values
        n = len(g)
        if n < 5:
            labels_too_small.add(str(label))
            continue
        mean = g.mean(axis=0)
        cov = np.cov(g.T)
        if cov.size == 1 or np.linalg.det(cov) <= 0:
            continue
        try:
            cov_inv = np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            continue
        labels_tested.add(str(label))
        # 마할라노비스 거리 제곱
        centered = g - mean
        d2 = np.sum(centered @ cov_inv * centered, axis=1)
        remove_in_group = d2 > threshold
        n_removed = remove_in_group.sum()
        if n_removed > 0:
            per_label_removed[label] = int(n_removed)
            idx_in_df = group.index
            keep_mask[idx_in_df] = ~remove_in_group

    filtered_df = df.loc[keep_mask].copy()
    total_removed = int((~keep_mask).sum())
    meta = {"labels_too_small": labels_too_small, "labels_tested": labels_tested}
    return filtered_df, total_removed, per_label_removed, meta
