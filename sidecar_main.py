"""PyInstaller entry point for the Tauri analysis sidecar."""

from __future__ import annotations

from sidecar.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
