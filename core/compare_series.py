"""Compare 다중 시리즈 기반 타입·alias (Phase 0.5).

시리즈는 ``series_id``(0, 1, 2, …)로 식별한다.
0·1번은 하위 호환용 legacy alias ``blue`` / ``red`` 를 유지한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterator

import config

# 0·1번 시리즈만 갖는 legacy UI/설정 키 (N>2 시 ``series_2`` … 사용)
LEGACY_SERIES_ALIASES: tuple[str, ...] = ("blue", "red")

_SERIES_COLOR_PALETTE: tuple[str, ...] = (
    config.COLOR_PRIMARY_BLUE,
    config.COLOR_PRIMARY_RED,
    "#388E3C",
    "#7B1FA2",
    "#F57C00",
    "#009688",
)
_SERIES_ELL_STYLES: tuple[str, ...] = ("-", "--", "-.", ":")


def legacy_key_from_series_id(series_id: int) -> str:
    if series_id < 0:
        raise ValueError(f"series_id must be >= 0, got {series_id!r}")
    if series_id < len(LEGACY_SERIES_ALIASES):
        return LEGACY_SERIES_ALIASES[series_id]
    return f"series_{series_id}"


def series_id_from_legacy(key: str) -> int:
    if key in LEGACY_SERIES_ALIASES:
        return LEGACY_SERIES_ALIASES.index(key)
    if key.startswith("series_"):
        suffix = key.split("_", 1)[1]
        if suffix.isdigit():
            return int(suffix)
    raise ValueError(
        f"unknown compare series key {key!r}; "
        f"expected legacy {LEGACY_SERIES_ALIASES} or series_N"
    )


def normalize_series_ref(ref: int | str) -> int:
    """``0``/``1``/…, ``\"blue\"``/``\"red\"``, ``\"series_2\"`` → series_id."""
    if isinstance(ref, int):
        if ref >= 0:
            return ref
        raise ValueError(f"series_id must be >= 0, got {ref!r}")
    if isinstance(ref, str):
        if ref.isdigit():
            return int(ref)
        return series_id_from_legacy(ref)
    raise TypeError(f"series ref must be int or str, got {type(ref).__name__}")


def default_series_color(series_id: int) -> str:
    return _SERIES_COLOR_PALETTE[
        normalize_series_ref(series_id) % len(_SERIES_COLOR_PALETTE)
    ]


def default_series_ell_style(series_id: int) -> str:
    return _SERIES_ELL_STYLES[normalize_series_ref(series_id) % len(_SERIES_ELL_STYLES)]


def iter_legacy_series() -> Iterator[tuple[int, str]]:
    for series_id, legacy_key in enumerate(LEGACY_SERIES_ALIASES):
        yield series_id, legacy_key


@dataclass(frozen=True)
class CompareSession:
    """Compare 창에 로드된 plot_data_list 인덱스 집합."""

    data_indices: tuple[int, ...]

    @classmethod
    def from_data_indices(cls, *indices: int) -> CompareSession:
        if len(indices) < 2:
            raise ValueError("compare session requires at least 2 data indices")
        return cls(tuple(indices))

    @property
    def count(self) -> int:
        return len(self.data_indices)

    def legacy_key(self, series_id: int) -> str:
        return legacy_key_from_series_id(series_id)

    def data_index(self, series_id: int) -> int:
        sid = normalize_series_ref(series_id)
        if sid >= self.count:
            raise IndexError(
                f"series_id {sid} out of range for session with {self.count} series"
            )
        return self.data_indices[sid]


@dataclass
class CompareSeriesInput:
    """PlotEngine compare 렌더 1시리즈 입력."""

    df: Any
    display_name: str
    filter_state: dict | None = None
    design_cfg: dict | None = None
    layer_overrides: dict | None = None
    custom_label_offsets: dict | None = None


@dataclass
class CompareDatasetSpec:
    """PlotEngine compare 렌더 루프용 시리즈 1개 묶음."""

    series_id: int
    legacy_key: str
    df: Any
    display_name: str
    filter_state: dict
    design_cfg: dict
    layer_overrides: dict
    custom_label_offsets: dict


