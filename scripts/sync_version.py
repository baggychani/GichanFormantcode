#!/usr/bin/env python3
"""config.APP_VERSION 기준으로 배포용 버전 문자열을 동기화합니다.

사용 예:
  uv run python scripts/sync_version.py              # config 기준으로 iss/info/… 갱신
  uv run python scripts/sync_version.py --check      # 불일치 시 종료 코드 1
  uv run python scripts/sync_version.py --set 2.3.4.3  # config + 전 파일 일괄 반영
  uv run python scripts/sync_version.py --from-tag v2.3.4.2
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.py"
ISS_PATH = ROOT / "GichanFormant.iss"
INFO_PATH = ROOT / "info.txt"
COMPLETE_PATH = ROOT / "complete.txt"
PYPROJECT_PATH = ROOT / "pyproject.toml"

_VERSION_RE = re.compile(r"^APP_VERSION\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)
_ISS_VERSION_RE = re.compile(r'(#define MyAppVersion ")[^"]+(")')
_PYPROJECT_VERSION_RE = re.compile(r'^(version\s*=\s*")[^"]+(")', re.MULTILINE)


def _fail(msg: str) -> None:
    print(f"sync_version: {msg}", file=sys.stderr)
    sys.exit(1)


def read_config_version() -> str:
    text = CONFIG_PATH.read_text(encoding="utf-8")
    m = _VERSION_RE.search(text)
    if not m:
        _fail(f"{CONFIG_PATH} 에서 APP_VERSION 을 찾을 수 없습니다.")
    return m.group(1)


def write_config_version(version: str) -> None:
    text = CONFIG_PATH.read_text(encoding="utf-8")
    if not _VERSION_RE.search(text):
        _fail(f"{CONFIG_PATH} 에 APP_VERSION 할당이 없습니다.")
    text = _VERSION_RE.sub(f'APP_VERSION = "{version}"', text, count=1)
    CONFIG_PATH.write_text(text, encoding="utf-8")


def parse_version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = version.strip().split(".")
    if not parts or not all(p.isdigit() for p in parts):
        _fail(f"버전 형식이 올바르지 않습니다: {version!r} (예: 2.3.4.2)")
    nums = [int(p) for p in parts]
    while len(nums) < 4:
        nums.append(0)
    if len(nums) > 4:
        _fail(f"버전은 최대 4자리까지 지원합니다: {version!r}")
    return nums[0], nums[1], nums[2], nums[3]


def render_info_txt(version: str) -> str:
    a, b, c, d = parse_version_tuple(version)
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({a}, {b}, {c}, {d}),
    prodvers=({a}, {b}, {c}, {d}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '041204b0',
        [StringStruct('CompanyName', 'Bae Gichan'),
        StringStruct('FileDescription', 'Formant Analysis Tool by Bae Gichan'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', 'GichanFormant'),
        StringStruct('LegalCopyright', 'Copyright (c) 2026 Bae Gichan. All rights reserved.'),
        StringStruct('OriginalFilename', 'GichanFormant.exe'),
        StringStruct('ProductName', 'GichanFormant'),
        StringStruct('ProductVersion', '{version}')])
      ]),
    VarFileInfo([VarStruct('Translation', [1042, 1200])])
  ]
)
"""


def read_iss_version() -> str:
    text = ISS_PATH.read_text(encoding="utf-8")
    m = re.search(r'#define MyAppVersion "([^"]+)"', text)
    if not m:
        _fail(f"{ISS_PATH} 에 #define MyAppVersion 을 찾을 수 없습니다.")
    return m.group(1)


def sync_iss(version: str) -> None:
    text = ISS_PATH.read_text(encoding="utf-8")
    if not _ISS_VERSION_RE.search(text):
        _fail(f"{ISS_PATH} 에 #define MyAppVersion 을 찾을 수 없습니다.")
    ISS_PATH.write_text(
        _ISS_VERSION_RE.sub(rf"\g<1>{version}\2", text), encoding="utf-8"
    )


def sync_info_txt(version: str) -> None:
    INFO_PATH.write_text(render_info_txt(version), encoding="utf-8")


_COMPLETE_HEAD_RE = re.compile(
    r"^GichanFormant v[\d.]+\s+설치가 성공적으로 완료되었습니다\.\s*$",
    re.MULTILINE,
)


