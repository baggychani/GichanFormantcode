# 레이어 로직 분리 계획 (1차)

## 1. 합리성 평가

### 1.1 현재 구조

- **ui/layer_dock.py** (~2,235줄): 레이어 도크 전체
  - **라벨 탭**: `_layer_rows` (vowel → row), `_global_row` (전체 눈/반투명), filter_state (ON/OFF/SEMI), layer_order, layer_design_overrides, layer_locked_vowels_by_file
  - **그리기 탭**: `_draw_layer_rows`, 그리기 객체 리스트(visible, semi, locked, parent_id → area_label 자식), 드래그/삭제/순서
  - **공통**: 눈(가시성), 반투명, 잠금, 순서 변경(드래그), 전체 한 줄(전체 눈/전체 반투명), 선택 상태
  - **차이**: 라벨은 vowel 단위 + 디자인 오버라이드; 그리기는 객체 단위 + type(polygon/line/area_label 등) + 부모/자식

### 1.2 분리했을 때 이점

- **한 곳에서 규칙 관리**: "전체 눈 클릭 시 모두 끄기/켜기", "드래그 후 새 순서 계산", "부모 잠금 시 자식 동기화" 등을 한 모듈에서 정의하면 레이어 도크는 UI만 담당.
- **테스트 용이**: Qt 없이 상태·순서·락 동작만 단위 테스트 가능.
- **재사용**: compare_plot 등에서 같은 규칙을 import 해서 쓰기 쉬움.
- **가독성**: layer_dock.py가 2천 줄대에서 줄어들고, "어디서 순서/잠금이 바뀌는지"를 layer_logic에서 추적 가능.

### 1.3 리스크·난이도

- **팝업/상태 소유권**: 지금 상태는 전부 `popup.vowel_filter_state`, `popup.layer_order` 등에 있어서, "로직"만 빼면 여전히 읽기/쓰기는 popup을 통해 이뤄짐. 완전히 독립한 LayerState 객체로 옮기면 대규모 리팩터가 됨.
- **점진적 분리**: "상태는 그대로 두고, **순수 함수**만 뽑는 방식"이면 리스크가 적음. 예: `compute_order_after_drop(ordered, dragged_list, drop_index, after)`, `apply_global_eye(state, keys, turn_on)` 등.
- **난이도**: 중상. 기존 동작을 유지하면서 조금씩 함수/상수만 새 py로 옮기고, layer_dock에서는 그 함수들을 호출하도록 바꾸는 식으로 진행 가능.

### 1.4 결론

- **별도 py로 공통 로직을 정리하는 것은 합리적**이다.
- 다만 **한 번에 전부 옮기기보다**, "상태는 popup에 두고, **규칙·계산·상수**만 새 모듈로 옮기는" 단계적 접근이 현실적이다.
- 새 모듈은 **Qt에 의존하지 않는** 순수 로직만 두고, layer_dock은 그걸 import 해서 사용한다.

---

## 2. 제안 모듈 구조

### 2.1 파일 위치

- **ui/layer_logic.py** (또는 **core/layer_logic.py**)
  - UI와 가깝게 쓰려면 `ui/layer_logic.py`, "도메인 규칙"에 가깝게 두려면 `core/layer_logic.py`.  
  - 레이어 도크가 ui에 있으므로 **ui/layer_logic.py** 로 두고, 필요 시 core에서 import 해도 됨.

### 2.2 담을 내용 (공통·순수 로직만)

