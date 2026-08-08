# Desktop (React + Tauri) 검증 체크리스트

메인 창과 대화형 플롯 창, Windows 설치본 기준.

범례: `[자동]` 로컬에서 빠르게, `[수동]` 앱 실행 후 눈으로, `[보류]` 이번 패스에서 스킵.

## 빠른 자동 검증

- [x] `[자동]` `cd desktop && npm run build` — React/TS 빌드 통과 (프론트 컴파일만, 설치본 아님)
- [x] `[자동]` `cd desktop && npm test` — React 렌더·상호작용 회귀 테스트
- [x] `[자동]` `cd desktop/src-tauri && cargo check` — Rust 명령 등록·컴파일 오류 확인 (`tauri:dev` 전체 기동 대용)

## Release 자동 검증 (Windows)

- [x] `[자동/Release]` React 테스트 통과 후 Tauri NSIS 빌드
- [x] `[자동/Release]` bundled sidecar를 Python·uv 없는 PATH로 실행해 `health` 확인
- [x] `[자동/Release]` 한글·공백 경로의 UTF-8 TSV를 bundled/installed sidecar에서 로드
- [x] `[자동/Release]` NSIS `/S` 임시 설치, 설치된 앱 기동, 무인 제거

검증 스크립트: `desktop/scripts/verify-windows-release.ps1`. 어느 단계든 실패하면 설치기 artifact 업로드와 GitHub Release 게시가 중단된다.

## 수동 스모크 (dev 앱)

- [ ] `[수동]` 첫 실행 시 시스템 테마 따름 (`localStorage`에 `gichanformant-theme` 없을 때). 무조건 라이트면 실패
- [ ] `[수동]` 메인 창 “대화형 플롯 열기” → React Tauri `single-plot` 창
- [ ] `[수동]` 같은 버튼 여러 번 → 창 중복 생성 없이 기존 창 focus
- [ ] `[수동]` 플롯 창: 데이터 없음 / 프리뷰 요청 / 분석 설정 변경이 깨지지 않음
- [ ] `[수동]` 플롯 창 “기존 PySide 플롯 열기” → 기존 PySide 창 정상 오픈
- [ ] `[수동]` 기존 PySide 앱(`uv run main.py`)·창 폐기되지 않았고 기존 기능 동작
- [ ] `[수동]` sidecar `health` 콜드 스타트에서 timeout 없이 통과
- [ ] `[수동]` CSV/TSV/XLSX/XLS 로드, 잘못된 파일 에러, 프리뷰 갱신
- [ ] `[수동]` 다크/라이트 전환, 고DPI, 창 리사이즈에서 UI 겹침 없음
- [ ] `[수동]` 비교 모드: 이번 범위 밖 — 기존 기능만 회귀 확인 (`uv run main.py`)

## 보류

- [ ] `[보류]` 별도 Windows PC/VM에서 완전 오프라인 설치·실행

## 실행 메모

```powershell
# 빠른 자동
cd desktop
npm test
npm run build
cd src-tauri
cargo check

# 수동 스모크용 개발 실행 (필요 시)
# uv run python desktop_main.py
# 정식 PySide: uv run main.py
```

결과 기록란 (날짜 / 누가 / 통과·실패):

| 항목 | 결과 | 메모 |
|------|------|------|
| npm run build | 통과 (2026-07-14) | `tsc && vite build` ~5s |
| npm test | 통과 (2026-08-09) | 4 files, 13 tests |
| cargo check | 통과 (2026-07-14) | ~19s, 명령 등록 OK |
| Windows release smoke | 통과 (2026-08-09) | bundled/installed sidecar, UTF-8 경로, NSIS 설치, 앱 기동 |
| 시스템 테마 | | 수동 |
| 플롯 창 오픈/focus | | 수동 |
| 플롯 셸 동작 | | 수동 |
| PySide 연동·회귀 | | 수동 |
| sidecar health | | 수동 |
| 파일 로드 | | 수동 |
| 테마/DPI/리사이즈 | | 수동 |
| 비교 모드 회귀 | | 수동 |
| 다른 PC·오프라인 | 보류 | 별도 깨끗한 Windows 환경 필요 |
