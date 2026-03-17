# Compare Draw Migration Checklist

다중 플롯(`ComparePlotPopup`)에 draw를 이식하기 전/중/후 작업 순서.

핵심 원칙:
- `popup_plot`의 검증된 로직을 최대한 재사용한다.
- 새 코드는 "연결/어댑터"만 추가하고, 렌더/모델/설정 로직은 공통 함수로 묶는다.
- 레이어 이름만 compare 규칙으로 치환한다.

---

## 0) Naming 규칙 확정 (사전 결정)

### 목표
- popup naming 로직은 유지하되, **파일 구분 접미사**만 추가한다.
- 예: 첫 번째 파일(범례 기준)은 `1`, 두 번째는 `2`.

### 규칙
- line/polygon에서 `point_labels`를 표시할 때, 라벨 토큰에 접미사 부여:
  - `a` -> `a1` (blue), `a2` (red)
  - `o-e-a` -> `o1-e1-a1` 또는 `o2-e2-a2`
- 객체 타입 prefix는 popup과 동일 유지:
  - `선 N : ...`
  - `영역 N : ...`
  - `참조선 : F1=...` (참조선은 파일 라벨 시퀀스가 없으므로 suffix 없음)

### 구현 포인트
- 기존 `ui/layer_dock.py`의 `_draw_object_display_name()`를 직접 복붙하지 말고,
  - 공통 formatter로 분리하거나
  - compare 전용 wrapper에서 `point_labels`만 suffix 치환 후 기존 formatter 호출.

---

## 1) 데이터 모델/저장소 정합

- [x] `ComparePlotPopup`에 공통 draw 저장소 API 준비됨:
  - `_get_current_draw_objects()`
  - `_set_current_draw_objects()`
  - `_redraw_draw_layer()`(현재 no-op)
- [ ] draw object에 "소속 시리즈(blue/red)" 메타 필드 확정:
  - 후보: `obj.series = "blue" | "red"`
  - 생성 시점(draw tool complete)에서 반드시 저장.

주의:
- compare는 draw 레이어 목록을 공통으로 쓰므로, 파일 인덱스 기반 분리(`_draw_objects_by_file`)를 그대로 쓰지 않는다.

---

## 2) Draw Tool 컨텍스트 주입

- [ ] line/polygon/reference draw tool 생성부를 `popup_plot`과 동일한 구조로 이식.
- [ ] 단, snapping source는 compare 특성 반영:
  - 현재 마우스가 가리키는 포인트의 시리즈 색/데이터를 유지.
  - hover highlight color는 기존 compare label move와 동일 철학으로 유지.

권장:
- "active series" 개념 도입 (`blue` or `red`) 후, draw 시작 시 series 고정.
- point snapping 시 해당 series의 `snapping_data`만 우선 검색하고, 필요시 전체 fallback.

---

## 3) 렌더러 이식 (실제 `_redraw_draw_layer`)

- [ ] `popup_plot._redraw_draw_layer`를 베이스로 공통 렌더 함수 추출:
  - line/polygon/reference/area_label
  - arrow head (open/latex/stealth)
  - z-order 정책(선 < centroid < head < label)
- [ ] compare에서는 draw object의 `series`에 맞춰 색/hover 정책 적용.
- [ ] `clip_on=False`, 예외 안전(`try/except`) 정책은 popup과 동일하게 유지.

재사용 전략:
- 함수 예시: `render_draw_objects(ax, objects, draw_artists, opts)` 형태로 분리하고
  - popup/compare는 `opts`만 다르게 준다.

---

## 4) Layer Dock 연동 (공통 draw 탭)

- [ ] `LayerDockWidget`의 draw 탭이 compare에서도 정상 표시되는지 확인:
  - 선택/멀티선택
  - 디자인 패널 동기화
  - 세부 요약(`arrow_mode/head`) 규칙
- [ ] 표시명 formatter에 series suffix 규칙 연결 (`a1`, `a2`).
- [ ] area label(↳ 넓이) 정책은 popup과 동일 유지.

---

## 5) 배타 모드 검증 (이미 선반영, 회귀 테스트만 수행)

현재 compare에 반영된 것:
- ruler hover/checked 스타일
- draw 버튼 명칭 `그리기 (P)` + P shortcut
- 키맵/버튼 공통 배타 가드:
  - draw/ruler/label_move 중 하나 켜려면 나머지는 모두 OFF여야 함

테스트:
- [ ] R on 상태에서 T/P 시도 -> 차단
- [ ] T on 상태에서 R/P 시도 -> 차단
- [ ] P on 상태에서 R/T 시도 -> 차단

---

## 6) 이식 후 회귀 테스트 체크리스트

- [ ] line 생성/삭제/잠금/가시성/반투명
- [ ] polygon + area_label ON/OFF 기본값
- [ ] reference 수평/수직 + 텍스트 clipping
- [ ] multi-select 디자인 일괄 적용 + 요약 반영
- [ ] arrow end/all + stealth/open/latex
- [ ] z-order: line < centroid < arrow head < label
- [ ] compare naming: `a1`, `a2` 일관성

---

## 7) 코드 재타이핑 최소화 원칙 (중요)

- 금지:
  - popup의 draw 렌더/적용 로직을 compare에 대량 복붙
- 권장:
  - 공통 모듈로 추출 후 popup/compare에서 호출
  - compare는 "series 결정/표시명 suffix/hover 색"만 어댑터로 처리
- 완료 기준:
  - draw 핵심 로직의 단일 소스화(최소 1곳)
  - popup/compare 차이는 인자/옵션 객체로만 제어

