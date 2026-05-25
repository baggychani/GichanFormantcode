# Compare N-way 확장 — 백엔드 기반

## 목표

- **UI 없이** N개 compare 렌더·설정·라벨 오프셋·저장명까지 core/controller/plot_engine에서 완성
- UI는 `CompareSession` + per-series getter만 연결하면 동작

## API

| 항목 | 위치 |
|------|------|
| `CompareSession`, `CompareRenderResult`, naming helpers | `core/compare_series.py` |
| 설정 dict (`series.N`, legacy `blue`/`red`/`series_2`) | `core/compare_settings.py` |
| session→inputs, popup 반영 | `core/compare_runtime.py` |
| `draw_compare_plot`, `draw_compare_plot_normalized` | `engine/plot_engine.py` |
| `open_compare_plot_for_indices`, `_refresh_compare_plot_for_session` | `core/controller.py` |
| per-series getter (UI 변경 없음) | `ui/windows/compare_plot.py` |

## UI 연결 시 할 일

1. `SelectCompareDialog` — N개 선택 → `controller.open_compare_plot_for_indices(indices)`
2. 디자인/필터/레이어 도크 — `get_*_for_series(series_id)` + `vowel_filter_states` / `layer_design_overrides_by_series` 채우기
3. 라벨 이동 탭 — `legacy_key_from_series_id(n)` 탭 추가
4. Draw suffix — `compare_draw_suffix(series_id)` (1-based)

## legacy 호환

- `draw_multi_plot` / `draw_compare_normalized` — 6-tuple wrapper 유지
- 2-way `_plot_key_compare` 형식 `(idx0, idx1, plot_type[, norm])` + legacy suffix 동일

## 회귀 (2-way UI)

- Compare 열기·그리기·디자인·레이어·라벨 이동·저장
