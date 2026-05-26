"""draw_reference — 참조선 라벨·스냅."""

from draw.draw_reference import format_ref_label, round_ref_value


def test_format_ref_label_hz():
    assert format_ref_label(500.0, "Hz") == "  500"
    assert format_ref_label(512.7, "Hz") == "  512"


def test_format_ref_label_norm():
    assert format_ref_label(1.234, "norm") == "  1.23"
    assert format_ref_label(2.0, "norm", normalization="gerstman") == "  2"


def test_format_ref_label_bark():
    assert format_ref_label(5.12, "bark", is_snapped=True) == "  5.12"
    assert format_ref_label(5.12, "bark", is_snapped=False) == "  5.1"


def test_round_ref_value_hz_linear():
    value, snapped = round_ref_value(512.0, "linear", "Hz")
    assert value == 510.0
    assert snapped is True


def test_round_ref_value_norm():
    value, snapped = round_ref_value(1.234, "linear", "norm")
    assert value == 1.23
    assert snapped is True
