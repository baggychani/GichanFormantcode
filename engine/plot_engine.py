# plot_engine.py

import os
import matplotlib.font_manager as fm
from matplotlib.patches import Ellipse
import matplotlib.patheffects as pe
import matplotlib.colors as mcolors
import numpy as np
import math
import platform
import config
from utils.math_utils import hz_to_bark, hz_to_log, calc_f2_prime


# assets/fonts에 있는 폰트 등록 (Noto Serif KR Medium 등)
def _register_assets_fonts():
    _base = getattr(config, "BASE_DIR", None) or os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
    fonts_dir = os.path.join(_base, "assets", "fonts")
    if not os.path.isdir(fonts_dir):
        return
    for name in os.listdir(fonts_dir):
        if name.endswith((".ttf", ".otf", ".TTF", ".OTF")):
            path = os.path.join(fonts_dir, name)
            try:
                fm.fontManager.addfont(path)
            except Exception:
                pass


_register_assets_fonts()

system_os = platform.system()
if system_os == "Windows":
    kor_font = "Malgun Gothic"
elif system_os == "Darwin":
    kor_font = "AppleGothic"
else:
    kor_font = "NanumGothic"

# 전역 rcParams 변경 금지 (스레드 경합 방지). 폰트는 draw_plot 등에서 객체별로 주입.


