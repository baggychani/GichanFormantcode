"""Explicit, testable Sentry consent handling."""

from __future__ import annotations

import os
from pathlib import Path

_TRUTHY = frozenset({"1", "true", "yes", "enabled"})


def has_sentry_consent(flag_path: str) -> bool:
    """Return true only for an explicit environment or file opt-in value."""
    env_value = os.environ.get("GICHANFORMANT_SENTRY_OPT_IN")
    if env_value is not None:
        return env_value.strip().casefold() in _TRUTHY
    try:
        value = Path(flag_path).read_text(encoding="utf-8").strip().casefold()
    except OSError:
        return False
    return value in _TRUTHY
