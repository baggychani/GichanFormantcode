# UI boundary and Tauri migration path

## 목표

분석·프로젝트·파일 상태가 특정 PySide 위젯에 종속되지 않게 하고, 기존
PySide UI와 향후 React/Tauri UI가 동일한 애플리케이션 계약을 사용하게 한다.

현재 단계에서는 기존 PySide 플롯 창을 유지한다. Tauri는 이후 메인 창의
프론트엔드가 되고, Python sidecar는 분석과 네이티브 플롯 창을 담당한다.

```text
PySide MainUI ---------> ApplicationService <--------- future IPC host
      ^                         |                            ^
      |                         v                            |
PySideMainViewAdapter <- MainController -> ApplicationEventBus
                              |
             +----------------+----------------+
             |                |                |
       WorkspaceState    RuntimePort    DesktopWindowPort
                              |                |
                       QtRuntimeAdapter   PySide coordinator
```

## 2차 분리 결과

- `WorkspaceState`: 파일 경로, 데이터 목록, 현재 인덱스, 라벨 위치와 최근
  경로를 소유한다. 기존 컨트롤러 속성은 호환 프로퍼티로 유지한다.
- `AnalysisSettings`: Qt를 모르는 불변 분석 설정이다.
- `ApplicationService`: PySide와 미래 IPC가 함께 사용하는 명령 및 JSON 상태
  진입점이다. 현재 `MainUI`의 주요 사용자 명령도 이 서비스를 사용한다.
- `ApplicationEventBus`: 상태, 파일, 프로젝트, 진행률, 미리보기와 오류를
  프레임워크 중립 이벤트로 발행한다. 한 구독자의 예외가 다른 명령을
  중단시키지 않는다.
- `ApplicationError`: 오류 코드, 메시지, 상세 정보를 JSON 객체로 제공한다.
- `MainViewPort`: 설정 표시, 파일 상태, 사용자 알림, 파일 선택과 미리보기
  표시의 프레젠테이션 계약이다.
- `PySideMainViewAdapter`: 기존 `MainUI`를 `MainViewPort`에 연결한다.
- `NullMainView`: `QApplication` 없이 컨트롤러와 서비스를 테스트한다.
- `PreviewRenderer`: 데이터와 설정을 PNG 바이트로 렌더링하며 Qt를 import하지
  않는다.
- `RuntimePort`: 디바운스, 이벤트 루프 예약, 앱 데이터·문서·다운로드 경로를
  추상화한다.
- `DesktopWindowPort`: 단일·비교 플롯, 분석·가이드 창, ruler·label 도구와
  batch worker의 생성 및 창 참조 생명주기를 담당한다.

`core.controller`와 애플리케이션 계약 모듈은 새 Python 프로세스에서 import해도
`PySide6` 또는 `ui.*`를 로드하지 않는다. 이 조건은 회귀 테스트로 고정한다.

## 명령 계약

`ApplicationService`의 다음 메서드를 IPC command에 연결할 수 있다.

| Command | 입력 | 출력 |
| --- | --- | --- |
| `get_state` / `snapshot` | 없음 | 분석 설정, 소스 목록, capability |
| `set_analysis_settings` | 부분 설정 객체 | 갱신된 상태 |
| `load_files` | 경로 배열 | 로드 결과와 갱신된 상태 |
| `remove_file` | 소스 인덱스 | 갱신된 상태 |
| `reset` | 없음 | 초기 상태 |
| `save_project` | 경로 | 완료 또는 `ApplicationError` |
| `load_project` | 경로 | 복원 상태 또는 `ApplicationError` |
| `open_single_plot` | 없음 | 기존 PySide 플롯 창 요청 |
| `open_compare` | 소스 그룹 배열, 정규화 | 기존 PySide 비교 창 요청 |

상태 응답은 JSON으로 직렬화된다.

```json
{
  "analysis": {
    "type": "f1_f2",
    "f1_scale": "linear",
    "f2_scale": "log",
    "origin": "top_right",
    "use_bark_units": false,
    "outlier_mode": null,
    "outlier_scope": null,
    "normalization": null
  },
  "current_index": 0,
  "sources": [],
  "capabilities": {
    "can_plot": false,
    "can_compare": false,
    "can_save_project": false
  }
}
```

## 이벤트 계약

- `state_changed`
- `files_changed`
- `operation_progress`
- `project_saved`, `project_loaded`
- `preview_ready`, `preview_cleared`, `preview_failed`
- `window_requested`
- `operation_failed`

`preview_ready`는 PNG를 Base64 문자열로 전달하므로 JSON transport에서 그대로
전송할 수 있다.

## 의도적으로 남겨둔 Qt 경계

- `PySideMainViewAdapter`의 `QPixmap` 변환과 메인 창 표시
- `QtRuntimeAdapter`의 `QTimer`, `QStandardPaths`
- `PySideDesktopWindowCoordinator`의 구체 창·도구·worker 생성
- `PlotPopup`, `ComparePlotPopup` 내부 위젯, 포커스, 모달과 DPI 처리
- 시작 스플래시, 업데이트 UI와 애플리케이션 생명주기

이 Qt 코드는 `core` import 경계 밖에 있다. Tauri 초기 단계에서는 Python
sidecar가 별도 `QApplication`을 유지해 기존 플롯 창을 생성한다.

## React/Tauri 착수 전 남은 작업

의존성 분리 2차는 완료됐다. 다음 작업은 UI 리팩터링이 아니라 transport와
sidecar 생명주기다.

1. 길이 제한과 요청 ID를 갖는 JSON-RPC 또는 로컬 IPC host를 추가한다.
2. 명령 입력 schema와 허용 파일 경로를 검증한다.
3. `ApplicationEventBus` 이벤트를 Tauri event stream으로 전달한다.
4. 정상 종료, 강제 종료, 재시작과 단일 sidecar 인스턴스를 구현한다.
5. 이후 React에서 파일 목록·분석 설정·프로젝트 명령부터 구현한다.
6. 혼합 창의 포커스·DPI·종료 동작을 Windows와 macOS에서 검증한다.
