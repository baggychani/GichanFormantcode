# 🎙️ GichanFormant (Code)

> [!NOTE]
> 이 레포지토리는 GichanFormant의 **소스 코드 전용** 저장소입니다. 
> 실행 파일(.exe) 다운로드를 원하시면 [GichanFormant 배포용 레포지토리](https://github.com/baggychani/GichanFormant)를 방문해 주세요.

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![PySide6](https://img.shields.io/badge/PySide6-41CD52?style=for-the-badge&logo=Qt&logoColor=white)
![uv](https://img.shields.io/badge/uv-DE5FE9?style=for-the-badge&logo=uv&logoColor=white)

**GichanFormant**는 모음 분석 및 포먼트 시각화를 위한 데스크톱 애플리케이션입니다.


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


## 📦 기술 스택

- **언어**: Python 3.10+
- **GUI 프레임워크**: PySide6
- **데이터 분석**: NumPy, Pandas, SciPy
- **시각화**: Matplotlib
- **패키지 관리자**: [uv](https://github.com/astral-sh/uv)


## 👥 기여자

- [배기찬(@baggychani)](https://github.com/baggychani)
- [박준영(@young-52)](https://github.com/young-52)
