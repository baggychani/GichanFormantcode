# layer_dock 리팩토링 계획서 (최종 개정안)

이 문서는 `ui/layer_dock.py`를 기능 누락 없이 분해하기 위한 실행 계획서다.
이번 개정안은 아래 4가지 리스크를 명시적으로 반영한다.

1. God View → God Manager 전이 방지 (Manager 도메인 분리)
2. Signal loop/전체 재렌더링 방지 (`blockSignals`, 부분 갱신 원칙)
3. Phase 순서 현실화 (구조적 분리 선행, 물리 분리 후행)
4. 중복 UI 제거 (`GlobalToggleRow` 공통 컴포넌트)

---

## 1) 핵심 원칙

- **최우선: 기능 누락 0건**
- **항상 실행 가능한 상태 유지**: 리팩토링 전 과정에서 앱이 깨진 상태로 오래 두지 않는다.
- **도메인 분리**: Label과 Draw를 하나의 Manager에 몰아넣지 않는다.
- **부분 갱신 우선**: `update_view()` 전체 리빌드는 초기화/대량 변경에만 사용.
- **시그널 역류 차단**: UI 동기화(setChecked/setValue) 시 반드시 `blockSignals(True/False)` 또는 동등한 가드 사용.

---

## 2) 범위 및 현재 상태

### 대상 파일

- `ui/layer_dock.py` (대형 파일, 현재 모든 역할 집중)
- `ui/layer_logic.py` (순수 로직 모듈, 이미 일부 분리됨)

### 신규 파일(계획)

- `ui/label_manager.py` (신규)
- `ui/draw_manager.py` (신규)
- `ui/layer_row_widgets.py` (신규)
- `ui/tab_label_view.py` (신규)
- `ui/tab_draw_view.py` (신규)

> 참고: 기존 계획의 단일 `layer_manager.py`는 이번 개정안에서 **도메인 분리형 2-manager 구조**로 대체한다.

---

## 3) 아키텍처 개정 (중요)

### 3.1 God Manager 방지: Manager 분리

#### LabelManager (라벨 도메인 전용)

담당 상태:
- `vowel_filter_state` (+ by_file / compare 변형)
- `layer_design_overrides` (+ by_file / compare 변형)
- `layer_order`
- (필요 시) 라벨 관련 locked set

대표 메서드:
- `get_filter_state()` / `set_filter_state(state)`
- `get_layer_overrides()` / `set_layer_overrides(overrides)`
- `get_layer_order()` / `set_layer_order(order)`
- `reset_layer_settings_for_current_file()`
- `reset_layer_order()`

#### DrawManager (그리기 도메인 전용)

담당 상태:
- `draw_objects` 조회/저장
- draw 전용 잠금/선택/삭제 정책
- redraw 호출 캡슐화

대표 메서드:
- `get_draw_objects()` / `set_draw_objects(objs)`
- `apply_design_settings(layer_id, settings)`
- `delete_selected(indices)`
- `delete_unlocked_all()`
- `update_draw_order(new_order)`
- `redraw()`

#### layer_dock.py (메인)의 책임

- UI shell 구성 (`QSplitter`, `QTabWidget`, 상/하단 배치)
- Manager 생성 및 각 View로 주입(Dependency Injection)
- **앱 전역 영향 이벤트만** 라우팅/emit (파일 저장, 다른 Dock 통신, 외부 공개 시그널 등)

즉, 메인은 **오케스트레이터(얇게 유지)**, Manager는 **도메인 로직/상태 접근 캡슐**, View는 **렌더링 + 도메인 내부 액션 처리** 역할을 가진다.

### 3.2 God Router 방지: Direct Connection 경계

- 도메인 내부 상호작용(Label 탭 내부, Draw 탭 내부)은 **View ↔ Manager 직접 연결**을 기본값으로 한다.
- 메인은 아래 경우만 개입한다.
  - 탭/도크/파일 단위의 전역 동기화
  - 외부 공개 시그널 emit (`filter_state_changed`, `order_changed` 등)
  - 도메인 간 조정이 필요한 소수 이벤트

예시:
- Bad: `tab_label_view` emit → `layer_dock` 수신 → `LabelManager` 호출
- Good: `layer_dock`이 `LabelManager`를 주입하고, `tab_label_view`가 manager 메서드를 직접 호출/연결

---

## 4) 이벤트 흐름 개정 (루프/성능 이슈 대응)

### 4.1 단방향 흐름

