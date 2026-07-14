"""Bridge trusted legacy popup edits into the shared plot session."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.interactive_plot_state import PlotSessionState


class PlotSessionService:
    @staticmethod
    def sync_from_popup(
        session: PlotSessionState,
        popup: Any,
        *,
        fallback_index: int,
        manual_ranges: dict[str, Any],
        design_settings: dict[str, Any],
        filter_state: dict[str, Any] | None,
        layer_overrides: dict[str, Any] | None,
    ) -> None:
        index = int(getattr(popup, "current_idx", fallback_index))
        session.active = True
        session.current_idx = index
        session.fixed_plot_params = deepcopy(
            getattr(popup, "fixed_plot_params", {}) or {}
        )
        session.ranges = {key: str(value) for key, value in manual_ranges.items()}
        if hasattr(popup, "get_sigma"):
            session.sigma = str(popup.get_sigma())
        session.design_settings = deepcopy(design_settings)
        session.vowel_filter_state_by_file[index] = dict(filter_state or {})
        session.layer_design_overrides_by_file[index] = deepcopy(layer_overrides or {})
        locked_by_file = getattr(popup, "layer_locked_vowels_by_file", {}) or {}
        session.layer_locked_vowels_by_file[index] = sorted(
            locked_by_file.get(index, set())
        )
        session.layer_order_by_file[index] = list(
            getattr(popup, "layer_order", []) or []
        )
        session.draw_objects_by_file = deepcopy(
            getattr(popup, "_draw_objects_by_file", {}) or {}
        )
        session.revision += 1

    @staticmethod
    def apply_to_popup(session: PlotSessionState, popup: Any, *, index: int) -> None:
        session.active = True
        popup.design_settings = deepcopy(session.design_settings)
        popup.vowel_filter_state_by_file = deepcopy(session.vowel_filter_state_by_file)
        popup.layer_design_overrides_by_file = deepcopy(
            session.layer_design_overrides_by_file
        )
        popup.layer_locked_vowels_by_file = {
            item_index: set(values)
            for item_index, values in session.layer_locked_vowels_by_file.items()
        }
        popup.layer_order = list(session.layer_order_by_file.get(index, []))
        popup._draw_objects_by_file = deepcopy(session.draw_objects_by_file)
        popup.fixed_plot_params.update(session.fixed_plot_params)
        popup.fixed_plot_params["sigma"] = float(session.sigma)