def sync_complete_txt(version: str) -> None:
    head = f"GichanFormant v{version} 설치가 성공적으로 완료되었습니다."
    if COMPLETE_PATH.is_file():
        text = COMPLETE_PATH.read_text(encoding="utf-8")
        if _COMPLETE_HEAD_RE.search(text):
            text = _COMPLETE_HEAD_RE.sub(head, text, count=1)
        else:
            text = head + "\n\n" + text.lstrip()
        COMPLETE_PATH.write_text(text.rstrip() + "\n", encoding="utf-8")
    else:
        COMPLETE_PATH.write_text(head + "\n", encoding="utf-8")


def read_pyproject_version() -> str:
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    m = _PYPROJECT_VERSION_RE.search(text)
    if not m:
        _fail(f"{PYPROJECT_PATH} 에 version = 을 찾을 수 없습니다.")
    full = m.group(0)
    return full.split('"')[1]


def sync_pyproject(version: str) -> None:
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    if not _PYPROJECT_VERSION_RE.search(text):
        _fail(f"{PYPROJECT_PATH} 에 version = 을 찾을 수 없습니다.")
    PYPROJECT_PATH.write_text(
        _PYPROJECT_VERSION_RE.sub(rf"\g<1>{version}\2", text), encoding="utf-8"
    )


def collect_versions() -> dict[str, str]:
    return {
        "config.py": read_config_version(),
        "GichanFormant.iss": read_iss_version(),
        "info.txt": _read_info_version(),
        "complete.txt": _read_complete_version(),
        "pyproject.toml": read_pyproject_version(),
    }


def _read_info_version() -> str:
    text = INFO_PATH.read_text(encoding="utf-8")
    m = re.search(r"StringStruct\('FileVersion', '([^']+)'\)", text)
    if not m:
        _fail("info.txt 에서 FileVersion 을 찾을 수 없습니다.")
    return m.group(1)


def _read_complete_version() -> str:
    text = COMPLETE_PATH.read_text(encoding="utf-8")
    m = re.match(r"^GichanFormant v([\d.]+)\s+설치가", text)
    if not m:
        _fail("complete.txt 첫 줄에서 버전을 찾을 수 없습니다.")
    return m.group(1)


def sync_all(version: str) -> None:
    write_config_version(version)
    sync_iss(version)
    sync_info_txt(version)
    sync_complete_txt(version)
    sync_pyproject(version)
    print(
        f"sync_version: {version} → config, iss, info.txt, complete.txt, pyproject.toml"
    )


def check_all() -> None:
    versions = collect_versions()
    expected = versions["config.py"]
    bad = {k: v for k, v in versions.items() if v != expected}
    if bad:
        print("sync_version: 버전 불일치 (기준: config.APP_VERSION)", file=sys.stderr)
        for k, v in sorted(versions.items()):
            mark = "OK" if v == expected else "!!"
            print(f"  [{mark}] {k}: {v}", file=sys.stderr)
        sys.exit(1)
    print(f"sync_version: OK (모두 {expected})")


def normalize_tag(tag: str) -> str:
    t = tag.strip()
    if t.startswith("refs/tags/"):
        t = t.removeprefix("refs/tags/")
    if t.startswith("v") or t.startswith("V"):
        t = t[1:]
    return t


def main() -> None:
    parser = argparse.ArgumentParser(description="배포 버전 문자열 동기화")
    parser.add_argument(
        "--set",
        metavar="VERSION",
        help="config.APP_VERSION 및 iss/info/complete/pyproject 일괄 설정",
    )
    parser.add_argument(
        "--from-tag",
        metavar="TAG",
        help="태그 이름에서 버전 추출 후 --set 과 동일",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="config 기준으로 다른 파일 일치 여부만 검사",
    )
    args = parser.parse_args()

    if args.check:
        check_all()
        return

    if args.from_tag:
        sync_all(normalize_tag(args.from_tag))
        return

    if args.set:
        sync_all(args.set.strip())
        return

    # 기본: config → 나머지 파일 갱신
    version = read_config_version()
    sync_iss(version)
    sync_info_txt(version)
    sync_complete_txt(version)
    sync_pyproject(version)
    print(
        f"sync_version: config.APP_VERSION={version} → iss, info.txt, complete.txt, pyproject.toml"
    )


if __name__ == "__main__":
    main()
