# 수직 참조선 관련 Python 파일 목록

수직 참조선(F2 참조선) 버그/로직 상담 시 참고용.

## 직접 구현·이벤트 처리

| 경로 | 역할 |
|------|------|
| `draw/draw_reference.py` | DrawReferenceTool: 수직/수평 참조선 그리기, `_on_move`/`_on_click`/`_draw_preview`, `event.inaxes` 사용, F2 값 계산·표시 |

## 데이터·모드 정의

| 경로 | 역할 |
|------|------|
| `draw/draw_common.py` | `DrawMode.REF_V`, `ReferenceLineObject` (mode, value, axis_units 등) |

## UI·인디케이터

| 경로 | 역할 |
|------|------|
| `draw/indicator.py` | 그리기 모드 버튼 그룹, "수직 참조선" 버튼, `MODE_REF_V`, `mode_changed` 시그널 |

## 연동·호출

| 경로 | 역할 |
|------|------|
| `ui/popup_plot.py` | 그리기 토글, `_on_draw_mode_changed`에서 `DrawMode.REF_V` 시 `DrawReferenceTool` 생성·활성화, `_redraw_draw_layer`에서 참조선 재그림 |
| `ui/layer_dock.py` | 그리기 레이어 목록에서 참조선 표시명(`_draw_object_display_name`: "참조선 F2=...") |

## 기타

| 경로 | 역할 |
|------|------|
| `draw/__init__.py` | draw 패키지 export (필요 시 참조) |
| `ui/main_window.py` | 팝업/플롯 열기 등 (참조선 툴은 popup_plot에서만 사용) |

---

**요약**: 수직 참조선 동작/버그는 우선 **`draw/draw_reference.py`** (이벤트·축·값 계산)와 **`ui/popup_plot.py`** (툴 생성·axes 전달·재그리기)를 보면 됨.
