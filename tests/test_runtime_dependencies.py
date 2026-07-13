import importlib.util


def test_legacy_xls_reader_is_installed():
    assert importlib.util.find_spec("xlrd") is not None
