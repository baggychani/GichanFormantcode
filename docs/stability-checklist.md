# GichanFormant 안정화 체크리스트

오랜만에 프로젝트를 다시 만질 때 우선 확인할 항목입니다. 새 기능보다 재현 가능한 개발환경과 회귀 방지를 먼저 봅니다.

## 1. 개발환경

- `uv sync --locked --all-extras --dev`가 성공하는지 확인
- `.venv`가 끊어진 Python 경로를 가리키지 않는지 확인
- Windows에서 uv 캐시 권한 문제가 나면 `$env:UV_CACHE_DIR = "$PWD\.uv-cache"` 지정 후 재시도
- pytest 임시 폴더 권한 문제가 나면 `scripts/dev_check.ps1`처럼 `.tmp`를 `TEMP`/`TMP`와 `--basetemp`로 지정
- 시스템에 Python이 없어도 uv가 `.python-version` 기준으로 환경을 만들 수 있는지 확인

## 2. 기본 검증

```powershell
.\scripts\dev_check.ps1
```

수동으로 실행할 때는 다음 순서를 사용합니다.

```powershell
uv run python scripts/sync_version.py --check
uv run ruff check .
uv run pytest tests/ -q
```

## 3. 수동 스모크 테스트

- 앱 실행 후 스플래시와 메인 창 표시 확인
- txt/xlsx 데이터 파일 로드
- 단일 플롯 생성, Hz/Bark 전환, 축 범위 수동 지정
- 레이어 순서 변경, 라벨 스타일 변경, 필터 ON/OFF
- compare 플롯에서 두 개 이상 데이터 비교
- draw 도구로 선/도형/텍스트 추가 후 저장
- 프로젝트 저장 후 다시 열어 레이어, 필터, draw 객체가 유지되는지 확인
- 이미지 저장, 통합 txt 저장, batch save 확인

## 4. 변경 시 우선순위

- 저장/불러오기, export, compare, 레이어 상태는 회귀 위험이 높으므로 테스트 먼저 추가
- `except Exception: pass`를 새로 만들지 말고 최소한 debug 로그를 남김
- 큰 파일은 기능 변경 없이 작은 순수 함수부터 분리
- 릴리스 전에는 `scripts/sync_version.py --check`와 GitHub Actions Release 워크플로를 함께 확인
