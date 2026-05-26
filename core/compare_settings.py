"""Compare 디자인 설정 dict 정규화 (Phase 0.5)."""

from __future__ import annotations

from typing import Any

from core.compare_series import (
    default_series_color,
    default_series_ell_style,
    legacy_key_from_series_id,
    normalize_series_ref,
    series_id_from_legacy,
)


def _default_series_cfg(series_id: int) -> dict[str, Any]:
    color = default_series_color(series_id)
    return {
        "lbl_color": color,
        "lbl_size": 16,
        "lbl_bold": True,
        "lbl_italic": False,
        "ell_thick": 1.0,
        "ell_style": default_series_ell_style(series_id),
        "ell_color": color,
        "ell_fill_color": None,
        "ell_fill_opacity": 0.15,
        "raw_color": "#606060",
        "centroid_marker": "o",
    }


def _discover_series_ids(settings: dict[str, Any]) -> list[int]:
    ids: set[int] = set()
    series_raw = settings.get("series")
    if isinstance(series_raw, dict):
        for key in series_raw:
            ids.add(normalize_series_ref(str(key)))
    for key, value in settings.items():
        if key in ("common", "series") or not isinstance(value, dict):
            continue
        try:
            ids.add(series_id_from_legacy(key))
        except ValueError:
            continue
    if not ids:
        return [0, 1]
    if ids.intersection({0, 1}) or "blue" in settings or "red" in settings:
        ids.update({0, 1})
    return sorted(ids)


def default_compare_design_settings(series_count: int = 2) -> dict[str, Any]:
    """Compare 기본 디자인 설정 (legacy + series 미러)."""
    if series_count < 2:
        raise ValueError("compare requires at least 2 series")
    return pack_compare_design_settings(
        common={
            "show_raw": True,
            "show_centroid": True,
            "box_spines": False,
            "show_grid": False,
            "y_label_rotation": False,
            "show_minor_ticks": True,
            "font_style": "serif",
        },
        series_cfgs=[_default_series_cfg(i) for i in range(series_count)],
    )


def pack_compare_design_settings(
    *,
    common: dict[str, Any],
    series_cfgs: list[dict[str, Any]],
) -> dict[str, Any]:
    """per-series cfg 목록 → legacy 키 + ``series`` 블록 dict."""
    if len(series_cfgs) < 2:
        raise ValueError("compare requires at least 2 series configs")
    out: dict[str, Any] = {"common": dict(common)}
    series_block: dict[str, dict[str, Any]] = {}
    for series_id, cfg in enumerate(series_cfgs):
        legacy = legacy_key_from_series_id(series_id)
        copied = dict(cfg)
        out[legacy] = copied
        series_block[str(series_id)] = dict(copied)
    out["series"] = series_block
    return out


def normalize_compare_design_settings(
    settings: dict[str, Any] | None,
) -> dict[str, Any]:
    """legacy 키와 ``series.N`` 블록을 동기화한 dict 반환."""
    if settings is None or "common" not in settings:
        return default_compare_design_settings()

    out: dict[str, Any] = {
        "common": dict(settings.get("common") or {}),
    }
    series_raw = settings.get("series")
    series_block: dict[str, dict[str, Any]] = {}

    for series_id in _discover_series_ids(settings):
        legacy = legacy_key_from_series_id(series_id)
        cfg: dict[str, Any] = {}
        if isinstance(series_raw, dict):
            cfg = dict(
                series_raw.get(str(series_id)) or series_raw.get(series_id) or {}
            )
        if legacy in settings and settings[legacy]:
            legacy_cfg = dict(settings[legacy])
            cfg = {**legacy_cfg, **cfg} if cfg else legacy_cfg
        if not cfg:
            cfg = _default_series_cfg(series_id)
        out[legacy] = dict(cfg)
        series_block[str(series_id)] = dict(cfg)

    out["series"] = series_block
    return out


def get_series_design_cfg(
    settings: dict[str, Any], series_ref: int | str
) -> dict[str, Any]:
    """series_id 또는 legacy 키로 per-series 디자인 cfg 조회."""
    normalized = normalize_compare_design_settings(settings)
    series_id = normalize_series_ref(series_ref)
    return dict(normalized.get(legacy_key_from_series_id(series_id), {}))
