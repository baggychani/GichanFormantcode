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


def get_log_dir():
    """
    애플리케이션이 로그를 저장할 안전한 디렉터리 경로를 반환합니다.
    - Windows: %LOCALAPPDATA%\GichanFormant\logs
    - macOS: ~/Library/Application Support/GichanFormant/logs
    - Linux: ~/.config/GichanFormant/logs
    """
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    elif system == "Darwin":  # macOS
        base = os.path.expanduser("~/Library/Application Support")
    else:  # Linux 등
        base = os.path.expanduser("~")

    return os.path.join(base, "GichanFormant", "logs")


def setup_logging(log_dir=None):
    """
    애플리케이션 전역 로거를 초기화합니다.
    - log_dir이 제공되지 않으면 get_log_dir()을 통해 안전한 경로를 사용합니다.
    - 폴더 생성 실패 시에도 크래시 없이 콘솔 로깅을 유지합니다.
    Returns: logging.Logger
    """
    if log_dir is None:
        log_dir = get_log_dir()

    logger = logging.getLogger("GichanFormant")

    # 중복 핸들러 방지
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    # 포맷터 설정
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)8s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. 콘솔 핸들러 (항상 안전함)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    # 2. 파일 핸들러 (폴더 생성 성공 시에만 추가하여 시한폭탄 제거)
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")

        file_handler = TimedRotatingFileHandler(
            log_file, when="D", interval=1, backupCount=7, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except Exception as e:
        # 폴더 생성이 실패하거나 다른 이유로 파일 쓰기가 안 되면, 콘솔 에러만 찍고 실행은 보장
        print(f"[Critical] Failed to initialize file logging: {e}")

    return logger
