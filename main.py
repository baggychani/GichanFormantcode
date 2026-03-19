# main.py — 진입점

import sys
import platform
from PyQt6.QtWidgets import QApplication

import config
import app_logger
from utils import icon_utils
from core.controller import MainController

if __name__ == "__main__":
    # Windows 작업표시줄 아이콘 버그 해결을 위한 AppUserModelID 설정
    if platform.system() == "Windows":
        import ctypes

        try:
            myappid = "gichan.formant.app"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("GichanFormant")
    app.setApplicationVersion(config.APP_VERSION)
    app.setOrganizationName(config.AUTHOR)
    app.setOrganizationDomain("com.gichan.formant")

    # 전역 앱 레벨에서 아이콘 적용
    try:
        app.setWindowIcon(icon_utils.get_app_icon())
    except Exception:
        pass

    app_logger.set_min_level_from_env()
    controller = MainController()
    sys.exit(app.exec())
