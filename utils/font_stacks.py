"""플롯·라벨 폰트 패밀리 스택 (포스터 STIX 우선, legacy fallback).

롤백: config.USE_POSTER_FONT_STACK = False
"""

from __future__ import annotations

import config

# --- Legacy (v2.4.2 기본, 삭제·변경하지 않음) ---
FONT_LEGACY_SERIF_AXIS = ["Noto Serif KR", "Charis SIL", "DejaVu Serif"]
FONT_LEGACY_SERIF_KO = ["Noto Serif KR"]
FONT_LEGACY_SERIF_IPA = ["Charis SIL"]
FONT_LEGACY_SANS_AXIS = ["Noto Sans KR", "Andika", "DejaVu Sans"]
FONT_LEGACY_SANS_KO = ["Noto Sans KR"]
FONT_LEGACY_SANS_IPA = ["Andika"]

# --- Poster (poster/poster.css 표·IPA, plot_style.yaml STIX 계열) ---
FONT_POSTER_SERIF_LATIN = [
    "STIX Two Text",
    "STIXGeneral",
    "Latin Modern Roman",
    "Times New Roman",
]
FONT_POSTER_SANS_KO = ["Noto Sans KR", "Malgun Gothic"]


def _merge_unique(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for name in group:
            if name not in seen:
                seen.add(name)
                out.append(name)
    return out


def use_poster_font_stack() -> bool:
    return bool(getattr(config, "USE_POSTER_FONT_STACK", False))


def axis_font_list(font_style: str) -> list[str]:
    """축·눈금 라벨용 패밀리 리스트."""
    if font_style == "serif":
        if use_poster_font_stack():
            return _merge_unique(
                FONT_POSTER_SERIF_LATIN,
                FONT_LEGACY_SERIF_AXIS,
            )
        return list(FONT_LEGACY_SERIF_AXIS)
    if use_poster_font_stack():
        return _merge_unique(FONT_POSTER_SANS_KO, FONT_LEGACY_SANS_AXIS)
    return list(FONT_LEGACY_SANS_AXIS)


def label_font_family(label_text: str, font_style: str) -> tuple[list[str], bool]:
    """plot_engine._label_font_family / draw.plot_fonts 와 동일 시그니처."""
    from engine.plot_engine import PlotEngine

    is_serif = font_style == "serif"
    is_korean = PlotEngine._is_korean(label_text)

    if is_korean:
        if is_serif:
            if use_poster_font_stack():
                families = _merge_unique(
                    FONT_LEGACY_SERIF_KO,
                    FONT_POSTER_SANS_KO,
                )
            else:
                families = list(FONT_LEGACY_SERIF_KO)
        else:
            if use_poster_font_stack():
                families = _merge_unique(
                    FONT_POSTER_SANS_KO,
                    FONT_LEGACY_SANS_KO,
                )
            else:
                families = list(FONT_LEGACY_SANS_KO)
        return (families, is_serif)

    if is_serif:
        if use_poster_font_stack():
            families = _merge_unique(
                FONT_POSTER_SERIF_LATIN,
                FONT_LEGACY_SERIF_IPA,
                FONT_LEGACY_SERIF_AXIS,
            )
        else:
            families = list(FONT_LEGACY_SERIF_IPA)
    else:
        if use_poster_font_stack():
            families = _merge_unique(
                FONT_POSTER_SERIF_LATIN,
                FONT_LEGACY_SANS_IPA,
            )
        else:
            families = list(FONT_LEGACY_SANS_IPA)
    return (families, False)
