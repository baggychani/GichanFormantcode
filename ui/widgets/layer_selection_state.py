from __future__ import annotations


def effective_override_value(
    vowel: str,
    key: str,
    overrides: dict[str, dict],
    default_design: dict,
    fallback,
):
    layer_override = overrides.get(vowel, {}) or {}
    return layer_override.get(key, default_design.get(key, fallback))


def common_override_value(
    selected_vowels: list[str],
    key: str,
    overrides: dict[str, dict],
    default_design: dict,
    fallback,
):
    values = [
        effective_override_value(vowel, key, overrides, default_design, fallback)
        for vowel in selected_vowels
    ]
    if not values:
        return default_design.get(key, fallback)
    first = values[0]
    return first if all(value == first for value in values[1:]) else None
