# utils/logger_setup.py
"""
Python 표준 logging 모듈을 사용한 백그라운드 전역 로깅 설정.
- 콘솔 출력 및 파일 출력(TimedRotatingFileHandler)을 담당합니다.
- GUI 로그창과는 별개로 동작하며, 상세한 디버그 정보를 날짜별로 기록합니다.
"""

import logging
import os
import platform
from logging.handlers import TimedRotatingFileHandler


def setup_logging(log_dir=None):
    """
    애플리케이션 전역 로거를 초기화합니다.
    - log_dir이 제공되지 않으면 Windows에서는 AppData\Local\GichanFormant\logs를 사용합니다.
    Returns: logging.Logger
    """
    if log_dir is None:
        if platform.system() == "Windows":
            local_app_data = os.environ.get("LOCALAPPDATA")
            if local_app_data:
                log_dir = os.path.join(local_app_data, "GichanFormant", "logs")
            else:
                log_dir = "logs"
        else:
            log_dir = "logs"

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    logger = logging.getLogger("GichanFormant")

    # 중복 핸들러 방지
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    # 백그라운드용 상세 포맷: [시간] [레벨] [모듈] 메시지
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)8s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. 파일 핸들러 (TimedRotatingFileHandler: 일 단위, 7일 보관)
    file_handler = TimedRotatingFileHandler(
        log_file, when="D", interval=1, backupCount=7, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # 2. 콘솔 핸들러 (터미널 출력용 - 개발 및 디버그 기록 포함)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    return logger
