# GichanFormant Desktop (실험용 파일럿)

> ⚠️ **정식 진입점이 아닙니다.**
> 배포·일상 개발 실행은 저장소 루트의 `main.py`만 사용하세요 (`uv run main.py`).

이 폴더는 메인 창을 Tauri + React로 옮기기 위한 **실험용** 셸입니다.
분석 엔진은 Python sidecar가 담당하며, 기존 PySide 앱을 대체하지 않습니다.

## 실행 (파일럿만)

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

- `src/` — React UI (파일럿)
- `src/plotUnits.ts` — Hz / Bark / 정규화 표시 단위의 단일 진입점 (PySide 정책과 맞춤)
- `ipc/` — TypeScript ↔ Python 계약
- `src-tauri/` — Tauri shell + sidecar 브리지

분석 설정(Bark 표시, Lobanov, F3 게이트 등)은 Python `ApplicationService.set_analysis_settings`가
PySide 메인 창과 같은 강제 규칙을 적용합니다.

## 되돌리기

React/Tauri 이전 PySide 전용 스냅샷:

```bash
git switch release/pyside-stable
# 또는
git switch --detach pyside-stable
```
