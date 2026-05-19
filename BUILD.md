# GichanFormant 빌드·배포 안내

## 버전 올릴 때 체크리스트 (마지막 자리 +1 예: 2.3.4.1 → 2.3.4.2)

아래를 **모두 같은 문자열**로 맞춥니다. 앱 UI·업데이트 알림·설치 프로그램이 `config.APP_VERSION`을 기준으로 동작합니다.

| 파일 | 항목 |
|------|------|
| `config.py` | `APP_VERSION` |
| `pyproject.toml` | `version` |
| `uv.lock` | `uv lock` 실행 후 반영 |
| `GichanFormant.iss` | `#define MyAppVersion` |
| `info.txt` | `filevers`, `prodvers`, `FileVersion`, `ProductVersion` (Windows exe 메타) |
| `complete.txt` | 설치 완료 문구 |

확인: `uv run main.py` 실행 → 스플래시·창 제목에 새 버전 표시.

**GitHub 릴리스 태그:** 배포용 레포 [baggychani/GichanFormant](https://github.com/baggychani/GichanFormant)에  
`v2.3.4.2` 형식으로 태그를 만들면 자동 업데이트 검사가 동작합니다 (`config.GITHUB_*`).

---

## 저장소 구분

| 레포 | 용도 |
|------|------|
| **GichanFormantcode** (이 레포) | 소스, CI 빌드, 개발 |
| **GichanFormant** | 사용자용 Releases (.exe / macOS zip) |

---

## macOS 빌드 (Windows PC만 있어도 됨)

**로컬 Mac이 없어도 됩니다.** `main`에 push하면 GitHub Actions가 macOS에서 빌드합니다.

1. [Actions → CI/CD](https://github.com/baggychani/GichanFormantcode/actions) (브랜치 `main` push 또는 **Run workflow**)
2. 완료 후 **Artifacts**에서 다운로드:
   - `GichanFormant-macos-arm64-<sha>.zip` (Apple Silicon)
   - `GichanFormant-macos-intel-<sha>.zip` (Intel)
3. 배포 레포 Releases에 업로드 (아래 「릴리스 게시」 참고)

macOS 앱 아이콘(`.icns`)을 쓰려면 `resources/icon.icns` 또는 루트 `icon.icns`를 추가한 뒤 CI를 다시 돌리세요. (현재 레포에는 `.ico`만 있음 → 기본 Qt 아이콘으로 빌드될 수 있음)

---

## Windows 빌드 (로컬)

```powershell
cd C:\Users\c\Desktop\GichanFormant
uv sync --locked --all-extras --dev
uv run pytest tests/
uv run pyinstaller --noconfirm --onefile --windowed --icon=assets/icon.ico --name=GichanFormant --version-file=info.txt main.py
```

결과: `dist\GichanFormant.exe`

### 설치 프로그램 (Inno Setup)

1. 위 PyInstaller로 `dist\GichanFormant.exe` 생성 (또는 onedir 구조를 쓰는 경우 `GichanFormant.iss`의 `MyBuildDir`와 맞출 것)
2. Inno Setup으로 `GichanFormant.iss` 컴파일  
   → 바탕화면 등에 `GichanFormant_v2.3.4.2_Setup.exe` 생성 (`MyAppVersion`과 일치)

> 참고: `.gitignore`에 `*.spec`이 있어 spec 파일은 레포에 없을 수 있습니다. CI와 동일하게 하려면 위 `pyinstaller` 한 줄 명령을 사용하세요.

---

## 릴리스 게시 (배포 레포)

1. **GichanFormantcode**: 버전 커밋 → `main` push → CI 녹색 확인 → Artifacts 또는 로컬 Windows 빌드물 준비
2. **GichanFormant** (배포용): [Releases → Draft new release](https://github.com/baggychani/GichanFormant/releases/new)
   - Tag: `v2.3.4.2` (`config.APP_VERSION`과 동일, 앞에 `v` 권장)
   - 제목/릴리스 노트 작성
   - 첨부:
     - Windows: `GichanFormant_v2.3.4.2_Setup.exe` (또는 zip)
     - macOS: arm64 / intel zip 각각
3. Publish 후, 구버전 앱에서 업데이트 알림이 뜨는지 확인

---

## .gitignore·불필요 파일 점검

이미 무시되는 항목: `.venv/`, `dist/`, `build/`, `__pycache__/`, `.pytest_cache/`, `logs/`, `*.spec`, `.idea/`, `.vscode/`

| 항목 | 권장 |
|------|------|
| `build_base.py` | 과거 리팩터용 일회성 스크립트. 배포에 불필요, 삭제해도 앱 실행에 영향 없음 |
| 루트 `icon.ico` | `assets/icon.ico`와 중복 가능 → 하나만 유지 |
| `docs/*.md` | 개발 메모. 배포물에 포함되지 않음 (PyInstaller 기본 설정 기준) |
| `compile_*.txt` | 빌드 로그, gitignore 대상 |

커밋 전: `git status`에 `.venv`, `dist`, `__pycache__`가 **staged 되지 않았는지** 확인.

---

## CI 요약 (`.github/workflows/ci.yml`)

- 트리거: `main` push, PR, 수동 `workflow_dispatch`
- 매트릭스: Windows x64, macOS Intel, macOS ARM64
- 테스트: `uv run python -m unittest discover tests` (로컬은 `pytest tests/` 동일 계열)

---

## 빠른 배포 순서 (요약)

1. 버전 체크리스트 반영 → `pytest` → 커밋·push (`GichanFormantcode`)
2. Actions에서 macOS zip + (선택) Windows는 로컬 exe/Setup
3. `GichanFormant`에 `vX.Y.Z.W` 태그 릴리스 + 바이너리 업로드
4. 이전 버전 설치본에서 업데이트 팝업 확인
