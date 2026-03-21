# tool_label_move.py
# 라벨 위치 이동: 호버 시 라벨 글자 bbox에 네모 테두리 + 십자 커서, 클릭 후 드래그로 실시간 이동.

import logging
import numpy as np
from PySide6.QtCore import Qt
import matplotlib.patches as mpatches

_log = logging.getLogger(__name__)


class LabelMoveTool:
    """단일/다중 플롯에서 개별 라벨을 centroid 기준 픽셀 반경 안에서 수동 이동."""

    def __init__(self):
        self.active = False
        self.canvas = None
        self.ax = None
        self.label_data = []
        self.max_radius_px = 50

        self.cid_press = None
        self.cid_motion = None
        self.cid_release = None

        self.dragging = None
        self._pick_radius_px = 18
        self.hovered_label = None
        self.highlight_rect = None
        self.highlight_color = "#E6A23C"
        self.cursor_changed = False

        self.drag_preview_text = None
        self.label_text_artists = []

        self.on_offset_saved = None
        self.on_offset_cleared = None

        # Ghost(유령화) 복구를 위한 상태 저장 변수
        self._dragged_original_artist = None
        self._dragged_original_alpha = 1.0

    @staticmethod
    def _safe_remove_artist(artist, name="artist"):
        """Artist를 축에서 제거. 실패 시 로그만 남기고 참조는 호출처에서 정리 (유령 객체 방지)."""
        if artist is None:
            return
        try:
            artist.remove()
        except Exception as e:
            _log.warning("LabelMoveTool %s remove failed: %s", name, e)

    def set_highlight_color(self, color):
        """다중 플롯: 네모 테두리/강조 색을 해당 파일 신뢰타원 선 색으로 설정."""
        if color and str(color).lower() != "transparent":
            self.highlight_color = color
        else:
            self.highlight_color = "#E6A23C"

    def set_context(
        self, canvas, ax, label_data, highlight_color=None, label_text_artists=None
    ):
        self.canvas = canvas
        self.ax = ax
        self.label_data = label_data if label_data else []
        self.label_text_artists = label_text_artists if label_text_artists else []
        if highlight_color is not None:
            self.set_highlight_color(highlight_color)
        else:
            self.highlight_color = "#E6A23C"
        self._clear_highlight()
        self._remove_drag_preview()
        if self.cursor_changed and self.canvas:
            self.canvas.unsetCursor()
            self.cursor_changed = False

    def _get_artist_for_label(self, lb):
        """주어진 라벨 데이터(lb)에 해당하는 실제 Text 아티스트 객체를 찾아 반환합니다."""
        if not self.label_text_artists or not self.label_data:
            return None
        lx, ly = lb.get("lx"), lb.get("ly")
        v = lb.get("vowel")
        for i, candidate in enumerate(self.label_data):
            if (
                candidate.get("vowel") == v
                and abs((candidate.get("lx") or 0) - (lx or 0)) < 1e-9
                and abs((candidate.get("ly") or 0) - (ly or 0)) < 1e-9
            ):
                if i < len(self.label_text_artists):
                    return self.label_text_artists[i]
        return None

    def _clear_highlight_rect(self):
        """강조 사각형만 제거 (호버 대상은 유지)."""
        if self.highlight_rect and self.ax:
            self._safe_remove_artist(self.highlight_rect, "highlight_rect")
            self.highlight_rect = None
        if self.canvas:
            self.canvas.draw_idle()

    def _draw_highlight(self, lb):
        """라벨 글자를 정확히 감싸는 네모 테두리. (Matplotlib 렌더러 기반 Bbox 계산)"""
        self._clear_highlight_rect()
        if not self.ax or not lb:
            return

        artist = self._get_artist_for_label(lb)
        if not artist:
            return
        if not self.canvas or not getattr(self.canvas, "renderer", None):
            return

        try:
            # 1. 렌더러를 통해 실제 글자가 화면에 그려진 정확한 Bbox(디스플레이 좌표)를 가져옵니다.
            bbox = artist.get_window_extent(self.canvas.renderer)

            # 2. 디스플레이 좌표를 현재 데이터 좌표계(축 반전 포함)로 완벽히 역변환합니다.
            bbox_data = bbox.transformed(self.ax.transData.inverted())

            # 3. 데이터 좌표계의 min/max를 구해 닫힌 사각형을 구성합니다. (Road 현상 원천 차단)
            x0, x1 = min(bbox_data.x0, bbox_data.x1), max(bbox_data.x0, bbox_data.x1)
            y0, y1 = min(bbox_data.y0, bbox_data.y1), max(bbox_data.y0, bbox_data.y1)
            w, h = x1 - x0, y1 - y0

            # 여백(Padding)을 조금 줍니다.
            pad_x, pad_y = w * 0.1, h * 0.1

            self.highlight_rect = mpatches.Rectangle(
                (x0 - pad_x, y0 - pad_y),
                w + 2 * pad_x,
                h + 2 * pad_y,
                linewidth=2,
                edgecolor=self.highlight_color,
                facecolor="none",
                alpha=0.9,
                zorder=100,
                clip_on=False,
            )
            self.ax.add_patch(self.highlight_rect)
            if self.canvas:
                self.canvas.draw_idle()
        except Exception:
            pass

    def _clear_highlight(self):
        """강조 사각형 제거 및 호버 대상 초기화."""
        self._clear_highlight_rect()
        self.hovered_label = None

    def _remove_drag_preview(self):
        """드래그 프리뷰(텍스트)를 제거하고, 유령화된 원본 텍스트를 원래대로 복구합니다."""
        # 1. 유령화(Ghost) 복구
        if self._dragged_original_artist:
            try:
                self._dragged_original_artist.set_alpha(self._dragged_original_alpha)
            except Exception:
                pass
            self._dragged_original_artist = None

        # 2. 따라다니던 프리뷰 텍스트 삭제
        if self.drag_preview_text and self.ax:
            self._safe_remove_artist(self.drag_preview_text, "drag_preview_text")
            self.drag_preview_text = None

        if self.canvas:
            self.canvas.draw_idle()

    def _create_drag_preview(self, lb):
        """드래그 중: 하얀 가리개를 폐지하고 원본을 유령화(투명도 0.2) 시킨 뒤 이동 텍스트를 띄웁니다."""
        self._remove_drag_preview()
        if not self.ax or not lb:
            return

        artist = self._get_artist_for_label(lb)
        if artist:
            # 상태 저장 후 원본 텍스트 유령화(Ghost)
            self._dragged_original_artist = artist
            self._dragged_original_alpha = artist.get_alpha()
            artist.set_alpha(0.2)

        lx, ly = lb["lx"], lb["ly"]

        kw = {
            "fontsize": int(lb.get("fontsize", 14))
            if lb.get("fontsize") is not None
            else 14,
            "fontweight": "bold" if lb.get("lbl_bold", True) else "normal",
            "fontstyle": "italic" if lb.get("lbl_italic", False) else "normal",
            "color": lb.get("lbl_color", "#E64A19"),
            "ha": lb.get("ha", "left"),
            "va": lb.get("va", "bottom"),
            "zorder": 200,  # 드래그 중인 텍스트는 무조건 맨 위로
            "clip_on": False,
        }

        self.drag_preview_text = self.ax.text(lx, ly, lb.get("vowel", "?"), **kw)

        # 원본 라벨에 있던 속성(테두리, 폰트 패밀리)을 프리뷰에도 복사
        if artist:
            # 1. 폰트 종류(세리프/산세리프 및 다국어 폰트) 복사 추가!
            self.drag_preview_text.set_fontfamily(artist.get_fontfamily())

            # 2. 흰색 테두리(PathEffect) 복사
            if artist.get_path_effects():
                self.drag_preview_text.set_path_effects(artist.get_path_effects())

        if self.canvas:
            self.canvas.draw_idle()

    def _update_drag_preview_position(self, lx, ly):
        if self.drag_preview_text:
            self.drag_preview_text.set_position((lx, ly))
            if self.canvas:
                self.canvas.draw_idle()

    def _find_label_at_px(self, x_px, y_px):
        """클릭 위치에서 라벨 픽: bbox 기반 hit 우선, 불가 시 (lx,ly) 거리로 폴백."""
        if not self.label_data or not self.ax:
            return None
        pad_px = 3
        try:
            # 1) bbox 기반: label_text_artists가 있으면 픽셀 bbox 안에 들어오는지 검사
            if (
                self.label_text_artists
                and self.canvas
                and getattr(self.canvas, "renderer", None)
            ):
                renderer = self.canvas.renderer
                for i, artist in enumerate(self.label_text_artists):
                    if i >= len(self.label_data):
                        break
                    try:
                        bbox = artist.get_window_extent(renderer)
                        # display 좌표: (x0,y0)~(x1,y1), 패딩 적용
                        x0, x1 = (
                            min(bbox.x0, bbox.x1) - pad_px,
                            max(bbox.x0, bbox.x1) + pad_px,
                        )
                        y0, y1 = (
                            min(bbox.y0, bbox.y1) - pad_px,
                            max(bbox.y0, bbox.y1) + pad_px,
                        )
                        if x0 <= x_px <= x1 and y0 <= y_px <= y1:
                            return self.label_data[i]
                    except Exception:
                        continue
            # 2) 폴백: (lx, ly) 한 점과의 거리
            xy_data = np.array([[lb["lx"], lb["ly"]] for lb in self.label_data])
            xy_display = self.ax.transData.transform(xy_data)
            dx = xy_display[:, 0] - x_px
            dy = xy_display[:, 1] - y_px
            dists = np.hypot(dx, dy)
            idx = np.argmin(dists)
            if dists[idx] <= self._pick_radius_px:
                return self.label_data[idx]
        except Exception:
            pass
        return None

    def _clamp_to_radius_px(self, cx, cy, lx, ly):
        """중심점(cx,cy) 기준 픽셀 반경 max_radius_px 안으로 (lx,ly) 제한."""
        if not self.ax:
            return lx, ly
        try:
            trans = self.ax.transData
            inv = trans.inverted()
            cp = trans.transform(np.array([[cx, cy]]))[0]
            lp = trans.transform(np.array([[lx, ly]]))[0]
            dx = lp[0] - cp[0]
            dy = lp[1] - cp[1]
            d = np.hypot(dx, dy)
            if d <= self.max_radius_px or d < 1e-6:
                return lx, ly
            scale = self.max_radius_px / d
            new_lp = cp[0] + dx * scale, cp[1] + dy * scale
            new_xy = inv.transform(np.array([new_lp]))[0]
            return (float(new_xy[0]), float(new_xy[1]))
        except Exception:
            return lx, ly

    def _connect(self):
        if self.canvas:
            self.cid_press = self.canvas.mpl_connect(
                "button_press_event", self._on_press
            )
            self.cid_motion = self.canvas.mpl_connect(
                "motion_notify_event", self._on_motion
            )
            self.cid_release = self.canvas.mpl_connect(
                "button_release_event", self._on_release
            )

    def detach(self):
        if self.canvas:
            try:
                if self.cid_press:
                    self.canvas.mpl_disconnect(self.cid_press)
                if self.cid_motion:
                    self.canvas.mpl_disconnect(self.cid_motion)
                if self.cid_release:
                    self.canvas.mpl_disconnect(self.cid_release)
            except (RuntimeError, AttributeError, TypeError, ReferenceError):
                # Qt C++ 객체가 이미 파괴된 경우 종료 중 예외를 무시
                pass
            if self.cursor_changed:
                try:
                    self.canvas.unsetCursor()
                except (RuntimeError, AttributeError, TypeError, ReferenceError):
                    pass
                self.cursor_changed = False
        self.cid_press = self.cid_motion = self.cid_release = None
        self.dragging = None
        self._clear_highlight()
        self._remove_drag_preview()

    def _on_press(self, event):
        # 우클릭(Matplotlib button 3) 원상복귀: 사용자 오프셋 제거 후 refresh로 자동 배치 복귀
        if event.button == 3:
            if self.hovered_label is not None:
                vowel = (self.hovered_label or {}).get("vowel")
                if vowel is not None and callable(
                    getattr(self, "on_offset_cleared", None)
                ):
                    self.on_offset_cleared(vowel)
                self._clear_highlight()
                self.hovered_label = None
                if self.canvas:
                    self.canvas.draw_idle()
            return
        if event.inaxes != self.ax:
            return
        if event.button != 1:
            return
        if self.dragging is not None:
            return
        hit = self._find_label_at_px(event.x, event.y)
        if hit:
            self.dragging = dict(hit)
            self._clear_highlight()
            self._create_drag_preview(self.dragging)

    def _on_motion(self, event):
        if event.inaxes != self.ax:
            if self.dragging is None:
                self._clear_highlight()
                if self.cursor_changed and self.canvas:
                    self.canvas.unsetCursor()
                    self.cursor_changed = False
            return
        xdata, ydata = event.xdata, event.ydata
        if xdata is None or ydata is None:
            return

        if self.dragging is not None:
            cx, cy = self.dragging["cx"], self.dragging["cy"]
            lx, ly = self._clamp_to_radius_px(cx, cy, xdata, ydata)
            self.dragging["lx"], self.dragging["ly"] = lx, ly
            self._update_drag_preview_position(lx, ly)
            return

        hit = self._find_label_at_px(event.x, event.y)
        if hit:
            if not self.cursor_changed:
                self.canvas.setCursor(Qt.CursorShape.SizeAllCursor)
                self.cursor_changed = True
            if self.hovered_label is not hit:
                self.hovered_label = hit
                self._draw_highlight(hit)
        else:
            if self.cursor_changed:
                self.canvas.unsetCursor()
                self.cursor_changed = False
            if self.hovered_label is not None:
                self._clear_highlight()

    def _on_release(self, event):
        if event.button != 1:
            return
        if self.dragging is not None:
            self._remove_drag_preview()
            if hasattr(self, "on_offset_saved") and callable(self.on_offset_saved):
                self.on_offset_saved(self.dragging)
            self.dragging = None
            if self.canvas:
                self.canvas.draw_idle()

    def toggle(self):
        self.active = not self.active
        if self.active:
            self._connect()
        else:
            self.detach()
        return self.active
