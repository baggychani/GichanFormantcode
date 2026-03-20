# GichanFormant 코드 개선 계획 (유지보수성·가독성·견고성)

**원칙**: 수정으로 인한 **로직 오류 위험**이 있는 변경은 제안하지 않음. 자신 있게 안전하다고 판단되는 항목만 포함함.

---

## Phase 1: 안전한 상수·설정 정리 (로직 변경 없음) — **완료**

### 1.1 UI 상수 모듈 확장

- **대상**: `ui/layout_constants.py` 또는 `config.py`
- **내용**:
  - 폰트 크기: `FONT_SIZE_SMALL = 9`, `FONT_SIZE_NORMAL = 10`, `FONT_SIZE_MEDIUM = 11`, `FONT_SIZE_TITLE = 12` 정의.
  - 자주 쓰는 여백: `MARGIN_DOCK_DEFAULT = (12, 15, 12, 15)`, `MARGIN_NARROW = (2, 2, 2, 2)` 등 (필요한 것만 선별).
  - Hex 색상: 이미 쓰이는 `#DCDFE6`, `#E4E7ED`, `#F5F7FA`, `#606266`, `#303133`, `#409EFF` 등을 `COLOR_BORDER`, `COLOR_BG_LIGHT`, `COLOR_TEXT_SECONDARY`, `COLOR_PRIMARY` 등 의미 있는 이름으로 한 곳에 정의.
- **적용**: ui 파일에서 해당 숫자/문자열을 상수 참조로 **점진적** 교체. 한 번에 전부가 아니라 파일 단위로 나눠 적용하면 리스크 최소화.
- **위험도**: 낮음 (값만 상수로 빼고 동작 동일).

### 1.2 매직 넘버만 상수로 대체

- **고정 폭/높이**: `AXIS_LABEL_WIDTH`, `_tab_width_px` 등 이미 있는 패턴을 유지하고, 새로 발견되는 반복 값(예: 26, 32, 35, 48)을 같은 파일 상단 또는 `layout_constants`에 이름 붙여서 사용.
- **위험도**: 낮음.

---

## Phase 2: _setup_ui 분리 (동작 불변) — **완료**

### 2.1 DesignSettingsPanel / CompareDesignSettingsPanel

- **방식**: `_setup_ui()` 내부를 **호출 순서만 유지**한 채, 논리 블록 단위로 메서드로 분리.
  - 예: `_setup_data_display_section()`, `_setup_style_section()`, `_setup_graph_background_section()`, `_setup_bottom_buttons()`.
  - `_setup_ui()`는 이 메서드들을 기존과 같은 순서로 호출만 하도록 변경.
- **조건**: 각 서브메서드는 **기존 코드를 그대로 이동**하고, 변수 스코프(`layout`, `font_bold` 등)만 인자나 `self`로 넘겨서 해결. **새 로직 추가·삭제 없음**.
- **위험도**: 낮음 (리팩터링만, 동작 동일).

### 2.2 popup_plot / compare_plot / layer_dock / filter_panel

- **방식**: 위와 동일. "분석 도구" 탭, "데이터 표시", "스타일", "그래프 배경" 등 주석으로 나뉜 구역을 그대로 서브메서드로 옮기고, `_setup_ui()`는 이들을 순서대로 호출.
- **위험도**: 낮음 (이동만 할 경우).

---

## Phase 3: 타입 힌트 추가 (동작 무영향) — **완료**

### 3.1 공개 API·유틸부터

- **대상**: `utils/display_utils.py` (이미 일부 있음), `utils/color_utils.py`, `utils/math_utils.py`의 공개 함수.
- **내용**: 인자와 반환 타입만 추가. 예: `def truncate_display_name(name: str, max_len: int = MAX_DISPLAY_NAME_LEN) -> str:`.
- **위험도**: 없음.

### 3.2 core / model / engine / ui

- **방식**: 새로 작성·수정하는 메서드부터 타입 힌트를 붙이고, 기존 메서드는 **손대는 파일만** 점진적으로 추가. 한 번에 전체 코드베이스 변경은 하지 않음.
- **위험도**: 없음 (타입 힌트는 런타임에 실행되지 않음).

---

## Phase 4: 방어적 코딩 (명확히 안전한 경우만) — **완료**

### 4.1 snapshot 빈 리스트 (core/controller.py 546행 근처)

- **현재**: `first_name = snapshot[0].get('name', '') if snapshot else ''` — `snapshot`이 빈 리스트면 `snapshot[0]`에서 IndexError.
- **수정**: `first_name = snapshot[0].get('name', '') if len(snapshot) > 0 else ''` 또는 `first_name = (snapshot[0].get('name', '') if snapshot else '')` 대신 `(snapshot[0] if snapshot else {}).get('name', '')`처럼 빈 리스트에서 인덱스 접근을 하지 않도록 변경.
- **위험도**: 낮음. 빈 리스트일 때 기대 동작(빈 문자열 등)만 일치시키면 됨.

