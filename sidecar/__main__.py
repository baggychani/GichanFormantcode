"""python -m sidecar — NDJSON IPC host for Tauri or local supervisors."""

from __future__ import annotations

import argparse
import sys

from sidecar.host import SidecarHost


def main(argv: list[str] | None = None) -> int:
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
    sys.exit(main())
