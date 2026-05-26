# core/controller.py

import os
import io
import traceback
import copy
from PySide6.QtCore import Qt, QTimer, QStandardPaths
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox
from matplotlib.figure import Figure

import config
from core.compare_series import (
    CompareSession,
    compare_default_save_basename,
    compare_label_offset_key,
)
from core.compare_runtime import (
    apply_compare_render_to_popup,
    build_compare_series_inputs,
    get_compare_names,
    label_data_for_series,
    label_text_artists_for_series,
    make_compare_plot_key,
    resolve_compare_session,
)
from utils import app_logger
from ui.windows.main_window import MainUI
from ui.dialogs.file_guide import DataGuidePopup
from ui.windows.popup_plot import PlotPopup
from ui.widgets.display_utils import (
    apply_file_indicator_style,
    format_file_label,
    strip_gichan_prefix,
)
from ui.windows.compare_plot import SelectCompareDialog, ComparePlotPopup
from ui.dialogs.vowel_analysis_dialog import VowelAnalysisDialog
from model.data_processor import DataProcessor
from engine.plot_engine import PlotEngine, kor_font
from tools.ruler import RulerTool
from tools.label_move import LabelMoveTool
from utils.math_utils import (
    remove_outliers_mahalanobis,
    lobanov_normalization,
    gerstman_normalization,
    watt_fabricius_normalization,
    bigham_normalization,
    nearey1_normalization,
    to_phonetic_vowel,
)
from model.combined_dataset import build_combined_entry, build_compare_group_entry
from model.formant_txt_export import formant_dataframe_to_txt
from .workers import BatchSaveWorker
from utils import path_prefs


