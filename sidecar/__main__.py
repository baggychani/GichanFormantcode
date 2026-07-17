"""python -m sidecar — NDJSON IPC host for Tauri or local supervisors."""

from __future__ import annotations

import argparse
import multiprocessing
import sys


def _configure_stdio_utf8() -> None:
    """Force UTF-8 NDJSON stdio even when the Windows locale is cp949.

    Tauri writes request lines as UTF-8 bytes. If Python decodes stdin with the
    process ANSI code page, Korean file paths become corrupted JSON and
    ``load_files`` never produces a matching response id.
    """
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="strict", newline="\n")
            except Exception:  # noqa: BLE001 - keep process alive on frozen stdio
                pass


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
    from sidecar.host import SidecarHost

    parser = argparse.ArgumentParser(description="GichanFormant analysis sidecar")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--headless",
        action="store_true",
        help="Run without a visible main window (default)",
    )
    mode.add_argument(
        "--desktop",
        action="store_true",
        help="Run a QApplication-backed host for legacy PySide plot windows",
    )
    args = parser.parse_args(argv)
    if args.desktop:
        from sidecar.desktop import run_desktop_sidecar

        return run_desktop_sidecar()

    host = SidecarHost.create_headless()
    try:
        return host.run()
    finally:
        host.close()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
