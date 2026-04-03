# config.py
"""
GichanFormant 전역 설정 (Configuration)

- 프로그램 전체에서 공통으로 쓰는 상수·텍스트·기본값을 한 곳에서 관리합니다.
- 디자인 변경, 숫자/문구 수정 시 이 파일만 보면 되도록 하드코딩을 최소화합니다.
- compare_plot / popup_plot 등 동일 로직이 적용되는 UI 숫자는 여기서 정의하고
  각 모듈은 config를 import해 사용합니다.
"""

# =============================================================================
# 1. 프로그램 기본 정보 (App Info)
# =============================================================================
APP_VERSION = "2.3.4.1"
APP_TITLE = f"GichanFormant v{APP_VERSION}"
AUTHOR = "Bae Gichan"
COPYRIGHT_TEXT = f"Copyright © 2026 {AUTHOR}. All rights reserved."

# 경로 설정 (Path Config)
import sys
import os

# 앱이 PyInstaller로 묶여서 실행 중인지, 아니면 파이썬 소스로 실행 중인지 확인
if getattr(sys, "frozen", False):
    # .exe 파일로 실행 중일 때 (사용자 환경)
    # sys.executable은 GichanFormant.exe 파일 자체의 절대 경로를 의미합니다.
    ROOT_DIR = os.path.dirname(sys.executable)
    # --onedir 모드일 경우 내부 리소스 폴더 (_internal) 경로
    BASE_DIR = sys._MEIPASS
else:
    # 파이썬 스크립트로 실행 중일 때 (기찬 님의 개발 환경)
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = ROOT_DIR

ASSETS_DIR = os.path.join(BASE_DIR, "assets")

import platform

# 1번: 로그 저장 폴더를 AppData/Local로 변경 (권한 문제 해결)
# 윈도우 표준에 따라 %LOCALAPPDATA% 폴더를 사용합니다.
if platform.system() == "Windows":
    _default_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
elif platform.system() == "Darwin":  # macOS
    _default_appdata = os.path.expanduser("~/Library/Application Support")
else:  # Linux 등
    _default_appdata = os.path.expanduser("~")

LOGS_DIR = os.path.join(_default_appdata, "GichanFormant", "logs")

# Sentry 플래그 파일 경로는 반드시 ROOT_DIR(exe가 있는 곳)로 설정해야 인스톨러가 만든 파일을 찾을 수 있습니다.
SENTRY_FLAG_PATH = os.path.join(ROOT_DIR, "sentry_opt_in.config")


# =============================================================================
# 2. UI 공통 (창 크기, 폰트, 미리보기 캔버스)
# =============================================================================
# 메인 창·팝업 창 기본 크기 (ui/main_window.py, ui/popup_plot.py, ui/compare_plot.py)
WINDOW_SIZE_MAIN = "860x710"
WINDOW_MINSIZE_POPUP = (680, 500)

# 플롯 창(단일/다중) 공통: 세로 높이(px), 중앙 캔버스 한 변(px). 두 값 모두 compare_plot / popup_plot 동일.
PLOT_WINDOW_HEIGHT_PX = 660
PLOT_CANVAS_SIZE_PX = 650

# 플롯 창 내 탭 바: 탭 최소 가로(px). compare_plot / popup_plot 스타일시트에서 동일 사용.
TAB_BAR_MIN_WIDTH_PX = 115

# 플롯 창 중앙 영역(캔버스 컨테이너) 여백(px). compare_plot / popup_plot 동일.
CENTRAL_LAYOUT_MARGIN_PX = 10

# 도크와 캔버스 사이 구분선 스타일 시트용 색상 (compare_plot / popup_plot)
SEPARATOR_BG_COLOR = "#F5F7FA"

# UI 폰트 크기 (pt). 플롯 창·다이얼로그·패널 등에서 공통 참조
FONT_SIZE_SMALL = 9
FONT_SIZE_NORMAL = 10
FONT_SIZE_MEDIUM = 11
FONT_SIZE_TITLE = 12

# UI 색상 (Hex). 테두리·배경·텍스트 등 공통 참조
COLOR_BORDER = "#DCDFE6"
COLOR_BORDER_LIGHT = "#E4E7ED"
COLOR_BG_LIGHT = "#F5F7FA"
COLOR_TEXT_SECONDARY = "#606266"
COLOR_TEXT_PRIMARY = "#303133"

# 확장 추가된 주요 테마 색상
COLOR_PRIMARY_BLUE = "#1976D2"
COLOR_PRIMARY_RED = "#E64A19"
COLOR_ACTION_BLUE = "#409EFF"
COLOR_ACTION_HOVER_BG = "#ECF5FF"
COLOR_ACTION_HOVER_BORDER = "#C6E2FF"
COLOR_TAB_HOVER = "#EBEEF5"

