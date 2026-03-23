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
    - Windows: AppData\Local\GichanFormant\logs
    - 기타: 현재 작업 디렉터리의 logs
    """
    if platform.system() == "Windows":
        # Windows의 경우 권한이 보장된 로컬 앱 데이터 폴더 사용
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return os.path.join(local_app_data, "GichanFormant", "logs")
        else:
            # 최악의 경우 절대 경로로 현재 폴더의 logs
            return os.path.join(os.getcwd(), "logs")
    else:
        # 타 OS는 현재 폴더 logs 사용
        return os.path.join(os.getcwd(), "logs")


def setup_logging(log_dir=None):
    """
    애플리케이션 전역 로거를 초기화합니다.
    - log_dir이 제공되지 않으면 get_log_dir()을 통해 안전한 경로를 사용합니다.
    Returns: logging.Logger
    """
    # 1. 로그 디렉터리 결정
    if log_dir is None:
        log_dir = get_log_dir()

    # 2. 디렉터리 생성 (하드코딩된 'logs' 제거하고 넘겨받은 log_dir 사용)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    logger = logging.getLogger("GichanFormant")

    # 중복 핸들러 방지
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    # 3. 포맷터 설정
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)8s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 4. 파일 핸들러 (TimedRotatingFileHandler)
    file_handler = TimedRotatingFileHandler(
        log_file, when="D", interval=1, backupCount=7, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # 5. 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    return logger
