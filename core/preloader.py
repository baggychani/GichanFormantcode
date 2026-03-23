# core/preloader.py
"""
앱 시작 시 무거운 라이브러리를 미리 로드하여 런타임 성능을 최적화합니다.
"""

import time
import importlib

# 1. 중량급 라이브러리 목록 (지연 로딩의 주범들)
HEAVY_LIBS = [
    "pandas",
    "numpy",
    "matplotlib.pyplot",
    "matplotlib.font_manager",
    "scipy.stats",
]


def warm_up(splash=None, context=None):
    """
    무거운 라이브러리를 미리 임포트하고 Matplotlib 등의 설정을 초기화합니다.
    리소스 체크, 시스템 정보 로깅, 로그 정리 등의 시작 작업을 병행합니다.
    """
    import os
    import sys
    import platform
    import datetime
    import config
    from utils import app_logger
    from PySide6.QtWidgets import QApplication

    if context is None:
        context = {}

    # 기본 컨텍스트 필드 보충 (기존 값 유지)
    defaults = {
        "data_processor": None,
        "plot_engine": None,
        "live_preview_fig": None,
        "path_prefs": None,
    }
    for k, v in defaults.items():
        if k not in context:
            context[k] = v

    def _update_msg(msg):
        if splash:
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QColor

            splash.showMessage(
                msg,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                QColor("white"),
            )
            QApplication.processEvents()
            time.sleep(0.01)  # UX 가독성을 위한 최소한의 지연

    # 1. 시스템 정보 기록 및 리소스 체크
    _update_msg("Taking a holiday before starting...")
    time.sleep(0.6)  # 이스터에그를 읽을 수 있도록 살짝 지연

    _update_msg("Checking System Environment...")
    try:
        # 시스템 정보 수집 (디버깅 지원)
        ver = sys.version.split("(")[0].strip()
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        app_logger.debug(f"[Startup] Python: {ver}")
        app_logger.debug(f"[Startup] OS: {os_info}")

        # 화면 해상도 정보 (DPI 관련 이슈 추적용)
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            dpr = screen.devicePixelRatio()
            app_logger.debug(
                f"[Startup] Display: {geom.width()}x{geom.height()} (DPR: {dpr})"
            )
    except Exception as e:
        app_logger.debug(f"[Startup] Failed to log system info: {e}")

    # 2. 핵심 리소스 확인
    _update_msg("Verifying App Resources...")
    important_files = [
        os.path.join(config.ASSETS_DIR, "GichanFormant_SplashScreen.jpg"),
        os.path.join(config.ROOT_DIR, "icon.ico"),
    ]
    for f in important_files:
        if not os.path.exists(f):
            app_logger.warning(f"[Startup] Missing resource: {f}")

    # 2.5 업데이트 확인 (영어로 메시지 표시, 비동기 호출)
    if context and "update_manager" in context and context["update_manager"]:
        _update_msg("Checking for updates...")
        try:
            from PySide6.QtCore import QStandardPaths

            app_data_dir = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
            from utils import path_prefs

            prefs = path_prefs.load_path_prefs(app_data_dir)
            context["path_prefs"] = prefs

            context["update_manager"].check_for_updates(
                config.APP_VERSION, prefs.get("last_update_check")
            )
        except Exception as e:
            app_logger.debug(f"[Startup] Update check trigger failed: {e}")

    # 3. 오래된 로그 정리 (7일 이상 경과)
    _update_msg("Cleaning Up Old Logs...")
    try:
        from utils import logger_setup
        log_dir = logger_setup.get_log_dir()
        if os.path.isdir(log_dir):
            now = datetime.datetime.now()
            retention_days = 7
            for filename in os.listdir(log_dir):
                file_path = os.path.join(log_dir, filename)
                if os.path.isfile(file_path) and filename.endswith(".log"):
                    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    if (now - mtime).days > retention_days:
                        os.remove(file_path)
                        app_logger.debug(f"[Startup] Removed old log: {filename}")
    except Exception as e:
        app_logger.debug(f"[Startup] Log cleanup failed: {e}")

    # 4. 라이브러리 병렬 임포트 (ThreadPoolExecutor 활용)
    _update_msg("Optimizing Library Loading...")
    import concurrent.futures

    def load_lib(lib_name):
        try:
            if lib_name not in sys.modules:
                importlib.import_module(lib_name)
                return True, lib_name
            return True, lib_name
        except Exception as e:
            return False, f"{lib_name}: {e}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(HEAVY_LIBS)) as executor:
        futures = {executor.submit(load_lib, lib): lib for lib in HEAVY_LIBS}

        for future in concurrent.futures.as_completed(futures):
            lib_name = futures[future]
            try:
                success, result = future.result()
                if success:
                    app_logger.debug(f"[Startup] Loaded {result}")
                    _update_msg(f"Loaded {result}...")
                else:
                    app_logger.error(f"[Startup] Failed to load {result}")
            except Exception as e:
                app_logger.error(f"[Startup] Future exception for {lib_name}: {e}")

    # 5. Matplotlib 백엔드 및 폰트 워밍업
    _update_msg("Initializing Graphics Engine...")
    try:
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        from matplotlib.figure import Figure

        # 5-1. 메인 컨트롤러에서 사용할 Figure 미리 생성 및 워밍업
        _update_msg("Warming up Graphics Canvas...")
        fig = Figure(figsize=(6.5, 6.5), dpi=150)
        fig.add_subplot(111).set_axis_off()
        context["live_preview_fig"] = fig

        # 5-2. 폰트 매니저 워밍업
        _update_msg("Scanning System Fonts...")
        fm.fontManager.get_default_weight()

        # 5-3. 기본 스타일 설정
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["axes.unicode_minus"] = False

    except Exception as e:
        app_logger.error(f"Failed to warm up matplotlib: {e}")

    # 6. 기타 핵심 모듈 사전 로드
    _update_msg("Loading Core Engines...")
    try:
        from engine.plot_engine import PlotEngine

        context["plot_engine"] = PlotEngine()
    except Exception as e:
        app_logger.error(f"Failed to pre-load core modules: {e}")

    _update_msg("System Ready")
    time.sleep(0.05)
    return context