# OS별 UI 기본 폰트 (플롯 창·다이얼로그 등에서 사용)
UI_FONT_WINDOWS = "Malgun Gothic"
UI_FONT_MAC = "AppleGothic"

# LIVE 미리보기 캔버스 크기·패딩 (메인 창 미리보기 영역)
PREVIEW_CFG = {
    "canvas_w": 290,
    "canvas_h": 150,
    "pad_x": 40,
    "pad_y": 25,
}


# =============================================================================
# 3. 다이얼로그 크기 (compare_plot / popup_plot 공통으로 참조)
# =============================================================================
# 비교 대상 선택 다이얼로그 (compare_plot.SelectCompareDialog)
DIALOG_SELECT_COMPARE_WIDTH_PX = 380
DIALOG_SELECT_COMPARE_HEIGHT_PX = 450

# 일괄 저장 설정 다이얼로그 (popup_plot.BatchSaveOptionsDialog)
DIALOG_BATCH_SAVE_WIDTH_PX = 440
DIALOG_BATCH_SAVE_HEIGHT_PX = 340

# 축 범위 입력 라인에디터 고정 폭(px). 일괄 저장 다이얼로그 등
RANGE_EDIT_FIXED_WIDTH_PX = 75


# =============================================================================
# 4. 플롯·분석 기본값 (Plot & Analysis Defaults)
# =============================================================================
# 신뢰 타원 기본 크기 (σ). plot_engine, controller, UI 초기값
DEFAULT_SIGMA = 2.0
# 앱 실행 시 최초 선택 플롯 타입
DEFAULT_PLOT_TYPE = "f1_f2"
# 기준점 기본값 (Praat 스타일)
DEFAULT_ORIGIN = "top_right"

# 자(Ruler) 도구: 스냅 거리(px), 삭제 제스처 거리(px). tools/ruler.py
RULER_SNAP_THRESHOLD_PX = 20
RULER_DELETE_THRESHOLD_PX = 40


# =============================================================================
# 5. 텍스트·설명 (Text & Descriptions)
# =============================================================================
# 메인 화면 플롯 타입 라디오 버튼 하단 설명 (ui/main_window.py)
PLOT_DESCS = {
    "f1_f2": ("F2 축:", "가장 표준적인 모음 사각도입니다."),
    "f1_f3": ("F3 축:", "R-coloring(Rhoticity) 등 F3가 중요한 언어 분석에 유용합니다."),
    "f1_f2_prime": (
        "F2' 축:",
        "F2와 F3를 통합하여 청각적 인지를 반영한 Effective F2 모델입니다.",
    ),
    "f1_f2_minus_f1": (
        "(F2-F1) 축:",
        "Ladefoged가 제안한 방식으로, 후설성을 청각적으로 더 정확히 반영합니다.",
    ),
    "f1_f2_prime_minus_f1": (
        "(F2'-F1) 축:",
        "모음의 스펙트럼 통합 효과를 고려하여 청각적 거리감을 극대화한 모델입니다.",
    ),
}


# =============================================================================
# 6. 축 범위(Range) 기본값 (Hz / Bark)
# =============================================================================
# plot_engine, controller, UI 범위 입력 초기값. 한 곳만 수정하면 전체 반영.
Y_BASE_HZ = {
    "y_min": 200,
    "y_max": 1000,
    "y_ticks": range(200, 1001, 200),
    "y_texts": [200, 400, 600, 800, 1000],
}

HZ_RANGES = {
    "f1_f2": {
        **Y_BASE_HZ,
        "x_min": 500,
        "x_max": 3500,
        "x_ticks": range(500, 3501, 500),
        "x_texts": [500, 1000, 2000, 3500],
    },
    "f1_f3": {
        **Y_BASE_HZ,
        "x_min": 1500,
        "x_max": 4500,
        "x_ticks": range(1500, 4501, 500),
        "x_texts": [1500, 3000, 4500],
    },
    "f1_f2_prime": {
        **Y_BASE_HZ,
        "x_min": 500,
        "x_max": 4000,
        "x_ticks": range(500, 4001, 500),
        "x_texts": [500, 1500, 2500, 3500],
    },
    "f1_f2_minus_f1": {
        **Y_BASE_HZ,
        "x_min": 0,
        "x_max": 3000,
        "x_ticks": range(0, 3001, 500),
        "x_texts": [0, 1000, 2000, 3000],
    },
    "f1_f2_prime_minus_f1": {
        **Y_BASE_HZ,
        "x_min": 0,
        "x_max": 3500,
        "x_ticks": range(0, 3501, 500),
        "x_texts": [0, 1000, 2000, 3000],
    },
}

Y_BASE_BARK = {
    "y_min": 2,
    "y_max": 9,
    "y_ticks": range(2, 10, 1),
    "y_texts": range(2, 10, 2),
}