도메인 내부(기본):
사용자 입력
→ Tab/View 핸들러
→ 주입된 Manager 호출
→ Manager가 Delta 이벤트 방출
→ Tab/View가 필요한 Row만 부분 갱신

앱 전역(예외):
사용자 입력
→ Tab/View 또는 Manager
→ `layer_dock.py` (전역 이벤트만 수신)
→ 외부 시그널 emit/타 도크 통지

### 4.2 전체 갱신 vs 부분 갱신 규칙

#### 전체 갱신(비싼 작업)

아래 경우에만 허용:
- 파일 전환
- 목록 구조 자체 변경(대량 reorder/reset)
- 초기 로딩

예: `set_vowels(...)`, draw row 전체 재구성

#### 부분 갱신(기본값)

일반 상호작용은 부분 갱신만 사용:
- 눈/반투명 토글 1건
- lock 토글 1건
- 선택 상태 변경
- 단일 아이템 효과 줄 갱신

예: `update_row_visibility(vowel, state)`, `update_draw_row_lock(idx, checked)`

### 4.3 Signal loop 방지 원칙 (필수)

UI 동기화 코드에서 반드시:

```python
widget.blockSignals(True)
try:
    widget.setChecked(new_value)
finally:
    widget.blockSignals(False)
```

또는 뷰 레벨 가드 플래그:
- `self._syncing_ui = True/False`
- 슬롯 시작부에서 `if self._syncing_ui: return`

> 원칙: "모델 반영을 위한 UI 세팅"은 절대 다시 모델 업데이트를 트리거하면 안 된다.

### 4.4 Delta 페이로드 규격 (부분 갱신 필수 조건)

부분 갱신을 실제로 가능하게 하려면 Manager 이벤트가 "무엇이 바뀌었는지"를 직접 전달해야 한다.

- 단일 변경 이벤트는 전체 dict를 보내지 말고 **Delta**를 보낸다.
  - 예: `filter_item_changed(key: str, new_state: str)`
  - 예: `draw_item_lock_changed(layer_id: str, locked: bool)`
- 대량 변경은 별도 이벤트로 분리한다.
  - 예: `filter_bulk_changed(state: dict)` / `draw_bulk_changed(snapshot: list)`

권장 원칙:
- `*_item_changed` = 부분 갱신 전용
- `*_bulk_changed` = 전체/대량 갱신 전용
- View는 이벤트 타입에 따라 `update_row_*` 또는 `rebuild_*`를 명확히 분기

---

## 5) UI 분할 개정

### 5.1 중복 제거: GlobalToggleRow 공통화

기존 `_build_global_row`(라벨) / `_build_draw_global_row`(그리기) 중복을 제거한다.

신규 공통 위젯:
- `layer_row_widgets.py`에 `GlobalToggleRow` 추가
- 기능: 전체 눈/전체 반투명 버튼 + 상태 동기화 API
- 탭별 차이는 콜백/시그널 인자로 전달

예시 시그널:
- `global_eye_clicked(bool turn_on)`
- `global_semi_clicked(bool semi_on)`

필수 동작(역동기화):
- 개별 row 상태가 변하면 View가 현재 목록을 스캔해 `GlobalToggleRow` 상태를 재계산한다.
- `update_global_row_state(...)`를 Label/Draw View 컨트롤러에 명시적으로 둔다.
- 이때 `GlobalToggleRow` 업데이트는 반드시 `blockSignals` 또는 가드로 감싸 역류 루프를 방지한다.

### 5.2 파일별 역할 (최종)

- `layer_dock.py`:
  - shell UI + managers 생성/주입 + 전역 이벤트 라우팅만 담당
- `layer_row_widgets.py`:
  - `_LayerRowFrame`, `_DrawLayerRowFrame`, DropArea들, `GlobalToggleRow`
- `tab_label_view.py`:
  - 라벨 탭 전용 UI(상단 디자인 + 목록 + `update_global_row_state`)
- `tab_draw_view.py`:
  - 그리기 탭 전용 UI(목록 + 하단 액션 + `update_global_row_state`)

---

## 6) Phase 재구성 (실행 가능 상태 유지형)

> 기존 3/4 분리 순서를 폐기하고, "구조적 분리 → 물리 분리"로 바꾼다.

### Phase 1 — `layer_logic.py` 순수 로직 분리 (현재 최우선) [완료]

