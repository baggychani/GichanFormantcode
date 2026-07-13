from utils.sentry_consent import has_sentry_consent


def test_missing_or_empty_flag_does_not_opt_in(tmp_path, monkeypatch):
    monkeypatch.delenv("GICHANFORMANT_SENTRY_OPT_IN", raising=False)
    flag = tmp_path / "sentry_opt_in.config"

    assert has_sentry_consent(str(flag)) is False
    flag.write_text("", encoding="utf-8")
    assert has_sentry_consent(str(flag)) is False


def test_enabled_flag_explicitly_opts_in(tmp_path, monkeypatch):
    monkeypatch.delenv("GICHANFORMANT_SENTRY_OPT_IN", raising=False)
    flag = tmp_path / "sentry_opt_in.config"
    flag.write_text("enabled\n", encoding="utf-8")

    assert has_sentry_consent(str(flag)) is True


def test_environment_value_explicitly_overrides_file(tmp_path, monkeypatch):
    flag = tmp_path / "sentry_opt_in.config"
    flag.write_text("enabled", encoding="utf-8")
    monkeypatch.setenv("GICHANFORMANT_SENTRY_OPT_IN", "false")

    assert has_sentry_consent(str(flag)) is False