def build_compare_dataset_specs(
    series_inputs: list[CompareSeriesInput],
) -> list[CompareDatasetSpec]:
    """시리즈 입력 목록 → 렌더 spec 목록 (개수 N ≥ 2)."""
    if len(series_inputs) < 2:
        raise ValueError("compare requires at least 2 series")
    specs: list[CompareDatasetSpec] = []
    for series_id, row in enumerate(series_inputs):
        specs.append(
            CompareDatasetSpec(
                series_id=series_id,
                legacy_key=legacy_key_from_series_id(series_id),
                df=row.df,
                display_name=row.display_name,
                filter_state=row.filter_state or {},
                design_cfg=row.design_cfg or {},
                layer_overrides=row.layer_overrides or {},
                custom_label_offsets=row.custom_label_offsets or {},
            )
        )
    return specs


class CompareLabelBuckets:
    """PlotEngine compare 반환용 — series_id별 버킷 + legacy blue/red 뷰."""

    def __init__(self) -> None:
        self._label_data: dict[int, list[dict]] = {}
        self._label_text_artists: dict[int, list] = {}

    def _ensure(self, series_id: int) -> int:
        sid = normalize_series_ref(series_id)
        self._label_data.setdefault(sid, [])
        self._label_text_artists.setdefault(sid, [])
        return sid

    def append_label_data(self, series_id: int, entry: dict) -> None:
        self._label_data[self._ensure(series_id)].append(entry)

    def append_text_artist(self, series_id: int, artist) -> None:
        self._label_text_artists[self._ensure(series_id)].append(artist)

    @property
    def label_data_blue(self) -> list[dict]:
        return self._label_data.get(0, [])

    @property
    def label_data_red(self) -> list[dict]:
        return self._label_data.get(1, [])

    @property
    def label_text_artists_blue(self) -> list:
        return self._label_text_artists.get(0, [])

    @property
    def label_text_artists_red(self) -> list:
        return self._label_text_artists.get(1, [])

    def as_dicts(
        self,
    ) -> tuple[dict[int, list[dict]], dict[int, list]]:
        return dict(self._label_data), dict(self._label_text_artists)


@dataclass
class CompareRenderResult:
    """Compare PlotEngine 반환값 — N-way dict + legacy 6-tuple 변환."""

    ax: Any
    snapping_data: list
    label_data: dict[int, list[dict]]
    label_text_artists: dict[int, list]

    def legacy_tuple(
        self,
    ) -> tuple[Any, list, list[dict], list[dict], list, list]:
        buckets = CompareLabelBuckets()
        for series_id, entries in self.label_data.items():
            for entry in entries:
                buckets.append_label_data(series_id, entry)
        for series_id, artists in self.label_text_artists.items():
            for artist in artists:
                buckets.append_text_artist(series_id, artist)
        return (
            self.ax,
            self.snapping_data,
            buckets.label_data_blue,
            buckets.label_data_red,
            buckets.label_text_artists_blue,
            buckets.label_text_artists_red,
        )


def compare_plot_key(
    data_indices: tuple[int, ...],
    plot_type: str,
    norm: str | None = None,
) -> tuple:
    """라벨 오프셋·플롯 상태 저장용 compare 키 prefix."""
    base = tuple(data_indices)
    if norm:
        return (*base, plot_type, norm)
    return (*base, plot_type)


def compare_label_offset_key(
    plot_key: tuple,
    series_ref: int | str,
) -> tuple:
    legacy = legacy_key_from_series_id(normalize_series_ref(series_ref))
    return (*plot_key, legacy)


def compare_window_title(
    names: list[str],
    *,
    outlier_suffix: str = "",
    norm: str | None = None,
) -> str:
    if not names:
        return "데이터 없음" + outlier_suffix
    if len(names) == 1:
        title = names[0] + outlier_suffix
    elif len(names) == 2:
        title = f"{names[0]}, {names[1]}{outlier_suffix}"
    else:
        title = f"{names[0]} 외 {len(names) - 1}개{outlier_suffix}"
    if norm:
        title += f" / {norm}"
    return title


def compare_default_save_basename(
    names: list[str],
    *,
    outlier_suffix: str = "",
    norm: str | None = None,
    norm_tag: str | None = None,
) -> str:
    stems = [os.path.splitext(name)[0] for name in names if name]
    if not stems:
        base = "compare"
    else:
        base = "_".join(stems)
    base += outlier_suffix
    if norm:
        tag = (
            norm_tag if norm_tag is not None else norm.replace("/", "").replace(" ", "")
        )
        base += f"_{tag}"
    return base


def compare_draw_suffix(series_id: int) -> str:
    """Draw 도구 point label suffix (1-based)."""
    return str(normalize_series_ref(series_id) + 1)
