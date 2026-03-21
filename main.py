# main.py — 진입점

import sys
import platform
import os
import sentry_sdk
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QFont, QColor
from PySide6.QtCore import Qt

import config

# Sentry 초기화 (가장 먼저 실행하여 모든 오류를 포착)
sentry_sdk.init(
    dsn=config.SENTRY_DSN,
    send_default_pii=config.SENTRY_SEND_PII,
    environment=getattr(config, "SENTRY_ENV", "production"),
    release=config.APP_VERSION,
)


if __name__ == "__main__":
    # High-DPI 스케일링 설정
    # Qt6에서는 AA_EnableHighDpiScaling과 AA_UseHighDpiPixmaps가 기본 활성화되어 있으므로
    # 경고를 피하기 위해 명시적 setAttribute 호출을 제거하고 소수점 스케일링 정책만 설정합니다.
    if hasattr(Qt.HighDpiScaleFactorRoundingPolicy, "PassThrough"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)

    # 1. 스플래시 스크린 즉시 설정 (가장 최우선 순위로 실행하여 시각적 반응성 극대화)
    import os
    from PySide6.QtGui import QPixmap, QFont, QColor
    from PySide6.QtCore import Qt

    SPLASH_WIDTH = 450
    splash_path = os.path.join(config.ASSETS_DIR, "GichanFormant_SplashScreen.jpg")
    splash_pix = QPixmap(splash_path)

    # 스플래시 이미지 로드 실패 시 폴백 처리
    if splash_pix.isNull():
        splash_pix = QPixmap(SPLASH_WIDTH, int(SPLASH_WIDTH * 0.6))
        splash_pix.fill(QColor("#1976D2"))
        from PySide6.QtGui import QPainter

        painter = QPainter(splash_pix)
        painter.setPen(QColor("white"))
        font = QFont("Malgun Gothic", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            splash_pix.rect(), Qt.AlignmentFlag.AlignCenter, "GichanFormant\nLoading..."
        )
        painter.end()

    # DPI 대응 리사이징 (한 번만 수행)
    dpr = app.primaryScreen().devicePixelRatio()
    scaled_pix = splash_pix.scaledToWidth(
        int(SPLASH_WIDTH * dpr), Qt.TransformationMode.SmoothTransformation
    )
    scaled_pix.setDevicePixelRatio(dpr)

    class VersionSplashScreen(QSplashScreen):
        def __init__(self, pixmap, version):
            super().__init__(
                pixmap,
                Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint,
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setStyleSheet("background: transparent; border: none;")
            self.version = version
            self.version_font = QFont("Malgun Gothic", 9)

        def drawContents(self, painter):
            super().drawContents(painter)
            painter.setRenderHint(painter.RenderHint.Antialiasing)
            painter.setPen(QColor("white"))
            painter.setFont(self.version_font)
            painter.drawText(
                self.rect().adjusted(0, 10, -15, 0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
                self.version,
            )

    splash = VersionSplashScreen(scaled_pix, f"Version {config.APP_VERSION}")
    splash.show()
    app.processEvents()

    # 2. 스플래시가 뜬 '이후' 로깅 및 기타 설정 초기화
    from utils import logger_setup
    from utils import app_logger

    logger_setup.setup_logging()

    if platform.system() == "Windows":
        import ctypes

        try:
            myappid = "gichan.formant.app"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app.setApplicationName("GichanFormant")
    app.setApplicationVersion(config.APP_VERSION)
    app.setOrganizationName(config.AUTHOR)
    app.setOrganizationDomain("com.gichan.formant")

    # 스플래시가 뜬 직후 무거운 유틸리티 및 프리로더 로드
    from utils import icon_utils, path_prefs
    from utils.update_manager import UpdateManager
    from core import preloader
    from PySide6.QtCore import QStandardPaths

    # 앱 데이터 경로 및 업데이트 매니저 초기화
    app_data_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    update_manager = UpdateManager()

    # 업데이트 확인 성공 시 마지막 확인 시각 저장 콜백 설정
    def on_update_success(check_time_iso):
        try:
            prefs = path_prefs.load_path_prefs(app_data_dir)
            prefs["last_update_check"] = check_time_iso
            path_prefs.save_path_prefs(app_data_dir, prefs)
            app_logger.debug(f"[Startup] Update check time saved: {check_time_iso}")
        except Exception as e:
            app_logger.debug(f"[Startup] Failed to save update check time: {e}")

    update_manager.on_success_callback = on_update_success

    # 전역 앱 레벨에서 아이콘 적용
    try:
        app.setWindowIcon(icon_utils.get_app_icon())
    except Exception:
        pass

    app_logger.set_min_level_from_env()

    # 업데이트 정보를 담을 임시 저장소 (스코프 문제 방지를 위해 리스트 사용)
    pending_update_holder = []

    # 업데이트 발견 시 정보를 저장만 해두고 나중에 띄움
    def handle_update_signal(version, url, notes):
        pending_update_holder.clear()
        pending_update_holder.append((version, url, notes))
        app_logger.debug(f"[Update] New version {version} detected and queued.")

    def show_update_dialog_if_pending():
        if not pending_update_holder:
            return

        try:
            version, url, notes = pending_update_holder[0]
            from ui.dialogs.update_dialog import CustomUpdateDialog
            from PySide6.QtWidgets import QDialog
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl

            parent = controller.ui if hasattr(controller, "ui") else None
            dlg = CustomUpdateDialog(parent, version, url, notes)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                QDesktopServices.openUrl(QUrl(url))

        except Exception as e:
            from utils import app_logger

            app_logger.debug(f"[UpdateUI] Failed to show custom dialog: {e}")

    # 시그널 연결
    update_manager.update_available.connect(handle_update_signal)

    # 3. 라이브러리 및 엔진 사전 로딩 (스플래시 업데이트 포함)
    # 업데이트 확인 객체를 context에 담아 전달
    startup_context = preloader.warm_up(
        splash, context={"update_manager": update_manager}
    )
    startup_context["update_manager"] = update_manager

    # UI 로딩 상태를 스플래시에 중계하기 위한 콜백 함수
    def status_callback(msg):
        if splash:
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QColor

            splash.showMessage(
                msg,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                QColor("white"),
            )
            app.processEvents()

    # 4. 메인 컨트롤러 생성 및 실행 (사전 초기화된 객체 및 콜백 전달)
    from core.controller import MainController

    controller = MainController(
        startup_context=startup_context, status_callback=status_callback
    )

    # 메인 윈도우가 준비되면 창을 띄우고 스플래시 종료
    if hasattr(controller, "ui") and controller.ui:
        controller.ui.show()
        splash.finish(controller.ui)
        # 스플래시가 끝난 직후 (메인 창이 활성화된 상태) 알림창 띄움
        show_update_dialog_if_pending()
    else:
        splash.close()
        show_update_dialog_if_pending()

    sys.exit(app.exec())
