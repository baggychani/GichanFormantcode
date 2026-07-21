# GichanFormant Desktop (Tauri + React)

> **마이그레이션 대상 UI입니다.**  
> 현재 배포·릴리스 기본 실행은 아직 저장소 루트 `main.py`(PySide)입니다.  
> 컷오버 전까지 두 경로를 병행합니다.

이 폴더는 메인 창과 대화형 플롯 창을 Tauri + React로 옮기는 **진행 중 마이그레이션**
셸입니다. 분석 엔진은 Python sidecar가 담당하며, 기존 PySide 앱과 같은
`ApplicationService` / IPC 계약을 사용합니다.

## 실행

저장소 루트에서:

```powershell
uv run desktop_main.py
```

또는 `desktop/`에서 직접:

```powershell
cd desktop
npm install
npm run tauri:dev
```

## 구성

- `src/` — React UI (메인 워크스페이스 + 대화형 플롯)
- `src/plotUnits.ts` — Hz / Bark / 정규화 표시 단위의 단일 진입점 (PySide 정책과 맞춤)
- `ipc/` — TypeScript ↔ Python 계약
- `src-tauri/` — Tauri shell + sidecar 브리지

분석 설정(Bark 표시, Lobanov, F3 게이트 등)은 Python `ApplicationService.set_analysis_settings`가
PySide 메인 창과 같은 강제 규칙을 적용합니다.

## 되돌리기

React/Tauri 이전 PySide 전용 스냅샷:

```bash
git switch release/pyside-stable
```
