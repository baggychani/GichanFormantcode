"""플롯·라벨 폰트 패밀리 스택.

assets/fonts 에 번들·등록된 패밀리와 Matplotlib DejaVu fallback 만 사용한다.
STIX·Latin Modern 등 미번들 폰트는 넣지 않아 findfont 경고를 원천 차단한다.
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


def use_poster_font_stack() -> bool:
    """하위 호환 플래그. 번들-only 정책 이후 True/False 동일 스택."""
    return bool(getattr(config, "USE_POSTER_FONT_STACK", False))


def axis_font_list(font_style: str) -> list[str]:
    """축·눈금 라벨용 패밀리 리스트."""
    if font_style == "serif":
        return list(FONT_LEGACY_SERIF_AXIS)
    return list(FONT_LEGACY_SANS_AXIS)


def label_font_family(label_text: str, font_style: str) -> tuple[list[str], bool]:
    """plot_engine._label_font_family / draw.plot_fonts 와 동일 시그니처."""
    from engine.plot_engine import PlotEngine

    is_serif = font_style == "serif"
    is_korean = PlotEngine._is_korean(label_text)

    if is_korean:
        if is_serif:
            return (list(FONT_LEGACY_SERIF_KO), True)
        return (list(FONT_LEGACY_SANS_KO), False)

    if is_serif:
        return (list(FONT_LEGACY_SERIF_IPA), False)

    return (list(FONT_LEGACY_SANS_IPA), False)
