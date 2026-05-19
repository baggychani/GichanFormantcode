"""포먼트 DataFrame → GichanFormant 입력용 .txt 텍스트."""

from __future__ import annotations

import pandas as pd


def _format_formant_value(value: float) -> str:
    if pd.isna(value):
        return ""
    rounded = round(float(value))
    if abs(float(value) - rounded) < 1e-6:
        return str(int(rounded))
    return f"{float(value):g}"


def _format_slash_label(label) -> str:
    s = str(label).strip()
    if not s or s.lower() in ("nan", "none"):
        return ""
    if s.startswith("/") and s.endswith("/") and len(s) >= 2:
        return s
    inner = s.strip("/")
    return f"/{inner}/"


def formant_dataframe_to_txt(df: pd.DataFrame, *, include_f3: bool) -> str:
    """로드 가이드와 동일한 열 순서: F1, F2, [F3], /라벨/ (탭 구분)."""
    if df is None or df.empty:
        return ""
    work = df
    if "Label" not in work.columns:
        return ""
    has_f3_col = include_f3 and "F3" in work.columns
    lines: list[str] = []
    for _, row in work.iterrows():
        label = _format_slash_label(row["Label"])
        if not label:
            continue
        f1 = _format_formant_value(row.get("F1"))
        f2 = _format_formant_value(row.get("F2"))
        if not f1 or not f2:
            continue
        if has_f3_col:
            f3 = _format_formant_value(row.get("F3"))
            if f3:
                lines.append(f"{f1}\t{f2}\t{f3}\t{label}")
            else:
                lines.append(f"{f1}\t{f2}\t\t{label}")
        else:
            lines.append(f"{f1}\t{f2}\t{label}")
    return "\n".join(lines) + ("\n" if lines else "")