| 항목 | 설명 | 비고 |
|------|------|------|
| **상수** | MIME 타입 문자열, 컬럼 너비 등 레이어 공통 상수 | layer_dock에서 재정의된 것 정리 |
| **필터 상태** | `apply_global_eye(state_dict, keys, turn_on)` → 새 dict 반환 | state_dict는 vowel→"ON"\|"OFF"\|"SEMI" |
| | `apply_global_semi(state_dict, keys, semi)` | |
| | `toggle_item_visibility(state_dict, key, eye_checked, semi_checked)` | 한 항목 눈/반투명 토글 결과 |
| **순서** | `compute_order_after_drop(ordered_list, dragged_indices, drop_index, after)` | 라벨(vowel 리스트)·그리기(인덱스) 공통 |
| **잠금** | `sync_parent_lock_to_children(items, parent_id_attr, locked_attr, parent_index, checked)` | 그리기용: 부모 잠금 시 자식 locked 플래그 동기화 |
| | 라벨용 locked_set add/discard 는 단순해서 유지 가능 | 필요 시 `toggle_lock(locked_set, key, checked)` |
| **드롭 타깃** | `get_drop_target_index(ordered_rows, pos_y, row_height)` → (index, after) | 로직만; 실제 좌표는 도크가 넘김 |

- **의존성**: Qt 없음, `list`, `dict`, `set` 수준만 사용.  
- **상태 소유**: 계속 popup이 갖고, layer_logic는 "입력 상태 + 인자 → 출력 상태"만 계산.

### 2.3 layer_dock.py가 하는 일 (분리 후)

- 위젯 생성·레이아웃·시그널 연결.
- `_get_current_filter_state()` / `_set_filter_state()` 등으로 popup에서 상태 읽기/쓰기.
- **변경 시**: `new_state = layer_logic.apply_global_eye(self._get_current_filter_state(), vowels, False)` 호출 후 `_set_filter_state(new_state)`.
- 드래그 드롭 시: `new_order = layer_logic.compute_order_after_drop(...)` 호출 후 popup.layer_order / draw_objects 순서 갱신.

---

## 3. 구현 순서 제안

1. **ui/layer_logic.py 생성**  
   - 상수(MIME 타입 등), 타입 힌트용 타입 알리아스만 넣고, layer_dock에서 해당 상수 import 하도록 변경.
2. **필터 상태 헬퍼**  
   - `apply_global_eye`, `apply_global_semi`, `toggle_item_visibility` 구현 후, _build_global_row / _build_layer_row 쪽에서 호출하도록 교체.
3. **순서 계산**  
   - `compute_order_after_drop` 구현 후, _on_layer_reorder / _on_draw_reorder 에서 사용.
4. **잠금 동기화**  
   - `sync_parent_lock_to_children` (그리기용) 구현 후, on_lock_toggled에서 호출.  
   - 이때 **#2 이슈(자식 UI가 부모 잠금을 따라가도록)** 도 함께 수정: 부모 잠금 토글 시 자식 행의 lock_btn.setChecked(...) 를 호출해 주는 부분을 도크에 추가.
5. **(선택)** 드롭 타깃 계산을 layer_logic로 옮겨 _get_drop_target_at_pos 등에서 사용.

---

## 4. 2·3·4번 요약 (추후 작업)

- **#2 자식 레이어가 부모 자물쇠를 UI에서 따라가기**  
  - 부모(polygon) lock_btn 토글 시, `_sync_area_labels_to_parent(objs, idx, "locked", checked)` 로 자식 객체만 바꾸고 있음.  
  - **추가 필요**: 같은 부모의 자식에 해당하는 **그리기 레이어 행**을 찾아서, 각 행의 `lock_btn.setChecked(checked)` 호출.  
  - layer_logic에 `get_children_indices(draw_objects, parent_index)` 같은 걸 두고, 도크에서 "부모 잠금 시 자식 행 UI 갱신"에 사용 가능.
- **#3 그리기 레이어 디자인 영역(상단)**  
  - 별도 py, 기존 라벨 디자인과 UI 구조 동일. 선/영역/참조선 중 선택에 따라 내용이 완전히 다르게 구성된다는 점만 유지.
- **#4 넓이 텍스트 이동 조건**  
  - "그리기 모드가 꺼져 있을 때 넓이 텍스트에 가까이 가져가면 이동 가능" → **해당 그리기 레이어(넓이 텍스트)에 포커스가 있을 때만** 이동 가능하도록 제한.  
  - 라벨 이동처럼 **우클릭 시 디폴트 위치(무게중심)** 로 복귀 기능 추가.

---

*문서 버전: 1차. 구현 시 이 순서대로 진행하고, 필요 시 계획 수정.*
