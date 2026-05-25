"""Compare N-way 런타임 브릿지 — UI 없이 Controller↔PlotEngine 연결."""

from __future__ import annotations

from typing import Any, Protocol

from core.compare_series import (
    CompareRenderResult,
    CompareSeriesInput,
    CompareSession,
    compare_label_offset_key,
    compare_plot_key,
    legacy_key_from_series_id,
    normalize_series_ref,
)
from core.compare_settings import (
    get_series_design_cfg,
    normalize_compare_design_settings,
)


class ComparePopupSeriesAccess(Protocol):
    """Compare 팝업이 per-series 상태를 제공할 때 사용하는 프로토콜."""

    def get_design_settings(self) -> dict: ...

    def get_filter_state_for_series(self, series_id: int) -> dict: ...

    def get_layer_design_overrides_for_series(self, series_id: int) -> dict: ...


def resolve_compare_session(
    popup_window: Any,
    idx_blue: int,
    idx_red: int,
) -> CompareSession:
    session = getattr(popup_window, "compare_session", None)
    if session is not None:
        return session
    return CompareSession.from_data_indices(idx_blue, idx_red)


def get_compare_names(controller: Any, session: CompareSession) -> list[str]:
    names: list[str] = []
    for series_id in range(session.count):
        idx = session.data_index(series_id)
        item = controller.get_data_item_at(idx)
        names.append(item["name"] if item else "")
    return names


def get_compare_data_items(
    controller: Any,
    session: CompareSession,
) -> list[dict | None]:
    return [
        controller.get_data_item_at(session.data_index(series_id))
        for series_id in range(session.count)
    ]


def _read_filter_state(popup_window: Any, series_id: int) -> dict:
    getter = getattr(popup_window, "get_filter_state_for_series", None)
    if getter is not None:
        return dict(getter(series_id) or {})
    legacy = legacy_key_from_series_id(series_id)
    legacy_getter = getattr(popup_window, f"get_filter_state_{legacy}", None)
    if legacy_getter is not None:
        return dict(legacy_getter() or {})
    return {}


def _read_layer_overrides(popup_window: Any, series_id: int) -> dict:
    getter = getattr(popup_window, "get_layer_design_overrides_for_series", None)
    if getter is not None:
        return dict(getter(series_id) or {})
    legacy = legacy_key_from_series_id(series_id)
    legacy_getter = getattr(popup_window, f"get_layer_design_overrides_{legacy}", None)
    if legacy_getter is not None:
        return dict(legacy_getter() or {})
    return {}


def build_compare_series_inputs(
    controller: Any,
    session: CompareSession,
    popup_window: Any,
    *,
    design_settings: dict | None,
    plot_type: str,
    norm: str | None,
    plot_key: tuple,
) -> list[CompareSeriesInput]:
    """CompareSession + 팝업 상태 → PlotEngine 입력 목록."""
    normalized_design = normalize_compare_design_settings(design_settings)
    inputs: list[CompareSeriesInput] = []

    for series_id in range(session.count):
        idx = session.data_index(series_id)
        item = controller.get_data_item_at(idx)
        df = item["df"] if item else None
        if norm and df is not None:
            df = controller._apply_normalization(df, norm)
        name = item["name"] if item else ""
        offset_key = compare_label_offset_key(plot_key, series_id)
        custom_offsets = controller.custom_label_offsets.get(offset_key, {})
        inputs.append(
            CompareSeriesInput(
                df=df,
                display_name=name,
                filter_state=_read_filter_state(popup_window, series_id),
                design_cfg=get_series_design_cfg(normalized_design, series_id),
                layer_overrides=_read_layer_overrides(popup_window, series_id),
                custom_label_offsets=custom_offsets,
            )
        )
    return inputs


def apply_compare_render_to_popup(
    popup_window: Any,
    result: CompareRenderResult,
    session: CompareSession,
    plot_key: tuple,
) -> None:
    """PlotEngine N-way 결과를 팝업 legacy 필드 + per-series dict에 반영."""
    popup_window.snapping_data = result.snapping_data
    popup_window.label_data_by_series = {
        series_id: list(entries) for series_id, entries in result.label_data.items()
    }
    popup_window.label_text_artists_by_series = {
        series_id: list(artists)
        for series_id, artists in result.label_text_artists.items()
    }
    popup_window.label_data_blue = result.label_data.get(0, [])
    popup_window.label_data_red = result.label_data.get(1, [])
    popup_window.label_text_artists_blue = result.label_text_artists.get(0, [])
    popup_window.label_text_artists_red = result.label_text_artists.get(1, [])
    popup_window._plot_key_compare = plot_key
    popup_window.compare_session = session


def label_data_for_series(popup_window: Any, series_ref: int | str) -> list[dict]:
    series_id = normalize_series_ref(series_ref)
    by_series = getattr(popup_window, "label_data_by_series", None)
    if isinstance(by_series, dict) and series_id in by_series:
        return by_series[series_id]
    legacy = legacy_key_from_series_id(series_id)
    return getattr(popup_window, f"label_data_{legacy}", [])


def label_text_artists_for_series(popup_window: Any, series_ref: int | str) -> list:
    series_id = normalize_series_ref(series_ref)
    by_series = getattr(popup_window, "label_text_artists_by_series", None)
    if isinstance(by_series, dict) and series_id in by_series:
        return by_series[series_id]
    legacy = legacy_key_from_series_id(series_id)
    return getattr(popup_window, f"label_text_artists_{legacy}", [])


def make_compare_plot_key(
    session: CompareSession,
    plot_type: str,
    norm: str | None = None,
) -> tuple:
    return compare_plot_key(session.data_indices, plot_type, norm)
