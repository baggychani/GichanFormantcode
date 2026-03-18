# GichanFormant 코드 리팩토링 검토 보고서

요청해주신 7가지 상세한 기준에 따라 현재 GichanFormant 전체 코드베이스의 상태를 분석하고, 향후 프로젝트의 유지보수성과 확장성을 비약적으로 높일 수 있는 리팩토링(Refactoring) 계획을 정리했습니다. 

## 1. 전반적인 진단 요약

현재 코드는 **"작동은 매우 훌륭하게 되지만, 점진적으로 새로운 기능들(레이어, 그리기 등)이 덧붙여지면서 일부 핵심 파일들이 과성장(God Object)한 상태"**입니다. 전체적으로 MVC 폴더 구조는 잘 기획되어 있으나 파일 내부적으로는 책임(Responsibility)의 분리가 다소 모호해져 리팩토링이 필요한 시점입니다.

---

## 2. 세부 검토 기준별 분석

### [1] 지나치게 비대한 파일 (God Objects) 및 함수
가장 시급하게 해결해야 할 부분입니다. 특정 파일이 너무 많은 역할을 맡고 있어 유지보수가 어렵습니다.
* **[ui/popup_plot.py](file:///c:/Users/c/Desktop/GichanFormant/ui/popup_plot.py) (2600줄 / 111KB), [ui/compare_plot.py](file:///c:/Users/c/Desktop/GichanFormant/ui/compare_plot.py) (2000줄 / 83KB):**  
  * **문제점:** 단순한 창(Window) 껍데기만 띄우는 게 아니라, 단축키 처리, 필터 패널 호출 유효성 검사, 드로잉 도구 바인딩, 저장 로직 일부 등 수백 가지 일을 혼자서 다 하고 있습니다.
  * **대책:** UI 요소의 배치(View)와 사용자 이벤트의 처리(Event Handler/Controller), 그리고 단축키 매핑(Shortcut Manager) 모듈을 분리해야 합니다.
* **[ui/layer_dock.py](file:///c:/Users/c/Desktop/GichanFormant/ui/layer_dock.py) (2200줄 / 96KB):**
  * **문제점:** 레이어 UI 목록을 생성하는 일과, 디자인 데이터(색상, 두께 등)를 임시 보관하는 일, 드래그 앤 드롭 인디케이터 그리기 들이 마구 섞여있습니다.
* **[core/controller.py](file:///c:/Users/c/Desktop/GichanFormant/core/controller.py) (1700줄 / 75KB):**
  * **문제점:** 원래 설계 목적은 앱의 핵심 제어기였겠으나, 현재는 PyQt의 `QFileDialog`를 직접 호출하거나, 백그라운드 Worker 스레드 클래스까지 품고 있어 View 코드에 너무 강하게 결합되어 있습니다.

### [2] M-V-C 구조의 준수 여부
* **현황:** 폴더 자체는 `model/`, `core/` (Controller 성격), [ui/](file:///c:/Users/c/Desktop/GichanFormant/ui/widgets/layer_dock.py#255-562) (View) 로 나뉘어 있어 **어느 정도 기본 골격은 훌륭합니다**.
* **문제점 (MVC 위반):** Controller 파일([controller.py](file:///c:/Users/c/Desktop/GichanFormant/core/controller.py)) 안에 UI 메시지 박스(`QMessageBox`)나 다이얼로그(`QFileDialog`, `QProgressDialog`) 코드가 직접 들어있습니다. Controller는 철저히 데이터만 처리하고, UI 표시는 View 쪽 프로토콜(Signal 등)로 넘겨야 진정한 MVC 패턴이라 할 수 있습니다.

### [3] 불필요한 하드코딩
* **문제점:** [layer_dock.py](file:///c:/Users/c/Desktop/GichanFormant/ui/layer_dock.py)나 [popup_plot.py](file:///c:/Users/c/Desktop/GichanFormant/ui/popup_plot.py) 등 곳곳에 `"#E64A19"`, `"#1976D2"` 같은 색상값과 폰트 크기 매직 넘버(Magic Numbers)가 흩어져 있습니다. 
* **대책:** [config.py](file:///c:/Users/c/Desktop/GichanFormant/config.py)나 별도의 `theme.py`에 이 값들을 모아서 중앙 통제식으로 관리해야, 나중에 다크 모드(Dark Mode)를 추가하거나 UI 테마를 바꿀 때 전체 코드를 뒤지는 참사를 막을 수 있습니다.

### [4] 폴더 및 파일 연관성 
* **현황:** 전반적으로 매우 훌륭합니다. [draw/](file:///c:/Users/c/Desktop/GichanFormant/draw/draw_polygon.py#235-262) 안에 그리기 관련 로직을, `engine/`에 matplotlib 관련 로직을 분리한 것은 좋은 설계적 판단입니다.
* **개선점:** [ui/](file:///c:/Users/c/Desktop/GichanFormant/ui/widgets/layer_dock.py#255-562) 폴더 내 파일이 21개로 너무 많습니다. `ui/layer/` (레이어 관련 위젯), `ui/dialogs/` (메시지나 설정 창), `ui/windows/` (메인 및 팝업 창)와 같이 하위 폴더로 묶으면 훨씬 깔끔할 것입니다.

### [5] 변수명 및 Naming Convention
* **현황:** `vowel_filter_state_blue` 등 직관적으로 데이터의 역할을 알 수 있는 아주 좋은 네이밍 컨벤션을 갖고 있습니다.
* **주의점:** 간혹 `btn_1`, `idx`, 라벨 등에서 `d_red`, `col_label` 등 약어를 섞어 쓰는 경우가 있습니다 (`df` 등). 가급적 `blue_dataset`, `label_column`처럼 의미를 분명히 풀어쓰는 것이 좋습니다. 또, "숨기다"라는 의미로 `close()`, `hide()`, `remove()`가 혼용되는 부분이 있어, 라이프사이클 함수명을 통일할 필요가 있습니다.

### [6] 스파게티 코드 (유지보수성)
* **문제점 파악:** "이벤트 핸들러 콜백 지옥". A를 클릭하면 B 함수를 부르고, B 안에서 C 모듈의 D 함수를 찔러 넣는 흐름이 일부 보입니다. 특히 `_on_apply()` 나 `_on_draw_object_complete` 과정에서 다른 창의 위젯 속성을 강제로 뜯어 고치는(coupling) 부분들이 약간의 스파게티 성향을 띠고 있습니다. (예: `setattr(obj, "series", self._active_draw_series)` 로 직접 객체를 조작).
* **대책:** 이벤트 기반 통신(`pyqtSignal`)을 적극 활용해서, 창 A가 객체 B를 직접 조작하지 않고 "*여기 클릭됐음*" 이라는 신호만 던지고 객체 B가 스스로 처리하도록(캡슐화) 제어 흐름을 단순화시켜야 합니다.

---

## 3. 리팩토링 제안 (Step-by-Step)

만약 제가 리팩토링을 하나씩 진행한다면 다음 순서로 하는 것을 제안합니다:

**Phase 1: 하드코딩 및 리소스 정리 (저위험군)**
1. `ui/` 내의 색상, 폰트 사이즈 등 하드코딩된 값들을 `config.py` (또는 UI Config 파일)로 일괄 추출.
2. `ui/` 내부의 서브 폴더를 생성해 역할별로 폴더 분리 (`dialogs`, `plot_windows` 등).

**Phase 2: MVC 경계 복원 및 신호 분리 (중위험군)**
3. `core/controller.py` 내의 GUI 코드(`QMessageBox`, `QFileDialog`)를 걷어내어 순수 파이썬 로직만 남깁니다. 에러가 나면 예외(Exception)를 반환하고 메시지는 `ui/main_window.py` 등 View가 띄우도록 수정합니다.
4. `core/workers.py`로 `BatchSaveWorker` 등을 별도로 빼내어 Controller의 무게를 줄입니다.

**Phase 3: 거대 클래스(God Object) 쪼개기 (고위험군 / 심화 모델)**
5. `popup_plot.py` 와 `compare_plot.py`의 공통된 로직(단축키 매핑, 그리기 도구 설정, 툴바 관리)을 묶어서 부모 클래스인 `BasePlotWindow`로 분리하여 상속받게 합니다. 중복 코드가 절반 이하로 줄어듭니다.
6. `layer_dock.py`를 `layer_data_model.py` (레이어 순서 및 상태 관리)와 `layer_ui_view.py` (화면에 리스트를 그려주는 로직) 로 철저히 쪼갭니다. MVC의 파편화가 해결됩니다.

---

## 4. Phase 3 세부 실행 계획 (Step-by-Step)

> **선행 조건:** Phase 1 ✅, Phase 2 ✅ 완료됨. Phase 3는 실행 전 반드시 `git commit`으로 체크포인트를 만들 것.

---

### Phase 3-A: `BasePlotWindow` 부모 클래스 추출 ✅ 완료

**목표:** `popup_plot.py`와 `compare_plot.py`에서 중복된 로직을 새 파일 `ui/windows/base_plot_window.py`로 분리한다.

#### 추출할 공통 메서드 목록

아래 메서드들은 두 파일 모두에 거의 동일하게 존재하므로 `BasePlotWindow`가 단독으로 소유해야 한다.

| 메서드명 | 현재 위치 | 이관 여부 |
|---|---|---|
| `_apply_pyqt6_icon()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_is_ruler_active()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_is_input_focused()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_is_draw_active()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_redraw_draw_layer()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_get_current_draw_objects()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_set_current_draw_objects()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_on_draw_object_complete()` | 양쪽 거의 동일 | ⚠️ 공통 부분만 super()로, 차이점은 override |
| `_safe_toggle_draw()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_safe_toggle_ruler()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_safe_draw_complete()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_safe_draw_rollback()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_safe_cancel_ruler_point()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_safe_set_draw_mode()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_rebind_draw_tool_if_active()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_on_draw_mode_changed()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_on_toggle_draw()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_draw_tool_deactivate()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_bind_shortcuts()` | 일부 겹침 | ⚠️ 공통 단축키만 super()로 묶기 |
| `update_ruler_style()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `update_unit_labels()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `update_x_label()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `update_label_move_style()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `_on_download_plot()` | 양쪽 거의 동일 | ⚠️ 공통 로직만 super() / 차이점 override |
| `show_warning()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `show_critical()` | 양쪽 동일 | ✅ BasePlotWindow로 이관 |
| `closeEvent()` | 비슷하나 차이 있음 | ⚠️ super() 호출 + 각자 override |

#### 실행 순서 (Phase 3-A)

```
1. [NEW] ui/windows/base_plot_window.py 파일 생성
   - QMainWindow를 상속, 공통 메서드들 이동
   - __init__에서 공통 속성 초기화 (canvas, figure, controller, _draw_objects_by_file 등)

2. [MODIFY] ui/windows/popup_plot.py
   - class PlotPopup(QMainWindow) → class PlotPopup(BasePlotWindow)
   - 이관된 메서드 제거
   - 필요시 super()._on_draw_object_complete(obj) 호출 추가

3. [MODIFY] ui/windows/compare_plot.py
   - class ComparePlotPopup(QMainWindow) → class ComparePlotPopup(BasePlotWindow)
   - 이관된 메서드 제거
   - compare 전용 오버라이드 유지 (series 분리 로직 등)

4. [TEST] 두 창 실행 확인
   - 단일 플롯 창: 단축키, 그리기, 저장, 눈금자 모두 동작 확인
   - 비교 플롯 창: 동일 항목 확인, 추가로 Blue/Red 레이어 전환 확인
```

> ⚠️ **주의사항**
> - `compare_plot.py`의 `_on_draw_object_complete`는 `setattr(obj, "series", self._active_draw_series)` 처리가 있어 단순 이관 불가. `super()` 호출 후 override 처리 필요.
> - `_bind_shortcuts`는 두 파일이 유사하지만 비교 플롯에만 있는 단축키(`Alt+B`, `Alt+R`, `T` 키 등)가 있음. 공통 단축키만 super()로 묶을 것.
> - `closeEvent`의 경우 popup은 `open_popups` 리스트에서 자신을 제거하는 로직이, compare는 ruler/label_move 상태 정리 로직이 있음. 세심하게 분리 필요.

---

### Phase 3-B: `layer_dock.py` 분리 (Model / View 분리) ✅ 완료

**목표:** `ui/widgets/layer_dock.py` (2200줄 / 96KB)를 두 개의 파일로 분리한다.

#### 분리 대상

| 새 파일 | 담당 역할 | 이관할 현재 메서드 |
|---|---|---|
| `layer_data_model.py` | 레이어 순서·상태 순수 데이터 관리 | `_get_current_filter_state()`, `_set_filter_state()`, `_set_layer_overrides()`, `_reset_layers_for_current_file()`, `_reset_layer_order()`, `_reset_draw_layers()`, `_reset_draw_order()`, 기타 상태 딕셔너리 관리 |
| `layer_dock.py` (잔류) | 화면에 리스트를 그려주는 View 로직만 | `_build_layer_row()`, `_build_global_row()`, `_build_draw_layer_row()`, `_build_draw_global_row()`, `_set_drop_indicator_between()`, `_set_draw_drop_indicator_between()`, `update_draw_layer_list()`, `set_vowels()`, `refresh_design_ui()` |

#### 실행 순서 (Phase 3-B)

```
1. [NEW] ui/widgets/layer_data_model.py 파일 생성
   - 순수 Python 클래스 (QWidget 미상속)
   - 레이어 순서 리스트, 오버라이드 딕셔너리, 필터 상태 딕셔너리 보관
   - 상태 변경 시 pyqtSignal로 알림 (layer_changed, filter_changed 등)

2. [MODIFY] ui/widgets/layer_dock.py
   - LayerDataModel을 주입받아 사용 (의존성 주입)
   - 직접 상태를 관리하던 속성들을 model 참조로 교체
   - refresh 시 model에서 상태 읽어서 UI 재구성

3. [TEST]
   - 레이어 순서 드래그 앤 드롭 확인
   - 레이어 설정(색상, 두께) 변경 확인
   - 그리기 레이어(선, 영역) 표시/숨김 확인
```

> ⚠️ **주의사항**
> - `layer_dock.py`는 현재 `popup_plot.py`와 `compare_plot.py`가 직접 `.update_draw_layer_list()`, `.set_vowels()` 등을 호출. 이 인터페이스는 반드시 유지해야 함.
> - `LayerDataModel`이 `pyqtSignal`을 내보내려면 `QObject`를 상속해야 함.

---

### Phase 3-C: `popup_plot.py` 내부 추가 정리 (선택적) ✅ 완료

**목표:** `popup_plot.py`에 남아있는 내부 클래스(다이얼로그)를 별도 파일로 분리한다.

| 현재 위치 | 제안 이동 위치 | 대상 클래스 |
|---|---|---|
| `popup_plot.py` 내부 | `ui/dialogs/batch_save_dialog.py` | `BatchSaveOptionsDialog` |
| `popup_plot.py` 내부 | `ui/dialogs/batch_save_dialog.py` | `BatchSaveProgressDialog` (있다면) |

---

### 전체 Phase 3 실행 권장 순서

```
Phase 3-A (BasePlotWindow) → 실행 테스트 → git commit
Phase 3-B (layer_dock 분리) → 실행 테스트 → git commit
Phase 3-C (내부 다이얼로그 분리) → 실행 테스트 → git commit
```

---

## 5. Phase 3 완료 후 기대 효과

- [X] **Phase 3-B: `popup_plot.py` 및 `compare_plot.py` 리팩토링** (완료)
    - `BasePlotWindow` 상속 구조를 통해 공통 shortcut 및 UI 헬퍼 메서드 통합.
    - `ComparePlotPopup`의 고유 로직(중첩 패널, 다중 레이어 도크 관리) 유지하며 베이스 인터페이스 준수.
- [X] **Phase 3-C (선택): `BasePlotWindow` 인터페이스 고도화** (완료)
    - `_safe_*` 계열의 숏컷 헬퍼 메서드를 베이스 클래스로 일괄 이관하여 `AttributeError` 방지 및 유지보수성 향상.
    - `on_toggle_ruler`, `_is_draw_active` 등 상태 체크 로직 표준화.

---

## 6. Phase 4 세부 실행 계획 — 변수명 및 Naming Convention 정리

> **선행 조건:** Phase 3 완료 권장 (God Object 분리 이후 파일 크기가 줄어 수정 범위가 명확해짐).
> Phase 3와 독립적으로도 진행 가능하나, 같은 코드를 두 번 건드리는 비효율이 발생할 수 있음.

### 코드베이스 전체 스캔 결과 (실측)

| 약어 패턴 | 전체 사용 횟수 | 주요 파일 |
|---|---|---|
| `df` | **174회** | 전체 파일에 분산 |
| `idx` | **~117회** | `popup_plot.py` 46회, `layer_dock.py` 22회, `controller.py` 13회 |
| `lbl` | **~39회** | `plot_engine.py` 6회, `layer_dock.py` 6회 |
| `ds` / `ds_settings` | **~8회** | `popup_plot.py`, `workers.py` |
| `ax` (Matplotlib axes) | **~100회 이상** | `plot_engine.py`, `popup_plot.py` 등 |
| `col` / `p_start` / `p_end` | 분산 | `math_utils.py`, `draw_line.py` 등 |

> ⚠️ `ax`는 Matplotlib 관례상 단독 약어를 허용. `df`는 pandas 관례이지만 **도메인 특화 이름이 없어** 모호함. 프로젝트 내부적으로 `formant_df` 또는 `vowel_df` 등으로 명확히 구분하는 것을 권장.

---

### Phase 4-A: 핵심 데이터 변수명 통일 (최우선, 위험도: 중간)

**범위:** `df`, `idx`, `ds` — 가장 빈번하게 혼용되는 약어 3종

#### 4-A-① `df` → 도메인 명칭으로 교체

| 현재 | 권장 명칭 | 적용 파일 | 비고 |
|---|---|---|---|
| `df` (함수 인자) | `vowel_df` | `plot_engine.py`, `controller.py`, `data_processor.py` | 모음 포먼트 데이터프레임 |
| `df` (지역 변수) | `filtered_df` | `controller.py` `_apply_outlier_filter` 등 | 이미 일부 `filtered_df` 존재 |
| `item["df"]` | `item["vowel_df"]` | `controller.py` plot_data_list 전체 | ⚠️ 딕셔너리 키 변경이므로 참조 전체 일괄 교체 필요 |
| `df.empty` 검사 | 그대로 유지 | — | pandas 내부 속성이므로 변경 불필요 |

> ⚠️ `item["df"]` → `item["vowel_df"]` 변경은 **딕셔너리 키 변경**이므로, `plot_data_list`를 참조하는 모든 위치를 일괄 교체해야 함. 누락 시 `KeyError` 발생.

#### 4-A-② `idx` → 의미 있는 인덱스 명칭으로

| 현재 | 권장 명칭 | 주요 위치 |
|---|---|---|
| `idx` (파일 인덱스) | `file_index` | `popup_plot.py`, `controller.py` |
| `idx` (레이어 인덱스) | `layer_index` | `layer_dock.py` |
| `idx` (루프 인덱스) | `i` 또는 `row_index` | 반복문 내부에서 `enumerate` 등 |
| `current_idx` | `current_file_index` | `popup_plot.py`, `controller.py` |

#### 4-A-③ `ds` / `ds_settings` → 전체 명칭 통일

| 현재 | 권장 명칭 | 위치 |
|---|---|---|
| `ds` | `design_settings` | `popup_plot.py` `_redraw_draw_layer` 내부 |
| `ds_settings` | `design_settings` | `workers.py` `BatchSaveWorker.__init__` |
| `ds_blue`, `ds_red` | `design_settings_blue`, `design_settings_red` | `compare_plot.py` 내부 (있다면) |

---

### Phase 4-B: UI 위젯 변수명 정리 (위험도: 낮음)

**범위:** `lbl`, `btn_숫자`, 기타 위젯 약어

#### 4-B-① `lbl` 약어 정리

| 현재 | 권장 명칭 | 위치 |
|---|---|---|
| `lbl` (함수 내 지역변수) | `label` 또는 `axis_label` | `plot_engine.py` |
| `lbl_info` (속성) | `lbl_info` 유지 — 위젯명은 `lbl_` prefix 허용 | `popup_plot.py` |
| `self.lbl_file_count` | 유지 (위젯 속성은 `lbl_` prefix 관례 허용) | `main_window.py` |

> 📝 **결론:** 위젯 속성(`self.lbl_*`)은 UI 코드 관례상 `lbl_` prefix를 허용. 단, 함수 내부 지역변수 `lbl`은 `label`로 풀어 쓸 것.

#### 4-B-② 의미 없는 숫자 suffix 버튼

| 현재 | 권장 명칭 | 위치 |
|---|---|---|
| `btn_1`, `btn_2` | `btn_apply`, `btn_cancel` 등 의미 있는 이름 | 각 UI 파일 |
| `row1_h`, `row2_h` | `top_row_layout`, `bottom_row_layout` | `main_window.py` |

---

### Phase 4-C: 생명주기 함수명 혼용 정리 (위험도: 낮음)

**범위:** `hide()`, `close()`, `remove()`, `clear()`, `deactivate()` 혼용

#### 현황 분석 (실측)

| 파일 | `hide()` | `close()` | `remove()` |
|---|---|---|---|
| `popup_plot.py` | 다수 | 다수 | 다수 |
| `compare_plot.py` | 다수 | 다수 | 다수 |
| `layer_dock.py` | 있음 | 있음 | 있음 |

#### 용어 통일 기준 (권장)

| 동작 의미 | 권장 함수 | 절대 혼용 금지 |
|---|---|---|
| 창을 숨기되 메모리 유지 | `.hide()` | ~~`.close()` 사용 금지~~ |
| 창을 닫고 메모리 해제 | `.close()` | ~~`.hide()` 사용 금지~~ |
| Matplotlib 아티스트 제거 | `.remove()` | 유지 (Matplotlib 내장 API) |
| 위젯/레이어 제거 | `_clear_*()` 메서드명으로 통일 | ~~`_remove_*()`, `_delete_*()`~~ |
| 도구 비활성화 | `.deactivate()` | ~~`_clear_current()` 혼용 금지~~ |

> ⚠️ `close()`는 PyQt에서 `closeEvent()`를 트리거하므로, `hide()`와 완전히 다른 동작임. 잘못 혼용하면 GC에 의한 팝업 소멸 등 런타임 오류 발생 가능.

---

### Phase 4-D: 기타 약어 및 파라미터명 정리 (위험도: 낮음)

| 현재 | 권장 명칭 | 파일 | 비고 |
|---|---|---|---|
| `p_start`, `p_end` | `start_point`, `end_point` | `draw_line.py`, `draw_polygon.py` | 위치 벡터를 나타냄 |
| `col` (열 이름) | `column_name` 또는 컨텍스트에 맞는 이름 | `math_utils.py`, `data_processor.py` | |
| `kor_font` | `korean_font` 또는 `fallback_font` | `plot_engine.py`, `controller.py` | |
| `fmt` | `file_format` | `controller.py` `_save_figure` | |
| `e` (except 절) | `error` 또는 `exc` | 전체 파일 | `except Exception as e` → `as error` |
| `xs`, `ys` | `x_coords`, `y_coords` | `draw_line.py`, `popup_plot.py` | 좌표 배열을 나타냄 |
| `cx`, `cy` | `centroid_x`, `centroid_y` | `popup_plot.py`, `compare_plot.py` | |
| `tx`, `ty` | `tip_x`, `tip_y` | `popup_plot.py` 화살촉 코드 | |

---

### 전체 Phase 4 실행 권장 순서 및 전략

```
Phase 4-A: df/idx/ds (가장 광범위 → 가장 먼저, 가장 꼼꼼히)
  → 실행 테스트 → git commit

Phase 4-B: 위젯 변수명 (범위 한정 → 비교적 빠름)
  → 실행 테스트 → git commit

Phase 4-C: 생명주기 함수 혼용 (로직 변경 없음, 이름만 통일)
  → 실행 테스트 → git commit

Phase 4-D: 기타 파라미터명 (파일별 순차 진행)
  → 실행 테스트 → git commit
```

#### 실행 전략 권장사항

1. **IDE의 전체 파일 Rename 기능** (`F2` 또는 Refactor → Rename)을 사용할 것. 수동 `Ctrl+H`는 실수 위험이 높음.
2. **`item["df"]` 키 변경**은 반드시 `grep`으로 전체 참조를 확인 후 일괄 교체.
3. **`except Exception as e`** 는 관례상 `e`가 허용되므로 선택적으로 변경.
4. 변경 전 `git stash` 또는 `git commit`으로 반드시 체크포인트를 만들 것.