class PlotEngine:
    def __init__(self):
        pass

    def _get_default_design(self):
        """단일 플롯 디자인 설정이 전달되지 않았을 때를 대비한 기본값"""
        return {
            "show_raw": True,
            "show_centroid": True,
            "raw_marker": "o",
            "centroid_marker": "o",
            "lbl_color": "#E64A19",
            "lbl_size": 16,
            "lbl_bold": True,
            "lbl_italic": False,
            "ell_thick": 1.0,
            "ell_style": "--",
            "ell_color": "#606060",
            "ell_fill_color": None,
            "box_spines": False,
            "show_grid": False,
            "y_label_rotation": False,
            "show_axis_units": False,
            "show_minor_ticks": True,
            "font_style": "serif",
            "label_slash_wrap": False,
        }

    def _to_mpl_linestyle(self, ell_style):
        """디자인/레이어의 ell_style('-', '--', '---')을 matplotlib linestyle로 변환. '---' = 긴 대시."""
        if ell_style == "---":
            return (0, (6.0, 3.0))  # 6pt dash, 3pt gap
        return ell_style if ell_style in ("-", "--", ":") else "--"

    @staticmethod
    def _resolve_centroid_marker(marker, default_face="black", base_size=70):
        """centroid_marker를 (mpl_marker, facecolor, edgecolor, linewidth, marker_size)로 반환. 흰색 테두리 도형은 면적 30% 축소."""
        if marker in ("wo", "ws", "w^", "wD"):
            # 외곽선 때문에 커지는 현상 방지: s값을 약 30% 줄임
            return (marker[1], "white", "black", 1.0, base_size * 0.7)
        mpl = marker if marker in ("o", "s", "^", "D") else "o"
        return (mpl, default_face, "white", 0.5, base_size)

    @staticmethod
    def _get_axis_font_list(font_style):
        """축/틱 라벨용 폰트 패밀리 리스트. rcParams를 건드리지 않고 객체에 주입할 때 사용."""
        if font_style == "serif":
            return ["Noto Serif KR", "Charis SIL", "DejaVu Serif"]
        return ["Noto Sans KR", "Andika", "DejaVu Sans"]

    @staticmethod
    def _is_korean(text):
        """문자열에 한글(완성형/자모/호환 자모)이 포함되면 True."""
        if not text:
            return False
        s = str(text)
        for c in s:
            o = ord(c)
            if (
                (0xAC00 <= o <= 0xD7A3)
                or (0x1100 <= o <= 0x11FF)
                or (0x3130 <= o <= 0x318F)
            ):
                return True
        return False

    def _label_font_family(self, label_text, font_style):
        """라벨 문자에 따라 한글이면 Noto, 아니면 IPA용 폰트(Charis/Andika) 반환. (fontfamily_list, serif_normal_use_medium)."""
        is_serif = font_style == "serif"
        if self._is_korean(label_text):
            return (["Noto Serif KR"] if is_serif else ["Noto Sans KR"], is_serif)
        return (["Charis SIL"] if is_serif else ["Andika"], False)

    def _get_default_multi_design(self):
        """다중 비교 모드 디자인 설정이 전달되지 않았을 때를 대비한 기본값"""
        return {
            "common": {
                "show_raw": True,
                "show_centroid": True,
                "box_spines": False,
                "show_grid": False,
                "y_label_rotation": False,
                "show_minor_ticks": True,
                "font_style": "serif",
            },
            "blue": {
                "lbl_color": "#1976D2",
                "lbl_size": 16,
                "lbl_bold": True,
                "lbl_italic": False,
                "ell_thick": 1.0,
                "ell_style": "-",
                "ell_color": "#1976D2",
                "ell_fill_color": None,
                "centroid_marker": "o",
            },
            "red": {
                "lbl_color": "#E64A19",
                "lbl_size": 16,
                "lbl_bold": True,
                "lbl_italic": False,
                "ell_thick": 1.0,
                "ell_style": "--",
                "ell_color": "#E64A19",
                "ell_fill_color": None,
                "centroid_marker": "o",
            },
        }

    def _prepare_plot_df(self, df, plot_params):
        """원본 df에 스케일 적용된 y_val, x_val 열을 추가한 플롯용 DataFrame을 반환한다."""
        df_plot = df.copy()
        df_plot["y_val"] = self._apply_scale(df_plot["F1"], plot_params["f1_scale"])
        plot_type = plot_params["type"]
        f3_data = df_plot["F3"] if "F3" in df_plot.columns else 0
        if plot_type == "f1_f2":
            x_raw = df_plot["F2"]
        elif plot_type == "f1_f3":
            x_raw = df_plot["F3"]
        elif plot_type == "f1_f2_prime":
            x_raw = calc_f2_prime(df_plot["F1"], df_plot["F2"], f3_data)
        elif plot_type == "f1_f2_minus_f1":
            x_raw = df_plot["F2"] - df_plot["F1"]
        elif plot_type == "f1_f2_prime_minus_f1":
            f2p = calc_f2_prime(df_plot["F1"], df_plot["F2"], f3_data)
            x_raw = f2p - df_plot["F1"]
        else:
            x_raw = df_plot["F2"]
        df_plot["x_val"] = self._apply_scale(x_raw, plot_params["f2_scale"])
        return df_plot

    def _compute_axes_ranges(self, plot_type, use_bark_units, manual_ranges):
        """플롯 타입·단위·수동 범위에 따라 축 범위(min/max)를 계산한다."""
        if manual_ranges:
            try:
                return {
                    "final_min_y": float(manual_ranges["y_min"]),
                    "final_max_y": float(manual_ranges["y_max"]),
                    "final_min_x": float(manual_ranges["x_min"]),
                    "final_max_x": float(manual_ranges["x_max"]),
                }
            except (ValueError, TypeError):
                pass
        fallback = (
            config.BARK_RANGES.get(plot_type, config.BARK_RANGES["f1_f2"])
            if use_bark_units
            else config.HZ_RANGES.get(plot_type, config.HZ_RANGES["f1_f2"])
        )
        return {
            "final_min_y": fallback["y_min"],
            "final_max_y": fallback["y_max"],
            "final_min_x": fallback["x_min"],
            "final_max_x": fallback["x_max"],
        }

    def draw_plot(
        self,
        figure,
        df,
        plot_params,
        manual_ranges=None,
        is_normalized=False,
        filter_state=None,
        design_settings=None,
        custom_label_offsets=None,
        layer_overrides=None,
    ):
        """custom_label_offsets: optional dict vowel -> (dx_data, dy_data). layer_overrides: optional dict vowel -> design dict (레이어별 디자인 오버라이드)."""
        figure.clear()
        if (
            df is None
            or not hasattr(df, "columns")
            or "F1" not in df.columns
            or "F2" not in df.columns
        ):
            ax = figure.add_subplot(111)
            ax.set_box_aspect(1)
            ax.set_axisbelow(True)
            return ax, [], [], []
        origin = plot_params["origin"]
        use_bark_units = plot_params.get("use_bark_units", False)

        sigma = float(plot_params.get("sigma", config.DEFAULT_SIGMA))
        snapping_data = []
        label_data = []
        label_text_artists = []

        if design_settings is None:
            design_settings = self._get_default_design()
        if custom_label_offsets is None:
            custom_label_offsets = {}
        if layer_overrides is None:
            layer_overrides = {}
        axis_font = self._get_axis_font_list(design_settings.get("font_style", "serif"))

        show_raw = design_settings.get("show_raw", True)
        show_centroid = design_settings.get("show_centroid", True)
        # 기본값(광역); 루프 내에서 layer_overrides로 덮어씀
        lbl_color = design_settings.get("lbl_color", "#FF0000")
        lbl_size = design_settings.get("lbl_size", 16)
        "bold" if design_settings.get("lbl_bold", True) else "normal"
        "italic" if design_settings.get("lbl_italic", False) else "normal"

        ell_thick = design_settings.get("ell_thick", 1.0)
        ell_style = design_settings.get("ell_style", "--")
        ell_color = design_settings.get("ell_color", "#606060")
        ell_fill = design_settings.get("ell_fill_color", None)
        centroid_marker = design_settings.get("centroid_marker", "o")

        box_spines = design_settings.get("box_spines", False)
        show_grid = design_settings.get("show_grid", False)
        axis_position_swap = design_settings.get("axis_position_swap", False)
        use_top_right = (origin == "top_right") != axis_position_swap
        if use_top_right:
            # 팝업 캔버스에서 축 영역이 위/아래로 치우치지 않도록 여백을 대칭에 가깝게 유지 (상하좌우 +0.02)
            figure.subplots_adjust(left=0.08, bottom=0.12, right=0.80, top=0.88)
        else:
            figure.subplots_adjust(left=0.20, bottom=0.12, right=0.92, top=0.88)

        ax = figure.add_subplot(111)
        ax.set_box_aspect(1)
        ax.set_axisbelow(True)

        if df.empty:
            return ax, [], [], []

        df_plot = self._prepare_plot_df(df, plot_params)
        plot_type = plot_params["type"]
        ranges = self._compute_axes_ranges(plot_type, use_bark_units, manual_ranges)
        final_min_y = ranges["final_min_y"]
        final_max_y = ranges["final_max_y"]
        final_min_x = ranges["final_min_x"]
        final_max_x = ranges["final_max_x"]

        vowels = df_plot["Label"].unique()
        placed_labels = []

        for vowel in vowels:
            state = "ON"
            if filter_state and vowel in filter_state:
                state = filter_state[vowel]

            if state == "OFF":
                continue

            is_semi = state == "SEMI"
            # 레이어별 오버라이드 병합 (레이어 설정 도크)
            over = layer_overrides.get(vowel, {})
            eff = {**design_settings, **over}
            v_lbl_color = eff.get("lbl_color", lbl_color)
            v_lbl_size = int(eff.get("lbl_size", lbl_size))
            v_lbl_bold = "bold" if eff.get("lbl_bold", True) else "normal"
            v_lbl_italic = "italic" if eff.get("lbl_italic", False) else "normal"
            v_ell_thick = float(eff.get("ell_thick", ell_thick))
            v_ell_style = eff.get("ell_style", ell_style)
            v_ell_color = eff.get("ell_color", ell_color)
            v_ell_fill = eff.get("ell_fill_color", ell_fill)
            v_centroid_marker = eff.get("centroid_marker", centroid_marker)
            v_raw_marker = eff.get("raw_marker", design_settings.get("raw_marker", "o"))

            subset = df_plot[df_plot["Label"] == vowel]
            x, y = subset["x_val"], subset["y_val"]

            scatter_alpha = 0.15 if is_semi else 0.5
            z_offset = -10 if is_semi else 0

            # 개별 데이터 표시 및 스냅 동기화
            raw_marker = v_raw_marker
            if show_raw:
                if raw_marker == "o":
                    ax.scatter(
                        x,
                        y,
                        s=15,
                        facecolors="none",
                        edgecolors="black",
                        linewidth=0.4,
                        alpha=scatter_alpha,
                        zorder=1 + z_offset,
                        clip_on=False,
                    )
                elif raw_marker == "x":
                    ax.scatter(
                        x,
                        y,
                        s=25,
                        marker="x",
                        color="black",
                        linewidths=0.5,
                        alpha=scatter_alpha,
                        zorder=1 + z_offset,
                        clip_on=False,
                    )
                else:  # 'a': 각 데이터 포인트를 해당 모음 라벨 문자로 표시, 폰트 스타일 따름, 타원 선 색, 크기 약간 키움
                    font_family, _ = self._label_font_family(
                        vowel, design_settings.get("font_style", "serif")
                    )
                    pt_color = v_ell_color if v_ell_color else "#606060"
                    for px, py in zip(x, y):
                        t = ax.text(
                            px,
                            py,
                            vowel,
                            fontsize=9,
                            ha="center",
                            va="center",
                            color=pt_color,
                            fontweight="normal",
                            zorder=1 + z_offset,
                            clip_on=False,
                        )
                        t.set_fontfamily(font_family)

                if not is_semi:
                    for px, py, f1_orig, f2_orig in zip(
                        x, y, subset["F1"], subset["F2"]
                    ):
                        snapping_data.append(
                            {
                                "x": px,
                                "y": py,
                                "raw_f1": f1_orig,
                                "raw_f2": f2_orig,
                                "label": vowel,
                                "type": "raw",
                                "color": "red",
                            }
                        )

            if len(subset) >= 3 and (v_ell_color or v_ell_fill):
                fc = mcolors.to_rgba(v_ell_fill, 0.15) if v_ell_fill else "none"
                ec = mcolors.to_rgba(v_ell_color, 1.0) if v_ell_color else "none"
                if is_semi:
                    if v_ell_fill:
                        fc = mcolors.to_rgba(v_ell_fill, 0.05)
                    if v_ell_color:
                        ec = mcolors.to_rgba(v_ell_color, 0.2)

                self._draw_confidence_ellipse(
                    x,
                    y,
                    ax,
                    n_std=sigma,
                    edgecolor=ec,
                    facecolor=fc,
                    linewidth=v_ell_thick,
                    linestyle=self._to_mpl_linestyle(v_ell_style),
                    zorder=2 + z_offset,
                    clip_on=False,
                )

            mean_x, mean_y = x.mean(), y.mean()
            raw_f1_mean, raw_f2_mean = subset["F1"].mean(), subset["F2"].mean()

            # 모음 중심점 표시 및 스냅 동기화
            if show_centroid:
                mean_alpha = 0.2 if is_semi else 1.0
                mpl_marker, face_c, edge_c, lw, m_size = self._resolve_centroid_marker(
                    v_centroid_marker, default_face="black"
                )
                ax.scatter(
                    [mean_x],
                    [mean_y],
                    s=m_size,
                    c=face_c,
                    marker=mpl_marker,
                    edgecolors=edge_c,
                    linewidths=lw,
                    alpha=mean_alpha,
                    zorder=3 + z_offset,
                    clip_on=False,
                )

                if not is_semi:
                    snapping_data.append(
                        {
                            "x": mean_x,
                            "y": mean_y,
                            "raw_f1": raw_f1_mean,
                            "raw_f2": raw_f2_mean,
                            "label": vowel,
                            "type": "mean",
                            "color": "blue",
                        }
                    )

            use_custom = vowel in custom_label_offsets and show_centroid
            if use_custom:
                dx_data, dy_data = custom_label_offsets[vowel]
                label_x, label_y = mean_x + dx_data, mean_y + dy_data
                ha, va = "left", "bottom"
            elif show_centroid:
                base_offset = 6
                final_dx, final_dy = self._calculate_non_overlapping_offset(
                    mean_x, mean_y, base_offset, placed_labels, ax
                )
                ha = "left" if final_dx >= 0 else "right"
                va = "bottom" if final_dy >= 0 else "top"
                label_x, label_y = self._offset_points_to_data(
                    ax, mean_x, mean_y, final_dx, final_dy
                )
            else:
                final_dx, final_dy = 0, 0
                ha, va = "center", "center"
                label_x, label_y = mean_x, mean_y

            if v_lbl_color != "transparent":
                text_alpha = 0.3 if is_semi else 1.0
                display_vowel = (
                    f"/{vowel}/" if design_settings.get("label_slash_wrap") else vowel
                )
                font_family, serif_use_medium = self._label_font_family(
                    vowel, design_settings.get("font_style", "serif")
                )
                fontweight = (
                    "medium"
                    if (serif_use_medium and v_lbl_bold == "normal")
                    else v_lbl_bold
                )
                if use_custom:
                    ann = ax.annotate(
                        display_vowel,
                        xy=(mean_x, mean_y),
                        xytext=(label_x, label_y),
                        textcoords="data",
                        fontsize=v_lbl_size,
                        fontweight=fontweight,
                        fontstyle=v_lbl_italic,
                        fontfamily=font_family,
                        color=v_lbl_color,
                        ha=ha,
                        va=va,
                        alpha=text_alpha,
                        zorder=100 + z_offset,
                    )
                else:
                    final_dx_pt = final_dx if show_centroid else 0
                    final_dy_pt = final_dy if show_centroid else 0
                    ann = ax.annotate(
                        display_vowel,
                        xy=(mean_x, mean_y),
                        xytext=(final_dx_pt, final_dy_pt),
                        textcoords="offset points",
                        fontsize=v_lbl_size,
                        fontweight=fontweight,
                        fontstyle=v_lbl_italic,
                        fontfamily=font_family,
                        color=v_lbl_color,
                        ha=ha,
                        va=va,
                        alpha=text_alpha,
                        zorder=100 + z_offset,
                    )

                ann.set_clip_on(False)
                ann.set_path_effects([pe.withStroke(linewidth=3, foreground="white")])
                label_text_artists.append(ann)

                if use_custom:
                    # 수동 지정 라벨은 placed_labels에 넣지 않아, 다른 자동 배치 라벨이 튀지 않게 함
                    pass
                else:
                    placed_labels.append(
                        {"x": mean_x, "y": mean_y, "dx": final_dx, "dy": final_dy}
                    )
                # ON·SEMI 모두 이동 대상 (OFF는 루프에서 스킵되어 옮기기 불가). 네모/드래그용 bbox·스타일 정보 포함.
                label_data.append(
                    {
                        "vowel": vowel,
                        "cx": mean_x,
                        "cy": mean_y,
                        "lx": label_x,
                        "ly": label_y,
                        "fontsize": v_lbl_size,
                        "ha": ha,
                        "va": va,
                        "lbl_color": v_lbl_color,
                        "lbl_bold": v_lbl_bold,
                        "lbl_italic": v_lbl_italic,
                    }
                )

        show_minor_ticks = design_settings.get("show_minor_ticks", True)
        self._set_ticks(
            ax,
            "x",
            plot_params["f2_scale"],
            final_min_x,
            final_max_x,
            500,
            100,
            use_bark_units,
            show_minor_ticks,
        )
        self._set_ticks(
            ax,
            "y",
            plot_params["f1_scale"],
            final_min_y,
            final_max_y,
            100,
            100,
            use_bark_units,
            show_minor_ticks,
        )

        def get_lim(val, scale, use_bark):
            return (
                val if (scale == "bark" and use_bark) else self._apply_scale(val, scale)
            )

        x_lim_start = get_lim(final_min_x, plot_params["f2_scale"], use_bark_units)
        x_lim_end = get_lim(final_max_x, plot_params["f2_scale"], use_bark_units)
        y_lim_start = get_lim(final_min_y, plot_params["f1_scale"], use_bark_units)
        y_lim_end = get_lim(final_max_y, plot_params["f1_scale"], use_bark_units)

        ax.set_xlim(x_lim_start, x_lim_end)
        ax.set_ylim(y_lim_start, y_lim_end)
        ax.margins(0.05)

        if box_spines:
            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_color("#333333")
                spine.set_linewidth(1.0)
        else:
            for spine in ax.spines.values():
                spine.set_visible(False)

        if show_grid:
            ax.grid(True, linestyle="-", alpha=0.3, color="#AAAAAA")
        else:
            ax.grid(False)

        # 축·눈금 위치만 반대(원점/방향은 origin으로만 결정)
        if use_top_right:
            ax.xaxis.tick_top()
            ax.xaxis.set_label_position("top")
            ax.yaxis.tick_right()
            ax.yaxis.set_label_position("right")
        else:
            ax.xaxis.tick_bottom()
            ax.yaxis.tick_left()
        if origin == "top_right":
            ax.invert_xaxis()
            ax.invert_yaxis()

        y_label_rotate = design_settings.get("y_label_rotation", False)
        show_axis_units = design_settings.get("show_axis_units", False)
        use_bark = plot_params.get("use_bark_units", False)
        x_unit = (
            "Bark" if (plot_params.get("f2_scale") == "bark" and use_bark) else "Hz"
        )
        y_unit = (
            "Bark" if (plot_params.get("f1_scale") == "bark" and use_bark) else "Hz"
        )
        x_lbl = self._get_axis_name(plot_type)
        if show_axis_units:
            x_lbl += f" ({x_unit})"
        y_lbl = "F1"
        if show_axis_units:
            y_lbl += (
                "\n({})".format(y_unit)
                if not y_label_rotate
                else " ({})".format(y_unit)
            )
        y_ha = "left" if use_top_right else "right"
        if y_label_rotate:
            y_rotation = -90 if use_top_right else 90
            ax.set_xlabel(
                x_lbl,
                fontsize=16,
                labelpad=13,
                fontweight="normal",
                fontfamily=axis_font,
            )
            ax.set_ylabel(
                y_lbl,
                fontsize=16,
                labelpad=13,
                rotation=y_rotation,
                va="center",
                fontweight="normal",
                fontfamily=axis_font,
            )
        else:
            ax.set_xlabel(
                x_lbl,
                fontsize=16,
                labelpad=13,
                fontweight="normal",
                fontfamily=axis_font,
            )
            ax.set_ylabel(
                y_lbl,
                fontsize=16,
                labelpad=20,
                rotation=0,
                va="center",
                ha=y_ha,
                fontweight="normal",
                fontfamily=axis_font,
            )

        ax.tick_params(axis="both", which="major", length=6, labelsize=13)
        for lbl in ax.get_xticklabels() + ax.get_yticklabels():
            lbl.set_fontfamily(axis_font)

        return ax, snapping_data, label_data, label_text_artists

    def draw_multi_plot(
        self,
        figure,
        df_blue,
        df_red,
        plot_params,
        manual_ranges=None,
        name_blue="기준",
        name_red="비교",
        filter_state_blue=None,
        filter_state_red=None,
        design_settings=None,
        custom_label_offsets_blue=None,
        custom_label_offsets_red=None,
        layer_overrides_blue=None,
        layer_overrides_red=None,
    ):
        figure.clear()

        def _has_required(df):
            return (
                df is not None
                and hasattr(df, "columns")
                and "F1" in df.columns
                and "F2" in df.columns
            )

        if not _has_required(df_blue) or not _has_required(df_red):
            ax = figure.add_subplot(111)
            ax.set_box_aspect(1)
            ax.set_axisbelow(True)
            return ax, [], [], [], [], []
        origin = plot_params["origin"]
        use_bark_units = plot_params.get("use_bark_units", False)
        sigma = float(plot_params.get("sigma", config.DEFAULT_SIGMA))
        snapping_data = []
        label_data_blue = []
        label_data_red = []
        label_text_artists_blue = []  # 추가됨: 파란색 데이터의 텍스트 객체 리스트
        label_text_artists_red = []  # 추가됨: 빨간색 데이터의 텍스트 객체 리스트

        if design_settings is None or "common" not in design_settings:
            design_settings = self._get_default_multi_design()
        if custom_label_offsets_blue is None:
            custom_label_offsets_blue = {}
        if custom_label_offsets_red is None:
            custom_label_offsets_red = {}
        if layer_overrides_blue is None:
            layer_overrides_blue = {}
        if layer_overrides_red is None:
            layer_overrides_red = {}

        common = design_settings.get("common", {})
        blue_cfg = design_settings.get("blue", {})
        red_cfg = design_settings.get("red", {})
        axis_font = self._get_axis_font_list(common.get("font_style", "serif"))

        show_raw = common.get("show_raw", True)
        show_centroid = common.get("show_centroid", True)
        box_spines = common.get("box_spines", False)
        show_grid = common.get("show_grid", False)
        axis_position_swap = common.get("axis_position_swap", False)
        use_top_right = (origin == "top_right") != axis_position_swap
        if use_top_right:
            figure.subplots_adjust(left=0.08, bottom=0.12, right=0.80, top=0.88)
        else:
            figure.subplots_adjust(left=0.20, bottom=0.12, right=0.92, top=0.88)

        ax = figure.add_subplot(111)
        ax.set_box_aspect(1)
        ax.set_axisbelow(True)

        plot_type = plot_params["type"]

        if manual_ranges:
            try:
                final_min_y = float(manual_ranges["y_min"])
                final_max_y = float(manual_ranges["y_max"])
                final_min_x = float(manual_ranges["x_min"])
                final_max_x = float(manual_ranges["x_max"])
            except (ValueError, TypeError):
                fallback = (
                    config.BARK_RANGES.get(plot_type, config.BARK_RANGES["f1_f2"])
                    if use_bark_units
                    else config.HZ_RANGES.get(plot_type, config.HZ_RANGES["f1_f2"])
                )
                final_min_y, final_max_y = fallback["y_min"], fallback["y_max"]
                final_min_x, final_max_x = fallback["x_min"], fallback["x_max"]
        else:
            fallback = (
                config.BARK_RANGES.get(plot_type, config.BARK_RANGES["f1_f2"])
                if use_bark_units
                else config.HZ_RANGES.get(plot_type, config.HZ_RANGES["f1_f2"])
            )
            final_min_y, final_max_y = fallback["y_min"], fallback["y_max"]
            final_min_x, final_max_x = fallback["x_min"], fallback["x_max"]

        layer_overrides_by_side = {
            "blue": layer_overrides_blue,
            "red": layer_overrides_red,
        }
        datasets = [
            (df_blue, "blue", name_blue, filter_state_blue, blue_cfg),
            (df_red, "red", name_red, filter_state_red, red_cfg),
        ]

        placed_labels = []

        for df_curr, ds_type, file_name, curr_filter_state, cfg in datasets:
            if df_curr.empty:
                continue
            curr_layer_overrides = layer_overrides_by_side.get(ds_type, {})

            # 플롯용 복사본: 스케일 적용된 x_val, y_val 등이 추가됨
            df_plot = df_curr.copy()
            df_plot["y_val"] = self._apply_scale(df_plot["F1"], plot_params["f1_scale"])
            f3_data = df_plot["F3"] if "F3" in df_plot.columns else 0

            if plot_type == "f1_f2":
                x_raw = df_plot["F2"]
            elif plot_type == "f1_f3":
                x_raw = df_plot["F3"]
            elif plot_type == "f1_f2_prime":
                x_raw = calc_f2_prime(df_plot["F1"], df_plot["F2"], f3_data)
            elif plot_type == "f1_f2_minus_f1":
                x_raw = df_plot["F2"] - df_plot["F1"]
            elif plot_type == "f1_f2_prime_minus_f1":
                f1_vals = df_plot["F1"]
                f2_vals = df_plot["F2"]
                f2_prime = calc_f2_prime(f1_vals, f2_vals, f3_data)
                x_raw = f2_prime - f1_vals
            else:
                x_raw = df_plot["F2"]

            df_plot["x_val"] = self._apply_scale(x_raw, plot_params["f2_scale"])

            vowels = df_plot["Label"].unique()

            for vowel in vowels:
                state = "ON"
                if curr_filter_state and vowel in curr_filter_state:
                    state = curr_filter_state[vowel]

                if state == "OFF":
                    continue

                is_semi = state == "SEMI"
                over = curr_layer_overrides.get(vowel, {})
                cfg_v = dict(cfg)
                for k, v in over.items():
                    if v is not None:
                        cfg_v[k] = v

                subset = df_plot[df_plot["Label"] == vowel]
                x, y = subset["x_val"], subset["y_val"]

                lbl_color = cfg_v.get(
                    "lbl_color", "#1976D2" if ds_type == "blue" else "#E64A19"
                )
                lbl_size = cfg_v.get("lbl_size", cfg.get("lbl_size", 16))
                lbl_bold = "bold" if cfg_v.get("lbl_bold", True) else "normal"
                lbl_italic = "italic" if cfg_v.get("lbl_italic", False) else "normal"
                hide_text = lbl_color == "transparent"
                ell_thick = cfg_v.get("ell_thick", cfg.get("ell_thick", 1.0))
                ell_style = cfg_v.get(
                    "ell_style",
                    cfg.get("ell_style", "-" if ds_type == "blue" else "--"),
                )
                ell_color = cfg_v.get(
                    "ell_color",
                    cfg.get("ell_color", "#1976D2" if ds_type == "blue" else "#E64A19"),
                )
                ell_fill = cfg_v.get("ell_fill_color", cfg.get("ell_fill_color", None))
                point_color = (
                    ell_color
                    if (ell_color and ell_color != "transparent")
                    else ("#1976D2" if ds_type == "blue" else "#E64A19")
                )
                centroid_marker = cfg_v.get(
                    "centroid_marker", cfg.get("centroid_marker", "o")
                )
                raw_marker = common.get("raw_marker", "o")
                if show_raw:
                    scatter_alpha = 0.1 if is_semi else 0.3
                    z_offset = -10 if is_semi else 0
                    if raw_marker == "o":
                        ax.scatter(
                            x,
                            y,
                            s=15,
                            facecolors="none",
                            edgecolors=point_color,
                            linewidth=0.4,
                            alpha=scatter_alpha,
                            zorder=1 + z_offset,
                            clip_on=False,
                        )
                    elif raw_marker == "x":
                        ax.scatter(
                            x,
                            y,
                            s=25,
                            marker="x",
                            color=point_color,
                            linewidths=0.5,
                            alpha=scatter_alpha,
                            zorder=1 + z_offset,
                            clip_on=False,
                        )
                    else:
                        font_family, _ = self._label_font_family(
                            vowel, common.get("font_style", "serif")
                        )
                        for px, py in zip(x, y):
                            t = ax.text(
                                px,
                                py,
                                vowel,
                                fontsize=9,
                                ha="center",
                                va="center",
                                color=point_color,
                                fontweight="normal",
                                zorder=1 + z_offset,
                                clip_on=False,
                            )
                            t.set_fontfamily(font_family)

                    if not is_semi:
                        for px, py, f1_orig, f2_orig in zip(
                            x, y, subset["F1"], subset["F2"]
                        ):
                            snapping_data.append(
                                {
                                    "x": px,
                                    "y": py,
                                    "raw_f1": f1_orig,
                                    "raw_f2": f2_orig,
                                    "label": f"{vowel} - {file_name}",
                                    "type": "raw",
                                    "color": point_color,
                                }
                            )

                if len(subset) >= 3 and (ell_color or ell_fill):
                    z_offset = -10 if is_semi else 0
                    fc = mcolors.to_rgba(ell_fill, 0.15) if ell_fill else "none"
                    ec = mcolors.to_rgba(ell_color, 1.0) if ell_color else "none"

                    if is_semi:
                        if ell_fill:
                            fc = mcolors.to_rgba(ell_fill, 0.05)
                        if ell_color:
                            ec = mcolors.to_rgba(ell_color, 0.2)

                    self._draw_confidence_ellipse(
                        x,
                        y,
                        ax,
                        n_std=sigma,
                        edgecolor=ec,
                        facecolor=fc,
                        linewidth=ell_thick,
                        linestyle=self._to_mpl_linestyle(ell_style),
                        zorder=2 + z_offset,
                        clip_on=False,
                    )

                mean_x, mean_y = x.mean(), y.mean()
                raw_f1_mean, raw_f2_mean = subset["F1"].mean(), subset["F2"].mean()

                if show_centroid:
                    mean_alpha = 0.2 if is_semi else 1.0
                    z_offset = -10 if is_semi else 0
                    mpl_marker, face_c, edge_c, lw, m_size = (
                        self._resolve_centroid_marker(
                            centroid_marker, default_face=point_color
                        )
                    )
                    ax.scatter(
                        [mean_x],
                        [mean_y],
                        s=m_size,
                        c=face_c,
                        marker=mpl_marker,
                        edgecolors=edge_c,
                        linewidths=lw,
                        alpha=mean_alpha,
                        zorder=3 + z_offset,
                        clip_on=False,
                    )

                    if not is_semi:
                        snapping_data.append(
                            {
                                "x": mean_x,
                                "y": mean_y,
                                "raw_f1": raw_f1_mean,
                                "raw_f2": raw_f2_mean,
                                "label": f"{vowel} - {file_name}",
                                "type": "mean",
                                "color": point_color,
                            }
                        )

                custom_offsets = (
                    custom_label_offsets_blue
                    if ds_type == "blue"
                    else custom_label_offsets_red
                )
                use_custom = vowel in custom_offsets and show_centroid
                if use_custom:
                    dx_data, dy_data = custom_offsets[vowel]
                    label_x, label_y = mean_x + dx_data, mean_y + dy_data
                    ha, va = "left", "bottom"
                elif show_centroid:
                    base_offset = 6
                    final_dx, final_dy = self._calculate_non_overlapping_offset(
                        mean_x, mean_y, base_offset, placed_labels, ax
                    )
                    ha = "left" if final_dx >= 0 else "right"
                    va = "bottom" if final_dy >= 0 else "top"
                    label_x, label_y = self._offset_points_to_data(
                        ax, mean_x, mean_y, final_dx, final_dy
                    )
                else:
                    final_dx, final_dy = 0, 0
                    ha, va = "center", "center"
                    label_x, label_y = mean_x, mean_y

                if not hide_text:
                    text_alpha = 0.3 if is_semi else 1.0
                    display_vowel = (
                        f"/{vowel}/" if common.get("label_slash_wrap") else vowel
                    )
                    z_offset = -10 if is_semi else 0
                    font_family, serif_use_medium = self._label_font_family(
                        vowel, common.get("font_style", "serif")
                    )
                    fontweight = (
                        "medium"
                        if (serif_use_medium and lbl_bold == "normal")
                        else lbl_bold
                    )
                    if use_custom:
                        ann = ax.annotate(
                            display_vowel,
                            xy=(mean_x, mean_y),
                            xytext=(label_x, label_y),
                            textcoords="data",
                            fontsize=lbl_size,
                            fontweight=fontweight,
                            fontstyle=lbl_italic,
                            fontfamily=font_family,
                            color=lbl_color,
                            ha=ha,
                            va=va,
                            alpha=text_alpha,
                            zorder=100 + z_offset,
                        )
                    else:
                        ann = ax.annotate(
                            display_vowel,
                            xy=(mean_x, mean_y),
                            xytext=(final_dx, final_dy),
                            textcoords="offset points",
                            fontsize=lbl_size,
                            fontweight=fontweight,
                            fontstyle=lbl_italic,
                            fontfamily=font_family,
                            color=lbl_color,
                            ha=ha,
                            va=va,
                            alpha=text_alpha,
                            zorder=100 + z_offset,
                        )

                    ann.set_clip_on(False)
                    ann.set_path_effects(
                        [pe.withStroke(linewidth=3, foreground="white")]
                    )

                    # 추가됨: 텍스트 아티스트를 리스트에 보관
                    if ds_type == "blue":
                        label_text_artists_blue.append(ann)
                    else:
                        label_text_artists_red.append(ann)

                    if use_custom:
                        # 수동 지정 라벨은 placed_labels에 넣지 않아 다른 자동 배치 라벨이 튀지 않게 함
                        pass
                    else:
                        placed_labels.append(
                            {"x": mean_x, "y": mean_y, "dx": final_dx, "dy": final_dy}
                        )
                    if ds_type == "blue":
                        label_data_blue.append(
                            {
                                "vowel": vowel,
                                "cx": mean_x,
                                "cy": mean_y,
                                "lx": label_x,
                                "ly": label_y,
                                "fontsize": lbl_size,
                                "ha": ha,
                                "va": va,
                                "lbl_color": lbl_color,
                                "lbl_bold": lbl_bold,
                                "lbl_italic": lbl_italic,
                                "ell_color": ell_color,
                            }
                        )
                    else:
                        label_data_red.append(
                            {
                                "vowel": vowel,
                                "cx": mean_x,
                                "cy": mean_y,
                                "lx": label_x,
                                "ly": label_y,
                                "fontsize": lbl_size,
                                "ha": ha,
                                "va": va,
                                "lbl_color": lbl_color,
                                "lbl_bold": lbl_bold,
                                "lbl_italic": lbl_italic,
                                "ell_color": ell_color,
                            }
                        )

        show_minor_ticks = common.get("show_minor_ticks", True)
        self._set_ticks(
            ax,
            "x",
            plot_params["f2_scale"],
            final_min_x,
            final_max_x,
            500,
            100,
            use_bark_units,
            show_minor_ticks,
        )
        self._set_ticks(
            ax,
            "y",
            plot_params["f1_scale"],
            final_min_y,
            final_max_y,
            100,
            100,
            use_bark_units,
            show_minor_ticks,
        )

        def get_lim(val, scale, use_bark):
            return (
                val if (scale == "bark" and use_bark) else self._apply_scale(val, scale)
            )

        x_lim_start = get_lim(final_min_x, plot_params["f2_scale"], use_bark_units)
        x_lim_end = get_lim(final_max_x, plot_params["f2_scale"], use_bark_units)
        y_lim_start = get_lim(final_min_y, plot_params["f1_scale"], use_bark_units)
        y_lim_end = get_lim(final_max_y, plot_params["f1_scale"], use_bark_units)

        ax.set_xlim(x_lim_start, x_lim_end)
        ax.set_ylim(y_lim_start, y_lim_end)
        ax.margins(0.05)

        if box_spines:
            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_color("#333333")
                spine.set_linewidth(1.0)
        else:
            for spine in ax.spines.values():
                spine.set_visible(False)

        if show_grid:
            ax.grid(True, linestyle="-", alpha=0.3, color="#AAAAAA")
        else:
            ax.grid(False)

        # 축·눈금 위치만 반대(원점/방향은 origin으로만 결정)
        if use_top_right:
            ax.xaxis.tick_top()
            ax.xaxis.set_label_position("top")
            ax.yaxis.tick_right()
            ax.yaxis.set_label_position("right")
        else:
            ax.xaxis.tick_bottom()
            ax.yaxis.tick_left()
        if origin == "top_right":
            ax.invert_xaxis()
            ax.invert_yaxis()

        y_label_rotate = common.get("y_label_rotation", False)
        show_axis_units = common.get("show_axis_units", False)
        x_unit = (
            "Bark"
            if (plot_params.get("f2_scale") == "bark" and use_bark_units)
            else "Hz"
        )
        y_unit = (
            "Bark"
            if (plot_params.get("f1_scale") == "bark" and use_bark_units)
            else "Hz"
        )
        x_lbl = self._get_axis_name(plot_type)
        if show_axis_units:
            x_lbl += f" ({x_unit})"
        y_lbl = "F1"
        if show_axis_units:
            y_lbl += (
                "\n({})".format(y_unit)
                if not y_label_rotate
                else " ({})".format(y_unit)
            )
        y_ha = "left" if use_top_right else "right"
        if y_label_rotate:
            y_rotation = -90 if use_top_right else 90
            ax.set_xlabel(
                x_lbl,
                fontsize=16,
                labelpad=13,
                fontweight="normal",
                fontfamily=axis_font,
            )
            ax.set_ylabel(
                y_lbl,
                fontsize=16,
                labelpad=13,
                rotation=y_rotation,
                va="center",
                fontweight="normal",
                fontfamily=axis_font,
            )
        else:
            ax.set_xlabel(
                x_lbl,
                fontsize=16,
                labelpad=13,
                fontweight="normal",
                fontfamily=axis_font,
            )
            ax.set_ylabel(
                y_lbl,
                fontsize=16,
                labelpad=20,
                rotation=0,
                va="center",
                ha=y_ha,
                fontweight="normal",
                fontfamily=axis_font,
            )

        ax.tick_params(axis="both", which="major", length=6, labelsize=13)
        for lbl in ax.get_xticklabels() + ax.get_yticklabels():
            lbl.set_fontfamily(axis_font)

        # 수정됨: 다중 플롯에서도 텍스트 아티스트 리스트들을 반환합니다.
        return (
            ax,
            snapping_data,
            label_data_blue,
            label_data_red,
            label_text_artists_blue,
            label_text_artists_red,
        )

    # 정규화 비교 플롯: 축 반전, nF1/nF2, 고정 범위
    NORM_RANGES = {
        "Lobanov": {
            "x_min": -2.0,
            "x_max": 2.0,
            "y_min": -2.0,
            "y_max": 2.0,
            "x_step": 0.5,
            "y_step": 0.5,
        },
        "Gerstman": {
            "x_min": 0,
            "x_max": 1000,
            "y_min": 0,
            "y_max": 1000,
            "x_step": 200,
            "y_step": 200,
        },
        "2mW/F": {
            "x_min": 0.4,
            "x_max": 1.8,
            "y_min": 0.4,
            "y_max": 1.8,
            "x_step": 0.2,
            "y_step": 0.2,
        },
        "Bigham": {
            "x_min": 0.4,
            "x_max": 1.8,
            "y_min": 0.4,
            "y_max": 1.8,
            "x_step": 0.2,
            "y_step": 0.2,
        },
        "Nearey1": {
            "x_min": -1.0,
            "x_max": 1.0,
            "y_min": -1.0,
            "y_max": 1.0,
            "x_step": 0.5,
            "y_step": 0.5,
        },
    }

    def draw_compare_normalized(
        self,
        figure,
        df_blue,
        df_red,
        norm_type,
        name_blue="",
        name_red="",
        filter_state_blue=None,
        filter_state_red=None,
        design_settings=None,
        sigma=2.0,
        custom_label_offsets_blue=None,
        custom_label_offsets_red=None,
        manual_ranges=None,
        layer_overrides_blue=None,
        layer_overrides_red=None,
    ):
        """정규화된 F1 vs F2 비교 플롯. manual_ranges 있으면(Gerstman 제외) 해당 범위 사용."""
        figure.clear()
        if design_settings is None or "common" not in design_settings:
            design_settings = self._get_default_multi_design()
        common = design_settings.get("common", {})
        blue_cfg = design_settings.get("blue", {})
        red_cfg = design_settings.get("red", {})
        axis_font = self._get_axis_font_list(common.get("font_style", "serif"))
        if custom_label_offsets_blue is None:
            custom_label_offsets_blue = {}
        if custom_label_offsets_red is None:
            custom_label_offsets_red = {}
        if layer_overrides_blue is None:
            layer_overrides_blue = {}
        if layer_overrides_red is None:
            layer_overrides_red = {}

        layer_overrides_by_side = {
            "blue": layer_overrides_blue,
            "red": layer_overrides_red,
        }

        show_raw = common.get("show_raw", True)
        show_centroid = common.get("show_centroid", True)
        box_spines = common.get("box_spines", False)
        show_grid = common.get("show_grid", False)
        sigma = float(sigma)

        r = self.NORM_RANGES.get(norm_type, self.NORM_RANGES["Lobanov"])
        if manual_ranges and norm_type != "Gerstman":
            try:
                x_min = float(manual_ranges.get("x_min", r["x_min"]))
                x_max = float(manual_ranges.get("x_max", r["x_max"]))
                y_min = float(manual_ranges.get("y_min", r["y_min"]))
                y_max = float(manual_ranges.get("y_max", r["y_max"]))
                if x_min < x_max and y_min < y_max:
                    r = {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max}
            except (ValueError, TypeError):
                pass
        # 정규화 비교에서도 세로 중심이 유지되도록 위/아래 여백을 대칭에 가깝게 설정 (상하좌우 +0.02)
        figure.subplots_adjust(left=0.22, right=0.91, bottom=0.12, top=0.88)
        ax = figure.add_subplot(111)
        ax.set_box_aspect(1)
        ax.set_axisbelow(True)
        ax.set_xlim(r["x_min"], r["x_max"])
        ax.set_ylim(r["y_min"], r["y_max"])
        ax.invert_xaxis()
        ax.invert_yaxis()
        ax.xaxis.tick_bottom()
        ax.yaxis.tick_left()
        y_label_rotate = common.get("y_label_rotation", False)
        ax.set_xlabel(
            "nF2", fontsize=16, labelpad=13, fontweight="normal", fontfamily=axis_font
        )
        if y_label_rotate:
            ax.set_ylabel(
                "nF1",
                fontsize=16,
                labelpad=18,
                rotation=90,
                va="center",
                fontweight="normal",
                fontfamily=axis_font,
            )
        else:
            ax.set_ylabel(
                "nF1",
                fontsize=16,
                labelpad=20,
                rotation=0,
                va="center",
                ha="left",
                fontweight="normal",
                fontfamily=axis_font,
            )
        ax.tick_params(axis="both", which="major", length=6, labelsize=13)
        for lbl in ax.get_xticklabels() + ax.get_yticklabels():
            lbl.set_fontfamily(axis_font)
        if box_spines:
            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_color("#333333")
                spine.set_linewidth(1.0)
        else:
            for spine in ax.spines.values():
                spine.set_visible(False)
        if show_grid:
            ax.grid(True, linestyle="-", alpha=0.3, color="#AAAAAA")
        else:
            ax.grid(False)

        snapping_data = []
        label_data_blue = []
        label_data_red = []
        label_text_artists_blue = []
        label_text_artists_red = []
        placed_labels = []

        for df_curr, ds_type, file_name, curr_filter_state, cfg in [
            (df_blue, "blue", name_blue, filter_state_blue or {}, blue_cfg),
            (df_red, "red", name_red, filter_state_red or {}, red_cfg),
        ]:
            if df_curr.empty:
                continue
            curr_layer_overrides = layer_overrides_by_side.get(ds_type, {})
            # 플롯용 복사본 (이 루프에서는 F1/F2를 그대로 x_val, y_val로 사용)
            df_plot = df_curr.copy()
            df_plot["y_val"] = df_plot["F1"]
            df_plot["x_val"] = df_plot["F2"]
            label_col = "Label" if "Label" in df_plot.columns else "label"
            vowels = df_plot[label_col].unique()
            custom_offsets = (
                custom_label_offsets_blue
                if ds_type == "blue"
                else custom_label_offsets_red
            )

            for vowel in vowels:
                state = curr_filter_state.get(vowel, "ON")
                if state == "OFF":
                    continue
                is_semi = state == "SEMI"
                over = curr_layer_overrides.get(vowel, {})
                cfg_v = dict(cfg)
                for k, v in over.items():
                    if v is not None:
                        cfg_v[k] = v
                ell_color = cfg_v.get(
                    "ell_color", "#1976D2" if ds_type == "blue" else "#E64A19"
                )
                lbl_color = (
                    cfg_v.get("lbl_color")
                    or ell_color
                    or ("#1976D2" if ds_type == "blue" else "#E64A19")
                )
                hide_text = lbl_color == "transparent" or (
                    isinstance(lbl_color, str) and lbl_color.lower() == "transparent"
                )
                ell_style = cfg_v.get("ell_style", "-" if ds_type == "blue" else "--")
                ell_thick = cfg_v.get("ell_thick", 1.0)
                ell_fill = cfg_v.get("ell_fill_color", None)
                centroid_marker = cfg_v.get("centroid_marker", "o")
                lbl_size = cfg_v.get("lbl_size", 16)
                lbl_bold = "bold" if cfg_v.get("lbl_bold", True) else "normal"
                lbl_italic = "italic" if cfg_v.get("lbl_italic", False) else "normal"

                subset = df_plot[df_plot[label_col] == vowel]
                x, y = subset["x_val"], subset["y_val"]

                raw_marker = common.get("raw_marker", "o")
                if show_raw:
                    scatter_alpha = 0.1 if is_semi else 0.3
                    if raw_marker == "o":
                        ax.scatter(
                            x,
                            y,
                            s=15,
                            facecolors="none",
                            edgecolors=ell_color,
                            linewidth=0.4,
                            alpha=scatter_alpha,
                            zorder=1,
                            clip_on=False,
                        )
                    elif raw_marker == "x":
                        ax.scatter(
                            x,
                            y,
                            s=25,
                            marker="x",
                            color=ell_color,
                            linewidths=0.5,
                            alpha=scatter_alpha,
                            zorder=1,
                            clip_on=False,
                        )
                    else:
                        font_family, _ = self._label_font_family(
                            vowel, common.get("font_style", "serif")
                        )
                        pt_color = ell_color if ell_color else "#606060"
                        for px, py in zip(x, y):
                            t = ax.text(
                                px,
                                py,
                                vowel,
                                fontsize=9,
                                ha="center",
                                va="center",
                                color=pt_color,
                                fontweight="normal",
                                zorder=1,
                                clip_on=False,
                            )
                            t.set_fontfamily(font_family)
                if len(subset) >= 3:
                    fc = mcolors.to_rgba(ell_fill, 0.15) if ell_fill else "none"
                    ec = mcolors.to_rgba(ell_color, 1.0) if ell_color else "none"
                    if is_semi and ell_color:
                        ec = mcolors.to_rgba(ell_color, 0.2)
                    self._draw_confidence_ellipse(
                        x,
                        y,
                        ax,
                        n_std=sigma,
                        edgecolor=ec,
                        facecolor=fc,
                        linewidth=ell_thick,
                        linestyle=self._to_mpl_linestyle(ell_style),
                        zorder=2,
                        clip_on=False,
                    )
                mean_x, mean_y = x.mean(), y.mean()
                if show_centroid:
                    z_offset = -10 if is_semi else 0
                    mpl_marker, face_c, edge_c, lw, m_size = (
                        self._resolve_centroid_marker(
                            centroid_marker, default_face=ell_color or "#606060"
                        )
                    )
                    ax.scatter(
                        [mean_x],
                        [mean_y],
                        s=m_size,
                        c=face_c,
                        marker=mpl_marker,
                        edgecolors=edge_c,
                        linewidths=lw,
                        zorder=3 + z_offset,
                        clip_on=False,
                    )
                    snapping_data.append(
                        {
                            "x": mean_x,
                            "y": mean_y,
                            "raw_f1": mean_y,
                            "raw_f2": mean_x,
                            "label": f"{vowel} - {file_name}",
                            "type": "mean",
                            "color": ell_color,
                        }
                    )

                use_custom = vowel in custom_offsets and show_centroid
                if use_custom:
                    dx_data, dy_data = custom_offsets[vowel]
                    label_x, label_y = mean_x + dx_data, mean_y + dy_data
                    ha, va = "left", "bottom"
                elif show_centroid:
                    base_offset = 6
                    final_dx, final_dy = self._calculate_non_overlapping_offset(
                        mean_x, mean_y, base_offset, placed_labels, ax
                    )
                    ha = "left" if final_dx >= 0 else "right"
                    va = "bottom" if final_dy >= 0 else "top"
                    label_x, label_y = self._offset_points_to_data(
                        ax, mean_x, mean_y, final_dx, final_dy
                    )
                else:
                    final_dx, final_dy = 0, 0
                    ha, va = "center", "center"
                    label_x, label_y = mean_x, mean_y

                placed_labels.append({"x": mean_x, "y": mean_y})

                if hide_text:
                    continue

                text_alpha = 0.3 if is_semi else 1.0
                display_vowel = (
                    f"/{vowel}/" if common.get("label_slash_wrap") else vowel
                )
                z_offset = -10 if is_semi else 0
                font_family, serif_use_medium = self._label_font_family(
                    vowel, common.get("font_style", "serif")
                )
                fontweight = (
                    "medium"
                    if (serif_use_medium and lbl_bold == "normal")
                    else lbl_bold
                )
                if use_custom:
                    ann = ax.annotate(
                        display_vowel,
                        xy=(mean_x, mean_y),
                        xytext=(label_x, label_y),
                        textcoords="data",
                        fontsize=lbl_size,
                        fontweight=fontweight,
                        fontstyle=lbl_italic,
                        fontfamily=font_family,
                        color=lbl_color,
                        ha=ha,
                        va=va,
                        alpha=text_alpha,
                        zorder=100 + z_offset,
                    )
                else:
                    ann = ax.annotate(
                        display_vowel,
                        xy=(mean_x, mean_y),
                        xytext=(final_dx, final_dy),
                        textcoords="offset points",
                        fontsize=lbl_size,
                        fontweight=fontweight,
                        fontstyle=lbl_italic,
                        fontfamily=font_family,
                        color=lbl_color,
                        ha=ha,
                        va=va,
                        alpha=text_alpha,
                        zorder=100 + z_offset,
                    )
                ann.set_clip_on(False)
                ann.set_path_effects([pe.withStroke(linewidth=3, foreground="white")])

                if ds_type == "blue":
                    label_text_artists_blue.append(ann)
                    label_data_blue.append(
                        {
                            "vowel": vowel,
                            "cx": mean_x,
                            "cy": mean_y,
                            "lx": label_x,
                            "ly": label_y,
                            "fontsize": lbl_size,
                            "ha": ha,
                            "va": va,
                            "lbl_color": lbl_color,
                        }
                    )
                else:
                    label_text_artists_red.append(ann)
                    label_data_red.append(
                        {
                            "vowel": vowel,
                            "cx": mean_x,
                            "cy": mean_y,
                            "lx": label_x,
                            "ly": label_y,
                            "fontsize": lbl_size,
                            "ha": ha,
                            "va": va,
                            "lbl_color": lbl_color,
                        }
                    )

        return (
            ax,
            snapping_data,
            label_data_blue,
            label_data_red,
            label_text_artists_blue,
            label_text_artists_red,
        )

    def _offset_points_to_data(self, ax, cx, cy, dx_pt, dy_pt):
        """offset (dx_pt, dy_pt) in points from (cx, cy) in data -> label position in data coords."""
        try:
            fig = ax.get_figure()
            disp = ax.transData.transform((cx, cy))
            pts_to_disp = fig.dpi / 72.0
            label_disp = (disp[0] + dx_pt * pts_to_disp, disp[1] - dy_pt * pts_to_disp)
            return ax.transData.inverted().transform(label_disp)
        except Exception:
            return (cx, cy)

    def _data_offset_to_points(self, ax, cx, cy, lx, ly):
        """label position (lx, ly) in data coords -> offset (dx_pt, dy_pt) from (cx, cy)."""
        try:
            fig = ax.get_figure()
            disp_c = ax.transData.transform((cx, cy))
            disp_l = ax.transData.transform((lx, ly))
            pts_to_disp = fig.dpi / 72.0
            dx_pt = (disp_l[0] - disp_c[0]) / pts_to_disp
            dy_pt = -(disp_l[1] - disp_c[1]) / pts_to_disp
            return (dx_pt, dy_pt)
        except Exception:
            return (6.5, 6.5)

    def _calculate_non_overlapping_offset(
        self, curr_x, curr_y, base, placed_labels, ax
    ):
        """각도(방향)를 바꿔가며 라벨이 다른 글자·다른 centroid와 겹치지 않는 위치를 선택. 기본은 centroid 우측 상단."""
        zone = 1.2
        same_zone = [
            lb
            for lb in placed_labels
            if abs(curr_x - lb["x"]) < zone and abs(curr_y - lb["y"]) < zone
        ]
        if same_zone:
            right_first = curr_x >= np.mean([lb["x"] for lb in same_zone])
        else:
            right_first = True

        r = float(base)
        dirs_deg = [
            (0, 1),
            (1, 1),
            (1, 0),
            (1, -1),
            (0, -1),
            (-1, -1),
            (-1, 0),
            (-1, 1),
        ]
        dirs_pt = [(r * d[0], r * d[1]) for d in dirs_deg]
        if right_first:
            order = [0, 1, 2, 3, 4, 5, 6, 7]
        else:
            order = [6, 5, 4, 7, 0, 3, 2, 1]
        candidates = [dirs_pt[i] for i in order]

        label_radius_data = 0.5
        label_label_min = 0.9
        try:
            x_lim = ax.get_xlim()
            y_lim = ax.get_ylim()
            rx = (x_lim[1] - x_lim[0]) or 1.0
            ry = (y_lim[1] - y_lim[0]) or 1.0
            scale = min(rx, ry)
            label_radius_data = max(0.4, min(0.7, 0.035 * scale))
            label_label_min = label_radius_data * 2.0
        except Exception:
            pass

        other_centroids = [(lb["x"], lb["y"]) for lb in placed_labels]
        for cand_dx, cand_dy in candidates:
            try:
                lx, ly = self._offset_points_to_data(
                    ax, curr_x, curr_y, cand_dx, cand_dy
                )
            except Exception:
                continue
            conflict = False
            for ox, oy in other_centroids:
                if abs(ox - curr_x) < 1e-9 and abs(oy - curr_y) < 1e-9:
                    continue
                d = np.hypot(lx - ox, ly - oy)
                if d < label_radius_data:
                    conflict = True
                    break
            if conflict:
                continue
            for lb in placed_labels:
                try:
                    olx, oly = self._offset_points_to_data(
                        ax, lb["x"], lb["y"], lb["dx"], lb["dy"]
                    )
                except Exception:
                    continue
                d = np.hypot(lx - olx, ly - oly)
                if d < label_label_min:
                    conflict = True
                    break
            if not conflict:
                return cand_dx, cand_dy

        r2 = r * 1.5
        for cand_dx, cand_dy in [
            (r2, r2),
            (-r2, r2),
            (r2, -r2),
            (-r2, -r2),
            (r2, 0),
            (-r2, 0),
            (0, r2),
            (0, -r2),
        ]:
            try:
                lx, ly = self._offset_points_to_data(
                    ax, curr_x, curr_y, cand_dx, cand_dy
                )
            except Exception:
                continue
            conflict = False
            for ox, oy in other_centroids:
                if abs(ox - curr_x) < 1e-9 and abs(oy - curr_y) < 1e-9:
                    continue
                if np.hypot(lx - ox, ly - oy) < label_radius_data:
                    conflict = True
                    break
            if conflict:
                continue
            for lb in placed_labels:
                try:
                    olx, oly = self._offset_points_to_data(
                        ax, lb["x"], lb["y"], lb["dx"], lb["dy"]
                    )
                    if np.hypot(lx - olx, ly - oly) < label_label_min:
                        conflict = True
                        break
                except Exception:
                    continue
            if not conflict:
                return cand_dx, cand_dy
        return (r, r) if right_first else (-r, r)

    def _apply_scale(self, data, scale_type):
        if scale_type == "bark":
            return hz_to_bark(data)
        elif scale_type == "log":
            return hz_to_log(data)
        return data

    def _set_ticks(
        self,
        ax,
        axis_name,
        scale_type,
        min_val,
        max_val,
        step_major,
        step_minor,
        use_bark_units=False,
        show_minor_ticks=True,
    ):
        start_val = min(min_val, max_val)
        end_val = max(min_val, max_val)

        boundary_vals = []
        tick_values = []

        if scale_type == "bark" and use_bark_units:
            b_start = math.ceil(start_val)
            b_end = math.floor(end_val)

            if b_start > b_end:
                bark_ticks = [b_start]
            else:
                step = 1 if abs(b_end - b_start) < 15 else 2
                bark_ticks = list(range(int(b_start), int(b_end) + 1, step))

            major_val = bark_ticks
            minor_val = []
            labels = [str(b) for b in bark_ticks]
            tick_values = bark_ticks
        else:
            first_tick = math.ceil(start_val / step_minor) * step_minor
            last_tick = math.floor(end_val / step_minor) * step_minor

            if first_tick > last_tick:
                all_ticks_hz = []
            else:
                all_ticks_hz = np.arange(
                    first_tick, last_tick + step_minor * 0.1, step_minor
                )

            major_hz = [h for h in all_ticks_hz if h % step_major == 0]
            minor_hz = (
                [h for h in all_ticks_hz if h % step_major != 0]
                if show_minor_ticks
                else []
            )

            if start_val not in major_hz:
                boundary_vals.append(start_val)
            if end_val not in major_hz and end_val != start_val:
                boundary_vals.append(end_val)

            all_major_hz = sorted(major_hz + boundary_vals)

            major_val = [self._apply_scale(h, scale_type) for h in all_major_hz]
            minor_val = [self._apply_scale(h, scale_type) for h in minor_hz]

            labels = [
                str(int(h)) if float(h).is_integer() else str(h) for h in all_major_hz
            ]
            tick_values = all_major_hz

        if axis_name == "x":
            ax.set_xticks(major_val)
            labels_obj = ax.set_xticklabels(labels)
            if show_minor_ticks and minor_val:
                ax.set_xticks(minor_val, minor=True)
            elif not show_minor_ticks:
                ax.xaxis.minorticks_off()
            if boundary_vals:
                for lbl_obj, h in zip(labels_obj, tick_values):
                    if h in boundary_vals:
                        lbl_obj.set_color("gray")
        else:
            ax.set_yticks(major_val)
            labels_obj = ax.set_yticklabels(labels)
            if show_minor_ticks and minor_val:
                ax.set_yticks(minor_val, minor=True)
            elif not show_minor_ticks:
                ax.yaxis.minorticks_off()
            if boundary_vals:
                for lbl_obj, h in zip(labels_obj, tick_values):
                    if h in boundary_vals:
                        lbl_obj.set_color("gray")

    def _get_axis_name(self, plot_type):
        names = {
            "f1_f2": "F2",
            "f1_f3": "F3",
            "f1_f2_prime": "F2'",
            "f1_f2_minus_f1": "F2 - F1",
            "f1_f2_prime_minus_f1": "F2' - F1",
        }
        return names.get(plot_type, "X-Axis")

    def _draw_confidence_ellipse(self, x, y, ax, n_std=2.0, **kwargs):
        try:
            x = np.asarray(x, dtype=float)
            y = np.asarray(y, dtype=float)
            if x.size < 3 or y.size < 3:
                return
            cov = np.cov(x, y)
            if cov is None or cov.size != 4:
                return
            if not np.isfinite(cov).all():
                return
            if cov[0, 0] <= 0 or cov[1, 1] <= 0:
                return
            lambda_, v = np.linalg.eig(cov)
            if not np.isfinite(lambda_).all():
                return
            lambda_ = np.maximum(lambda_, 1e-10)
            order = lambda_.argsort()[::-1]
            lambda_, v = lambda_[order], v[:, order]
            angle = np.rad2deg(np.arctan2(v[1, 0], v[0, 0]))
            width = 2 * n_std * np.sqrt(lambda_[0])
            height = 2 * n_std * np.sqrt(lambda_[1])
            if not (
                np.isfinite(width) and np.isfinite(height) and width > 0 and height > 0
            ):
                return
            ell = Ellipse(
                xy=(np.mean(x), np.mean(y)),
                width=width,
                height=height,
                angle=angle,
                **kwargs,
            )
            ell.set_clip_on(False)
            ax.add_patch(ell)
        except Exception:
            pass
