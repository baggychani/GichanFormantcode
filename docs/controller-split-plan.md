# MainController 분리 계획

`core/controller.py`는 아직 god object다 (~2500줄).
당장 한 번에 쪼개지 말고, **ApplicationService로 명령이 모인 뒤** 기능 덩어리별로 떼어낸다.

## 목표

- UI(PySide/미래 셸)는 `ApplicationService`만 부른다
- `MainController`는 오케스트레이션만 남기거나, 도메인 서비스 facade가 된다
- 플롯 팝업이 `controller.메서드`를 직접 호출하는 결합을 줄인다

## 현재 덩어리 (대략)

| 덩어리 | 예시 | 이동 후보 |
| --- | --- | --- |
| Workspace / files | load/remove/reset, current index | 이미 `data_loading_service` + service 경유 강화 |
| Project I/O | save/load `.gfproj` | `project_service` + `ApplicationService` (진행 중) |
| Preview | live preview render | `preview_renderer` + service |
| Single plot window | open/refresh/export | `plot_session_service` (신규) |
| Compare | session, virtual indices | `compare_service` 확장 |
| Design / layers | defaults, layer order sync | 기존 design 유틸 + session |
| Tools | ruler, label move, draw | tool coordinator (UI 쪽 유지 가능) |
| Batch export | worker 생성 | `export_service` / workers |

## 단계

### Phase A — 명령 단일화 (지금~단기)
1. 메인 창 파일/프로젝트/삭제를 service로 통일 ← **이번 작업**
2. 분석 설정 변경도 `set_analysis_settings` 경유 (PySide 위젯 → service)
3. 계약 테스트: 같은 입력 → 같은 이벤트

### Phase B — 읽기 쉬운 경계
1. `MainController` public API를 “service가 부르는 메서드” 목록으로 문서화
2. 팝업의 `controller.foo` 호출을 카탈로그화 (grep 기준)
3. 새 기능은 controller에 넣지 말고 service 또는 전용 서비스에 추가

### Phase C — 세션 객체 추출
1. `PlotSession` / `CompareSession` 런타임 상태를 controller 밖으로
2. window coordinator는 창 생성만, 세션 로직은 서비스
3. controller 줄 수를 의미 있게 줄인 뒤에야 클래스 분할 커밋

### Phase D — 셸 교체 직전
1. IPC 명령 = ApplicationService public methods 1:1
2. 팝업이 필요로 하는 동작도 service 명령으로 승격
3. headless + desktop sidecar 경로 검증

## 하지 말 것

- “파일 하나 쪼개기”만 하는 기계적 분할 (import 지옥만 늘고 동작은 그대로)
- React UI와 동시에 controller 대개편
- 테스트 없는 대규모 move

## 완료 신호

- 메인 창 사용자 동작의 이벤트 스트림이 service-only
- `tests/test_application_boundary.py`가 dialog/project/remove 경로를 고정
- controller public surface가 문서화된 짧은 목록으로 줄어듦
