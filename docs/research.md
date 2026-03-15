# GichanFormant 코드베이스 분석 (유지보수성·가독성·견고성)

전체 코드를 **유지보수성(Maintainability), 가독성(Readability), 안정성(Robustness)** 관점에서 분석한 결과입니다. 수정은 하지 않고 읽기·검색만 수행했습니다.

---

## 1. DRY — 중복 코드 및 과도한 _setup_ui

### 1.1 중복 UI 패턴

- **토글 행**
  - `ui/design_panel.py`: `_create_toggle_row()`(704–711행)가 단일/비교 패널 양쪽에서 사용. 비교 패널(959–1063행)에서도 동일 패턴 반복.
  - `ui/layer_dock.py`: 576–601, 676–701, 896–927행에서 "레이어 행"(눈 아이콘, 반투명 버튼, 고정 높이 26/22) 구성이 거의 동일하게 3곳 반복.

- **버튼 그룹·스타일**
  - `ui/design_panel.py`: `_create_visual_button_group()` 내부에서 `QFrame` 스타일 `"background-color: white; border: 1px solid #DCDFE6; border-radius: 4px"` 및 `setContentsMargins(2,2,2,2)`, `setSpacing(0)` 반복.
  - `ui/filter_panel.py`: 단일(56–210행) vs 다중(305–494행) 탭에서 "모두 ON/OFF" + 스크롤 + 모음별 ON/OFF/반투명 행 구성 및 스타일시트 블록이 대량 중복.

- **레이아웃 여백·간격**
  - `setContentsMargins(12, 15, 12, 15)` + `setSpacing(12)`: `popup_plot.py` 572–573, `compare_plot.py` 541–542.
  - `(0,0,0,0)`, `(12,12,12,15)` 등 숫자가 여러 파일에 하드코딩. `layout_constants.py`, `config.py`에 일부만 상수화됨.

### 1.2 과도한 _setup_ui (한 메서드에 너무 많은 책임)

| 파일 | 메서드 | 대략 라인 범위 | 내용 |
|------|--------|----------------|------|
| ui/design_panel.py | DesignSettingsPanel._setup_ui | 222 ~ 540 | 데이터 표시, 스타일, 그래프 배경, 하단 버튼이 한 메서드에 포함 |
| ui/design_panel.py | CompareDesignSettingsPanel._setup_ui | 933 ~ 1194 | 1. 데이터 표시, 2. 스타일, 3. 그래프 배경, 서브 탭, 하단 초기화가 한 메서드에 포함 |
| ui/popup_plot.py | _setup_ui / _build_unified_dock 내부 | 540 ~ 800 | 분석 도구 탭 내 축 범위·도구 버튼·내보내기 등이 한 흐름으로 김 |
| ui/compare_plot.py | _setup_analysis_ui | 541 ~ 780 | 범례·정규화·축 범위·도구 버튼 등이 한 메서드에 김 |
| ui/layer_dock.py | LayerDock._setup_ui | 246 ~ 495 | 상단 스크롤, 탭, 레이어 리스트, 리셋 행, 하단이 한 메서드에 포함 |
| ui/filter_panel.py | 단일/다중 _setup_ui | 56–210, 305–394 | 스타일 + 헤더 + 스크롤 + 모음 행이 각각 한 메서드에 포함 |

---

## 2. 매직 넘버·문자열 (Magic Numbers & Strings)

### 2.1 폰트·고정 크기(px)·여백

- **폰트 크기**: `QFont(..., 9)`, `10`, `11`, `12`가 design_panel, popup_plot, compare_plot, layer_dock, filter_panel, file_guide, vowel_analysis_dialog, icon_widgets 등에 반복. `FONT_SIZE_SMALL = 9`, `FONT_SIZE_NORMAL = 10` 등으로 통일 가능.
- **고정 너비/높이**: `setFixedWidth(48)`, `setFixedHeight(26|32|34|35|38)`, `AXIS_LABEL_WIDTH`, `setFixedWidth(50|55|70|80|114|200)` 등이 여러 파일에 흩어짐.
- **여백·간격**: `setContentsMargins(28,26,28,22)`, `(12,15,12,15)`, `(2,2,2,2)`, `(0,5,0,5)` 등 값이 파일마다 하드코딩.