class MainController:
    """
    GichanFormant의 핵심 비즈니스 로직을 제어하는 컨트롤러입니다.
    파일 가이드 연동 및 데이터 기반 인터랙션 제어를 담당합니다.
    """

    def __init__(self, startup_context=None, status_callback=None):
        self.filepaths = []
        self.plot_data_list = []
        self.current_idx = 0
        # 이상치 제거 모드 변경 로그를 위한 직전 상태 저장 (초기 None)
        self.last_outlier_mode = None
        # 저장 다이얼로그에서 사용할 마지막 저장 디렉터리 (없으면 Downloads)
        self.last_save_dir = None
        # 파일 열기 다이얼로그에서 사용할 마지막 선택 디렉터리 (없으면 Documents)
        self.last_open_dir = None

        # startup_context에서 사전 로드된 설정 반영
        context = startup_context or {}
        _loaded_prefs = context.get("path_prefs")

        if _loaded_prefs:
            if _loaded_prefs.get("last_open_dir") and os.path.isdir(
                _loaded_prefs["last_open_dir"]
            ):
                self.last_open_dir = _loaded_prefs["last_open_dir"]
            if _loaded_prefs.get("last_save_dir") and os.path.isdir(
                _loaded_prefs["last_save_dir"]
            ):
                self.last_save_dir = _loaded_prefs["last_save_dir"]
        else:
            # context가 없거나 prefs가 없으면 직접 로딩 시도 (폴더가 존재할 때만 반영)
            _prefs_base = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
            if _prefs_base:
                _loaded = path_prefs.load_path_prefs(_prefs_base)
                if _loaded.get("last_open_dir") and os.path.isdir(
                    _loaded["last_open_dir"]
                ):
                    self.last_open_dir = _loaded["last_open_dir"]
                if _loaded.get("last_save_dir") and os.path.isdir(
                    _loaded["last_save_dir"]
                ):
                    self.last_save_dir = _loaded["last_save_dir"]

        # PySide6에서는 팝업 창이 가비지 컬렉터(GC)에 의해 증발하는 것을
        # 막기 위해 리스트에 참조를 보관해야 합니다.
        self.open_popups = []
        self._compare_virtual_items: dict[int, dict] = {}
        self._compare_virtual_next_id = -1

        self.ruler_tool = RulerTool()
        self.label_move_tool = None  # LabelMoveTool: 단일 플롯 팝업에서만 생성
        self.custom_label_offsets = {}  # (file_idx, plot_type) -> { vowel: (dx_data, dy_data) }

        # 사전 초기화된 엔진 재사용
        self.data_processor = context.get("data_processor") or DataProcessor()
        self.plot_engine = context.get("plot_engine") or PlotEngine()
        self.live_preview_fig = context.get("live_preview_fig") or Figure(
            figsize=(6.5, 6.5), dpi=150
        )

        # LIVE 미리보기 디바운스: 연속 호출 시 마지막 한 번만 렌더 (메인 스레드 블로킹 완화)
        self._live_preview_timer = QTimer()
        self._live_preview_timer.setSingleShot(True)
        self._live_preview_timer.timeout.connect(self._render_live_preview)

        self.ui = MainUI(self, status_callback=status_callback)
        app_logger.set_ui(self.ui)
        # 작업표시줄 아이콘이 처음 실행 시 바로 뜨도록, 창 표시 전에 한 번 더 아이콘 적용
        try:
            if hasattr(self.ui, "_apply_window_icon"):
                self.ui._apply_window_icon()
        except Exception as e:
            app_logger.debug(f"[_apply_window_icon] 초기 아이콘 적용 실패: {e}")

        # 사전 초기화된 Fig가 있다면 첫 렌더링을 즉시 동기적으로 수행하여 스플래시 종료 전 화면을 채웁니다.
        # (실제 창 표시는 main.py에서 splash.finish()와 함께 수행하여 겹침 현상을 방지합니다)
        self._render_live_preview()
        app_logger.info(config.LOG_MSG["APP_START"].format(app_title=config.APP_TITLE))

    def _deferred_init_after_show(self):
        """
        메인 창이 화면에 완전히 표시된 후 수행할 지연 작업들을 처리합니다.
        현재는 대부분의 초기화가 __init__에서 완료되므로, 향후 네트워크 체크나
        복잡한 리소스 로딩이 필요할 경우를 위한 확장 포인트로 남겨둡니다.
        """
        pass

    def _build_outlier_log_message(
        self, total_removed, file_removed, files_with_small_labels, any_label_tested
    ):
        """이상치 제거 적용 결과에 대한 로그 메시지 문자열만 생성한다. append_log는 호출하지 않는다."""
        if total_removed > 0:
            file_removed = sorted(file_removed, key=lambda x: -x[1])
            parts = [f"{name}: {cnt}개" for name, cnt in file_removed[:5]]
            detail = " (" + ", ".join(parts)
            if len(file_removed) > 5:
                detail += " … 외)"
            else:
                detail += ")"
            return config.LOG_MSG["OUTLIER_REMOVED_SUMMARY"].format(
                file_count=len(file_removed), total_removed=total_removed, detail=detail
            )
        if files_with_small_labels:
            parts = []
            for name, labels in files_with_small_labels[:5]:
                preview = ", ".join(labels[:5])
                more = " …" if len(labels) > 5 else ""
                parts.append(f"{name}: {preview}{more}")
            detail = " / ".join(parts)
            return config.LOG_MSG["OUTLIER_NOT_REMOVED_MIN_LABELS"].format(
                detail=detail
            )
        if any_label_tested:
            return config.LOG_MSG["OUTLIER_NOT_REMOVED_NONE"]
        return None

    def on_outlier_mode_changed(self):
        """
        사용자가 이상치 제거 모드(None, 1σ, 2σ)를 변경했을 때의 처리를 담당합니다.
        1. 변경된 모드에 따라 real 화자 항목별로 마할라노비스 기반 이상치를 제거합니다.
           (Combined는 직접 필터링하지 않고, real 항목들이 갱신된 뒤 그것들로부터 재합성합니다.
            그래야 '특정 화자의 클러스터 때문에 다른 화자의 정상 토큰이 제거'되는 일이 없습니다.)
        2. 필터링된 데이터를 각 화자 항목에 반영합니다.
        3. 변경 결과를 로그로 출력하고 실시간 미리보기를 갱신합니다.
        """
        outlier_mode = self.ui.get_outlier_mode()
        prev_outlier_mode = self.last_outlier_mode
        self.last_outlier_mode = outlier_mode
        plot_type = self.ui.get_plot_type()

        if not self.plot_data_list:
            return

        # Combined는 파생 항목이므로 직접 처리하지 않는다.
        real_items = [
            item for item in self.plot_data_list if not item.get("is_combined")
        ]

        # 기존 항목에 df_original이 없으면 현재 df를 원본으로 보존 (호환성)
        for item in real_items:
            if "df_original" not in item:
                item["df_original"] = item["df"].copy()

        if outlier_mode is None:
            # 이전에 이상치 제거가 적용되어 있었다면, 해제 로그를 한 번 남긴다.
            if prev_outlier_mode is not None:
                app_logger.info(config.LOG_MSG["OUTLIER_OFF"])
            for item in real_items:
                item["df"] = item["df_original"].copy()
            self._rebuild_combined_entry()
            self.update_live_preview()
            return

        # 1sigma / 2sigma 적용
        file_removed = []
        total_removed = 0
        files_with_small_labels = []
        any_label_tested = False
        for item in real_items:
            df_orig = item["df_original"]
            filtered_df, n_removed, _, meta = remove_outliers_mahalanobis(
                df_orig, plot_type, outlier_mode
            )
            item["df"] = filtered_df
            total_removed += n_removed
            if n_removed > 0:
                file_removed.append((item["name"], n_removed))
            # 라벨 개수 부족(5개 미만) 메타 정보 수집
            labels_too_small = (meta or {}).get("labels_too_small") or set()
            labels_tested = (meta or {}).get("labels_tested") or set()
            if labels_too_small:
                files_with_small_labels.append((item["name"], sorted(labels_too_small)))
            if labels_tested:
                any_label_tested = True

        msg = self._build_outlier_log_message(
            total_removed, file_removed, files_with_small_labels, any_label_tested
        )
        if msg:
            app_logger.info(msg)

        # 필터링된 real 항목들로부터 Combined를 다시 합성
        self._rebuild_combined_entry()
        self.update_live_preview()

    def _refresh_open_popups(self):
        """
        현재 데이터 상태(이상치 제거, 정규화 등)에 맞춰 이미 열려 있는
        모든 단일 플롯(PlotPopup) 및 비교 플롯(ComparePlotPopup) 창의 그래프를 다시 그립니다.
        """
        for w in self.open_popups:
            if hasattr(w, "on_apply"):
                try:
                    w.on_apply()
                except Exception as e:
                    traceback.print_exc()
                    app_logger.error(config.LOG_MSG["PLOT_REFRESH_ERROR"].format(e=e))

    def _apply_normalization(self, df, norm_name):
        """Raw Hz DataFrame에 정규화 적용.

        W&F(2mW/F)는 코너 모음 'i', 'a' 식별을 위해 라벨을 음성학 코드(Vowel)로 매핑한 뒤 호출합니다.
        한글 라벨(ㅏ, ㅣ 등)도 매핑되어 W&F가 무동작이 되는 사일런트 실패를 방지합니다.
        매핑 후에도 'i' 또는 'a' 토큰이 없으면 경고 로그를 남깁니다(W&F는 적용 불가).
        """
        if not norm_name or df.empty:
            return df.copy()
        df = df.copy()
        label_col = "Label" if "Label" in df.columns else "label"
        if norm_name == "Lobanov":
            return lobanov_normalization(df)
        if norm_name == "Gerstman":
            return gerstman_normalization(df)
        if norm_name == "2mW/F":
            df["Vowel"] = df[label_col].apply(to_phonetic_vowel)
            if not (df["Vowel"] == "i").any() or not (df["Vowel"] == "a").any():
                unique_vowels = sorted(
                    {v for v in df["Vowel"].astype(str).unique() if v}
                )
                app_logger.warning(
                    "[2mW/F] 코너 모음 'i' 또는 'a' 토큰이 없어 정규화가 적용되지 않았습니다. "
                    f"(현재 라벨: {unique_vowels[:10]}{' …' if len(unique_vowels) > 10 else ''})"
                )
            return watt_fabricius_normalization(df, variant="2m")
        if norm_name == "Bigham":
            return bigham_normalization(df)
        if norm_name == "Nearey1":
            return nearey1_normalization(df)
        return df

    def _rebuild_combined_entry(self):
        """real 화자 항목들로부터 Combined 항목을 (재)구성한다.

        - 기존 Combined 항목은 제거 후 새로 만들어 plot_data_list 마지막에 추가.
        - real 항목이 2개 미만이면 Combined는 추가하지 않음.
        - current_idx가 범위를 벗어나면 자동으로 보정.
        """
        self.plot_data_list = [
            it for it in self.plot_data_list if not it.get("is_combined")
        ]
        combined = build_combined_entry(self.plot_data_list)
        if combined is not None:
            self.plot_data_list.append(combined)
        if self.current_idx >= len(self.plot_data_list):
            self.current_idx = max(0, len(self.plot_data_list) - 1)

    def clear_label_offsets_for_popup(self, popup_window):
        """디자인 초기화 시 해당 팝업의 라벨 커스텀 위치를 제거. 초기화 버튼에서 호출."""
        key = getattr(popup_window, "_plot_key", None)
        if key:
            self.custom_label_offsets.pop(key, None)
        key_cmp = getattr(popup_window, "_plot_key_compare", None)
        if key_cmp:
            self.custom_label_offsets.pop((*key_cmp, "blue"), None)
            self.custom_label_offsets.pop((*key_cmp, "red"), None)

    def remove_popup(self, popup):
        """팝업이 닫힐 때 View에서 호출. 리스트 및 라벨 오프셋에서 제거."""
        self._remove_popup_from_list(popup)

    def _remove_popup_from_list(self, popup):
        """QObject.destroyed 시그널로 팝업이 파괴될 때 리스트에서 제거 (예외/강제 종료 시에도 메모리 누수 방지)"""
        key = getattr(popup, "_plot_key", None)
        if key:
            self.custom_label_offsets.pop(key, None)
        key_cmp = getattr(popup, "_plot_key_compare", None)
        if key_cmp:
            self.custom_label_offsets.pop((*key_cmp, "blue"), None)
            self.custom_label_offsets.pop((*key_cmp, "red"), None)
        if popup in self.open_popups:
            self.open_popups.remove(popup)

    def _get_x_axis_label(self, plot_type):
        """플롯 타입에 맞는 X축 라벨 문자열 반환."""
        return config.PLOT_X_AXIS_LABEL.get(plot_type, "X-Axis")

    def _get_axis_units_from_params(self, plot_params):
        """플롯 파라미터에서 F1/F2 단위를 계산해 반환."""
        f1_scale = plot_params.get("f1_scale", "linear")
        f2_scale = plot_params.get("f2_scale", "linear")
        use_bark = plot_params.get("use_bark_units", False)
        f1_unit = "Bark" if (f1_scale == "bark" and use_bark) else "Hz"
        f2_unit = "Bark" if (f2_scale == "bark" and use_bark) else "Hz"
        return f1_unit, f2_unit

    def _read_manual_ranges(self, range_widgets):
        """범위 입력 위젯에서 수동 범위 dict를 읽어 반환."""
        return {
            "y_min": range_widgets["y_min"].text(),
            "y_max": range_widgets["y_max"].text(),
            "x_min": range_widgets["x_min"].text(),
            "x_max": range_widgets["x_max"].text(),
        }

    def _apply_ranges_to_widgets(self, range_widgets, ranges):
        """범위 dict를 입력 위젯에 반영."""
        range_widgets["y_min"].setText(ranges["y_min"])
        range_widgets["y_max"].setText(ranges["y_max"])
        range_widgets["x_min"].setText(ranges["x_min"])
        range_widgets["x_max"].setText(ranges["x_max"])

    def _disable_ruler_for_open_popups(self):
        """열린 팝업 전체에서 눈금자 모드를 비활성화."""
        if not self.ruler_tool.active:
            return
        self.ruler_tool.active = False
        self.ruler_tool.detach()
        self.ruler_tool.clear_all()
        for p in self.open_popups:
            if hasattr(p, "update_ruler_style"):
                p.update_ruler_style(False)
        app_logger.info(config.LOG_MSG["RULER_OFF_INFO"])

    def _disable_label_move_for_open_popups(self):
        """열린 팝업 전체에서 라벨 이동 모드를 비활성화."""
        if not (self.label_move_tool and self.label_move_tool.active):
            return
        self.label_move_tool.active = False
        self.label_move_tool.detach()
        for p in self.open_popups:
            if hasattr(p, "update_label_move_style"):
                p.update_label_move_style(False)
        app_logger.info(config.LOG_MSG["LABEL_MOVE_OFF"])

    def _get_label_offset_delta(self, dragging):
        """드래깅 결과에서 중심 대비 라벨 오프셋(dx, dy)을 계산."""
        return dragging["lx"] - dragging["cx"], dragging["ly"] - dragging["cy"]

    # --- 데이터 관리 로직 ---

    def handle_file_drop(self, files):
        """
        사용자가 메인 창에 파일을 드롭했을 때의 진입점입니다.
        전달받은 파일 경로 리스트를 내부 로드 프로세스로 연결합니다.
        """
        self._process_new_files(files)

    def open_file_dialog(self):
        """파일 탐색기를 통한 파일 추가 요청(실제 다이얼로그는 View에서 처리)"""
        if hasattr(self.ui, "request_file_open"):
            self.ui.request_file_open(self._process_new_files)

    def add_files(self, filepaths):
        """
        새로운 데이터 파일들을 로드하고 내부 메모리(plot_data_list)에 추가합니다.

        Args:
            filepaths (list): 로드할 파일들의 절대 경로 리스트

        Returns:
            dict: 로드 성공 횟수, 실패 에러 정보, F3 가용 여부, 제외된 데이터 행 정보 등을 포함한 결과 요약
        """
        # Combined는 항상 마지막에 위치하므로, 새 화자 항목을 append하기 전에 일단 제거한다.
        # (작업 마지막에 _rebuild_combined_entry로 다시 추가)
        self.plot_data_list = [
            it for it in self.plot_data_list if not it.get("is_combined")
        ]

        result = {
            "success_count": 0,
            "failed": [],  # [(fname, errors), ...]
            "has_f3_all": False,
            "total_files": len(self.filepaths),
            "row_dropped": [],  # [(fname, detail_dict), ...]
        }
        new_files = [f for f in filepaths if f not in self.filepaths]
        if not new_files:
            # 새 파일이 없어도, 제거했던 Combined를 동일 상태로 복원
            self._rebuild_combined_entry()
            result["total_files"] = len(self.filepaths)
            return result

        for f in new_files:
            fname = os.path.basename(f)
            temp_processor = DataProcessor()
            success, has_f3, errors = temp_processor.load_files([f])

            if success:
                # 로드된 원본 DataFrame 복사본 (plot_data_list 항목용)
                raw_df = temp_processor.get_data(copy=False)
                self.filepaths.append(f)
                self.plot_data_list.append(
                    {
                        "name": fname,
                        "df": raw_df.copy(),
                        "df_original": raw_df.copy(),
                        "has_f3": has_f3,
                    }
                )
                result["success_count"] += 1
                # 데이터 조건 위반으로 제외된 행이 있다면, 파일명 기준으로 누락 라벨 정보를 누적
                for path, drop_report in getattr(temp_processor, "row_drops", []):
                    if drop_report:
                        result["row_dropped"].append(
                            (os.path.basename(path), drop_report)
                        )
            else:
                result["failed"].append((fname, errors or []))

        # 새로 추가된 real 항목들로 Combined를 재구성
        self._rebuild_combined_entry()

        result["total_files"] = len(self.filepaths)
        # has_f3는 real 화자 파일들만 보고 판단 (Combined는 real의 has_f3로부터 파생)
        real_items_for_check = [
            d for d in self.plot_data_list if not d.get("is_combined")
        ]
        result["has_f3_all"] = (
            all(d["has_f3"] for d in real_items_for_check)
            if real_items_for_check
            else False
        )
        return result

    def _apply_file_load_result_to_ui(self, result):
        """
        파일 로드 결과를 바탕으로 메인 UI(테이블, 로그, 필터 패널)를 갱신합니다.
        로드된 파일의 통계 정보 및 누락된 데이터에 대한 안내를 수행합니다.
        """
        if result["success_count"] > 0:
            app_logger.info(
                config.LOG_MSG["FILE_LOAD_NEW_SUCCESS"].format(
                    success_count=result["success_count"],
                    total_files=result["total_files"],
                )
            )
            # 신규 파일 로드 로그 이후, 조건 미충족으로 제외된 행에 대한 라벨별 누락 정보를 파일별로 출력
            for name, drop_report in result.get("row_dropped", []):
                if drop_report:
                    detail = ", ".join(
                        f"{lbl}: {cnt}개" for lbl, cnt in drop_report.items()
                    )
                    app_logger.info(
                        config.LOG_MSG["FILE_ROW_DROPPED"].format(
                            name=name, detail=detail
                        )
                    )
        if result["failed"]:
            names = ", ".join(name for name, _ in result["failed"])
            app_logger.warning(
                config.LOG_MSG["FILE_LOAD_FAILED_SUMMARY"].format(
                    fail_count=len(result["failed"]), names=names
                )
            )
            for name, errs in result["failed"][:3]:
                if errs:
                    sample_path, msg = errs[0]
                    app_logger.debug(
                        config.LOG_MSG["FILE_LOAD_FAILED_DEBUG"].format(
                            name=name, msg=msg
                        )
                    )

        self.ui.update_file_status(result["total_files"])
        self.ui.toggle_f3_options(result["has_f3_all"])
        if result["success_count"] > 0:
            self.update_live_preview()

    def _process_new_files(self, files):
        """새 파일 로드 후 UI에 결과 반영 (add_files + _apply_file_load_result_to_ui)."""
        result = self.add_files(files)
        self._apply_file_load_result_to_ui(result)

    def remove_file(self, index):
        """테이블의 '×' 버튼 클릭 시 특정 인덱스 데이터 삭제"""
        if index < 0 or index >= len(self.plot_data_list):
            # 잘못된 인덱스는 조용히 무시하되, 디버그 로그로만 남긴다.
            app_logger.debug(
                config.LOG_MSG.get(
                    "FILE_REMOVE_INDEX_INVALID",
                    "[DEBUG] remove_file: 잘못된 인덱스 요청",
                )
            )
            return

        # Combined 항목은 테이블에 노출되지 않으므로 이 경로로 들어올 일이 없지만,
        # 어떤 경로로든 호출되었을 때 안전하게 무시한다 (Combined는 파생 항목).
        if self.plot_data_list[index].get("is_combined"):
            app_logger.debug("[remove_file] Combined 항목은 직접 삭제할 수 없습니다.")
            return

        removed_name = self.plot_data_list[index]["name"]
        # index는 real 화자 항목(0..N-1) 범위 안에 있으므로 filepaths 인덱스와 동일하게 사용 가능.
        self.filepaths.pop(index)
        self.plot_data_list.pop(index)

        if index < self.current_idx:
            self.current_idx -= 1

        # 남은 real 항목들로 Combined 재구성 (real이 1개 이하가 되면 Combined 자동 제거).
        # 메서드 내부에서 current_idx 경계 보정도 수행.
        self._rebuild_combined_entry()

        # UI 갱신 (count는 real 파일 수 = filepaths 길이)
        self.ui.update_file_status(len(self.filepaths))
        app_logger.info(
            config.LOG_MSG["FILE_REMOVED"].format(removed_name=removed_name)
        )

        # 남은 데이터에 따라 버튼 상태 재조정 (Combined는 real의 파생이므로 real만 확인)
        real_items = [d for d in self.plot_data_list if not d.get("is_combined")]
        if not real_items:
            self.ui.toggle_f3_options(False)
        else:
            current_has_f3 = all(d["has_f3"] for d in real_items)
            self.ui.toggle_f3_options(current_has_f3)

        # 제거 후 라이브 모니터 갱신
        self.update_live_preview()

    def reset_data(self):
        """모든 데이터와 설정을 리셋 (사용자 확인은 View에서 수행)"""
        if not self.filepaths:
            return
        self.filepaths = []
        self.plot_data_list = []
        self.current_idx = 0
        self.data_processor = DataProcessor()
        self.ui.reset_ui_state()
        app_logger.info(config.LOG_MSG["RESET_ALL"])

    # --- 라이브 모니터 렌더링 로직 ---

    def get_initial_open_dir(self):
        """파일 열기 다이얼로그 초기 폴더: 최근 선택 폴더가 있으면 사용, 없으면 문서 폴더."""
        if self.last_open_dir and os.path.isdir(self.last_open_dir):
            return self.last_open_dir
        return (
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DocumentsLocation
            )
            or ""
        )

    def set_last_open_dir(self, dir_path):
        """파일 열기 후 선택한 폴더를 기억 (다음 열기 시 초기 폴더로 사용)."""
        if dir_path and os.path.isdir(dir_path):
            self.last_open_dir = dir_path
            self._save_path_prefs()

    def set_last_save_dir(self, dir_path):
        """저장 후 선택한 폴더를 기억 (다음 저장 시 초기 폴더로 사용)."""
        if dir_path and os.path.isdir(dir_path):
            self.last_save_dir = dir_path
            self._save_path_prefs()

    def _save_path_prefs(self):
        """현재 last_open_dir / last_save_dir를 JSON에 저장."""
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        if not base:
            return
        path_prefs.save_path_prefs(
            base,
            {
                "last_open_dir": self.last_open_dir,
                "last_save_dir": self.last_save_dir,
            },
        )

    def _get_default_design(self):
        """라이브 모니터 등 UI 객체가 없을 때 사용할 기본 디자인 설정"""
        return {
            "show_raw": True,
            "show_centroid": True,
            "raw_color": "#606060",
            "lbl_color": "#E64A19",
            "lbl_size": 16,
            "lbl_bold": True,
            "lbl_italic": False,
            "ell_thick": 1.0,
            "ell_style": ":",
            "ell_color": "#606060",
            "ell_fill_color": None,
            "ell_fill_opacity": 0.15,
            "box_spines": False,
            "show_grid": False,
            "y_label_rotation": False,
            "show_minor_ticks": True,
        }

    def _get_preview_design(self, params):
        """LIVE MONITOR용 디자인. 정규화 모드는 플롯 창과 동일하게 테두리·그리드 ON."""
        design = self._get_default_design()
        if (params or {}).get("normalization"):
            design.update(
                {
                    "box_spines": True,
                    "show_grid": True,
                    "y_label_rotation": True,
                }
            )
        return design

    def _set_preview_empty(self):
        """LIVE 모니터를 데이터 없음 상태로 표시합니다."""
        self.ui.preview_label.clear()
        self.ui.preview_label.setText("LIVE")
        if hasattr(self.ui, "preview_info_label"):
            self.ui.preview_info_label.setText("")

    def _norm_ranges_for_widgets(self, norm):
        """정규화 축 범위 dict (range_widgets용 문자열 값)."""
        r = PlotEngine.NORM_RANGES.get(norm, PlotEngine.NORM_RANGES["Lobanov"])
        return {k: str(r[k]) for k in ["y_min", "y_max", "x_min", "x_max"]}

    def _sync_single_popup_normalization(self, popup_window):
        """메인 창 정규화 선택을 단일 PlotPopup에 반영."""
        if not getattr(popup_window, "uses_main_normalization", False):
            return
        norm = self.ui.get_normalization()
        prev = getattr(popup_window, "_last_synced_normalization", "__unset__")
        norm_changed = norm != prev
        popup_window.normalization = norm
        popup_window._last_synced_normalization = norm
        if hasattr(popup_window, "lbl_norm_value"):
            popup_window.lbl_norm_value.setText(norm or "없음")
        if norm_changed:
            if norm:
                self._apply_ranges_to_widgets(
                    popup_window.range_widgets, self._norm_ranges_for_widgets(norm)
                )
            elif hasattr(popup_window, "_reset_ranges_to_default"):
                popup_window._reset_ranges_to_default(apply_plot=False)
        if hasattr(popup_window, "_apply_normalization_axis_ui"):
            popup_window._apply_normalization_axis_ui()

    def _render_live_preview_content(
        self, current_data, params, smart_ranges, default_design
    ):
        """LIVE 모니터에 플롯을 그려 버퍼로 저장한 뒤 레이블에 표시하고 하단 정보를 갱신합니다."""
        self.live_preview_fig.clear()
        norm = (params or {}).get("normalization")
        if norm:
            df_norm = self._apply_normalization(current_data["df"], norm)
            manual_ranges = self._norm_ranges_for_widgets(norm)
            *_, _ = self.plot_engine.draw_single_normalized(
                self.live_preview_fig,
                df_norm,
                norm,
                manual_ranges=manual_ranges,
                design_settings=default_design,
                plot_params=params,
            )
        else:
            *_, _ = self.plot_engine.draw_plot(
                self.live_preview_fig,
                current_data["df"],
                params,
                manual_ranges=smart_ranges,
                design_settings=default_design,
            )

        buf = io.BytesIO()
        buf = io.BytesIO()
        self.live_preview_fig.savefig(buf, format="png", facecolor="white")
        buf.seek(0)

        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())

        # High-DPI 대응: label의 논리 좌표와 실제 픽셀 해상도를 맞춤
        dpr = self.ui.preview_label.devicePixelRatio()
        w = int(self.ui.preview_label.width() * dpr)
        h = int(self.ui.preview_label.height() * dpr)

        scaled_pixmap = pixmap.scaled(
            w,
            h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled_pixmap.setDevicePixelRatio(dpr)

        self.ui.preview_label.setPixmap(scaled_pixmap)
        buf.close()

        # 모니터 하단 정보: 파일명(확장자 제거), F1(스케일, 단위) / F2(스케일, 단위) / 이상치 제거(선택 시만)
        if hasattr(self.ui, "preview_info_label"):
            fname_base = strip_gichan_prefix(os.path.splitext(current_data["name"])[0])
            norm = (params or {}).get("normalization")
            if norm:
                line2 = f"nF1 / nF2 / {norm} 정규화"
            else:
                f1_scale = params.get("f1_scale", "linear")
                f2_scale = params.get("f2_scale", "linear")
                use_bark = params.get("use_bark_units", False)
                u1 = "Bark" if (f1_scale == "bark" and use_bark) else "Hz"
                u2 = "Bark" if (f2_scale == "bark" and use_bark) else "Hz"
                x_names = {
                    "f1_f2": "F2",
                    "f1_f3": "F3",
                    "f1_f2_prime": "F2'",
                    "f1_f2_minus_f1": "F2-F1",
                    "f1_f2_prime_minus_f1": "F2'-F1",
                }
                x_name = x_names.get(params["type"], "F2")
                disp_f1, disp_f2 = self.ui.get_display_scale_for_preview()
                line2 = (
                    f"F1({disp_f1.capitalize()}, {u1}) / "
                    f"{x_name}({disp_f2.capitalize()}, {u2})"
                )
            outlier_mode = self.ui.get_outlier_mode()
            if outlier_mode == "1sigma":
                line2 += " / 이상치 제거 : 1σ"
            elif outlier_mode == "2sigma":
                line2 += " / 이상치 제거 : 2σ"
            self.ui.preview_info_label.setText(f"{fname_base}\n{line2}")

    def update_live_preview(self):
        """LIVE 미리보기 갱신 요청. 디바운스(150ms) 후 한 번만 렌더링해 메인 스레드 블로킹을 줄입니다."""
        if not hasattr(self, "ui") or not hasattr(self.ui, "preview_label"):
            return
        if not self.plot_data_list:
            self._set_preview_empty()
            return
        self._live_preview_timer.stop()
        self._live_preview_timer.start(150)

    def _render_live_preview(self):
        """디바운스 타이머 만료 시 실제 LIVE 미리보기 렌더링을 수행합니다."""
        if not hasattr(self, "ui") or not hasattr(self.ui, "preview_label"):
            return
        if not self.plot_data_list:
            self._set_preview_empty()
            return
        current_data = self.plot_data_list[0]
        params = self._get_main_ui_plot_params()
        if params.get("normalization"):
            smart_ranges = self._norm_ranges_for_widgets(params["normalization"])
        else:
            smart_ranges = self._get_smart_ranges(
                params["type"],
                params["use_bark_units"],
                params["f1_scale"],
                params["f2_scale"],
            )
        default_design = self._get_preview_design(params)
        try:
            self._render_live_preview_content(
                current_data, params, smart_ranges, default_design
            )
        except Exception as e:
            traceback.print_exc()
            try:
                self.live_preview_fig.clear()
                ax = self.live_preview_fig.add_subplot(111)
                ax.text(
                    0.5,
                    0.5,
                    "LIVE 렌더링 오류",
                    ha="center",
                    va="center",
                    fontfamily=kor_font,
                    fontsize=11,
                )
                ax.set_axis_off()
            except Exception as e:
                app_logger.debug(f"[_render_live_preview] 렌더링 오류 폴백 실패: {e}")
            self.ui.preview_label.clear()
            self.ui.preview_label.setText("LIVE 렌더링 오류")
            if hasattr(self.ui, "preview_info_label"):
                self.ui.preview_info_label.setText(str(e))

    # --- 팝업 생성 및 가이드 로직 ---

    def open_guide(self):
        """데이터 파일 준비 가이드 팝업 표시"""
        guide = DataGuidePopup(self.ui)
        guide.exec()

    def open_single_plot(self):
        """현재 데이터로 시각화 창(PlotPopup)을 생성합니다."""
        self._cleanup_popups()
        if not self.plot_data_list:
            self.ui.show_warning("데이터 없음", "분석할 데이터를 먼저 로드해 주세요.")
            return

        fig = Figure(figsize=(6.5, 6.5), dpi=100)
        plot_type = self.ui.get_plot_type()
        x_label = self._get_x_axis_label(plot_type)
        params = self._get_main_ui_plot_params()
        norm = params.get("normalization")

        popup = PlotPopup(
            parent=self.ui,
            controller=self,
            figure=fig,
            x_axis_label=x_label,
            normalization=norm,
        )
        popup.set_initial_plot_state(
            params,
            copy.deepcopy(self.plot_data_list),
            self.current_idx,
        )
        popup._last_synced_normalization = norm

        current_data = popup.plot_data_snapshot[popup.current_idx]
        f1_scale = popup.fixed_plot_params.get("f1_scale", "linear")
        f2_scale = popup.fixed_plot_params.get("f2_scale", "linear")
        use_bark = popup.fixed_plot_params.get("use_bark_units", False)
        f1_unit, f2_unit = self._get_axis_units_from_params(popup.fixed_plot_params)

        if norm:
            self._apply_ranges_to_widgets(
                popup.range_widgets, self._norm_ranges_for_widgets(norm)
            )
            popup._apply_normalization_axis_ui()
        else:
            try:
                popup.update_unit_labels(f1_unit, f2_unit)
            except TypeError:
                popup.update_unit_labels(f1_unit)
            smart_ranges = self._get_smart_ranges(
                plot_type, use_bark, f1_scale, f2_scale
            )
            self._apply_ranges_to_widgets(popup.range_widgets, smart_ranges)

        popup.update_file_nav_indicator(popup.current_idx, current_data)

        filter_state = popup.get_filter_state()
        ds_settings = popup.get_design_settings() or self._get_default_design()

        plot_type_fixed = (
            "f1_f2" if norm else popup.fixed_plot_params.get("type", "f1_f2")
        )
        plot_key_suffix = (plot_type_fixed, norm) if norm else (plot_type_fixed,)
        custom_offsets = self.custom_label_offsets.get(
            (popup.current_idx, *plot_key_suffix), {}
        )
        layer_overrides = popup.get_layer_design_overrides()
        if norm:
            df_norm = self._apply_normalization(current_data["df"], norm)
            popup.fixed_plot_params = dict(
                popup.fixed_plot_params or {}, normalization=norm
            )
            manual_ranges = self._read_manual_ranges(popup.range_widgets)
            sigma = float(popup.fixed_plot_params.get("sigma", config.DEFAULT_SIGMA))
            _, snapping_data, label_data, label_text_artists = (
                self.plot_engine.draw_single_normalized(
                    fig,
                    df_norm,
                    norm,
                    manual_ranges=manual_ranges,
                    filter_state=filter_state,
                    design_settings=ds_settings,
                    sigma=sigma,
                    custom_label_offsets=custom_offsets,
                    layer_overrides=layer_overrides,
                    plot_params=popup.fixed_plot_params,
                )
            )
            popup._update_window_title(current_data["name"])
        else:
            _, snapping_data, label_data, label_text_artists = (
                self.plot_engine.draw_plot(
                    fig,
                    current_data["df"],
                    popup.fixed_plot_params,
                    manual_ranges=smart_ranges,
                    filter_state=filter_state,
                    design_settings=ds_settings,
                    custom_label_offsets=custom_offsets,
                    layer_overrides=layer_overrides,
                )
            )
        popup.set_draw_result(
            snapping_data,
            label_data,
            label_text_artists,
            (popup.current_idx, *plot_key_suffix),
        )
        popup.canvas.draw()

        popup.show()
        self.open_popups.append(popup)
        if hasattr(popup, "_refresh_layer_dock_vowels"):
            popup._refresh_layer_dock_vowels()
        app_logger.info(
            config.LOG_MSG["PLOT_OPEN_DONE"].format(fname=current_data["name"])
        )

    def open_vowel_analysis_window(self, popup_window):
        """popup_plot 또는 compare_plot의 '모음 상세 분석' 클릭 시 호출. 해당 창의 파일(들)에 대한 분석 창을 연다."""
        self._cleanup_popups()
        snapshot = getattr(popup_window, "plot_data_snapshot", None)
        params = getattr(popup_window, "fixed_plot_params", None)
        if (
            snapshot is None
            and hasattr(popup_window, "idx_blue")
            and hasattr(popup_window, "idx_red")
        ):
            data_blue, data_red = self.get_compare_data(
                popup_window.idx_blue, popup_window.idx_red
            )
            if data_blue and data_red:
                snapshot = [data_blue, data_red]
            params = params or self._get_current_plot_params(popup_window)
        if not snapshot or not params:
            return
        outlier_mode = self.get_outlier_mode()
        if outlier_mode == "1sigma":
            suffix = " (이상치 제거 : 1σ)"
        elif outlier_mode == "2sigma":
            suffix = " (이상치 제거 : 2σ)"
        else:
            suffix = ""
        if len(snapshot) == 1:
            title_suffix = snapshot[0].get("name", "") + suffix
        elif len(snapshot) == 2 and hasattr(popup_window, "idx_blue"):
            # 다중 플롯(비교) 모드: 파일A, 파일B의 ...
            names = [snapshot[0].get("name", ""), snapshot[1].get("name", "")]
            title_suffix = f"{names[0]}, {names[1]}{suffix}"
        else:
            if len(snapshot) > 0:
                first_name = snapshot[0].get("name", "")
                title_suffix = f"{first_name} 외 {len(snapshot) - 1}개{suffix}"
            else:
                title_suffix = "데이터 없음" + suffix
        norm = (params or {}).get("normalization")
        if norm:
            title_suffix += f" / {norm}"
        app_logger.info(
            config.LOG_MSG["ANALYSIS_OPEN"].format(title_suffix=title_suffix)
        )
        initial_tab = getattr(popup_window, "current_idx", 0)
        dlg = VowelAnalysisDialog(
            popup_window,
            self,
            snapshot,
            params,
            title_suffix,
            initial_tab_idx=initial_tab,
        )
        popup_window.raise_()
        popup_window.activateWindow()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        self.open_popups.append(dlg)

    # --- 다중 비교 팝업 및 제어 로직 ---

    def open_compare_dialog(self, current_idx, parent_window=None):
        """다중 비교를 위한 대상 파일 선택 창(SelectCompareDialog)을 호출합니다."""
        # 비교 기능은 real 화자 파일 ≥ 2개일 때만 의미가 있다.
        real_count = sum(1 for it in self.plot_data_list if not it.get("is_combined"))
        if real_count < 2:
            (parent_window or self.ui).show_warning(
                "데이터 부족",
                "비교할 대상이 부족합니다.\n2개 이상의 데이터를 로드해 주세요.",
            )
            return

        # Combined 항목 자체는 비교의 시작점으로 사용할 수 없다 (여러 화자가 합쳐진 파생 데이터).
        if 0 <= current_idx < len(self.plot_data_list) and self.plot_data_list[
            current_idx
        ].get("is_combined"):
            (parent_window or self.ui).show_warning(
                "비교 불가",
                "Combined 항목은 다중 비교의 기준이 될 수 없습니다.\n"
                "비교를 시작하려면 개별 화자 파일로 먼저 이동해 주세요.",
            )
            return

        self._disable_ruler_for_open_popups()
        self._disable_label_move_for_open_popups()

        dialog = SelectCompareDialog(parent_window or self.ui, self, current_idx)
        dialog.exec()

    def open_compare_plot(
        self, current_idx, target_idx, normalization=None, parent_window=None
    ):
        """선택된 두 데이터로 다중 비교 시각화 창(ComparePlotPopup)을 생성합니다."""
        self.open_compare_plot_for_groups(
            [current_idx],
            [target_idx],
            normalization=normalization,
            parent_window=parent_window,
        )

    def open_compare_plot_for_groups(
        self,
        left_indices: list[int],
        right_indices: list[int],
        normalization=None,
        parent_window=None,
    ):
        """양쪽 그룹(각 1~N 파일)을 combine한 뒤 compare 창을 연다."""
        left_item = self.build_compare_group_from_indices(left_indices)
        right_item = self.build_compare_group_from_indices(right_indices)
        if left_item is None or right_item is None:
            (parent_window or self.ui).show_warning(
                "비교 불가",
                "선택한 그룹에서 비교할 데이터를 만들 수 없습니다.",
            )
            return
        idx_left = self.register_compare_virtual_item(left_item)
        idx_right = self.register_compare_virtual_item(right_item)
        self.open_compare_plot_for_indices(
            [idx_left, idx_right],
            normalization=normalization,
            parent_window=parent_window,
            virtual_indices=(idx_left, idx_right),
        )

    def open_compare_plot_for_indices(
        self,
        indices: list[int],
        normalization=None,
        parent_window=None,
        *,
        virtual_indices: tuple[int, ...] | None = None,
    ):
        """N개 데이터 인덱스로 compare 창을 연다. UI 탭은 0·1번만, 렌더는 session 전체."""
        if len(indices) < 2:
            (parent_window or self.ui).show_warning(
                "비교 불가",
                "compare에는 2개 이상의 데이터가 필요합니다.",
            )
            return

        current_idx, target_idx = indices[0], indices[1]
        session = CompareSession.from_data_indices(*indices)

        self._cleanup_popups()
        try:
            fig = Figure(figsize=(6.5, 6.5), dpi=100)

            plot_type = self.ui.get_plot_type()
            x_label = self._get_x_axis_label(plot_type)
            self._disable_ruler_for_open_popups()

            popup = ComparePlotPopup(
                parent_window or self.ui,
                self,
                fig,
                current_idx,
                target_idx,
                x_axis_label=x_label,
                normalization=normalization,
            )
            popup.compare_session = session
            popup.fixed_plot_params = self._get_current_plot_params()
            if virtual_indices:
                popup._compare_virtual_indices = tuple(virtual_indices)
                popup.destroyed.connect(
                    lambda *_args, v=tuple(virtual_indices): self._release_compare_virtual_indices(
                        v
                    )
                )

            if not normalization:
                f1_scale = popup.fixed_plot_params.get("f1_scale", "linear")
                f2_scale = popup.fixed_plot_params.get("f2_scale", "linear")
                use_bark = popup.fixed_plot_params.get("use_bark_units", False)
                f1_unit, _ = self._get_axis_units_from_params(popup.fixed_plot_params)
                try:
                    popup.update_unit_labels(f1_unit)
                except TypeError as e:
                    app_logger.debug(
                        f"[open_compare_plot] 단위 라벨 업데이트 실패: {e}"
                    )
                smart_ranges = self._get_smart_ranges(
                    plot_type, use_bark, f1_scale, f2_scale
                )
                self._apply_ranges_to_widgets(popup.range_widgets, smart_ranges)

            self._disable_label_move_for_open_popups()

            popup.show()
            QTimer.singleShot(
                0,
                lambda: self._refresh_compare_plot_for_session(
                    fig,
                    popup.canvas,
                    popup.range_widgets,
                    None,
                    popup,
                    session,
                ),
            )

            self.open_popups.append(popup)

            names = get_compare_names(self, session)
            log_msg = f"다중 비교 플롯 창 생성 완료: {', '.join(names)}"
            if normalization:
                log_msg += f" (정규화 : {normalization})"
            app_logger.info(log_msg)
        except Exception as e:
            traceback.print_exc()
            (parent_window or self.ui).show_critical(
                "다중 플롯 오류",
                f"다중 플롯 창을 열 수 없습니다.\n\n{e}",
            )
            app_logger.error(config.LOG_MSG["PLOT_OPEN_FAIL"].format(e=e))

    def refresh_compare_plot(
        self, figure, canvas, range_widgets, lbl_info, popup_window, idx_blue, idx_red
    ):
        """다중 비교 플롯 창의 범위를 적용하고 캔버스를 갱신합니다."""
        session = resolve_compare_session(popup_window, idx_blue, idx_red)
        self._refresh_compare_plot_for_session(
            figure, canvas, range_widgets, lbl_info, popup_window, session
        )

    def _refresh_compare_plot_for_session(
        self,
        figure,
        canvas,
        range_widgets,
        lbl_info,
        popup_window,
        session: CompareSession,
    ):
        if (
            figure is None
            or canvas is None
            or range_widgets is None
            or popup_window is None
        ):
            return
        try:
            manual_ranges = self._read_manual_ranges(range_widgets)

            popup_window.fixed_plot_params = self._get_current_plot_params(popup_window)
            if hasattr(popup_window, "cb_sigma") and popup_window.cb_sigma is not None:
                try:
                    popup_window.fixed_plot_params = dict(
                        popup_window.fixed_plot_params or {},
                        sigma=float(popup_window.cb_sigma.currentText()),
                    )
                except (ValueError, TypeError) as e:
                    app_logger.debug(f"[refresh_compare_plot] 시그마 값 파싱 실패: {e}")

            norm = popup_window.normalization
            ds_settings = (
                popup_window.get_design_settings() or self._get_default_design()
            )
            sigma = (
                popup_window.fixed_plot_params.get("sigma", 2.0)
                if popup_window.fixed_plot_params
                else 2.0
            )

            if norm and hasattr(self.plot_engine, "draw_compare_plot_normalized"):
                popup_window.fixed_plot_params = dict(
                    popup_window.fixed_plot_params or {}, normalization=norm
                )
                plot_key = make_compare_plot_key(session, "f1_f2", norm)
                series_inputs = build_compare_series_inputs(
                    self,
                    session,
                    popup_window,
                    design_settings=ds_settings,
                    plot_type="f1_f2",
                    norm=norm,
                    plot_key=plot_key,
                )
                result = self.plot_engine.draw_compare_plot_normalized(
                    figure,
                    series_inputs,
                    norm,
                    design_settings=ds_settings,
                    sigma=sigma,
                    manual_ranges=manual_ranges,
                )
            elif hasattr(self.plot_engine, "draw_compare_plot"):
                plot_type = popup_window.fixed_plot_params.get("type", "f1_f2")
                plot_key = make_compare_plot_key(session, plot_type, None)
                series_inputs = build_compare_series_inputs(
                    self,
                    session,
                    popup_window,
                    design_settings=ds_settings,
                    plot_type=plot_type,
                    norm=None,
                    plot_key=plot_key,
                )
                result = self.plot_engine.draw_compare_plot(
                    figure,
                    series_inputs,
                    popup_window.fixed_plot_params,
                    manual_ranges=manual_ranges,
                    design_settings=ds_settings,
                )
            else:
                figure.clear()
                ax = figure.add_subplot(111)
                ax.text(
                    0.5,
                    0.5,
                    "[알림] plot_engine.py 내에\ndraw_compare_plot() 구현이 필요합니다.",
                    ha="center",
                    va="center",
                    fontfamily=kor_font,
                    fontsize=12,
                )
                popup_window.snapping_data = []
                canvas.draw()
                return

            apply_compare_render_to_popup(popup_window, result, session, plot_key)
            canvas.draw()

            if self.ruler_tool.active and figure.axes:
                r_design = getattr(popup_window, "design_settings", None) or {}
                if not r_design and getattr(popup_window, "design_tab", None):
                    r_design = getattr(
                        popup_window.design_tab, "get_current_settings", lambda: {}
                    )()
                self.ruler_tool.set_context(
                    canvas,
                    figure.axes[0],
                    popup_window.fixed_plot_params,
                    popup_window.snapping_data,
                    r_design or None,
                )
            if self.label_move_tool and self.label_move_tool.active and figure.axes:
                series = getattr(popup_window, "_label_move_series", None)
                if series:
                    ld = label_data_for_series(popup_window, series)
                    lta = label_text_artists_for_series(popup_window, series)
                    design = getattr(popup_window, "design_settings", None) or (
                        getattr(popup_window, "design_tab", None)
                        and getattr(
                            popup_window.design_tab, "get_current_settings", lambda: {}
                        )()
                    )
                    ell_color = (design.get(series) or {}).get(
                        "ell_color", "#1976D2" if series == "blue" else "#E64A19"
                    )
                    self.label_move_tool.set_context(
                        canvas,
                        figure.axes[0],
                        ld,
                        highlight_color=ell_color,
                        label_text_artists=lta,
                    )
        except Exception as e:
            traceback.print_exc()
            app_logger.error(config.LOG_MSG["PLOT_REFRESH_FAIL"].format(e=e))
            try:
                figure.clear()
                ax = figure.add_subplot(111)
                ax.text(
                    0.5,
                    0.5,
                    "다중 플롯 렌더링 오류",
                    ha="center",
                    va="center",
                    fontfamily=kor_font,
                    fontsize=11,
                )
                ax.set_axis_off()
                canvas.draw()
            except Exception as e:
                app_logger.debug(f"[refresh_compare_plot] 렌더링 오류 폴백 실패: {e}")

    # --- 팝업 UI 내부에서 호출되는 액션 핸들러들 ---

    def refresh_plot(self, figure, canvas, range_widgets, lbl_info, popup_window):
        """[범위 적용] 버튼 클릭 또는 필터/디자인 적용 시 현재 입력된 상태로 플롯을 갱신합니다."""
        try:
            manual_ranges = self._read_manual_ranges(range_widgets)

            self._sync_single_popup_normalization(popup_window)
            popup_window.fixed_plot_params = self._get_current_plot_params(popup_window)
            data_list = popup_window.plot_data_snapshot or self.plot_data_list
            idx = popup_window.current_idx
            current_data = data_list[idx]
            norm = getattr(popup_window, "normalization", None) or (
                popup_window.fixed_plot_params or {}
            ).get("normalization")
            plot_type = (
                "f1_f2" if norm else popup_window.fixed_plot_params.get("type", "f1_f2")
            )
            plot_key_suffix = (plot_type, norm) if norm else (plot_type,)
            custom_offsets = self.custom_label_offsets.get((idx, *plot_key_suffix), {})

            filter_state = popup_window.get_filter_state()
            ds_settings = (
                popup_window.get_design_settings() or self._get_default_design()
            )
            layer_overrides = popup_window.get_layer_design_overrides()
            if norm:
                popup_window.fixed_plot_params = dict(
                    popup_window.fixed_plot_params or {}, normalization=norm
                )
                if hasattr(popup_window, "cb_sigma") and popup_window.cb_sigma:
                    try:
                        popup_window.fixed_plot_params["sigma"] = float(
                            popup_window.cb_sigma.currentText()
                        )
                    except (ValueError, TypeError):
                        pass
                df_norm = self._apply_normalization(current_data["df"], norm)
                sigma = float(
                    popup_window.fixed_plot_params.get("sigma", config.DEFAULT_SIGMA)
                )
                _, snapping_data, label_data, label_text_artists = (
                    self.plot_engine.draw_single_normalized(
                        figure,
                        df_norm,
                        norm,
                        manual_ranges=manual_ranges,
                        filter_state=filter_state,
                        design_settings=ds_settings,
                        sigma=sigma,
                        custom_label_offsets=custom_offsets,
                        layer_overrides=layer_overrides,
                        plot_params=popup_window.fixed_plot_params,
                    )
                )
                popup_window._update_window_title(current_data["name"])
            else:
                _, snapping_data, label_data, label_text_artists = (
                    self.plot_engine.draw_plot(
                        figure,
                        current_data["df"],
                        popup_window.fixed_plot_params,
                        manual_ranges=manual_ranges,
                        filter_state=filter_state,
                        design_settings=ds_settings,
                        custom_label_offsets=custom_offsets,
                        layer_overrides=layer_overrides,
                    )
                )
            popup_window.set_draw_result(
                snapping_data, label_data, label_text_artists, (idx, *plot_key_suffix)
            )
            canvas.draw()

            if self.ruler_tool.active:
                r_design = popup_window.get_design_settings() or {}
                if not r_design and getattr(popup_window, "design_tab", None):
                    r_design = getattr(
                        popup_window.design_tab, "get_current_settings", lambda: {}
                    )()

                self.ruler_tool.set_context(
                    canvas,
                    figure.axes[0],
                    popup_window.fixed_plot_params,
                    snapping_data,
                    r_design or None,
                )
            if self.label_move_tool and self.label_move_tool.active:
                self.label_move_tool.set_context(
                    canvas,
                    figure.axes[0],
                    label_data,
                    label_text_artists=label_text_artists,
                )
        except Exception as e:
            traceback.print_exc()
            app_logger.error(config.LOG_MSG["PLOT_APPLY_FAIL"].format(e=e))
            # 실패 시 이전 그래프 대신 간단한 오류 안내만 표시
            try:
                figure.clear()
                ax = figure.add_subplot(111)
                ax.text(
                    0.5,
                    0.5,
                    "플롯 렌더링 오류",
                    ha="center",
                    va="center",
                    fontfamily=kor_font,
                    fontsize=11,
                )
                ax.set_axis_off()
                canvas.draw()
            except Exception as e:
                app_logger.debug(f"[refresh_plot] 렌더링 오류 폴백 실패: {e}")

    def navigate_plot(
        self, direction, figure, canvas, lbl_info, popup_window, range_widgets
    ):
        """이전/다음 버튼 클릭 시 데이터셋 전환. 떠나는 파일의 라벨 커스텀 위치는 리셋."""
        data_list = popup_window.plot_data_snapshot or self.plot_data_list
        if not data_list:
            return

        key_leaving = popup_window._plot_key
        if key_leaving:
            self.custom_label_offsets.pop(key_leaving, None)

        if self.ruler_tool.active:
            self.ruler_tool.clear_all()

        idx = popup_window.current_idx
        if direction == "prev":
            idx = (idx - 1) % len(data_list)
        else:
            idx = (idx + 1) % len(data_list)
        self.current_idx = idx
        popup_window.current_idx = idx

        # 파일 전환 시 그리기 레이어 완전 초기화: 현재(새) 파일의 그리기 목록·UI 상태 비우기
        if hasattr(popup_window, "_set_current_draw_objects"):
            popup_window._set_current_draw_objects([])
        if hasattr(popup_window, "_layer_dock_content") and getattr(
            popup_window, "_layer_dock_content", None
        ):
            ld = popup_window._layer_dock_content
            ld._selected_draw_indices = set()
            ld.update_draw_layer_list([])

        current_data = data_list[idx]
        if hasattr(popup_window, "update_file_nav_indicator"):
            popup_window.update_file_nav_indicator(idx, current_data)
        else:
            lbl_info.setText(
                format_file_label(idx + 1, len(data_list), current_data["name"])
            )
            apply_file_indicator_style(lbl_info, current_data)

        self.refresh_plot(figure, canvas, range_widgets, lbl_info, popup_window)

    def toggle_ruler(self, popup_window):
        """눈금자 활성화/비활성화 토글 제어. 켜질 때 라벨 위치 옮기기 모드가 있으면 강제 OFF."""
        if not self.ruler_tool.active:
            if self.label_move_tool and self.label_move_tool.active:
                self.label_move_tool.active = False
                self.label_move_tool.detach()
                if hasattr(popup_window, "update_label_move_style"):
                    popup_window.update_label_move_style(False)
                elif hasattr(popup_window, "update_compare_label_move_style"):
                    series = getattr(popup_window, "_label_move_series", None) or "blue"
                    popup_window.update_compare_label_move_style(series, False)
                    popup_window._label_move_series = None
                app_logger.info(config.LOG_MSG["LABEL_MOVE_OFF"])
            self.ruler_tool.active = True
            if popup_window.figure.axes:
                snapping_data = popup_window.snapping_data
                design = (
                    popup_window.get_design_settings()
                    if hasattr(popup_window, "get_design_settings")
                    else {}
                )
                if not design and getattr(popup_window, "design_tab", None):
                    design = getattr(
                        popup_window.design_tab, "get_current_settings", lambda: {}
                    )()
                self.ruler_tool.set_context(
                    popup_window.canvas,
                    popup_window.figure.axes[0],
                    popup_window.fixed_plot_params,
                    snapping_data,
                    design or None,
                )
            popup_window.update_ruler_style(True)
            app_logger.info(config.LOG_MSG["RULER_ON"])
        else:
            self.ruler_tool.active = False
            self.ruler_tool.detach()
            self.ruler_tool.clear_all()
            popup_window.update_ruler_style(False)
            app_logger.info(config.LOG_MSG["RULER_OFF_INFO"])

    def _refresh_single_popup_after_label_move(self, popup_window):
        """단일 플롯 라벨 위치 변경 후 현재 팝업을 다시 그린다."""
        self.refresh_plot(
            popup_window.figure,
            popup_window.canvas,
            popup_window.range_widgets,
            popup_window.lbl_info,
            popup_window,
        )

    def _refresh_compare_popup_after_label_move(self, popup_window):
        """비교 플롯 라벨 위치 변경 후 현재 팝업을 다시 그린다."""
        self.refresh_compare_plot(
            popup_window.figure,
            popup_window.canvas,
            popup_window.range_widgets,
            None,
            popup_window,
            popup_window.idx_blue,
            popup_window.idx_red,
        )

    def _get_compare_label_offset_key(self, popup_window, series):
        """비교 플롯(blue/red 또는 series_id) 라벨 오프셋 저장 키를 반환한다."""
        key_cmp = getattr(popup_window, "_plot_key_compare", None)
        if not key_cmp:
            return None
        return compare_label_offset_key(key_cmp, series)

    def _save_label_offset(self, dragging, popup_window):
        key = getattr(popup_window, "_plot_key", None)
        if not key:
            return
        dx, dy = self._get_label_offset_delta(dragging)
        self.custom_label_offsets.setdefault(key, {})[dragging["vowel"]] = (dx, dy)
        self._refresh_single_popup_after_label_move(popup_window)

    def _clear_label_offset(self, popup_window, vowel):
        """우클릭 원상복귀: 해당 모음의 사용자 지정 오프셋을 제거하면 refresh 시 자동 배치로 복귀."""
        key = getattr(popup_window, "_plot_key", None)
        if not key:
            return
        self.custom_label_offsets.get(key, {}).pop(vowel, None)
        self._refresh_single_popup_after_label_move(popup_window)

    def toggle_label_move(self, popup_window):
        """라벨 위치 이동 모드 토글. 눈금자 툴이 켜져 있으면 켜지지 않음."""
        if self.ruler_tool.active:
            return
        if self.label_move_tool is None:
            self.label_move_tool = LabelMoveTool()
        self.label_move_tool.on_offset_saved = (
            lambda pw: lambda d: self._save_label_offset(d, pw)
        )(popup_window)
        self.label_move_tool.on_offset_cleared = (
            lambda pw: lambda v: self._clear_label_offset(pw, v)
        )(popup_window)
        # 켜기 전에 context 설정해야 _connect() 시 canvas/ax가 유효함
        if not self.label_move_tool.active and popup_window.figure.axes:
            self.label_move_tool.set_context(
                popup_window.canvas,
                popup_window.figure.axes[0],
                getattr(popup_window, "label_data", []),
                label_text_artists=getattr(popup_window, "label_text_artists", None),
            )
        on_now = self.label_move_tool.toggle()
        if hasattr(popup_window, "update_label_move_style"):
            popup_window.update_label_move_style(on_now)
        if on_now:
            app_logger.info(config.LOG_MSG["LABEL_MOVE_ON"])
        else:
            app_logger.info(config.LOG_MSG["LABEL_MOVE_OFF"])

    def _save_compare_label_offset(self, dragging, popup_window, series):
        key = self._get_compare_label_offset_key(popup_window, series)
        if not key:
            return
        dx, dy = self._get_label_offset_delta(dragging)
        self.custom_label_offsets.setdefault(key, {})[dragging["vowel"]] = (dx, dy)
        self._refresh_compare_popup_after_label_move(popup_window)

    def _clear_compare_label_offset(self, popup_window, series, vowel):
        """우클릭 원상복귀: 해당 모음의 사용자 지정 오프셋 제거 후 refresh 시 자동 배치로 복귀."""
        key = self._get_compare_label_offset_key(popup_window, series)
        if not key:
            return
        self.custom_label_offsets.get(key, {}).pop(vowel, None)
        self._refresh_compare_popup_after_label_move(popup_window)

    def toggle_compare_label_move(self, popup_window, series):
        """다중 플롯에서 해당 파일(blue/red) 라벨 위치 이동 토글 및 스위칭."""
        if self.ruler_tool.active:
            return
        if self.label_move_tool is None:
            self.label_move_tool = LabelMoveTool()

        old_series = getattr(popup_window, "_label_move_series", None)

        # [추가된 로직] 1. 다른 탭의 라벨 이동으로 '스위칭' 하는 경우
        if self.label_move_tool.active and old_series and old_series != series:
            # 타겟 저장/원상복귀 함수 교체
            self.label_move_tool.on_offset_saved = (
                lambda pw, s: lambda d: self._save_compare_label_offset(d, pw, s)
            )(popup_window, series)
            self.label_move_tool.on_offset_cleared = (
                lambda pw, s: lambda v: self._clear_compare_label_offset(pw, s, v)
            )(popup_window, series)

            # 넘어갈 탭(새로운 series)의 데이터와 텍스트 아티스트를 가져옴
            label_data = label_data_for_series(popup_window, series)
            label_text_artists = label_text_artists_for_series(popup_window, series)
            design = getattr(popup_window, "design_settings", None) or (
                getattr(popup_window.design_tab, "get_current_settings", lambda: {})()
            )
            ell_color = (design.get(series) or {}).get(
                "ell_color", "#1976D2" if series == "blue" else "#E64A19"
            )

            # 툴을 끄지 않고(detach 안 함), 포인터가 바라보는 타겟만 즉시 교체!
            self.label_move_tool.set_context(
                popup_window.canvas,
                popup_window.figure.axes[0],
                label_data,
                highlight_color=ell_color,
                label_text_artists=label_text_artists,
            )

            popup_window._label_move_series = series

            # UI 버튼 상태 업데이트 (A는 꺼지고 B는 켜진 상태로 만듦)
            if hasattr(popup_window, "update_compare_label_move_style"):
                popup_window.update_compare_label_move_style(series, True)

            app_logger.info(
                config.LOG_MSG["LABEL_MOVE_SERIES"].format(
                    series="기준" if series == "blue" else "비교"
                )
            )
            return

        # 2. 일반적인 토글 (처음 켜거나, 켜져있던 걸 끄는 경우)
        self.label_move_tool.on_offset_saved = (
            lambda pw, s: lambda d: self._save_compare_label_offset(d, pw, s)
        )(popup_window, series)
        self.label_move_tool.on_offset_cleared = (
            lambda pw, s: lambda v: self._clear_compare_label_offset(pw, s, v)
        )(popup_window, series)

        if not self.label_move_tool.active and popup_window.figure.axes:
            label_data = label_data_for_series(popup_window, series)
            label_text_artists = label_text_artists_for_series(popup_window, series)
            design = getattr(popup_window, "design_settings", None) or (
                getattr(popup_window.design_tab, "get_current_settings", lambda: {})()
            )
            ell_color = (design.get(series) or {}).get(
                "ell_color", "#1976D2" if series == "blue" else "#E64A19"
            )

            self.label_move_tool.set_context(
                popup_window.canvas,
                popup_window.figure.axes[0],
                label_data,
                highlight_color=ell_color,
                label_text_artists=label_text_artists,
            )

        on_now = self.label_move_tool.toggle()
        popup_window._label_move_series = series if on_now else None

        if hasattr(popup_window, "update_compare_label_move_style"):
            popup_window.update_compare_label_move_style(series, on_now)

        if on_now:
            app_logger.info(
                config.LOG_MSG["LABEL_MOVE_ON_SERIES"].format(
                    series="기준" if series == "blue" else "비교"
                )
            )
        else:
            app_logger.info(config.LOG_MSG["LABEL_MOVE_OFF"])

    def _get_outlier_save_suffix(self):
        """현재 이상치 제거 모드에 맞는 저장 파일명 suffix를 반환."""
        outlier_mode = getattr(self.ui, "get_outlier_mode", lambda: None)()
        if outlier_mode == "1sigma":
            return "_이상치 제거 1σ"
        if outlier_mode == "2sigma":
            return "_이상치 제거 2σ"
        return ""

    def _get_initial_save_dir(self):
        """저장 다이얼로그의 초기 디렉터리를 반환 (세션 메모리 → path_prefs.json)."""
        if self.last_save_dir and os.path.isdir(self.last_save_dir):
            return self.last_save_dir
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        if base:
            loaded = path_prefs.load_path_prefs(base)
            saved = loaded.get("last_save_dir")
            if saved and os.path.isdir(saved):
                self.last_save_dir = saved
                return saved
        downloads_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )
        return downloads_dir or ""

    def _normalize_tag_for_filename(self, norm):
        """정규화 이름을 파일명용 태그로 변환."""
        return {
            "Lobanov": "Lobanov",
            "Gerstman": "Gerstman",
            "2mW/F": "2mWF",
            "Bigham": "Bigham",
        }.get(norm, norm.replace("/", "").replace(" ", ""))

    def _build_default_save_name(self, fmt, parent_window=None):
        """현재 상태/팝업 문맥을 기반으로 저장 기본 파일명을 생성."""
        outlier_suffix = self._get_outlier_save_suffix()
        session = getattr(parent_window, "compare_session", None)
        if session is not None and session.count >= 2:
            names = get_compare_names(self, session)
            norm = getattr(parent_window, "normalization", None)
            base = compare_default_save_basename(
                names,
                outlier_suffix=outlier_suffix,
                norm=norm,
                norm_tag=self._normalize_tag_for_filename(norm) if norm else None,
            )
            return f"{base}.{fmt}"
        if (
            parent_window
            and getattr(parent_window, "idx_blue", None) is not None
            and getattr(parent_window, "idx_red", None) is not None
        ):
            name_blue = os.path.splitext(
                self.plot_data_list[parent_window.idx_blue]["name"]
            )[0]
            name_red = os.path.splitext(
                self.plot_data_list[parent_window.idx_red]["name"]
            )[0]
            base = f"{name_blue}_{name_red}{outlier_suffix}"
            norm = getattr(parent_window, "normalization", None)
            if norm:
                base += "_" + self._normalize_tag_for_filename(norm)
            return f"{base}.{fmt}"

        current_name = self.plot_data_list[self.current_idx]["name"]
        base = os.path.splitext(current_name)[0]
        return f"{base}{outlier_suffix}.{fmt}"

    def get_default_save_path(self, fmt, parent_window=None):
        """단일 이미지 저장의 기본 경로 및 디렉터리 반환."""
        if not self.plot_data_list:
            return "", ""
        default_name = self._build_default_save_name(fmt, parent_window)
        initial_dir = self._get_initial_save_dir()
        initial_path = (
            os.path.join(initial_dir, default_name) if initial_dir else default_name
        )
        return initial_path, initial_dir

    def _get_plot_item_at(self, popup_window=None):
        if popup_window is not None:
            data_list = (
                getattr(popup_window, "plot_data_snapshot", None) or self.plot_data_list
            )
            idx = getattr(popup_window, "current_idx", self.current_idx)
        else:
            data_list = self.plot_data_list
            idx = self.current_idx
        if not data_list or idx < 0 or idx >= len(data_list):
            return None, -1
        return data_list[idx], idx

    def get_default_combined_txt_path(self, parent_window=None):
        """Combined 항목 .txt 저장 기본 경로."""
        item, _ = self._get_plot_item_at(parent_window)
        if not item or not item.get("is_combined"):
            return "", ""
        base = os.path.splitext(item["name"])[0]
        if not base.lower().endswith(".txt"):
            default_name = f"{base}.txt"
        else:
            default_name = base
        initial_dir = self._get_initial_save_dir()
        initial_path = (
            os.path.join(initial_dir, default_name) if initial_dir else default_name
        )
        return initial_path, initial_dir

    def export_combined_txt(self, file_path, parent_window=None, parent_widget=None):
        """현재 Combined plot_data의 df를 입력 형식 .txt로 저장."""
        item, _ = self._get_plot_item_at(parent_window)
        if not item or not item.get("is_combined"):
            return False, "Combined 항목이 아닙니다."
        df = item.get("df")
        if df is None or df.empty:
            return False, "저장할 데이터가 없습니다."
        text = formant_dataframe_to_txt(df, include_f3=bool(item.get("has_f3", False)))
        if not text.strip():
            return False, "유효한 행이 없어 파일을 만들 수 없습니다."
        try:
            with open(file_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            self.set_last_save_dir(os.path.dirname(file_path))
            app_logger.info(config.LOG_MSG["COMBINED_TXT_SAVE"].format(path=file_path))
            return True, file_path
        except OSError as e:
            return False, str(e)

    def prompt_save_combined_txt(self, parent_window=None, parent_widget=None):
        """Combined txt 저장 대화상자."""
        item, _ = self._get_plot_item_at(parent_window)
        if not item or not item.get("is_combined"):
            QMessageBox.information(
                parent_widget,
                "Combined txt",
                "Combined 항목에서만 사용할 수 있습니다.",
            )
            return False
        initial_path, _ = self.get_default_combined_txt_path(parent_window)
        path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Combined 데이터 txt 저장",
            initial_path,
            "Text Files (*.txt);;All Files (*.*)",
        )
        if not path:
            return False
        if not path.lower().endswith(".txt"):
            path += ".txt"
        ok, msg = self.export_combined_txt(path, parent_window, parent_widget)
        if ok:
            QMessageBox.information(
                parent_widget,
                "저장 완료",
                f"Combined 데이터를 저장했습니다.\n{path}",
            )
            return True
        QMessageBox.warning(parent_widget, "저장 실패", msg or "저장에 실패했습니다.")
        return False

    def save_plot_to_file(self, figure, file_path, fmt, parent_window=None):
        """실제 파일 저장만을 수행, 오류시 예외 발생."""
        try:
            self.set_last_save_dir(os.path.dirname(file_path))
        except Exception as e:
            app_logger.debug(f"[save_plot_to_file] 마지막 저장 경로 저장 실패: {e}")
        if self.ruler_tool.active:
            self.ruler_tool.clear_all()
        if parent_window:
            if getattr(parent_window, "_draw_tool", None) is not None:
                try:
                    parent_window._draw_tool.cancel()
                except Exception as e:
                    app_logger.debug(f"[save_plot_to_file] 그리기 도구 취소 실패: {e}")
            if hasattr(parent_window, "begin_export_render"):
                parent_window.begin_export_render()
        try:
            if parent_window and getattr(parent_window, "canvas", None) is not None:
                try:
                    parent_window.canvas.draw()
                except Exception as e:
                    app_logger.debug(
                        f"[save_plot_to_file] 캔버스 다시 그리기 실패: {e}"
                    )
            figure.set_size_inches(6.5, 6.5)
            if fmt.lower() == "png":
                figure.savefig(file_path, format="png", dpi=300, transparent=True)
            else:
                figure.savefig(file_path, format=fmt, dpi=300, facecolor="white")
            app_logger.info(config.LOG_MSG["SAVE_SINGLE_SHORT"].format(path=file_path))
        finally:
            if parent_window and hasattr(parent_window, "end_export_render"):
                parent_window.end_export_render()

    def get_default_batch_save_dir(self):
        """일괄 저장에 사용할 기본 디렉터리 반환."""
        return self._get_initial_save_dir()

    def create_batch_save_worker(
        self,
        save_dir,
        ranges,
        sigma,
        img_format,
        design_settings=None,
        parent_popup=None,
        batch_options=None,
    ):
        """일괄 저장을 위한 Worker 객체 생성 및 초기 설정만 수행."""
        self.set_last_save_dir(save_dir)

        batch_options = batch_options or {}
        apply_global = batch_options.get("apply_global_design", True)
        apply_layer = batch_options.get("apply_layer_design", True)
        apply_visibility = batch_options.get("apply_layer_visibility", True)
        apply_labels = batch_options.get("apply_label_positions", True)
        apply_legend = batch_options.get("apply_legend", False)
        apply_draw_annotations = batch_options.get("apply_draw_annotations", True)

        plot_params = self._get_current_plot_params(parent_popup)
        plot_params["sigma"] = sigma
        plot_params["outlier_mode"] = getattr(
            self.ui, "get_outlier_mode", lambda: None
        )()

        if apply_global and design_settings:
            ds_settings = design_settings
        else:
            ds_settings = self._get_default_design()

        norm_name = plot_params.get("normalization")
        normalize_fn = (
            (lambda df: self._apply_normalization(df, norm_name)) if norm_name else None
        )

        per_file_overrides = {}
        per_file_filters = {}
        if parent_popup is not None:
            if apply_layer:
                per_file_overrides = dict(
                    getattr(parent_popup, "layer_design_overrides_by_file", {})
                )
            if apply_visibility:
                per_file_filters = dict(
                    getattr(parent_popup, "vowel_filter_state_by_file", {})
                )

        label_offsets = dict(self.custom_label_offsets) if apply_labels else {}

        per_file_draw_objects = {}
        if (apply_legend or apply_draw_annotations) and parent_popup is not None:
            per_file_draw_objects = dict(
                getattr(parent_popup, "_draw_objects_by_file", {})
            )

        return BatchSaveWorker(
            save_dir,
            self.plot_data_list,
            self.plot_engine,
            plot_params,
            ranges,
            ds_settings,
            img_format,
            normalize_fn=normalize_fn,
            per_file_filters=per_file_filters,
            per_file_overrides=per_file_overrides,
            label_offsets=label_offsets,
            per_file_draw_objects=per_file_draw_objects,
            apply_layer_visibility=apply_visibility,
            apply_layer_design=apply_layer,
            apply_label_positions=apply_labels,
            apply_legend=apply_legend,
            apply_draw_annotations=apply_draw_annotations,
        )

    # --- 공개 API (View는 이 메서드들만 사용) ---

    def get_plot_type(self):
        """현재 플롯 타입(메인 UI 기준)."""
        return self.ui.get_plot_type() if hasattr(self.ui, "get_plot_type") else "f1_f2"

    def get_outlier_mode(self):
        """이상치 제거 모드: None, '1sigma', '2sigma'."""
        return (
            self.ui.get_outlier_mode() if hasattr(self.ui, "get_outlier_mode") else None
        )

    def get_plot_data_list(self):
        """로드된 플롯 데이터 목록. View는 이 목록을 읽기 전용으로 사용."""
        return self.plot_data_list

    def get_plot_data_count(self):
        """로드된 파일 개수."""
        return len(self.plot_data_list)

    def get_current_index(self):
        """현재 선택 인덱스."""
        return self.current_idx

    def get_current_file_data(self):
        """현재 선택 파일 데이터 (data_item, index). 없으면 (None, 0)."""
        if not self.plot_data_list:
            return None, 0
        idx = max(0, min(self.current_idx, len(self.plot_data_list) - 1))
        return self.plot_data_list[idx], idx

    def get_data_item_at(self, index):
        """지정 인덱스의 데이터 항목. 범위 밖이면 None."""
        if index in self._compare_virtual_items:
            return self._compare_virtual_items[index]
        if index < 0 or index >= len(self.plot_data_list):
            return None
        return self.plot_data_list[index]

    def register_compare_virtual_item(self, item: dict) -> int:
        """Compare 전용 임시 항목 — plot_data_list에 넣지 않고 음수 인덱스로 등록."""
        idx = self._compare_virtual_next_id
        self._compare_virtual_next_id -= 1
        self._compare_virtual_items[idx] = item
        return idx

    def _release_compare_virtual_indices(self, indices: tuple[int, ...]) -> None:
        for idx in indices:
            self._compare_virtual_items.pop(idx, None)

    def build_compare_group_from_indices(self, indices: list[int]) -> dict | None:
        items = []
        for i in indices:
            if i < 0 or i >= len(self.plot_data_list):
                continue
            it = self.plot_data_list[i]
            if it.get("is_combined"):
                continue
            items.append(it)
        return build_compare_group_entry(items)

    def get_compare_file_list(self):
        """비교 선택 UI용 — Combined 제외 전체 real 파일 [(idx, name), ...]."""
        return [
            (i, item["name"])
            for i, item in enumerate(self.plot_data_list)
            if not item.get("is_combined")
        ]

    def set_current_index(self, index):
        """현재 선택 인덱스 설정(네비게이션 등). 범위 내로 클램프."""
        if not self.plot_data_list:
            self.current_idx = 0
            return
        self.current_idx = max(0, min(index, len(self.plot_data_list) - 1))

    def get_compare_choices(self, exclude_index):
        """비교 대상 선택 목록: [(인덱스, 파일명), ...] (exclude_index 및 Combined 항목 제외)."""
        return [
            (i, item["name"])
            for i, item in enumerate(self.plot_data_list)
            if i != exclude_index and not item.get("is_combined")
        ]

    def get_compare_data(self, idx_blue, idx_red):
        """비교 플롯용 두 데이터 항목. (data_blue, data_red) 또는 (None, None)."""
        b = self.get_data_item_at(idx_blue)
        r = self.get_data_item_at(idx_red)
        return b, r

    def get_compare_data_for_session(self, session: CompareSession):
        """CompareSession에 해당하는 plot_data_list 항목 목록."""
        return [
            self.get_data_item_at(session.data_index(series_id))
            for series_id in range(session.count)
        ]

    def get_smart_ranges_for_params(
        self, plot_type, use_bark=False, f1_scale=None, f2_scale=None
    ):
        """플롯 타입·스케일에 따른 축 범위 dict. View/팝업은 이 공개 메서드만 호출."""
        return self._get_smart_ranges(plot_type, use_bark, f1_scale, f2_scale)

    def _cleanup_popups(self):
        """이미 닫혀서 파괴된 팝업 창들에 대한 참조를 리스트에서 제거합니다."""
        if not hasattr(self, "open_popups"):
            return
        # isVisible()이 False이거나 파이썬 객체가 살아있어도
        # C++ 객체가 파괴된 경우(RuntimeError 발생 가능) 등을 걸러냅니다.
        active = []
        for p in self.open_popups:
            try:
                # isVisible() 체크를 통해 닫힌 창(WA_DeleteOnClose가 작동 중인 창 포함) 제외
                if p and not p.isHidden() and p.isVisible():
                    active.append(p)
            except (RuntimeError, AttributeError):
                # 래퍼만 남고 내부는 이미 파괴된 경우
                continue
        self.open_popups = active

    # --- 유틸리티 메서드 ---

    def _get_smart_ranges(
        self, plot_type, use_bark=False, f1_scale=None, f2_scale=None
    ):
        """플롯 타입과 스케일에 따른 지능형 범위 설정 (각 축의 단위를 독립적으로 반영)"""
        if f1_scale is None or f2_scale is None:
            params = self._get_current_plot_params()
            f1_scale = f1_scale or params.get("f1_scale", "linear")
            f2_scale = f2_scale or params.get("f2_scale", "linear")

        hz_rc = config.HZ_RANGES.get(plot_type, config.HZ_RANGES["f1_f2"])
        bk_rc = config.BARK_RANGES.get(plot_type, config.BARK_RANGES["f1_f2"])

        f1_unit = "Bark" if (f1_scale == "bark" and use_bark) else "Hz"
        f2_unit = "Bark" if (f2_scale == "bark" and use_bark) else "Hz"

        y_rc = bk_rc if f1_unit == "Bark" else hz_rc
        x_rc = bk_rc if f2_unit == "Bark" else hz_rc

        x_min = x_rc["x_min"]
        x_max = x_rc["x_max"]
        # F1 vs (F2-F1) / (F2'-F1) 이고 해당 축이 Log일 때만 최소값 100(Hz) 또는 그에 상응하는 Bark로 고정 (눈금 구부러짐 방지)
        if (
            plot_type in ("f1_f2_minus_f1", "f1_f2_prime_minus_f1")
            and f2_scale == "log"
        ):
            if f2_unit == "Hz":
                x_min = 100
            else:
                from utils.math_utils import hz_to_bark

                x_min = max(0, int(round(hz_to_bark(100.0))))

        return {
            "y_min": str(y_rc["y_min"]),
            "y_max": str(y_rc["y_max"]),
            "x_min": str(x_min),
            "x_max": str(x_max),
        }

    def _get_main_ui_plot_params(self):
        """메인 창 UI에서 현재 플롯 타입·스케일·원점·단위(Unit)를 취합한다. Scale과 Unit은 별개."""
        f1_scale = self.ui.get_f1_scale()
        f2_scale = self.ui.get_f2_scale()
        use_bark = self.ui.get_use_bark_units()
        f1_unit = "Bark" if (f1_scale == "bark" and use_bark) else "Hz"
        f2_unit = "Bark" if (f2_scale == "bark" and use_bark) else "Hz"
        return {
            "type": self.ui.get_plot_type(),
            "f1_scale": f1_scale,
            "f2_scale": f2_scale,
            "f1_unit": f1_unit,
            "f2_unit": f2_unit,
            "origin": self.ui.get_origin(),
            "use_bark_units": use_bark,
            "sigma": config.DEFAULT_SIGMA,
            "normalization": self.ui.get_normalization(),
        }

    def _get_current_plot_params(self, popup_window=None):
        """팝업이 있으면 해당 창의 고정 파라미터, 없으면 메인 UI 설정값을 반환한다. Scale과 Unit은 별도 필드로 유지."""
        if popup_window and hasattr(popup_window, "fixed_plot_params"):
            params = popup_window.fixed_plot_params.copy()
            if hasattr(popup_window, "get_sigma"):
                try:
                    params["sigma"] = float(popup_window.get_sigma())
                except ValueError:
                    pass
            # 단위(Unit)가 없으면 스케일+use_bark로 보정 (호환성)
            if "f1_unit" not in params or "f2_unit" not in params:
                f1_scale = params.get("f1_scale", "linear")
                f2_scale = params.get("f2_scale", "linear")
                use_bark = params.get("use_bark_units", False)
                params.setdefault(
                    "f1_unit", "Bark" if (f1_scale == "bark" and use_bark) else "Hz"
                )
                params.setdefault(
                    "f2_unit", "Bark" if (f2_scale == "bark" and use_bark) else "Hz"
                )
            if getattr(popup_window, "uses_main_normalization", False):
                norm = self.ui.get_normalization()
                params["normalization"] = norm
                popup_window.normalization = norm
            return params
        return self._get_main_ui_plot_params()
