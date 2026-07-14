# Desktop (React + Tauri) 검증 체크리스트

UI 껍데기(메인 창 + 대화형 플롯 창 셸) 기준.  
**제외(느림):** `tauri build` / release 패키징 / 다른 PC·오프라인 설치 검증.

범례: `[자동]` 로컬에서 빠르게, `[수동]` 앱 실행 후 눈으로, `[보류]` 이번 패스에서 스킵.

## 빠른 자동 검증

- [x] `[자동]` `cd desktop && npm run build` — React/TS 빌드 통과 (프론트 컴파일만, 설치본 아님)
- [x] `[자동]` `cd desktop/src-tauri && cargo check` — Rust 명령 등록·컴파일 오류 확인 (`tauri:dev` 전체 기동 대용)

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

## 보류 (시간 오래 걸림)

- [ ] `[보류]` release 빌드에서 bundled sidecar가 Python/uv 없이 실행
- [ ] `[보류]` Windows 다른 PC, 공백/한글 사용자 경로, 오프라인 설치 앱 실행

## 실행 메모

```powershell
# 빠른 자동
cd desktop
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
| cargo check | 통과 (2026-07-14) | ~19s, 명령 등록 OK |
| 시스템 테마 | | 수동 |
| 플롯 창 오픈/focus | | 수동 |
| 플롯 셸 동작 | | 수동 |
| PySide 연동·회귀 | | 수동 |
| sidecar health | | 수동 |
| 파일 로드 | | 수동 |
| 테마/DPI/리사이즈 | | 수동 |
| 비교 모드 회귀 | | 수동 |
| release/다른 PC | 보류 | 설치본·패키징 제외 |