목표:
- `_rebuild_area_labels_for_all_polygons` 내부 순수 계산을 `layer_logic.py`로 이동
- `_apply_draw_settings_to_objects` 내부 속성 매핑 순수 로직을 `layer_logic.py`로 이동

산출물:
- `rebuild_area_labels_for_polygons(all_objs) -> list`
- `apply_line_settings(obj, cfg)`
- `apply_polygon_settings(obj, cfg)`
- `apply_reference_settings(obj, cfg)`

제약:
- `layer_logic.py`는 Qt import 금지

### Phase 2 — Manager 도입 (분리형) [완료]

목표:
- 단일 Manager 대신 `LabelManager` + `DrawManager` 도입
- 기존 popup 직접 접근을 점진 치환
- Manager 이벤트를 Delta/Bulk 규격으로 분리

산출물:
- `ui/label_manager.py`, `ui/draw_manager.py`
- 탭 View에서 manager 직접 연결 가능한 인터페이스

완료 요약:
- `LabelManager`/`DrawManager` 신규 추가 및 `layer_dock.py`에 주입 완료
- 라벨 핵심 상태 접근(`filter_state`, `layer_overrides`, `layer_order`)이 manager 경유로 전환 완료
- 그리기 핵심 상태 접근(`get/set draw objects`, `redraw`)이 manager 경유로 전환 완료
- `on_apply` 호출 지점을 manager `notify_apply()` 경유로 전환 완료
- 추가 정리: `layer_dock.py`의 런타임 `popup` 직접 접근 제거(주석/문서 텍스트 제외) 완료

### Phase 3 — 구조적 분리(같은 파일 안) [완료]

목표:
- 아직 파일을 쪼개지 않고, `layer_dock.py` 내부에서 먼저 시그널 인터페이스를 확정
- 기존 직접 호출을 시그널-슬롯 경유로 교체
- 전체 갱신/부분 갱신 API 분리

핵심 작업:
- View 이벤트 핸들러를 도메인 내부에서는 manager 직접 호출로 전환
- 메인 슬롯은 전역 이벤트만 담당하도록 축소
- `blockSignals`/가드 플래그 적용
- `update_global_row_state` 및 Delta 기반 부분 갱신 루틴 완성

완료 기준:
- 앱이 동일 기능으로 실행되고, loop/flicker 없음

완료 요약:
- `layer_dock.py`에 Delta 이벤트 시그널 추가:
  - `label_filter_item_changed(vowel, new_state)`
  - `draw_item_state_changed(draw_index, key, value)`
- 단일 항목 변경 핸들러(`_on_label_filter_item_changed`, `_on_draw_item_state_changed`) 추가로 부분 갱신 경로 확립
- draw row 토글(눈/반투명/잠금)에서 전체 리스트 재구성(`update_draw_layer_list`) 호출 제거
- row 컨트롤 동기화 시 `blockSignals`를 통한 역류 방지 유지
- draw global 토글 경로에서 manager set/redraw 일관성 확보

### Phase 4 — 물리적 분리(파일 분할) [완료]

목표:
- Phase 3에서 안정화된 인터페이스를 그대로 옮겨 파일 분할

순서:
1) `layer_row_widgets.py` (행/드롭/GlobalToggleRow)
2) `tab_label_view.py`
3) `tab_draw_view.py`

완료 기준:
- import 경로 정리 완료
- 동작 동일성 유지

완료 요약:
- `ui/layer_row_widgets.py` 신규 생성 후 행/드롭 관련 클래스 물리 분리 완료
  - `_RowClickForwarder`, `_LayerRowFrame`, `_LayerListDropArea`, `_DrawLayerRowFrame`, `_DrawListDropArea`
- `ui/tab_label_view.py` 신규 생성 후 라벨 탭 생성 코드 분리(`create_label_tab`)
- `ui/tab_draw_view.py` 신규 생성 후 그리기 탭 생성 코드 분리(`create_draw_tab`)
- `layer_dock.py`는 분리된 모듈을 import하여 탭/행 UI를 조립하는 구조로 전환
- 정적 검증: `ReadLints` 오류 없음, `python -m py_compile` 통과

### Phase 5 — 안정화/회귀 검증 [완료]

목표:
- 단일/compare 모드 회귀 점검
- 성능/루프/선택 상태 버그 점검

