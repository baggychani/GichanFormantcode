# tool_ruler.py

import logging
import numpy as np
import platform
from PySide6.QtCore import Qt
from utils.math_utils import hz_to_bark

_log = logging.getLogger(__name__)

try:
    from scipy.spatial import cKDTree

    _HAS_KD = True
except ImportError:
    cKDTree = None
    _HAS_KD = False


def snap_query(ax, snapping_data, x_px, y_px, max_dist_px=20):
    """픽셀 좌표 (x_px, y_px)에서 가장 가까운 스냅 점을 찾아 반환.
    draw 모드 등에서 눈금자와 동일한 스냅 로직을 재사용할 때 사용.
    ax: matplotlib Axes, snapping_data: [{"x","y", ...}, ...], (x_px,y_px): 캔버스 픽셀.
    반환: 거리 <= max_dist_px이면 해당 점 dict, 아니면 None.
    """
    if not ax or not snapping_data:
        return None
    pts = np.array([[p["x"], p["y"]] for p in snapping_data])
    pts_px = ax.transData.transform(pts)
    query_pt = np.array([x_px, y_px])
    if _HAS_KD and len(pts_px) > 0:
        kdtree = cKDTree(pts_px)
        d_min, min_idx = kdtree.query(query_pt, k=1)
        d_min = float(d_min)
        min_idx = int(min_idx)
    else:
        dists = np.linalg.norm(pts_px - query_pt, axis=1)
        min_idx = int(np.argmin(dists))
        d_min = float(dists[min_idx])
    if d_min <= max_dist_px:
        return snapping_data[min_idx]
    return None


