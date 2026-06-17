from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from core.compare_series import legacy_key_from_series_id, normalize_series_ref


class LabelManager:
    """라벨(모음) 도메인 상태 접근 전용 매니저."""

    def __init__(
        self,
        popup: object,
        state_key: str | None = None,
        series_id: int | str | None = None,
    ):
        self._popup = popup
        self._series_id = self._coerce_series_id(series_id, state_key)
        self._state_key = None if self._series_id is not None else state_key

    @staticmethod
    def _coerce_series_id(
        series_id: int | str | None,
        state_key: str | None,
    ) -> int | None:
        ref = series_id if series_id is not None else state_key
        if ref is None:
            return None
        try:
            return normalize_series_ref(ref)
        except (TypeError, ValueError):
            return None

    def _is_series_scoped(self) -> bool:
        return self._series_id is not None

    def _series_map(self, attr: str) -> dict:
        mapping = getattr(self._popup, attr, None)
        if mapping is None:
            mapping = {}
            setattr(self._popup, attr, mapping)
        return mapping

    def _legacy_attr(self, base_name: str) -> str | None:
        if self._series_id is None or self._series_id > 1:
            return None
        return f"{base_name}_{legacy_key_from_series_id(self._series_id)}"

    def _scoped_attr(self, base_name: str) -> str:
        if self._state_key:
            return f"{base_name}_{self._state_key}"
        return base_name

    def get_filter_state(self) -> Dict[str, str]:
        if self._is_series_scoped():
            states = getattr(self._popup, "vowel_filter_states", {}) or {}
            if self._series_id in states:
                return dict(states[self._series_id] or {})
            legacy_attr = self._legacy_attr("vowel_filter_state")
            if legacy_attr:
                return dict(getattr(self._popup, legacy_attr, {}) or {})
            return {}
        return dict(
            getattr(self._popup, self._scoped_attr("vowel_filter_state"), {}) or {}
        )

    def set_filter_state(self, state: Dict[str, str]) -> None:
        if self._is_series_scoped():
            copied = dict(state)
            self._series_map("vowel_filter_states")[self._series_id] = copied
            return
        setattr(self._popup, self._scoped_attr("vowel_filter_state"), dict(state))

    def get_layer_overrides(self) -> Dict[str, Dict[str, Any]]:
        if self._is_series_scoped():
            by_series = (
                getattr(self._popup, "layer_design_overrides_by_series", {}) or {}
            )
            if self._series_id in by_series:
                return deepcopy(by_series[self._series_id])
            legacy_attr = self._legacy_attr("layer_design_overrides")
            if legacy_attr:
                return deepcopy(getattr(self._popup, legacy_attr, {}) or {})
            return {}
        return deepcopy(
            getattr(self._popup, self._scoped_attr("layer_design_overrides"), {}) or {}
        )

    def set_layer_overrides(self, overrides: Dict[str, Dict[str, Any]]) -> None:
        if self._is_series_scoped():
            copied = deepcopy(overrides)
            self._series_map("layer_design_overrides_by_series")[self._series_id] = (
                copied
            )
            return
        setattr(
            self._popup,
            self._scoped_attr("layer_design_overrides"),
            deepcopy(overrides),
        )

    def get_layer_order(self) -> List[str]:
        if self._is_series_scoped():
            by_series = getattr(self._popup, "layer_order_by_series", {}) or {}
            if self._series_id in by_series:
                return list(by_series[self._series_id] or [])
            return list(getattr(self._popup, "layer_order", None) or [])
        return list(getattr(self._popup, "layer_order", None) or [])

    def set_layer_order(self, order: List[str]) -> None:
        if self._is_series_scoped():
            self._series_map("layer_order_by_series")[self._series_id] = list(order)
            return
        self._popup.layer_order = list(order)

    def notify_apply(self) -> None:
        if hasattr(self._popup, "request_plot_refresh"):
            self._popup.request_plot_refresh()
            return
        if hasattr(self._popup, "on_apply"):
            self._popup.on_apply()

    def get_current_index(self, default: int | None = None) -> int | None:
        idx = getattr(self._popup, "current_idx", None)
        if idx is not None:
            return idx
        controller = getattr(self._popup, "controller", None)
        return getattr(controller, "current_idx", default)

    def get_locked_vowels_set(self) -> set[str]:
        if self._is_series_scoped():
            by_series = self._series_map("layer_locked_vowels_by_series")
            if self._series_id not in by_series:
                legacy_attr = self._legacy_attr("layer_locked_vowels")
                legacy_value = (
                    getattr(self._popup, legacy_attr, None) if legacy_attr else None
                )
                by_series[self._series_id] = (
                    legacy_value if isinstance(legacy_value, set) else set()
                )
            return by_series[self._series_id]

        if self._state_key:
            attr = f"layer_locked_vowels_{self._state_key}"
            if not hasattr(self._popup, attr):
                setattr(self._popup, attr, set())
            return getattr(self._popup, attr)

        idx = self.get_current_index(default=0)
        by_file = getattr(self._popup, "layer_locked_vowels_by_file", None)
        if by_file is None:
            self._popup.layer_locked_vowels_by_file = {}
            by_file = self._popup.layer_locked_vowels_by_file
        return by_file.setdefault(idx, set())

    def set_locked_vowel(self, vowel: str, checked: bool) -> None:
        locked = self.get_locked_vowels_set()
        if checked:
            locked.add(vowel)
        else:
            locked.discard(vowel)

    def sync_overrides_by_current_file(
        self, overrides: Dict[str, Dict[str, Any]]
    ) -> None:
        if self._is_series_scoped() or self._state_key:
            return
        idx = self.get_current_index(default=None)
        if idx is None:
            return
        by_file = getattr(self._popup, "layer_design_overrides_by_file", None)
        if by_file is None:
            return
        by_file[idx] = deepcopy(overrides)

    def sync_filter_state_by_current_file(self, state: Dict[str, str]) -> None:
        if self._is_series_scoped() or self._state_key:
            return
        idx = self.get_current_index(default=None)
        if idx is None:
            return
        by_file = getattr(self._popup, "vowel_filter_state_by_file", None)
        if by_file is None:
            return
        by_file[idx] = dict(state)

    def prune_to_locked_only_for_current_file(self) -> set[str]:
        locked_set = self.get_locked_vowels_set()
        if self._is_series_scoped():
            self.set_layer_overrides(
                {
                    v: dict(ov)
                    for v, ov in self.get_layer_overrides().items()
                    if v in locked_set
                }
            )
            self.set_filter_state(
                {v: st for v, st in self.get_filter_state().items() if v in locked_set}
            )
            return locked_set

        if self._state_key:
            ov_attr = self._scoped_attr("layer_design_overrides")
            st_attr = self._scoped_attr("vowel_filter_state")
            current_ov = getattr(self._popup, ov_attr, {}) or {}
            current_st = getattr(self._popup, st_attr, {}) or {}
            setattr(
                self._popup,
                ov_attr,
                {v: dict(ov) for v, ov in current_ov.items() if v in locked_set},
            )
            setattr(
                self._popup,
                st_attr,
                {v: st for v, st in current_st.items() if v in locked_set},
            )
            return locked_set

        idx = self.get_current_index(default=None)
        if idx is None:
            return locked_set

        self._popup.layer_design_overrides = {
            v: dict(ov)
            for v, ov in (
                getattr(self._popup, "layer_design_overrides", {}) or {}
            ).items()
            if v in locked_set
        }
        by_file_ov = getattr(self._popup, "layer_design_overrides_by_file", None)
        if by_file_ov is not None:
            by_file_ov[idx] = {
                v: dict(ov)
                for v, ov in (by_file_ov.get(idx) or {}).items()
                if v in locked_set
            }
        self._popup.vowel_filter_state = {
            v: st
            for v, st in (getattr(self._popup, "vowel_filter_state", {}) or {}).items()
            if v in locked_set
        }
        by_file_st = getattr(self._popup, "vowel_filter_state_by_file", None)
        if by_file_st is not None:
            by_file_st[idx] = {
                v: st
                for v, st in (by_file_st.get(idx) or {}).items()
                if v in locked_set
            }
        return locked_set
