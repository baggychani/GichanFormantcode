"""플롯 라벨과 동일한 sans/serif · 한글/IPA 폰트 선택."""

from __future__ import annotations

from matplotlib.font_manager import FontProperties

from engine.plot_engine import PlotEngine


def resolve_font_style(ctx) -> str:
    ds = getattr(ctx, "design_settings", None) or {}
    if not isinstance(ds, dict):
        return "serif"
    if ds.get("font_style"):
        return str(ds.get("font_style"))
    common = ds.get("common", {})
    if isinstance(common, dict) and common.get("font_style"):
        return str(common.get("font_style"))
    return "serif"


def is_korean_char(ch: str) -> bool:
    return PlotEngine._is_korean(ch)


def font_family_for_run(*, is_korean: bool, font_style: str) -> tuple[list[str], bool]:
    """(fontfamily_list, serif_use_medium) — plot_engine._label_font_family 와 동일."""
    if is_korean:
        is_serif = font_style == "serif"
        return (["Noto Serif KR"] if is_serif else ["Noto Sans KR"], is_serif)
    is_serif = font_style == "serif"
    return (["Charis SIL"] if is_serif else ["Andika"], False)


def font_properties_for_run(
    *,
    is_korean: bool,
    font_style: str,
    font_size: float,
    font_bold: bool,
) -> FontProperties:
    family, serif_use_medium = font_family_for_run(
        is_korean=is_korean, font_style=font_style
    )
    if serif_use_medium and not font_bold:
        weight = "medium"
    else:
        weight = "bold" if font_bold else "normal"
    return FontProperties(
        family=family,
        size=font_size,
        weight=weight,
        style="normal",
    )


def iter_text_runs(text: str):
    """문자열을 (run_text, is_korean) 단위로 분할. '\\n'은 별도 run."""
    if not text:
        return
    buf: list[str] = []
    run_ko: bool | None = None
    for ch in text:
        if ch == "\n":
            if buf:
                yield ("".join(buf), run_ko if run_ko is not None else False)
                buf = []
                run_ko = None
            yield ("\n", False)
            continue
        ko = is_korean_char(ch)
        if run_ko is None:
            run_ko = ko
            buf = [ch]
        elif ko == run_ko:
            buf.append(ch)
        else:
            yield ("".join(buf), run_ko)
            buf = [ch]
            run_ko = ko
    if buf:
        yield ("".join(buf), run_ko if run_ko is not None else False)
