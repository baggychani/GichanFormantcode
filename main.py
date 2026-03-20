# main.py — 진입점

import sys
import platform
import os
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QFont, QColor
from PyQt6.QtCore import Qt

import config
import app_logger
from utils import icon_utils, logger_setup
from core import preloader

if __name__ == "__main__":
    # 백그라운드 로깅 시스템 초기화
    logger_setup.setup_logging()

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

    # 1. 스플래시 스크린 설정 (크기 조절 가능하도록 변수화)
    SPLASH_WIDTH = 450
    splash_path = os.path.join(config.ASSETS_DIR, "GichanFormant_SplashScreen.jpg")
    splash_pix = QPixmap(splash_path)

    # 스플래시 이미지 로드 실패 시 폴백 처리 (안정성 강화)
    if splash_pix.isNull():
        splash_pix = QPixmap(SPLASH_WIDTH, int(SPLASH_WIDTH * 0.6))
        splash_pix.fill(QColor("#1976D2"))  # 브랜드 컬러 계열
        from PyQt6.QtGui import QPainter

        painter = QPainter(splash_pix)
        painter.setPen(QColor("white"))
        font = QFont("Malgun Gothic", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            splash_pix.rect(), Qt.AlignmentFlag.AlignCenter, "GichanFormant\nLoading..."
        )
        painter.end()

    # DPI 대응 리사이징
    dpr = app.primaryScreen().devicePixelRatio()
    scaled_pix = splash_pix.scaledToWidth(
        int(SPLASH_WIDTH * dpr), Qt.TransformationMode.SmoothTransformation
    )
    scaled_pix.setDevicePixelRatio(dpr)

    # 커스텀 클래스로 버전 정보 상시 표시 및 테두리 제거 해결
    class VersionSplashScreen(QSplashScreen):
        def __init__(self, pixmap, version):
            # FramelessWindowHint와 함께 배경 투명화 속성을 부여하여 테두리/배경색 문제를 원천 봉쇄합니다.
            super().__init__(
                pixmap,
                Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint,
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setStyleSheet("background: transparent; border: none;")
            self.version = version
            self.version_font = QFont("Malgun Gothic", 9)

        def drawContents(self, painter):
            # 1. 기본 메시지(Ready... 등) 그리기
            super().drawContents(painter)
            # 2. 우측 상단에 버전 정보 겹쳐서 그리기 (강제로 흰색 펜 설정)
            painter.setRenderHint(painter.RenderHint.Antialiasing)
            painter.setPen(QColor("white"))
            painter.setFont(self.version_font)
            # 여백을 주어 우측 상단에 배치
            painter.drawText(
                self.rect().adjusted(0, 10, -15, 0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
                self.version,
            )

    splash = VersionSplashScreen(scaled_pix, f"Version {config.APP_VERSION}")

    # 2. 스플래시 표시
    splash.show()
    app.processEvents()

    # 전역 앱 레벨에서 아이콘 적용
    try:
        app.setWindowIcon(icon_utils.get_app_icon())
    except Exception:
        pass

    app_logger.set_min_level_from_env()

    # 3. 라이브러리 및 엔진 사전 로딩 (스플래시 업데이트 포함)
    startup_context = preloader.warm_up(splash)

    # UI 로딩 상태를 스플래시에 중계하기 위한 콜백 함수
    def status_callback(msg):
        if splash:
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QColor

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

    # 메인 윈도우가 준비되면 스플래시 종료
    if hasattr(controller, "ui") and controller.ui:
        splash.finish(controller.ui)
    else:
        splash.close()

    sys.exit(app.exec())
