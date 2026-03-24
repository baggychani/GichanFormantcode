# app_logger.py
"""
로그 채널 추상화 및 레벨 분리.
- info / warning / error: 사용자용 메시지 → GUI + (설정에 따라) 콘솔/파일
- debug: 개발용 상세 → 콘솔/파일만, GUI 제외
- [Dual-Layer]: 내부적으로 표준 logging 모듈을 호출하여 백그라운드 기록을 병행합니다.
"""

import os
import logging

# 레벨 상수 (숫자가 클수록 심각)
DEBUG = 0
INFO = 1
WARNING = 2
ERROR = 3

_ui = None
_console = False
# 콘솔에 기록할 최소 레벨 (이 레벨 이상만 기록). 기본 DEBUG (터미널용)
_min_level = DEBUG
# GUI에 기록할 최소 레벨. DEBUG는 GUI에 안 넣음
_gui_min_level = INFO

# 백그라운드용 표준 로거 인스턴스
_logger = logging.getLogger("GichanFormant")


def set_ui(ui):
    """메인 창 UI(append_log 메서드 보유)를 등록합니다. 로그는 해당 위젯에 출력됩니다."""
    global _ui
    _ui = ui


def set_console(enabled):
    """True면 로그 시 콘솔(print)에도 출력합니다."""
    global _console
    _console = bool(enabled)


def set_min_level(level):
    """콘솔/파일에 기록할 최소 레벨을 설정합니다. DEBUG면 debug 메시지도 기록."""
    global _min_level
    _min_level = int(level)


def set_min_level_from_env():
    """환경변수 LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)이 있으면 _min_level을 설정합니다."""
    raw = os.environ.get("LOG_LEVEL", "").strip().upper()
    if raw == "DEBUG":
        set_min_level(DEBUG)
    elif raw == "WARNING":
        set_min_level(WARNING)
    elif raw == "ERROR":
        set_min_level(ERROR)
    # INFO 또는 비어 있으면 기본값 유지


def _write(msg, level):
    if not msg:
        return

    # 1. [Dual-Layer] 백그라운드 표준 로깅 연동
    # app_logger 레벨을 logging 모듈 레벨로 매핑
    lvl_map = {DEBUG: 10, INFO: 20, WARNING: 30, ERROR: 40}
    _logger.log(lvl_map.get(level, 20), msg)

    # 2. [GUI/기존 로직] 기존 출력 방식 유지 (포맷 100% 동일 보장)
    # GUI: INFO 이상만
    if level >= _gui_min_level and _ui is not None and hasattr(_ui, "append_log"):
        try:
            _ui.append_log(msg)
        except Exception:
            pass
    # 콘솔: _min_level 이상만
    if level < _min_level:
        return
    if _console:
        try:
            print(msg, end="" if msg.endswith("\n") else "\n")
        except Exception:
            pass


def debug(msg):
    """개발/디버깅용 상세. 콘솔·파일에만 기록하고 GUI에는 넣지 않음."""
    _write(msg, DEBUG)


def info(msg):
    """사용자용 요약·상태. GUI + (설정 시) 콘솔/파일."""
    _write(msg, INFO)


def warning(msg):
    """경고. GUI + 콘솔/파일."""
    _write(msg, WARNING)


def error(msg):
    """오류. GUI + 콘솔/파일."""
    _write(msg, ERROR)


def log(msg):
    """
    호환용. info(msg)와 동일하게 동작합니다.
    로그 한 줄을 등록된 채널(UI, 파일, 콘솔)에 기록합니다.
    """
    info(msg)
