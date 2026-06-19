"""Controller-facing helpers for compare-session state."""

from __future__ import annotations

from typing import MutableMapping

from core.compare_series import compare_label_offset_key


def clear_compare_label_offsets(
    offsets: MutableMapping,
    plot_key: tuple,
    session=None,
) -> None:
    """Remove all label offsets associated with one compare plot key."""
    if session is not None:
        for series_id in range(session.count):
            offsets.pop(compare_label_offset_key(plot_key, series_id), None)
        return

    prefix = tuple(plot_key)
    prefix_len = len(prefix)
    for key in list(offsets):
        if isinstance(key, tuple) and key[:prefix_len] == prefix:
            offsets.pop(key, None)