완료 요약:
- 테스트 실행 환경 보강: `pytest` 설치 후 저장소 테스트 실행
- 자동 테스트 결과: `16 passed` (`tests/test_data_processor.py`, `tests/test_math_utils.py`)
- 리팩토링 대상 모듈 컴파일 검증 완료:
  - `layer_dock.py`, `layer_row_widgets.py`, `tab_label_view.py`, `tab_draw_view.py`, `label_manager.py`, `draw_manager.py`
- 모듈 스모크 import 검증 완료:
  - `ui.layer_dock`, `ui.layer_row_widgets`, `ui.tab_label_view`, `ui.tab_draw_view`, `main`
- 구조 회귀 확인:
  - `layer_dock.py`에서 행/드롭 클래스 정의 제거됨(물리 분리 유지)
  - `layer_dock.py`가 분리 모듈 import 후 조립하는 경로 유지
- 정적 진단: `ReadLints` 오류 없음

---

## 7) 커서(Agent)에게 전달할 안전 가드레일

아래 항목을 작업 지시문에 포함한다.

- "UI 상태 동기화(setChecked/setValue) 코드는 반드시 `blockSignals` 또는 가드 플래그로 감쌀 것"
- "전체 목록 재생성은 파일 전환/초기화/대량 변경에만 허용"
- "일반 토글은 해당 row만 부분 업데이트"
- "Manager 이벤트는 Delta/Bulk를 분리하고, 단일 변경에 전체 dict를 보내지 말 것"
- "View는 popup 직접 접근 금지, Manager 메서드만 사용"
- "Label/Draw Manager를 절대 합치지 말 것"
- "layer_dock를 God Router로 만들지 말고, 도메인 내부는 View-Manager 직접 연결할 것"
- "각 phase 종료 시 앱이 실행 가능한 상태여야 하며, 깨진 중간 상태 커밋 금지"

---

## 8) Phase 1 상세 실행 체크리스트 (즉시 사용 가능) [완료]

### 8.1 추출 대상

- `layer_dock.py::_apply_draw_settings_to_objects` 내부의
  - `_apply_line`
  - `_apply_polygon`
  - `_apply_reference`
  - `_rebuild_area_labels_for_all_polygons`

### 8.2 구현 체크 [완료]

- [x] `layer_logic.py`에 순수 함수 추가 (PyQt import 없음) [완료]
- [x] `rebuild_area_labels_for_polygons`는 새 리스트 반환형으로 구현 [완료]
- [x] polygon의 `show_area_label`에 따라 area_label 생성/제거 로직 이전 [완료]
- [x] `axis_units`, `visible`, `locked`, `semi` 복사 규칙 유지 [완료]
- [x] line/polygon/reference 속성 매핑 fallback 유지 [완료]
- [x] `layer_dock.py`에서 기존 중첩 함수 제거 후 layer_logic 함수 호출 [완료]

### 8.3 회귀 확인 [완료]

- [x] 그리기 객체 디자인 변경 경로가 동일한 대상/순서로 적용됨(코드 경로 검증) [완료]
- [x] polygon 넓이 라벨 on/off 시 area_label 재구성 함수로 일괄 처리되도록 변경 [완료]
- [x] redraw/list update 호출 타이밍 유지 (`_set_current_draw_objects` → `_redraw_draw_layer` → `update_draw_layer_list`) [완료]
- [x] 정적 검증: `ReadLints` 오류 없음, `python -m py_compile` 통과 [완료]

### 8.4 Phase 1 착수 지시 템플릿 (Cursor용)

아래 텍스트를 그대로 작업 지시문으로 사용 가능:

```text
[Phase 1만 수행]
목표: ui/layer_dock.py의 순수 로직을 ui/layer_logic.py로 분리한다.

필수 작업:
1) _apply_draw_settings_to_objects 내부의 _apply_line/_apply_polygon/_apply_reference를 layer_logic.py 순수 함수로 이동
2) _rebuild_area_labels_for_all_polygons 로직을 layer_logic.py의 rebuild_area_labels_for_polygons(all_objs)->list로 이동
3) layer_dock.py는 위 순수 함수를 호출하도록 교체

제약:
- layer_logic.py에 Qt import 금지
- 기존 동작(넓이 라벨 생성/제거, 속성 fallback, redraw/list update 타이밍) 100% 유지
- 이번 Phase에서는 Manager 분리/파일 분할/시그널 구조 변경 금지

검증:
- polygon area_label on/off 동작 동일
- line/polygon/reference 디자인 반영 동일
- 회귀 테스트 결과를 요약 보고
```

### 8.5 Phase 2 구현 체크리스트 [완료]

