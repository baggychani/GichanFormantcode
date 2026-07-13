import subprocess
import sys


def test_application_modules_do_not_import_pyside_or_ui_packages():
    code = """
import sys
import core.application_events
import core.application_service
import core.application_state
import core.controller
import core.preview_renderer
import core.runtime_port
import core.view_port
import core.window_port
import core.workspace_state
leaked = sorted(
    name for name in sys.modules
    if name == 'PySide6' or name.startswith('PySide6.')
    or name == 'ui' or name.startswith('ui.')
)
if leaked:
    raise SystemExit('presentation imports leaked: ' + ', '.join(leaked))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