BARK_RANGES = {
    "f1_f2": {
        **Y_BASE_BARK,
        "x_min": 4,
        "x_max": 16,
        "x_ticks": range(4, 17, 1),
        "x_texts": range(4, 17, 2),
    },
    "f1_f3": {
        **Y_BASE_BARK,
        "x_min": 12,
        "x_max": 19,
        "x_ticks": range(12, 20, 1),
        "x_texts": range(12, 20, 2),
    },
    "f1_f2_prime": {
        **Y_BASE_BARK,
        "x_min": 4,
        "x_max": 18,
        "x_ticks": range(4, 19, 1),
        "x_texts": range(4, 20, 2),
    },
    "f1_f2_minus_f1": {
        **Y_BASE_BARK,
        "x_min": 0,
        "x_max": 12,
        "x_ticks": range(0, 13, 1),
        "x_texts": range(0, 14, 2),
    },
    "f1_f2_prime_minus_f1": {
        **Y_BASE_BARK,
        "x_min": 0,
        "x_max": 14,
        "x_ticks": range(0, 15, 1),
        "x_texts": range(0, 16, 2),
    },
}


# =============================================================================
# 7. 파싱·검증 에러 메시지 (DataProcessor 등)
# =============================================================================
PARSE_ERR_COLUMNS_TOO_FEW = "F1/F2 열 개수가 부족합니다."
PARSE_ERR_F1_F2_INVALID = (
    "F1/F2가 모두 숫자가 아니거나 F1 < F2 조건을 만족하지 않습니다."
)
PARSE_ERR_EMPTY_RESULT = "데이터 파싱 결과가 비어 있습니다."


