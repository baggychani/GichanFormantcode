import numpy as np


def calculate_pillai_score(group1_coords, group2_coords):
    """
    두 데이터 그룹(예: Group 1, Group 2) 간의 Pillai Score (Pillai's Trace)를 계산합니다.
    다변량 분산분석(MANOVA)을 통해 두 그룹이 얼마나 분리되어 있는지를 0~1 사이의 값으로 나타냅니다.

    Args:
        group1_coords (np.ndarray): 그룹 1의 좌표 데이터 (n, 2)
        group2_coords (np.ndarray): 그룹 2의 좌표 데이터 (m, 2)

    Returns:
        float or None: Pillai Score 값 (실패 시 None)
    """
    try:
        # 데이터가 NumPy 배열인지 확인 및 변환
        g1 = np.asarray(group1_coords)
        g2 = np.asarray(group2_coords)

        n1 = len(g1)
        n2 = len(g2)
        N = n1 + n2

        # 입력 배열의 길이가 너무 작으면 계산 불가
        if n1 < 2 or n2 < 2:
            return None

        # 1. 평균 벡터 계산
        mean1 = np.mean(g1, axis=0)  # v_bar_1
        mean2 = np.mean(g2, axis=0)  # v_bar_2
        grand_mean = (n1 * mean1 + n2 * mean2) / N  # v_bar (전체 평균)

        # 2. 가설 행렬 (H, 집단 간 분산) 계산
        # H = sum(n_g * (v_bar_g - v_bar) * (v_bar_g - v_bar)^T)
        diff1 = mean1 - grand_mean
        diff2 = mean2 - grand_mean
        H = n1 * np.outer(diff1, diff1) + n2 * np.outer(diff2, diff2)

        # 3. 오차 행렬 (E, 집단 내 분산) 계산
        # E = sum(sum((v_gi - v_bar_g) * (v_gi - v_bar_g)^T))
        # numpy의 행렬 연산을 사용하여 각 그룹 내 분산 합산
        E = np.zeros((2, 2))
        for v in g1:
            d = v - mean1
            E += np.outer(d, d)
        for v in g2:
            d = v - mean2
            E += np.outer(d, d)

        # 4. Pillai Score (V) 도출
        # V = Trace(H * (H + E)^-1)
        # 특이 행렬 오류 방지를 위해 np.linalg.pinv(의사역행렬) 사용
        HE_inv = np.linalg.pinv(H + E)
        V = np.trace(H @ HE_inv)

        return float(V)

    except Exception:
        return None