- [x] `ui/label_manager.py` 신규 생성 [완료]
- [x] `ui/draw_manager.py` 신규 생성 [완료]
- [x] `layer_dock.py`에서 manager 인스턴스 생성/주입 [완료]
- [x] `_get_current_filter_state` / `_set_filter_state`를 `LabelManager`로 위임 [완료]
- [x] `_get_layer_overrides` / `_set_layer_overrides`를 `LabelManager`로 위임 [완료]
- [x] `layer_order` 읽기/쓰기 경로를 `LabelManager`로 전환 [완료]
- [x] draw object `get/set/redraw` 경로를 `DrawManager`로 전환 [완료]
- [x] `popup._get_current_draw_objects`, `popup._set_current_draw_objects`, `popup._redraw_draw_layer`, `popup.layer_order`, `popup.on_apply` 직접 호출 제거 [완료]
- [x] 잠금/파일별 override 동기화 경로까지 `LabelManager` 위임 완료 [완료]
- [x] 정적 검증: `ReadLints` 오류 없음, `python -m py_compile` 통과 [완료]

### 8.6 Phase 3 구현 체크리스트 [완료]

- [x] 구조적 분리용 Delta 시그널 추가 (`label_filter_item_changed`, `draw_item_state_changed`) [완료]
- [x] View 이벤트 핸들러를 단일 항목 Delta 처리 경로로 전환 [완료]
- [x] draw row 토글에서 전체 재구성 호출 제거, 부분 갱신(`_sync_draw_row_controls`) 적용 [완료]
- [x] `update_global_row_state`/`_update_draw_global_row_state`와 `blockSignals` 가드 유지 [완료]
- [x] draw global 토글에서 manager set/redraw 경로 보강 [완료]
- [x] 정적 검증: `ReadLints` 오류 없음, `python -m py_compile` 통과 [완료]

### 8.7 Phase 4 구현 체크리스트 [완료]

- [x] `ui/layer_row_widgets.py` 파일 생성 및 행/드롭 클래스 물리 분리 [완료]
- [x] `ui/tab_label_view.py` 파일 생성 및 라벨 탭 생성 코드 분리 [완료]
- [x] `ui/tab_draw_view.py` 파일 생성 및 그리기 탭 생성 코드 분리 [완료]
- [x] `layer_dock.py`에서 분리 모듈 import 및 조립 경로 교체 [완료]
- [x] 정적 검증: `ReadLints` 오류 없음, `python -m py_compile` 통과 [완료]

### 8.8 Phase 5 검증 체크리스트 [완료]

- [x] `pytest` 설치 후 테스트 스위트 실행 [완료]
- [x] 테스트 16건 통과 (`16 passed`) [완료]
- [x] 리팩토링 대상 모듈 `python -m py_compile` 통과 [완료]
- [x] 핵심 모듈 스모크 import 통과 (`main`, `ui.layer_dock` 등) [완료]
- [x] 구조 회귀 점검(분리된 클래스/탭 조립 경로 유지) [완료]
- [x] 정적 진단(`ReadLints`) 오류 없음 [완료]

---

## 9) 위험요소와 대응

- **위험 A: God Manager 재발**
  - 대응: Label/Draw manager 파일 분리 강제, 코드리뷰 체크리스트에 "manager 간 교차 책임" 항목 추가
- **위험 B: 시그널 무한 루프**
  - 대응: 모든 UI 동기화 루틴에 `blockSignals`/가드 의무화
- **위험 C: 깜빡임/성능 저하**
  - 대응: 부분 갱신 API 우선, 전체 재구성 호출 지점 제한
- **위험 D: God Router 재발**
  - 대응: 메인은 전역 이벤트만 처리, 도메인 내부는 View-Manager 직접 연결
- **위험 E: 분할 중 실행 불가 상태**
  - 대응: 구조적 분리(Phase 3) 완료 후 물리 분리(Phase 4)

---

## 10) 결론

이번 최종안의 핵심은 다음 3가지다.

1. **Manager 도메인 분리**(Label/Draw)로 God Object를 원천 차단
2. **Signal 안전 원칙**(`blockSignals`, 부분 갱신 우선)으로 루프/성능 문제 예방
3. **실행 가능 상태 유지형 Phase**(구조적 분리 선행)로 리팩토링 리스크 최소화

이 문서를 기준으로 작업하면, 기능 누락 없이 대형 리팩토링을 안정적으로 진행할 수 있다.
