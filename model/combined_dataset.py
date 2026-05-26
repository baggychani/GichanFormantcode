# model/combined_dataset.py
"""
Combined 항목 구성 유틸리티.

여러 화자(파일)의 포먼트 데이터를 하나의 DataFrame으로 합쳐
plot_data_list 항목과 동일한 형식의 dict를 생성합니다.

UI/엔진/저장 워커는 이 dict를 기존 개별 화자 항목과 동일하게 취급하므로,
별도의 Combined 전용 분기가 거의 필요하지 않습니다.

Combined 항목은 항상 plot_data_list의 마지막에 위치한다고 가정합니다.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

import config


def build_combined_entry(real_items: list[dict]) -> Optional[dict]:
    """real_items: 화자별 plot_data_list 항목 리스트 (Combined 제외).

    각 항목은 다음 키를 가집니다: 'name', 'df', 'df_original', 'has_f3'.
    반환: Combined 항목 dict 또는 None (대상이 2개 미만이거나 합칠 데이터가 없을 때).
    Combined 항목은 동일한 키 + 'is_combined': True 를 추가로 가집니다.
    """
    if not real_items or len(real_items) < 2:
        return None

    dfs = [
        it["df"]
        for it in real_items
        if isinstance(it.get("df"), pd.DataFrame) and not it["df"].empty
    ]
    if not dfs:
        return None

    df_combined = pd.concat(dfs, ignore_index=True)

    # df_original이 없는 항목은 현재 df를 원본으로 간주 (호환성)
    df_origs = []
    for it in real_items:
        df_o = it.get("df_original")
        if not isinstance(df_o, pd.DataFrame) or df_o.empty:
            df_o = it.get("df")
        if isinstance(df_o, pd.DataFrame) and not df_o.empty:
            df_origs.append(df_o)
    df_orig_combined = (
        pd.concat(df_origs, ignore_index=True) if df_origs else df_combined.copy()
    )

    has_f3 = all(bool(it.get("has_f3", False)) for it in real_items)
    n = len(real_items)
    display = getattr(config, "COMBINED_DISPLAY_NAME_FMT", "Combined ({n}명)").format(
        n=n
    )
    # 저장·plot_data_list 식별자: 다른 화자 파일과 동일하게 GichanFormant_ 접두사 사용.
    # UI 표시는 strip_gichan_prefix()로 display 문자열만 보여 준다.
    name = f"GichanFormant_{display}"

    return {
        "name": name,
        "df": df_combined,
        "df_original": df_orig_combined,
        "has_f3": has_f3,
        "is_combined": True,
        "combined_source_names": [it.get("name", "") for it in real_items],
    }


def build_compare_group_entry(real_items: list[dict]) -> Optional[dict]:
    """Compare 한쪽(A/B) 그룹 — 1명이면 그 파일, 2명 이상이면 subset Combined."""
    if not real_items:
        return None
    if len(real_items) == 1:
        it = real_items[0]
        df = it.get("df")
        if not isinstance(df, pd.DataFrame) or df.empty:
            return None
        df_orig = it.get("df_original")
        if not isinstance(df_orig, pd.DataFrame) or df_orig.empty:
            df_orig = df
        return {
            "name": it.get("name", ""),
            "df": df,
            "df_original": df_orig,
            "has_f3": bool(it.get("has_f3", False)),
            "is_combined": False,
        }
    return build_combined_entry(real_items)