class RulerTool:
    def __init__(self):
        self.active = False
        self.canvas = None
        self.ax = None
        self.params = None
        self.snapping_data = []
        self._kdtree = None
        self._kdtree_px = None

        self.cid_click = None
        self.cid_move = None
        self.cid_key = None
        self.cid_release = None

        self.start_point_info = None
        self.start_marker = None
        self.snapped_point = None

        self.measurements = []
        self.snap_marker = None
        self.guide_line = None
        self.tooltip_text = None

        self.hovered_text = None
        self.dragging_text = None
        self.drag_start_x = None
        self.drag_start_y = None
        self.cursor_changed = False

        system_os = platform.system()
        if system_os == "Windows":
            self.ui_font_name = "Malgun Gothic"
        elif system_os == "Darwin":
            self.ui_font_name = "AppleGothic"
        else:
            self.ui_font_name = "NanumGothic"
        self._font_family = ["DejaVu Sans", self.ui_font_name]

    @staticmethod
    def _safe_remove_artist(artist, name="artist"):
        """Artist를 축에서 제거. 실패 시 로그만 남기고 참조는 호출처에서 정리 (유령 객체 방지)."""
        if artist is None:
            return
        try:
            artist.remove()
        except Exception as e:
            _log.warning("RulerTool %s remove failed: %s", name, e)

    def _build_kdtree(self):
        """스냅 데이터가 바뀌었을 때 픽셀 좌표 KDTree 재구성 (O(log N) 조회용)"""
        self._kdtree = None
        self._kdtree_px = None
        if not self.ax or not self.snapping_data:
            return
        pts = np.array([[p["x"], p["y"]] for p in self.snapping_data])
        pts_px = self.ax.transData.transform(pts)
        self._kdtree_px = pts_px
        if _HAS_KD and len(pts_px) > 0:
            self._kdtree = cKDTree(pts_px)

    def _font_family_from_design(self, design_settings=None):
        """눈금자 거리·툴팁 텍스트용 폰트 패밀리. 항상 산세리프를 사용."""
        return ["Arial", "Noto Sans KR", "DejaVu Sans", self.ui_font_name]

    def set_context(self, canvas, ax, params, snapping_data=None, design_settings=None):
        self.detach()

        old_measurements = getattr(self, "measurements", [])
        self.measurements = []

        self._clear_guide_line()
        self._clear_snap_marker()
        self._clear_tooltip()
        self.start_marker = None
        self.start_point_info = None

        self.canvas = canvas
        self.ax = ax
        self.params = params
        self.snapping_data = snapping_data if snapping_data else []
        self._font_family = self._font_family_from_design(design_settings)
        self._build_kdtree()

        for m in old_measurements:
            if "p1" in m and "p2" in m:
                self._redraw_measurement(m["p1"], m["p2"], m.get("text_pos"))

        if self.active:
            self._connect()

        if self.canvas:
            self.canvas.draw_idle()

    def toggle(self):
        self.active = not self.active
        if self.active:
            self._connect()
        else:
            self.detach()
            self.clear_all()
        return self.active

    def _connect(self):
        if self.canvas:
            self.cid_click = self.canvas.mpl_connect(
                "button_press_event", self.on_click
            )
            self.cid_move = self.canvas.mpl_connect(
                "motion_notify_event", self.on_mouse_move
            )
            self.cid_key = self.canvas.mpl_connect("key_press_event", self.on_key_press)
            self.cid_release = self.canvas.mpl_connect(
                "button_release_event", self.on_release
            )

    def detach(self):
        if self.canvas:
            if self.cid_click:
                self.canvas.mpl_disconnect(self.cid_click)
            if self.cid_move:
                self.canvas.mpl_disconnect(self.cid_move)
            if self.cid_key:
                self.canvas.mpl_disconnect(self.cid_key)
            if self.cid_release:
                self.canvas.mpl_disconnect(self.cid_release)

            if self.cursor_changed:
                self.canvas.unsetCursor()
                self.cursor_changed = False

        self.cid_click = self.cid_move = self.cid_key = self.cid_release = None

    def clear_all(self):
        for m in self.measurements:
            for artist in m["artists"]:
                self._safe_remove_artist(artist, "measurement")
        self.measurements = []
        self._clear_snap_marker()
        self._cancel_current_drawing()
        self._clear_tooltip()
        if self.canvas:
            self.canvas.draw_idle()

    def _cancel_current_drawing(self):
        self._clear_guide_line()
        if self.start_marker:
            self._safe_remove_artist(self.start_marker, "start_marker")
            self.start_marker = None
        self.start_point_info = None
        if self.canvas:
            self.canvas.draw_idle()

    def _clear_snap_marker(self):
        if self.snap_marker:
            self._safe_remove_artist(self.snap_marker, "snap_marker")
            self.snap_marker = None

    def _clear_tooltip(self):
        if self.tooltip_text:
            self._safe_remove_artist(self.tooltip_text, "tooltip")
            self.tooltip_text = None

    def _clear_guide_line(self):
        if self.guide_line:
            self._safe_remove_artist(self.guide_line, "guide_line")
            self.guide_line = None

    def on_key_press(self, event):
        if self.active and event.key == "escape":
            self._cancel_current_drawing()

    def on_mouse_move(self, event):
        if not self.active:
            if self.cursor_changed:
                self.canvas.unsetCursor()
                self.cursor_changed = False
            self._clear_snap_marker()
            self._clear_tooltip()
            self.snapped_point = None
            return
        # 다른 축이면 무시. inaxes가 None이어도 스냅된 점이 있으면 호버/클릭 허용 (축 밖 점 지원)
        if event.inaxes is not None and event.inaxes != self.ax:
            if self.cursor_changed:
                self.canvas.unsetCursor()
                self.cursor_changed = False
            self._clear_snap_marker()
            self._clear_tooltip()
            self.snapped_point = None
            return

        if self.dragging_text and event.xdata is not None and event.ydata is not None:
            dx = event.xdata - self.drag_start_x
            dy = event.ydata - self.drag_start_y
            x0, y0 = self.dragging_text.get_position()
            self.dragging_text.set_position((x0 + dx, y0 + dy))
            self.drag_start_x = event.xdata
            self.drag_start_y = event.ydata
            self.canvas.draw_idle()
            return

        is_hovering = False
        hovered_artist = None
        for m in self.measurements:
            txt_artist = m["artists"][-1]  # 리스트의 마지막 객체가 Text 라벨
            contains, _ = txt_artist.contains(event)
            if contains:
                is_hovering = True
                hovered_artist = txt_artist
                break

        if is_hovering:
            if not self.cursor_changed:
                self.canvas.setCursor(Qt.CursorShape.SizeAllCursor)
                self.cursor_changed = True
            self.hovered_text = hovered_artist
            self._clear_snap_marker()
            self._clear_tooltip()
            self.snapped_point = None
        else:
            if self.cursor_changed:
                self.canvas.unsetCursor()
                self.cursor_changed = False
            self.hovered_text = None

        if not is_hovering and self.snapping_data:
            query_pt = np.array([event.x, event.y])
            if _HAS_KD and self._kdtree is not None:
                d_min, min_idx = self._kdtree.query(query_pt, k=1)
                d_min = float(d_min)
                min_idx = int(min_idx)
            else:
                pts_px = self.ax.transData.transform(
                    np.array([[p["x"], p["y"]] for p in self.snapping_data])
                )
                dists = np.linalg.norm(pts_px - np.array([event.x, event.y]), axis=1)
                min_idx = int(np.argmin(dists))
                d_min = float(dists[min_idx])

            if d_min < 20:
                pt = self.snapping_data[min_idx]
                if self.snapped_point != pt:
                    self.snapped_point = pt
                    self._draw_snap_marker(pt)
                    self._draw_tooltip(pt)
            else:
                if self.snapped_point:
                    self.snapped_point = None
                    self._clear_snap_marker()
                    self._clear_tooltip()
                    self.canvas.draw_idle()

        # 점과 점을 잇는 가이드 라인 업데이트
        if self.start_point_info:
            self._clear_guide_line()
            x1, y1 = self.start_point_info["x"], self.start_point_info["y"]
            x2, y2 = (
                (self.snapped_point["x"], self.snapped_point["y"])
                if self.snapped_point
                else (event.xdata, event.ydata)
            )
            (self.guide_line,) = self.ax.plot(
                [x1, x2],
                [y1, y2],
                color="gray",
                ls=":",
                lw=1,
                alpha=0.4,
                zorder=2,
                clip_on=False,
            )
            self.canvas.draw_idle()

    def on_click(self, event):
        if not self.active:
            return
        if event.inaxes is not None and event.inaxes != self.ax:
            return
        # 축 밖에 그려진 점(clip_on=False)은 inaxes가 None일 수 있음. 스냅된 점이 있으면 클릭 허용
        if event.inaxes is None and not self.snapped_point:
            return

        # 우클릭 (삭제)
        if event.button == 3:
            self._delete_nearest_measurement(event)
            return

        # 좌클릭 (점 찍기 or 드래그 시작)
        if event.button == 1:
            if self.hovered_text:
                self.dragging_text = self.hovered_text
                self.drag_start_x = event.xdata
                self.drag_start_y = event.ydata
                return

            if not self.snapped_point:
                return

            pt = self.snapped_point
            if self.start_point_info is None:
                self.start_point_info = pt.copy()
                m_style = "s" if pt["type"] == "mean" else "o"
                m_color = pt.get("color", "red")

                (self.start_marker,) = self.ax.plot(
                    pt["x"],
                    pt["y"],
                    m_style,
                    markersize=12 if pt["type"] == "mean" else 10,
                    markerfacecolor="none",
                    markeredgecolor=m_color,
                    markeredgewidth=2,
                    zorder=101,
                    clip_on=False,
                )
                self.canvas.draw_idle()
            else:
                p1, p2 = self.start_point_info, pt
                if p1["x"] == p2["x"] and p1["y"] == p2["y"]:
                    return

                self._clear_guide_line()
                artists = []
                (line,) = self.ax.plot(
                    [p1["x"], p2["x"]],
                    [p1["y"], p2["y"]],
                    "k-",
                    linewidth=1.2,
                    alpha=0.7,
                    zorder=2,
                    clip_on=False,
                )
                artists.extend([line, self.start_marker])

                m_style = "s" if p2["type"] == "mean" else "o"
                m_color = p2.get("color", "red")

                (end_m,) = self.ax.plot(
                    p2["x"],
                    p2["y"],
                    m_style,
                    markersize=12 if p2["type"] == "mean" else 10,
                    markerfacecolor="none",
                    markeredgecolor=m_color,
                    markeredgewidth=2,
                    zorder=101,
                    clip_on=False,
                )
                artists.append(end_m)

                dist_text = self._calculate_real_distance(p1, p2)
                mid_x, mid_y = (p1["x"] + p2["x"]) / 2, (p1["y"] + p2["y"]) / 2

                txt = self.ax.text(
                    mid_x,
                    mid_y,
                    dist_text,
                    ha="center",
                    va="bottom",
                    color="black",
                    fontsize=10,
                    fontweight="bold",
                    fontfamily=self._font_family,
                    zorder=102,
                    bbox=dict(
                        facecolor="#ffffdd", alpha=0.6, edgecolor="orange", pad=2
                    ),
                    clip_on=False,
                )
                artists.append(txt)

                self.measurements.append(
                    {
                        "artists": artists,
                        "p1": p1.copy(),
                        "p2": p2.copy(),
                        "text_pos": (mid_x, mid_y),
                    }
                )
                self.canvas.draw_idle()
                self.start_point_info = self.start_marker = None

    def on_release(self, event):
        """[추가] 좌클릭을 떼었을 때 드래그 상태 해제 및 새 위치 저장"""
        if event.button == 1 and self.dragging_text:
            for m in self.measurements:
                if m["artists"][-1] == self.dragging_text:
                    # 마우스를 놓은 위치의 좌표를 기억 (화면 리프레시 방어용)
                    m["text_pos"] = self.dragging_text.get_position()
                    break
            self.dragging_text = None

    def _draw_snap_marker(self, pt):
        self._clear_snap_marker()
        x, y = pt["x"], pt["y"]
        if self.start_point_info and (
            x == self.start_point_info["x"] and y == self.start_point_info["y"]
        ):
            return

        m_style = "s" if pt["type"] == "mean" else "o"
        m_color = pt.get("color", "red")

        (self.snap_marker,) = self.ax.plot(
            x,
            y,
            m_style,
            markersize=12 if pt["type"] == "mean" else 10,
            markerfacecolor="none",
            markeredgecolor=m_color,
            markeredgewidth=2,
            zorder=200,
            clip_on=False,
        )
        self.canvas.draw_idle()

    def _draw_tooltip(self, pt):
        self._clear_tooltip()

        label = pt.get("label", pt.get("Label"))
        if not label and pt.get("type") == "mean":
            min_dist = float("inf")
            for other_pt in self.snapping_data:
                if other_pt.get("type") == "raw" and (
                    "label" in other_pt or "Label" in other_pt
                ):
                    d = (other_pt["x"] - pt["x"]) ** 2 + (other_pt["y"] - pt["y"]) ** 2
                    if d < min_dist:
                        min_dist = d
                        label = other_pt.get("label", other_pt.get("Label"))
        if not label:
            label = "Unknown"

        f1_orig = pt.get("raw_f1", 0)
        f2_orig = pt.get("raw_f2", 0)
        f3_orig = pt.get("raw_f3", 0)

        use_bark = self.params.get("use_bark_units", False)
        is_norm = bool(self.params.get("normalization"))
        unit = "" if is_norm else ("Bk" if use_bark else "Hz")

        def convert(val):
            return hz_to_bark(val) if use_bark else val

        plot_type = self.params.get("type", "f1_f2")

        if is_norm:
            y_name, x_name = "nF1", "nF2"
            val_y, val_x = pt["y"], pt["x"]
        else:
            y_name = "F1"
            val_y = convert(f1_orig)
            if plot_type == "f1_f2_minus_f1":
                x_name = "F2 - F1"
                val_x = convert(f2_orig) - convert(f1_orig)
            elif plot_type == "f1_f3":
                x_name = "F3"
                val_x = convert(f3_orig) if f3_orig else pt["x"]
            elif plot_type == "f1_f2_prime":
                x_name = "F2'"
                val_x = pt["x"]
            elif plot_type == "f1_f2_prime_minus_f1":
                x_name = "F2' - F1"
                val_x = pt["x"]
            else:
                x_name = "F2"
                val_x = convert(f2_orig)

        if is_norm:
            info_text = f"[{label}]\n{y_name}: {val_y:.4g}\n{x_name}: {val_x:.4g}"
        elif use_bark:
            info_text = (
                f"[{label}]\n{y_name}: {val_y:.2f} {unit}\n{x_name}: {val_x:.2f} {unit}"
            )
        else:
            info_text = (
                f"[{label}]\n{y_name}: {val_y:.0f} {unit}\n{x_name}: {val_x:.0f} {unit}"
            )

        # 툴팁 좌/우: 데이터가 아닌 화면 픽셀 기준으로 판단 (F2 반전 시 잘림 방지)
        try:
            pt_disp = self.ax.transData.transform((pt["x"], pt["y"]))
            ax_bbox = self.ax.get_window_extent(self.canvas.get_renderer())
            center_x_px = ax_bbox.x0 + ax_bbox.width * 0.5
            tooltip_offset = (-15, 15) if pt_disp[0] > center_x_px else (15, 15)
        except Exception:
            tooltip_offset = (15, 15)

        self.tooltip_text = self.ax.annotate(
            info_text,
            xy=(pt["x"], pt["y"]),
            xytext=tooltip_offset,
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="#ffffe0", ec="gray", alpha=0.9),
            fontsize=9,
            color="black",
            fontfamily=self._font_family,
            zorder=300,
            clip_on=False,
        )
        self.canvas.draw_idle()

    def _redraw_measurement(self, old_p1, old_p2, text_pos=None):
        new_p1 = next(
            (
                pt
                for pt in self.snapping_data
                if pt["raw_f1"] == old_p1["raw_f1"]
                and pt["raw_f2"] == old_p1["raw_f2"]
                and pt["type"] == old_p1["type"]
            ),
            None,
        )
        new_p2 = next(
            (
                pt
                for pt in self.snapping_data
                if pt["raw_f1"] == old_p2["raw_f1"]
                and pt["raw_f2"] == old_p2["raw_f2"]
                and pt["type"] == old_p2["type"]
            ),
            None,
        )

        if not new_p1 or not new_p2:
            return

        artists = []
        (line,) = self.ax.plot(
            [new_p1["x"], new_p2["x"]],
            [new_p1["y"], new_p2["y"]],
            "k-",
            linewidth=1.2,
            alpha=0.7,
            zorder=2,
            clip_on=False,
        )
        artists.append(line)

        m1_style = "s" if new_p1["type"] == "mean" else "o"
        m1_color = new_p1.get("color", "red")
        (start_m,) = self.ax.plot(
            new_p1["x"],
            new_p1["y"],
            m1_style,
            markersize=12 if new_p1["type"] == "mean" else 10,
            markerfacecolor="none",
            markeredgecolor=m1_color,
            markeredgewidth=2,
            zorder=101,
            clip_on=False,
        )
        artists.append(start_m)

        m2_style = "s" if new_p2["type"] == "mean" else "o"
        m2_color = new_p2.get("color", "red")
        (end_m,) = self.ax.plot(
            new_p2["x"],
            new_p2["y"],
            m2_style,
            markersize=12 if new_p2["type"] == "mean" else 10,
            markerfacecolor="none",
            markeredgecolor=m2_color,
            markeredgewidth=2,
            zorder=101,
            clip_on=False,
        )
        artists.append(end_m)

        dist_text = self._calculate_real_distance(new_p1, new_p2)
        mid_x, mid_y = (new_p1["x"] + new_p2["x"]) / 2, (new_p1["y"] + new_p2["y"]) / 2

        if text_pos:
            txt_x, txt_y = text_pos
        else:
            txt_x, txt_y = mid_x, mid_y

        txt = self.ax.text(
            txt_x,
            txt_y,
            dist_text,
            ha="center",
            va="bottom",
            color="black",
            fontsize=10,
            fontweight="bold",
            fontfamily=self._font_family,
            zorder=102,
            bbox=dict(facecolor="#ffffdd", alpha=0.6, edgecolor="orange", pad=2),
            clip_on=False,
        )
        artists.append(txt)

        self.measurements.append(
            {"artists": artists, "p1": new_p1, "p2": new_p2, "text_pos": (txt_x, txt_y)}
        )

    def _delete_nearest_measurement(self, event):
        """[수정] 라벨 클릭 검사를 우선 수행하고, 없으면 선분 근처 클릭 검사로 넘어감"""
        if not self.measurements:
            return

        click_x, click_y = event.x, event.y
        idx_to_remove = -1

        # 1순위 검사: 내가 옮겨놓은 라벨 텍스트 박스를 정확히 우클릭했는가?
        for i, m in enumerate(self.measurements):
            txt_artist = m["artists"][-1]
            contains, _ = txt_artist.contains(event)
            if contains:
                idx_to_remove = i
                break

        # 2순위 검사: 라벨을 클릭한게 아니라면 선의 중심이나 선 자체를 클릭했는가?
        if idx_to_remove == -1:
            min_dist = float("inf")
            for i, m in enumerate(self.measurements):
                p1, p2 = m["p1"], m["p2"]
                pts_px = self.ax.transData.transform(
                    [[p1["x"], p1["y"]], [p2["x"], p2["y"]]]
                )
                mid_x, mid_y = (p1["x"] + p2["x"]) / 2, (p1["y"] + p2["y"]) / 2
                center_px = self.ax.transData.transform((mid_x, mid_y))

                d_center = np.hypot(click_x - center_px[0], click_y - center_px[1])
                d_line = self._dist_to_segment(
                    click_x,
                    click_y,
                    pts_px[0][0],
                    pts_px[0][1],
                    pts_px[1][0],
                    pts_px[1][1],
                )
                d_final = min(d_center, d_line)

                if d_final < min_dist:
                    min_dist = d_final
                    idx_to_remove = i

            if min_dist > 40:
                idx_to_remove = -1

        # 최종 삭제 처리
        if idx_to_remove != -1:
            for artist in self.measurements[idx_to_remove]["artists"]:
                self._safe_remove_artist(artist, "measurement")
            self.measurements.pop(idx_to_remove)
            self.canvas.draw_idle()

    def _dist_to_segment(self, px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        if dx == dy == 0:
            return np.hypot(px - x1, py - y1)
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        return np.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    def _calculate_real_distance(self, p1, p2):
        if self.params.get("normalization"):
            d = np.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)
            if np.isnan(d):
                return "—"
            return f"{d:.4g}"
        f1a, f2a = p1["raw_f1"], p1["raw_f2"]
        f1b, f2b = p2["raw_f1"], p2["raw_f2"]

        z1_f1, z1_f2 = hz_to_bark(f1a), hz_to_bark(f2a)
        z2_f1, z2_f2 = hz_to_bark(f1b), hz_to_bark(f2b)

        dist_hz = np.sqrt((f1a - f1b) ** 2 + (f2a - f2b) ** 2)
        dist_bk = np.sqrt((z1_f1 - z2_f1) ** 2 + (z1_f2 - z2_f2) ** 2)
        if np.isnan(dist_hz) or np.isnan(dist_bk):
            return "—"

        scale_type = self.params.get("f2_scale", "linear")
        if scale_type == "bark":
            return f"{dist_bk:.2f} Bk ≒ {dist_hz:.0f} Hz"
        else:
            return f"{dist_hz:.0f} Hz ≒ {dist_bk:.2f} Bk"
