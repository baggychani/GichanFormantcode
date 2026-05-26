"""plot_fonts — 한글/IPA run 분할."""

from draw.plot_fonts import font_family_for_run, iter_text_runs, is_korean_char


def test_is_korean_char():
    assert is_korean_char("안")
    assert not is_korean_char("a")
    assert not is_korean_char("ɪ")


def test_iter_text_runs_mixed():
    runs = list(iter_text_runs("heed 안녕 [i]"))
    assert runs == [("heed ", False), ("안녕", True), (" [i]", False)]


def test_font_family_for_run():
    ko_serif, medium = font_family_for_run(is_korean=True, font_style="serif")
    assert ko_serif == ["Noto Serif KR"]
    assert medium is True
    ipa_sans, medium2 = font_family_for_run(is_korean=False, font_style="sans")
    assert ipa_sans == ["Andika"]
    assert medium2 is False