### 2.2 Hex 색상·문자열

- **Hex 색상**: `#DCDFE6`, `#E4E7ED`, `#F5F7FA`, `#C0C4CC`, `#606266`, `#303133`, `#409EFF`, `#F0F2F5`, `#F56C6C`, `#67C23A`, `#E6A23C`, `#EBEEF5` 등이 ui 전반에 반복. `config.py`에는 `SEPARATOR_BG_COLOR` 등 소수만 정의.
- **폰트명**: "Malgun Gothic", "Arial", "Times New Roman"이 design_panel, compare_plot, icon_widgets 등에 반복.
- **문자열**: "blue", "red", "QPushButton", "QFrame" 스타일 문자열이 비슷한 패턴으로 여러 곳에 반복.

---

## 3. PEP8·타입 힌트·가독성

### 3.1 타입 힌트 부재

- **core/controller.py**: `__init__`, `handle_file_drop`, `open_file_dialog`, `refresh_plot`, `navigate_plot`, `download_plot` 등 대부분 메서드에 인자/반환 타입 없음.
- **model/data_processor.py**: `load_files`, `_parse_fixed_columns`, `_read_csv_with_encoding` 등 타입 힌트 없음.
- **engine/plot_engine.py**: `draw_plot`, `draw_multi_plot`, `_prepare_plot_df` 등 타입 힌트 없음.
- **ui**: `_setup_ui`, `_build_unified_dock`, `_create_toggle_row`, `_build_individual_tab` 등 인자/반환 타입 없음.
- **utils/vowel_stats.py**, **tools/ruler.py**, **tools/label_move.py**: 일부만 타입 힌트 있음.

### 3.2 변수명·조건 복잡도

- **모호한 이름**: `ui/compare_plot.py` 514행 `col = lambda df: ...` → "라벨 컬럼명 반환 함수"임을 드러내는 이름 권장. `ui/design_panel.py`의 `ctrl`, `cfg` 등도 역할이 드러나도록 구체화 가능.
- **복잡한 한 줄**: `ui/popup_plot.py` 156, 177행의 인덱스별 스타일 삼항 연산자 체인 → 리스트/딕셔너리로 분리하면 가독성 향상.
- **이벤트 덮어쓰기**: `ui/design_panel.py` 1112행 `graph_header_row.mousePressEvent = lambda e: toggle_graph_bg_cmp()` → 명시적 메서드로 분리하면 유지보수·디버깅에 유리.

---

## 4. 리소스·성능 (시그널/위젯)

### 4.1 시그널·슬롯

- **ui/main_window.py** 319, 415행: `lambda checked, b=btn: ...`, `lambda _, idx=i: ...` — 기본 인자로 캡처하여 루프 변수 문제 없음. 위젯 제거 시 연결 해제 여부만 확인하면 됨.
- **ui/filter_panel.py**, **ui/design_panel.py**: `lambda: self._set_all_on(tab_id)` 등 `tab_id`/`series` 캡처 — 적절함.
- **ui/design_panel.py** 1112행: 람다로 `mousePressEvent` 덮어쓰기 — 메서드로 빼는 편이 안전하고 명확.

### 4.2 QWidget 부모 미지정

- `QWidget()`만 하고 `addWidget`/`setWidget`/`setLayout`으로 나중에 부모에 붙이는 패턴이 popup_plot, compare_plot, layer_dock, design_panel, main_window, filter_panel, file_guide, vowel_analysis_dialog 등에 다수 있음.
- Qt가 레이아웃 추가 시 부모를 설정하므로 실질적 누수 위험은 낮을 수 있으나, **명시적 `parent=`** 를 주면 소유 관계와 라이프사이클이 분명해짐.

