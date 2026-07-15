# 🎙️ GichanFormant (Code)

> [!NOTE]
> 이 레포지토리는 GichanFormant의 **소스 코드 전용** 저장소입니다. 
> 실행 파일(.exe) 다운로드를 원하시면 [GichanFormant 배포용 레포지토리](https://github.com/baggychani/GichanFormant)를 방문해 주세요.

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![PySide6](https://img.shields.io/badge/PySide6-41CD52?style=for-the-badge&logo=Qt&logoColor=white)
![uv](https://img.shields.io/badge/uv-DE5FE9?style=for-the-badge&logo=uv&logoColor=white)

**GichanFormant**는 모음 분석 및 포먼트 시각화를 위한 데스크톱 애플리케이션입니다.

> **진입점:** 정식 실행은 항상 `main.py`입니다 (`uv run main.py`).
> Tauri/React 파일럿만 보려면 `uv run desktop_main.py` 를 사용하세요.
> `desktop/` 자체는 실험용이며 기본 실행 경로가 아닙니다.


## 🚀 시작하기

이 프로젝트는 패키지 매니저 [uv](https://github.com/astral-sh/uv)를 사용하여 관리합니다.

### 1. uv 설치
`uv`가 설치되어 있지 않다면 다음 명령어로 설치할 수 있습니다.
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 프로젝트 준비 및 실행
다음 명령어를 입력하여 앱을 실행합니다.

```bash
uv sync
uv run main.py
```

Tauri/React 파일럿(실험):

```bash
uv run desktop_main.py
```

### 되돌리기 (PySide 안정 지점)

React/Tauri 실험 커밋 이전의 PySide 전용 상태는 태그 `pyside-stable`과 브랜치 `release/pyside-stable`에 고정되어 있습니다.

```bash
# 그 시점 코드만 잠깐 보기
git switch --detach pyside-stable

# 또는 안정 브랜치로 작업
git switch release/pyside-stable

# main으로 다시 돌아오기
git switch main
```

## ✅ 개발 점검

코드를 수정하기 전후에는 다음 검사를 통과시키는 것을 권장합니다.

```bash
uv sync --locked --all-extras --dev
uv run python scripts/sync_version.py --check
uv run ruff check .
uv run pytest tests/ -q
```

Windows PowerShell에서는 같은 검사를 한 번에 실행할 수 있습니다.

```powershell
.\scripts\dev_check.ps1
```

이 스크립트는 Windows 권한 문제를 줄이기 위해 프로젝트 내부의 `.uv-cache`와 `.tmp`를 우선 사용합니다.

의존성 다운로드가 막히는 환경에서는 먼저 네트워크 권한을 확인한 뒤 다시 실행해 주세요.
uv 캐시 문제를 피하려면 프로젝트 내부 캐시를 지정할 수 있습니다.

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv sync --locked --all-extras --dev
```

Windows에서 `uv run`이 Python 실행 파일의 `Access is denied`로 시작되지 않으면,
uv가 관리하는 Python 런타임을 프로젝트 내부에 다시 만들 수 있습니다.

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.uv-python"
uv python install --reinstall 3.10
uv venv --clear --python 3.10 .venv
uv sync --locked --all-extras --dev
```

테스트는 Qt 창을 띄우지 않도록 다음 환경 변수를 사용합니다.

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
uv run pytest tests/ -q
```


## 📦 기술 스택

- **언어**: Python 3.10+
- **GUI 프레임워크**: PySide6
- **데이터 분석**: NumPy, Pandas, SciPy
- **시각화**: Matplotlib
- **패키지 관리자**: [uv](https://github.com/astral-sh/uv)


## 👥 기여자

- [배기찬(@baggychani)](https://github.com/baggychani)
- [박준영(@young-52)](https://github.com/young-52)
