# GichanFormant 빌드·배포 안내

## 버전은 `config.py` 한 곳만 수정

```text
config.py  →  APP_VERSION = "2.3.4.2"
```

그다음 동기화:

```powershell
uv run python scripts/sync_version.py
uv lock   # pyproject 버전 변경 시
uv run python scripts/sync_version.py --check
```

`scripts/sync_version.py`가 자동으로 갱신합니다.

| 대상 | 내용 |
|------|------|
| `GichanFormant.iss` | `#define MyAppVersion` |
| `info.txt` | Windows exe 버전 리소스 (전체 재생성) |
| `complete.txt` | 설치 완료 **첫 줄** 버전만 교체 (아래 안내 본문 유지) |
| `pyproject.toml` | `version` |

태그 릴리스 시 CI가 `--set`으로 맞추므로, **태그 push 전** 로컬에서도 위 스크립트를 한 번 돌려 두면 좋습니다.

---

## GitHub Actions (Windows·macOS 모두 클라우드 빌드)

로컬 PC에 Mac이 없어도 됩니다.

### CI (`ci.yml`) — `main` push / PR

- **테스트 + 버전 검사만** (약 1~2분, Ubuntu 1잡)
- PySide6용 Linux 시스템 라이브러리 설치 후 `pytest`
- **바이너리 빌드는 하지 않음** (push마다 Win+Mac 3대 빌드하던 것 제거 → Actions 실행 수 대폭 감소)

같은 브랜치에 연속 push하면 **진행 중인 이전 CI는 자동 취소**됩니다.

### Release (`release.yml`) — **권장 배포 경로**

**트리거**

1. **태그 push** (권장): `git tag v2.3.4.2` → `git push origin v2.3.4.2`
2. **수동**: Actions → **Release** → Run workflow  
   - `version` 비우면 `config.APP_VERSION` 사용  
   - `create_github_release`: GitHub Releases에 바이너리 업로드

**하는 일**

1. 버전 동기화 (`scripts/sync_version.py`)
2. 테스트
3. **Windows**: onedir 빌드 → **Inno Setup 설치 프로그램** + portable zip
4. **macOS**: arm64 / Intel 각각 `.app` zip
5. **배포 레포** [baggychani/GichanFormant](https://github.com/baggychani/GichanFormant) 에 GitHub Release·바이너리 자동 업로드 (설정 시)

| Artifacts / Release 파일 | 설명 |
|------------------------|------|
| `GichanFormant_vX.Y.Z.W_Setup.exe` | Windows 설치 프로그램 |
| `GichanFormant-windows-x64-portable-vX.Y.Z.W.zip` | Windows 압축 풀어 실행 |
| `GichanFormant-macos-arm64-vX.Y.Z.W.zip` | Apple Silicon |
| `GichanFormant-macos-intel-vX.Y.Z.W.zip` | Intel Mac |

태그 이름은 `v` + `APP_VERSION` (예: `v2.3.4.2`)과 맞추세요.  
앱 내 자동 업데이트(`config.GITHUB_*`)도 **GichanFormant** Releases를 봅니다.

### 배포 레포 자동 업로드 (코드 레포 ≠ 배포 레포)

| 레포 | 용도 |
|------|------|
| **GichanFormantcode** (비공개 권장) | 소스·CI·빌드 |
| **[baggychani/GichanFormant](https://github.com/baggychani/GichanFormant)** | 실행 파일만 공개·배포 |

기본 `GITHUB_TOKEN`은 **다른 레포에 Release를 만들 수 없습니다.**  
배포 레포 전용 **PAT**를 코드 레포 Secrets에 넣어야 합니다.

**1회 설정**

1. GitHub → **Settings** → **Developer settings** → **Fine-grained tokens** → Generate  
2. **Repository access**: Only **GichanFormant**  
3. **Permissions**: **Contents** → Read and write  
4. **GichanFormantcode** → Settings → Secrets and variables → Actions → **New secret**  
   - Name: `DEPLOY_REPO_TOKEN`  
   - Value: 위 PAT

**Release 실행 시**

- **Publish → baggychani/GichanFormant** job이 배포 레포에 `v2.3.4.2` + exe/zip 4개를 올립니다.  
- 코드 레포에도 올리려면 Run workflow 시 **「코드 레포에도 Release」** 체크 (기본 끔).

**다운로드**

- 사용자·업데이트: [GichanFormant Releases](https://github.com/baggychani/GichanFormant/releases)  
- 개발자 백업: Actions **Artifacts** (code 레포)

---

## 로컬 Windows 빌드 (선택)

```powershell
uv sync --locked --all-extras --dev
uv run python scripts/sync_version.py --check
uv run pyinstaller --noconfirm --windowed --icon=assets/icon.ico --name=GichanFormant --version-file=info.txt --collect-all PySide6 --add-data "assets;assets" main.py
```

Inno Setup (바탕화면 출력 기본):

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" "GichanFormant.iss"
```

CI와 동일 출력 경로:

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" "/DMyOutputDir=$PWD\release" "GichanFormant.iss"
```

---

## 배포 체크리스트

1. `config.py` `APP_VERSION` 수정  
2. `uv run python scripts/sync_version.py` → `--check`  
3. `uv run pytest tests/`  
4. 커밋·push `main`  
5. `git tag vX.Y.Z.W` && `git push origin vX.Y.Z.W`  
6. **Release** 워크플로 완료 확인  
7. (선택) **GichanFormant** 배포 레포에 동일 태그·바이너리 업로드  
8. 구버전에서 업데이트 알림 확인  

---

## macOS 아이콘

`resources/icon.icns` 또는 루트 `icon.icns`가 있으면 번들 아이콘에 반영할 수 있습니다 (현재는 `.ico`만 포함 가능).

---

## .gitignore

커밋하지 말 것: `.venv/`, `dist/`, `build/`, `release/`, `__pycache__/`, `.pytest_cache/`, `logs/`, `*.spec`

`build_base.py`는 개발용 일회성 스크립트로 배포에 불필요합니다.