### 4.2 hovered_label None 체크 (tools/label_move.py 280행 근처)

- **현재**: `self.hovered_label.get('vowel')` — `hovered_label`이 None이면 AttributeError.
- **수정**: `(self.hovered_label or {}).get('vowel')` 또는 사용 전 `if self.hovered_label:` 분기 추가.
- **위험도**: 낮음.

### 4.3 dict.get()에 기본값 추가

- **대상**: `tools/ruler.py`, `ui/vowel_analysis_dialog.py` 등에서 `.get('key')`만 쓰고 None이 올 수 있는 경우. **기존 동작이 "None이면 기본값"인지** 확인 후, 동일 의미로 `get('key', default)` 추가.
- **주의**: 이미 `or fallback`으로 처리하는 코드는 로직이 바뀌지 않도록 그대로 두거나, `get('key', fallback)`으로 통일할 때 의미가 동일한지 검토.
- **위험도**: 낮음 (의도가 같을 때만 적용).

---

## Phase 5: 가독성·PEP8 (로직 변경 없음) — **완료**

### 5.1 람다·이벤트 덮어쓰기 정리

- **ui/design_panel.py** 1112행: `graph_header_row.mousePressEvent = lambda e: toggle_graph_bg_cmp()`  
  → `def _on_graph_header_clicked(self, e): toggle_graph_bg_cmp()` 같은 메서드로 빼고, `graph_header_row.mousePressEvent = self._on_graph_header_clicked`로 연결. (PySide6에서는 시그널이 있다면 시그널 사용이 더 나음.)
- **위험도**: 낮음.

### 5.2 복잡한 스타일 분기

- **ui/popup_plot.py** 156, 177행: 인덱스별로 다른 스타일 문자열을 삼항 연산자 체인으로 붙이는 부분 → 인덱스 → 스타일 문자열 매핑을 리스트/딕셔너리로 두고 `styles[i]`처럼 참조하도록 변경.
- **위험도**: 낮음 (출력 문자열만 동일하게 유지).

### 5.3 변수명 구체화

- **ui/compare_plot.py** 514행: `col = lambda df: ...` → `get_label_column = lambda df: ...` 또는 별도 함수 `def _get_label_column(df): ...`로 이름만 명확히.
- **위험도**: 없음.

---

## Phase 6: 리소스 (선택·점진 적용)

### 6.1 QWidget 생성 시 parent 명시

- **내용**: 새로 추가하는 위젯만 `QWidget(parent=self)` 또는 해당 부모 위젯을 넘기도록 하고, 기존 코드는 **수정 시에만** 같이 parent를 넣어 줌. 전면 일괄 변경은 하지 않음.
- **위험도**: 낮음 (부모만 명시해도 동작은 보통 동일).

### 6.2 시그널·람다

- **현재**: `lambda checked, b=btn: ...`, `lambda _, idx=i: ...` 등 기본 인자 캡처는 적절히 사용됨. 별도 수정 없이, **새로 연결할 때만** 불필요한 람다를 줄이고 메서드로 연결하는 방식을 권장.

---

## 제외·보류 권장 (로직 오류 위험)

- **model/data_processor.py** 140행 `str_data.str.extract(...)[0]`: 빈 결과 처리 시 인덱스·타입이 바뀌면 이후 파이프라인에 영향. **원본 데이터 형식과 예외 케이스를 정확히 파악한 뒤** 별도 이슈로 처리 권장.
- **engine/plot_engine.py** `manual_ranges` 키 접근: 호출부가 항상 같은 구조로 채우는지 먼저 확인. 확인 후에만 `get()` + 기본값 또는 호출부에서 채우기로 통일.
- **대규모 DRY 통합**: filter_panel 단일/다중을 하나로 합치거나, layer_dock의 레이어 행 3곳을 한 팩토리로 통합하는 작업은 **동작 검증 범위가 크므로** 별도 태스크로 나누고 테스트 후 진행 권장.

---

## 적용 순서 제안

1. ~~**Phase 1**: 상수 정리 (layout_constants / config) — 한 파일씩 적용.~~ **완료**
2. ~~**Phase 4**: controller 546행, label_move 280행 등 **명확한 방어 1~2곳**만 먼저 수정.~~ **완료**
3. ~~**Phase 3**: display_utils, color_utils 등 **유틸 타입 힌트**부터 추가.~~ **완료**
4. ~~**Phase 2**: design_panel의 _setup_ui를 **한 클래스만** 먼저 서브메서드로 분리해 보고, 문제 없으면 나머지 확대.~~ **완료** (CompareDesignSettingsPanel만 적용)
5. ~~**Phase 5**: 람다/이벤트·변수명·스타일 분기 등 **가독성** 개선.~~ **완료**
6. **Phase 6**: 새 코드 위주로 parent 명시, 나머지는 기회 있을 때만. (미진행)

이 순서로 진행하면 **로직 변경을 최소화**하면서 유지보수성·가독성·견고성을 단계적으로 높일 수 있습니다.
