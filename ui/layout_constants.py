# ui/layout_constants.py
"""
플롯 창·도크의 **가로 길이** 관련 상수만 모아 둔 파일입니다.
세로 높이·캔버스 크기·다이얼로그 크기 등은 config.py (PLOT_WINDOW_HEIGHT_PX, PLOT_CANVAS_SIZE_PX 등)에서 관리합니다.

목적:
- 도크 폭·구분선·캔버스 영역을 한 곳에서 관리해, 나중에 "레이어 도크 접기" 등 기능 추가 시
  창 가로를 "도크1 + 구분선 + 캔버스 + 구분선 + 도크2" 식으로 일관되게 계산할 수 있게 함.
- 모든 사이즈 관련 변수에는 단위(px)와 용도를 주석으로 명시합니다.
"""

# ---------------------------------------------------------------------------
# 도크(Dock) 폭
# ---------------------------------------------------------------------------
# DOCK_WIDTH: 도구 및 설정 도크, 레이어 설정 도크 각각의 가로 폭(px).
# 두 도크 모두 고정 폭으로 동일한 값 사용. 변경 시 popup_plot, compare_plot, layer_dock 내 setMinimumWidth/setMaximumWidth 등에서 공통 참조.
DOCK_WIDTH_PX = 260

# ---------------------------------------------------------------------------
# 구분선(Separator) 폭
# ---------------------------------------------------------------------------
# SEPARATOR_WIDTH_PX: 중앙 캔버스 영역과 좌/우 도크 사이에 그리는 세로 구분선의 가로 폭(px).
# popup_plot, compare_plot에서 sep_left, sep_right에 setFixedWidth로 적용.
SEPARATOR_WIDTH_PX = 3

# ---------------------------------------------------------------------------
# 도크·패널 레이아웃 여백 (px)
# ---------------------------------------------------------------------------
# 도크 내부 콘텐츠 좌우 상하 마진. design_panel, popup_plot, compare_plot 등에서 참조.
MARGIN_DOCK_CONTENTS = (12, 12, 12, 15)
# 좁은 여백 (버튼 그룹 등)
MARGIN_NARROW = (2, 2, 2, 2)

# ---------------------------------------------------------------------------
# 일반(단일) 플롯 창 가로
# ---------------------------------------------------------------------------
# 일반 플롯 창(popup_plot)은 좌측 도구 도크 + 좌 구분선 + 중앙(캔버스·여백) + 우 구분선 + 우측 레이어 도크 구성.
PLOT_CANVAS_AREA_WIDTH_PX = 700
# 도크 접기/플로팅 시 창 가로 보정치(px). PLOT_WINDOW_WIDTH_FLOATING_PX 계산에 사용.
PLOT_WIDTH_CORRECTION_PX = 50

PLOT_WINDOW_WIDTH_PX = (
    DOCK_WIDTH_PX * 2 + SEPARATOR_WIDTH_PX * 2 + PLOT_CANVAS_AREA_WIDTH_PX
)
# 도크가 하나 또는 둘 다 떼어져(플로팅) 있을 때 사용하는 창 가로(px).
# 식: 도크 1개 + 구분선 1개 + 캔버스 영역 + 보정치.
PLOT_WINDOW_WIDTH_FLOATING_PX = (
    DOCK_WIDTH_PX + SEPARATOR_WIDTH_PX + PLOT_CANVAS_AREA_WIDTH_PX + PLOT_WIDTH_CORRECTION_PX
)

# ---------------------------------------------------------------------------
# 비교(다중) 플롯 창 가로
# ---------------------------------------------------------------------------
COMPARE_CANVAS_AREA_WIDTH_PX = 700
COMPARE_WINDOW_WIDTH_PX = (
    DOCK_WIDTH_PX + SEPARATOR_WIDTH_PX * 2 + COMPARE_CANVAS_AREA_WIDTH_PX
)