# =============================================================================
# 8. 로그 메시지 템플릿 (Log Messages)
# =============================================================================
# 사용: config.LOG_MSG["키"].format(변수명=값)
LOG_MSG = {
    "APP_START": "{app_title}이(가) 실행되었습니다. 데이터 파일을 드래그하거나 클릭하여 로드하세요.",
    "RESET_ALL": "[SYSTEM] 모든 데이터가 초기화되었습니다. 새로운 분석을 시작할 수 있습니다.",
    "RESET_UI": "[SYSTEM] 화면 설정 및 옵션이 기본값으로 복구되었습니다.",
    "FILE_LOAD_NEW_SUCCESS": "신규 파일 {success_count}개가 로드되었습니다. (총 {total_files}개)",
    "FILE_LOAD_FAILED_SUMMARY": "로드 실패: {fail_count}개의 파일에 데이터 오류가 있습니다. ({names})",
    "FILE_LOAD_FAILED_DEBUG": "[DEBUG] {name} 로드 실패 원인 예시: {msg}",
    "FILE_REMOVED": "파일이 리스트에서 제거되었습니다: {removed_name}",
    "FILE_ROW_DROPPED": "[INFO] {name}에서 데이터 조건을 만족하지 않아 일부 데이터 행이 제외되었습니다. (라벨별 누락: {detail})",
    "OUTLIER_OFF": "[INFO] 이상치 제거가 해제되었습니다.",
    "OUTLIER_REMOVED_SUMMARY": "총 {file_count}개 파일에서 {total_removed}개의 데이터 포인트가 이상치로 제거되었습니다.{detail}",
    "OUTLIER_NOT_REMOVED_MIN_LABELS": "[INFO] 이상치 제거가 수행되지 않았습니다. "
    "모음별 최소 5개 데이터가 있어야 이상치 제거가 가능합니다. (데이터 수 부족 라벨 예시: {detail})",
    "OUTLIER_NOT_REMOVED_NONE": "[INFO] 이상치 제거 기준을 적용했지만 제거된 데이터 포인트가 없습니다.",
    "PLOT_REFRESH_ERROR": "[ERROR] 플롯 창 갱신 중 오류가 발생했습니다: {e}",
    "PLOT_REFRESH_FAIL": "[ERROR] 플롯 갱신 실패: {e}",
    "FILE_LOAD_SUMMARY": "[SUCCESS] 총 {new_count}개의 파일이 로드되었습니다. (현재 총 {total_count}개)",
    "FILE_LOAD_ERROR": "[ERROR] {fail_count}개의 파일을 불러오지 못했습니다. (지원하지 않는 형식이거나 데이터 없음)",
    "PLOT_OPEN": "[INFO] {ptype} 플롯이 새 창으로 열렸습니다. (대상: {fname})",
    "PLOT_OPEN_DONE": "플롯 창 생성 완료: {fname}",
    "ANALYSIS_OPEN": "모음 상세 분석 창이 열렸습니다: {title_suffix}",
    "COMPARE_OPEN": "[INFO] 다중 플롯 비교 모드가 실행되었습니다. ({blue_name} vs {red_name})",
    "PLOT_UPDATE": "[INFO] 축 범위 및 신뢰 타원 설정이 업데이트되었습니다.",
    "PLOT_RANGE_INIT": "[INFO] 좌표축 범위 및 신뢰 타원이 초기화되었습니다.",
    "PLOT_RANGE_APPLIED": "[INFO] 좌표축 범위가 적용되었습니다.",
    "DESIGN_KEPT": "[INFO] 디자인 설정이 유지됩니다.",
    "DESIGN_UNKEPT": "[INFO] 디자인 설정 유지가 해제되었습니다.",
    "DESIGN_RESET": "[INFO] 디자인 설정이 초기화되었습니다.",
    "DESIGN_RESET_ALL": "[INFO] 디자인 설정이 전체 초기화되었습니다.",
    "LAYER_ORDER_RESET": "[INFO] 레이어 순서가 초기화되었습니다.",
    "LAYER_SETTINGS_RESET": "[INFO] 레이어 설정이 초기화되었습니다.",
    "SAVE_SINGLE": "[SUCCESS] 이미지가 저장되었습니다.\n▶ 파일: {fname}\n▶ 위치: {folder}",
    "SAVE_SINGLE_SHORT": "이미지가 저장되었습니다: {path}",
    "BATCH_START": "[SYSTEM] 일괄 저장 작업을 시작합니다... (총 {total}건, σ={sigma})",
    "BATCH_END": "[SUCCESS] 일괄 저장이 완료되었습니다. (성공: {success}건, 실패: {fail}건)\n▶ 위치: {folder}",
    "BATCH_SUCCESS": "일괄 저장 완료: {success_count}개의 이미지가 저장되었습니다.",
    "BATCH_ALL_FAILED": "일괄 저장 실패: {fail_count}개 파일 저장에 실패했습니다. 예시: {sample}",
    "BATCH_ALL_FAILED_BOX": "모든 이미지 저장에 실패했습니다. 로그를 확인하세요.",
    "RULER_ON": "[TOOL] 눈금자 측정 모드가 활성화되었습니다. 그래프 상의 두 점을 클릭하세요.",
    "RULER_OFF": "[TOOL] 눈금자 측정 모드가 종료되었습니다.",
    "RULER_OFF_INFO": "눈금자 툴이 꺼졌습니다.",
    "DRAW_ON": "[TOOL] 그리기 모드가 활성화되었습니다. 좌측 하단에서 선·영역·참조선을 선택하세요.",
    "DRAW_OFF_INFO": "그리기 모드가 꺼졌습니다.",
    "LABEL_MOVE_OFF": "라벨 위치 이동 모드가 꺼졌습니다.",
    "LABEL_MOVE_ON": "라벨 위치 이동 모드가 켜졌습니다. 옮길 라벨에 마우스를 올린 뒤 드래그하세요.",
    "LABEL_MOVE_SERIES": "라벨 위치 이동 대상이 변경되었습니다. ({series})",
    "LABEL_MOVE_ON_SERIES": "라벨 위치 이동 모드가 켜졌습니다. ({series} 데이터 라벨만 이동 가능)",
    "PLOT_OPEN_FAIL": "[오류] 다중 플롯 창 생성 실패: {e}",
    "PLOT_APPLY_FAIL": "[오류] 플롯 갱신 실패: {e}",
}

# =============================================================================
# 9. UI 옵션 리스트 (콤보박스/라디오 버튼용)
# =============================================================================
# 비교 다이얼로그용 정규화 목록
NORMALIZATION_OPTIONS = [
    ("없음", None),
    ("Lobanov", "Lobanov"),
    ("Gerstman", "Gerstman"),
    ("2mW/F", "2mW/F"),
    ("Bigham", "Bigham"),
    ("Nearey1", "Nearey1"),
]

# 팝업 창의 신뢰 타원 시그마 선택 항목
SIGMA_VALS = ["1.0", "2.0"]

# 메인 UI의 이상치 제거 옵션
OUTLIER_SIGMA_OPTIONS = [
    ("1σ (68.27%)", "1sigma"),
    ("2σ (95.45%)", "2sigma"),
]
# =============================================================================
# 10. Sentry 설정 (Error Tracking)
# =============================================================================
SENTRY_DSN = "https://a2dd8b24066388a79cdfad4db2bf76f0@o4511081333915648.ingest.us.sentry.io/4511081343221760"
# 배포 환경 설정 (production / development)
SENTRY_ENV = "production"
# IP 주소 등 개인 식별 정보 수집 여부 (보안을 위해 False 권장)
SENTRY_SEND_PII = False

# =============================================================================
# 11. 업데이트 및 외부 프로젝트 정보 (Update Config)
# =============================================================================
GITHUB_OWNER = "baggychani"
GITHUB_REPO = "GichanFormant"
GITHUB_RELEASE_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
GITHUB_API_LATEST_RELEASE = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