---

## 5. 방어적 코딩 (Defensive Programming)

### 5.1 dict.get() 기본값·None 처리

- **core/controller.py** 546행: `first_name = snapshot[0].get('name', '') if snapshot else ''` — `snapshot`이 **빈 리스트**이면 `snapshot[0]`에서 **IndexError**. `if snapshot`은 빈 리스트를 걸러주지 않음. `len(snapshot) > 0` 또는 `snapshot and snapshot[0]` 등으로 보강 필요.
- **tools/label_move.py** 280행: `self.hovered_label.get('vowel')` — `hovered_label`이 None이면 AttributeError. 호출 전 None 체크 필요.
- **tools/ruler.py**: `design_settings.get('font_style')`, `m.get('text_pos')`, `pt.get('label', pt.get('Label'))` 등 일부만 기본값 있음. 일관된 `get(key, default)` 권장.
- **ui/vowel_analysis_dialog.py**: `result.get('point_distances') or {}` 등은 방어적. `pd_v.get('distance_mean')`, `pd_v.get('distance_std')`는 기본값 없으나 `_fmt_*`에서 None 처리하는지 확인 필요.
- **engine/plot_engine.py**: `manual_ranges['y_min']` 등 직접 키 접근 — 키 없을 때 KeyError 가능. 호출부에서 항상 채우는지 또는 `manual_ranges.get('y_min')` 등으로 방어할지 결정 필요.

### 5.2 타입 변환·인덱스 접근

- **ui/popup_plot.py** 1175–1178, **ui/compare_plot.py** 953–956: `float(self.range_widgets['y_min'].text())` — 빈/비숫자 입력 시 ValueError. 현재 try/except ValueError로 처리되어 있음.
- **model/data_processor.py** 140행: `str_data.str.extract(r'/([^/]+)/')[0]` — extract 결과가 비어 있으면 인덱스 0 접근 시 예외 가능. 빈 시리즈/NaN 처리 필요.
- **ui/main_window.py** 504–505, 549–556: `self.plot_type_group.buttons()[0].setChecked(True)` — 버튼이 없으면 IndexError. 방어적으로 `if self.plot_type_group.buttons():` 체크 가능.

---

## 6. 요약 표 (파일·라인 참조)

| 구분 | 파일 | 라인(또는 범위) | 내용 |
|------|------|------------------|------|
| DRY | ui/design_panel.py | 222–540, 933–1194 | _setup_ui 과도하게 김; 섹션별 서브메서드 분리 권장 |
| DRY | ui/filter_panel.py | 56–210, 305–494 | 단일/다중 _setup_ui·스타일시트 대량 중복 |
| DRY | ui/layer_dock.py | 576–601, 676–701, 896–927 | 레이어 행 UI 3곳 반복 |
| Magic | ui/*.py 전반 | 다수 | 폰트 9/10/11/12, 고정 px, 마진, hex 색상 반복 |
| PEP8/타입 | core, model, engine, ui, tools, utils | 전역 | 공개/비공개 메서드 대부분 타입 힌트 없음 |
| PEP8 | ui/design_panel.py | 1112 | mousePressEvent 람다 → 명시적 메서드 권장 |
| 리소스 | ui 여러 파일 | 4.2 항 | QWidget() 무부모 생성; parent= 명시 권장 |
| 방어 | core/controller.py | 546 | snapshot 빈 리스트 시 snapshot[0] → IndexError 가능 |
| 방어 | tools/label_move.py | 280 | hovered_label None 시 .get() → AttributeError 가능 |
| 방어 | model/data_processor.py | 140 | .str.extract(...)[0] 빈 결과 시 인덱스 오류 가능 |
| 방어 | engine/plot_engine.py | 151–154, 497–500 | manual_ranges 키 없을 때 KeyError 가능성 |

---

*이 문서는 코드 수정 없이 읽기·검색만으로 작성되었습니다. 구체적인 개선 작업은 plan.md를 참고하세요.*
