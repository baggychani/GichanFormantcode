# desktop_main.py — Tauri/React 마이그레이션 UI 진입점
#
# 현재 배포 기본 실행은 아직 main.py(PySide)입니다.
# 이 파일은 desktop/ React+Tauri 셸을 실행하며, 컷오버를 위한 마이그레이션 경로입니다.

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DESKTOP = ROOT / "desktop"


def _die(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def _require_cmd(name: str) -> str:
    path = shutil.which(name)
    if not path:
        _die(
            f"'{name}' 를 찾을 수 없습니다.\n"
            f"Node.js/npm이 설치되어 있는지 확인한 뒤 다시 실행하세요."
        )
    return path


def _ensure_dependencies(npm: str) -> None:
    if (DESKTOP / "node_modules").is_dir():
        return
    print("desktop/node_modules 가 없어 npm install 을 실행합니다…")
    result = subprocess.run([npm, "install"], cwd=DESKTOP, check=False)
    if result.returncode != 0:
        _die("npm install 실패. desktop/ 에서 수동으로 npm install 후 다시 시도하세요.")


def main() -> int:
    if not DESKTOP.is_dir():
        _die(f"desktop/ 폴더가 없습니다: {DESKTOP}")

    npm = _require_cmd("npm")
    _require_cmd("cargo")  # Tauri 네이티브 빌드에 필요
    _ensure_dependencies(npm)

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    # Keep uv's cache inside the project. A broken/shared user cache can make
    # the development sidecar fail before it can answer IPC requests.
    env.setdefault("UV_CACHE_DIR", str(ROOT / ".uv-cache"))

    print("GichanFormant Tauri/React 마이그레이션 UI를 시작합니다.")
    print(f"  경로: {DESKTOP}")
    print("  현재 배포 기본 실행은 계속 `uv run main.py` (PySide) 입니다.\n")

    # npm.cmd on Windows needs shell=False with full path; use npm run
    completed = subprocess.run(
        [npm, "run", "tauri:dev"],
        cwd=DESKTOP,
        env=env,
        check=False,
    )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
