# core/controller.py

import os
import traceback

import config
from core.compare_series import (
    CompareSession,
    compare_label_offset_key,
)
from core.compare_runtime import (
    resolve_compare_session,
)
from core.data_loading_service import load_plot_item_from_file
from core.application_state import AnalysisSettings
from core.application_service import ApplicationService
from core.interactive_plot_state import PlotSessionState
from core.plot_session_service import PlotSessionService
from core.plot_data_types import PlotDataItem, PlotParams
from core.live_preview_service import LivePreviewService
from core.view_port import MainViewPort
from core.desktop_adapter_factory import (
    create_default_runtime,
    create_default_view,
    create_default_window_coordinator,
)
from core.workspace_state import WorkspaceState, WorkspaceStateMixin
from core.workspace_service import WorkspaceService
from core.legacy_window_registry import LegacyWindowRegistry
from core.project_restore_service import ProjectRestoreService
from core.popup_lifecycle_service import PopupLifecycleService
from core.plot_configuration_service import PlotConfigurationService
from core.controller_service_bundle import ControllerServiceBundle
from utils import app_logger
from core.design_defaults import get_single_design_defaults
from model.data_processor import DataProcessor
from utils.math_utils import (
    remove_outliers_tukey_iqr,
    remove_outliers_mahalanobis_scoped,
)
from core.normalization_service import apply_normalization, normalize_dataframe
from model.combined_dataset import build_compare_group_entry
from utils import path_prefs


class MainController(WorkspaceStateMixin):
    """
    GichanFormant의 핵심 비즈니스 로직을 제어하는 컨트롤러입니다.
    파일 가이드 연동 및 데이터 기반 인터랙션 제어를 담당합니다.
    """

    @property
    def open_popups(self):
        return self.legacy_windows.windows

    @open_popups.setter
    def open_popups(self, value):
        registry = self.__dict__.get("legacy_windows")
        if registry is None:
            self.__dict__["_pending_open_popups"] = list(value)
            return
        registry.replace(value)

    def __init__(
        self,
        startup_context=None,
        status_callback=None,
        *,
        view_factory=None,
        timer_factory=None,
        runtime=None,
        window_coordinator=None,
        render_initial_preview=True,
    ):
        self.workspace = WorkspaceState()
        self.workspace_service = WorkspaceService(self.workspace)
        ControllerServiceBundle.create(self).attach(self)
        self.filepaths = []
        self.plot_data_list: list[PlotDataItem] = []
        self.current_idx = 0
        self.plot_session_state = PlotSessionState()
        self._analysis_settings = AnalysisSettings()
        # 이상치 제거 모드 변경 로그를 위한 직전 상태 저장 (초기 None)
        self.last_outlier_mode = None
        # 저장 다이얼로그에서 사용할 마지막 저장 디렉터리 (없으면 Downloads)
        self.last_save_dir = None
        # 파일 열기 다이얼로그에서 사용할 마지막 선택 디렉터리 (없으면 Documents)
        self.last_open_dir = None

        # startup_context에서 사전 로드된 설정 반영
        context = startup_context or {}
        if runtime is None:
            runtime = create_default_runtime(timer_factory=timer_factory)
        self.runtime = runtime
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
            _prefs_base = self.runtime.app_data_dir()
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

        self.ruler_tool = context.get("ruler_tool")
        self.label_move_tool = context.get("label_move_tool")
        self.custom_label_offsets = {}  # (file_idx, plot_type) -> { vowel: (dx_data, dy_data) }

        # 사전 초기화된 엔진 재사용. React --desktop sidecar starts with
        # render_initial_preview=False so matplotlib Figure / PlotEngine stay
        # cold until the first preview (health answers sooner on laptops).
        self.data_processor = context.get("data_processor") or DataProcessor()
        self.plot_engine = context.get("plot_engine")
        self.live_preview_fig = context.get("live_preview_fig")
        self.preview_renderer = context.get("preview_renderer")

        # LIVE 미리보기 디바운스: 연속 호출 시 마지막 한 번만 렌더 (메인 스레드 블로킹 완화)
        self._live_preview_debouncer = self.runtime.create_debouncer(
            self._render_live_preview
        )

        self.application_service = ApplicationService(self)

        if view_factory is None:
            view_factory = create_default_view
        self.view: MainViewPort = view_factory(self, status_callback)
        self.ui = self.view.native_window
        self.live_preview_service = LivePreviewService(
            renderer=self.preview_renderer,
            figure=self.live_preview_fig,
            view=self.view,
            publish_ready=self.application_service.publish_preview,
            publish_empty=self.application_service.publish_empty_preview,
            publish_error=self.application_service.publish_preview_error,
        )
        if window_coordinator is None:
            window_coordinator = create_default_window_coordinator(self.ui)
        self.window_coordinator = window_coordinator
        self.legacy_windows = LegacyWindowRegistry(self.window_coordinator)
        self.open_popups = self.__dict__.pop("_pending_open_popups", [])
        if self.ruler_tool is None:
            self.ruler_tool = self.window_coordinator.create_ruler_tool()
        self.sync_analysis_settings_from_view()
        if self.ui is not None:
            app_logger.set_ui(self.ui)
        # 작업표시줄 아이콘이 처음 실행 시 바로 뜨도록, 창 표시 전에 한 번 더 아이콘 적용
        try:
            if self.ui is not None and hasattr(self.ui, "_apply_window_icon"):
                self.ui._apply_window_icon()
        except Exception as e:
            app_logger.debug(f"[_apply_window_icon] 초기 아이콘 적용 실패: {e}")

        # 사전 초기화된 Fig가 있다면 첫 렌더링을 즉시 동기적으로 수행하여 스플래시 종료 전 화면을 채웁니다.
        # (실제 창 표시는 main.py에서 splash.finish()와 함께 수행하여 겹침 현상을 방지합니다)
        if render_initial_preview:
            self._ensure_live_preview()
            if self.view.supports_preview():
                self._render_live_preview()
        app_logger.info(config.LOG_MSG["APP_START"].format(app_title=config.APP_TITLE))

    def _ensure_plot_engine(self):
        """Import and construct PlotEngine on first analysis/render use."""
        if self.plot_engine is not None:
            return
        from engine.plot_engine import PlotEngine

        self.plot_engine = PlotEngine()

    def _ensure_live_preview(self) -> None:
        """Create PlotEngine / Figure / PreviewRenderer on first live preview use."""
        if self.live_preview_fig is not None and self.preview_renderer is not None:
            self._ensure_plot_engine()
            return
        from matplotlib.figure import Figure
        from core.preview_renderer import PreviewRenderer

        self._ensure_plot_engine()
        if self.live_preview_fig is None:
            self.live_preview_fig = Figure(figsize=(6.5, 6.5), dpi=150)
        if self.preview_renderer is None:
            self.preview_renderer = PreviewRenderer(
                self.plot_engine, self.live_preview_fig
            )
        self.live_preview_service.renderer = self.preview_renderer
        self.live_preview_service.figure = self.live_preview_fig

    def on_outlier_mode_changed(self):
        """
        사용자가 이상치 제거 모드(None, 1σ, 2σ)를 변경했을 때의 처리를 담당합니다.
        1. 변경된 모드에 따라 real 화자 항목별로 마할라노비스 기반 이상치를 제거합니다.
           (Combined는 직접 필터링하지 않고, real 항목들이 갱신된 뒤 그것들로부터 재합성합니다.
            그래야 '특정 화자의 클러스터 때문에 다른 화자의 정상 토큰이 제거'되는 일이 없습니다.)
        2. 필터링된 데이터를 각 화자 항목에 반영합니다.
        3. 변경 결과를 로그로 출력하고 실시간 미리보기를 갱신합니다.
        """
        self.analysis_workflow_service.outlier_changed(
            remove_outliers_mahalanobis_scoped,
            remove_outliers_tukey_iqr,
        )

    def _refresh_open_popups(self):
        """
        현재 데이터 상태(이상치 제거, 정규화 등)에 맞춰 이미 열려 있는
        모든 단일 플롯(PlotPopup) 및 비교 플롯(ComparePlotPopup) 창의 그래프를 다시 그립니다.
        """
        def report(error):
            traceback.print_exc()
            app_logger.error(config.LOG_MSG["PLOT_REFRESH_ERROR"].format(e=error))

        self.legacy_windows.refresh(on_error=report)
        return

    def _apply_normalization(self, df, norm_name, *, is_pre_lobanov: bool = False):
        """Compatibility wrapper for normalization service."""
        return apply_normalization(df, norm_name, is_pre_lobanov=is_pre_lobanov)

    def _normalize_dataframe(self, df, norm_name, data_item=None):
        """Compatibility wrapper that respects the item pre-Lobanov flag."""
        return normalize_dataframe(df, norm_name, data_item)

    def _real_plot_items(self):
        return self.workspace_service.real_items()

    def all_real_items_pre_lobanov(self) -> bool:
        real = self._real_plot_items()
        return bool(real) and all(it.get("is_pre_lobanov") for it in real)

    def _sync_pre_lobanov_ui(self):
        self.view.sync_pre_lobanov_normalization(self.all_real_items_pre_lobanov())

    def _rebuild_combined_entry(self):
        """real 화자 항목들로부터 Combined 항목을 (재)구성한다.

        - 기존 Combined 항목은 제거 후 새로 만들어 plot_data_list 마지막에 추가.
        - real 항목이 2개 미만이면 Combined는 추가하지 않음.
        - current_idx가 범위를 벗어나면 자동으로 보정.
        """
        self.workspace_service.rebuild_combined_entry()

    def clear_label_offsets_for_popup(self, popup_window):
        """디자인 초기화 시 해당 팝업의 라벨 커스텀 위치를 제거. 초기화 버튼에서 호출."""
        self._popup_lifecycle().clear_offsets(popup_window)

    def remove_popup(self, popup):
        """팝업이 닫힐 때 View에서 호출. 리스트 및 라벨 오프셋에서 제거."""
        self._remove_popup_from_list(popup)

    def _remove_popup_from_list(self, popup):
        """QObject.destroyed 시그널로 팝업이 파괴될 때 리스트에서 제거 (예외/강제 종료 시에도 메모리 누수 방지)"""
        self._popup_lifecycle().remove(popup)

    def _clear_compare_label_offsets_for_plot_key(self, plot_key, popup_window=None):
        """Compare plot key에 연결된 모든 series 라벨 오프셋을 제거한다."""
        self._popup_lifecycle().clear_compare_offsets(plot_key, popup_window)

    def _get_x_axis_label(self, plot_type):
        """플롯 타입에 맞는 X축 라벨 문자열 반환."""
        return config.PLOT_X_AXIS_LABEL.get(plot_type, "X-Axis")

    _get_axis_units_from_params = staticmethod(PlotConfigurationService.axis_units)

    def _read_manual_ranges(self, range_widgets):
        """범위 입력 위젯에서 수동 범위 dict를 읽어 반환."""
        return PlotConfigurationService.read_ranges(range_widgets)

    def _apply_ranges_to_widgets(self, range_widgets, ranges):
        """범위 dict를 입력 위젯에 반영."""
        PlotConfigurationService.apply_ranges(range_widgets, ranges)

    def _disable_ruler_for_open_popups(self):
        """열린 팝업 전체에서 눈금자 모드를 비활성화."""
        self._popup_lifecycle().disable_ruler()

    def _disable_label_move_for_open_popups(self):
        """열린 팝업 전체에서 라벨 이동 모드를 비활성화."""
        self._popup_lifecycle().disable_label_move()

    def _get_label_offset_delta(self, dragging):
        """드래깅 결과에서 중심 대비 라벨 오프셋(dx, dy)을 계산."""
        return dragging["lx"] - dragging["cx"], dragging["ly"] - dragging["cy"]

    # --- 데이터 관리 로직 ---

    def handle_file_drop(self, files):
        """
        사용자가 메인 창에 파일을 드롭했을 때의 진입점입니다.
        전달받은 파일 경로 리스트를 내부 로드 프로세스로 연결합니다.
        """
        self.main_workflow_service.handle_file_drop(files)

    def open_file_dialog(self):
        """파일 탐색기를 통한 파일 추가 요청(실제 다이얼로그는 View에서 처리)"""
        self.main_workflow_service.request_file_open()

    def _active_single_plot_popup(self):
        for popup in reversed(self.open_popups):
            if getattr(popup, "plot_data_snapshot", None) is not None and not hasattr(
                popup, "compare_session"
            ):
                return popup
        return None

    def prompt_save_project(self, popup_window=None):
        """프로젝트 저장 다이얼로그를 열고 현재 세션을 .gfproj로 저장한다."""
        self.main_workflow_service.prompt_save_project(popup_window)

    def prompt_open_project(self):
        """프로젝트 열기 다이얼로그를 열고 .gfproj를 복원한다."""
        self.main_workflow_service.prompt_open_project()

    def save_project_file(self, path, popup_window=None):
        """UI callback: route save through ApplicationService for event parity."""
        self.main_workflow_service.save_project_file(path, popup_window)

    def save_project_document(self, path, popup_window=None):
        """Save a project and propagate failures to non-UI callers."""
        self.main_workflow_service.save_project_document(path, popup_window)

    def load_project_file(self, path):
        """UI callback: route load through ApplicationService for event parity."""
        self.main_workflow_service.load_project_file(path)

    def load_project_document(self, path, *, restore_windows=True):
        """Load a project and propagate failures to non-UI callers."""
        return self.main_workflow_service.load_project_document(
            path, restore_windows=restore_windows
        )

    def _project_restore(self):
        """Lazily provide the restore service for legacy direct-call sites."""
        service = self.__dict__.get("project_restore_service")
        if service is None:
            service = ProjectRestoreService(self)
            self.__dict__["project_restore_service"] = service
        return service

    def _popup_lifecycle(self):
        service = self.__dict__.get("popup_lifecycle_service")
        if service is None:
            service = PopupLifecycleService(self)
            self.__dict__["popup_lifecycle_service"] = service
        return service

    def _load_file_item(self, path, **kwargs):
        """Compatibility injection seam for the source-file loader."""
        return load_plot_item_from_file(path, **kwargs)

    def _load_project_source_item(self, source, snapshots):
        return self._project_restore().load_source_item(source, snapshots)

    def _prepare_loaded_project(self, project):
        """Validate and construct project state without mutating the session."""
        return self._project_restore().prepare(project)

    def _apply_loaded_project(self, project, *, restore_windows=True):
        return self._project_restore().apply(project, restore_windows=restore_windows)

    def _restore_single_plot_from_project(self, single_state):
        return self._project_restore().restore_single(single_state)

    def _restore_compare_sessions_from_project(self, compare_sessions):
        return self._project_restore().restore_compares(compare_sessions)

    def add_files(self, filepaths):
        """Load sources through the framework-free workspace lifecycle."""
        return self.main_workflow_service.load_files(filepaths)

    def _apply_file_load_result_to_ui(self, result):
        """
        파일 로드 결과를 바탕으로 메인 UI(테이블, 로그, 필터 패널)를 갱신합니다.
        로드된 파일의 통계 정보 및 누락된 데이터에 대한 안내를 수행합니다.
        """
        self.file_load_presentation_service.apply(result)

    def _process_new_files(self, files):
        """새 파일 로드 후 UI에 결과 반영. ApplicationService로 위임한다."""
        return self.application_service.load_files(files)

    def load_files(self, files):
        """Public file-loading command for desktop and external frontends."""
        return self.main_workflow_service.load_files(files)

    def remove_file(self, index) -> bool:
        """Remove a source, then apply the resulting presentation updates."""
        return self.main_workflow_service.remove_file(int(index))

    def reset_data(self):
        """모든 데이터와 설정을 리셋 (사용자 확인은 View에서 수행)"""
        self.main_workflow_service.reset()

    # --- 라이브 모니터 렌더링 로직 ---

    def get_initial_open_dir(self):
        """파일 열기 다이얼로그 초기 폴더: 최근 선택 폴더가 있으면 사용, 없으면 문서 폴더."""
        return self.path_preference_service.initial_open_dir()

    def set_last_open_dir(self, dir_path):
        """파일 열기 후 선택한 폴더를 기억 (다음 열기 시 초기 폴더로 사용)."""
        self.path_preference_service.set_open_dir(dir_path)

    def set_last_save_dir(self, dir_path):
        """저장 후 선택한 폴더를 기억 (다음 저장 시 초기 폴더로 사용)."""
        self.path_preference_service.set_save_dir(dir_path)

    def _save_path_prefs(self):
        """현재 last_open_dir / last_save_dir를 JSON에 저장."""
        self.path_preference_service.save()

    def _get_default_design(self):
        """라이브 모니터 등 UI 객체가 없을 때 사용할 기본 디자인 설정"""
        return get_single_design_defaults()

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
        self.live_preview_service.show_empty()

    def _norm_ranges_for_widgets(self, norm):
        """정규화 축 범위 dict (range_widgets용 문자열 값)."""
        from engine.plot_engine import PlotEngine

        r = PlotEngine.NORM_RANGES.get(norm, PlotEngine.NORM_RANGES["Lobanov"])
        return {k: str(r[k]) for k in ["y_min", "y_max", "x_min", "x_max"]}

    def _sync_single_popup_normalization(self, popup_window):
        """메인 창 정규화 선택을 단일 PlotPopup에 반영."""
        self.analysis_workflow_service.sync_single_popup_normalization(popup_window)

    def _render_live_preview_content(
        self, current_data, params, smart_ranges, default_design
    ):
        """LIVE 모니터에 플롯을 그려 버퍼로 저장한 뒤 레이블에 표시하고 하단 정보를 갱신합니다."""
        self._ensure_live_preview()
        self.live_preview_service.render(
            current_data,
            params,
            smart_ranges,
            default_design,
            outlier_mode=self.get_analysis_settings().outlier_mode,
            request_id=getattr(self.application_service, "_main_preview_request_id", None),
        )

    def update_live_preview(self):
        """LIVE 미리보기 갱신 요청. 디바운스(150ms) 후 한 번만 렌더링해 메인 스레드 블로킹을 줄입니다."""
        self.analysis_workflow_service.request_preview()

    def _render_live_preview(self):
        """디바운스 타이머 만료 시 실제 LIVE 미리보기 렌더링을 수행합니다."""
        self.main_preview_workflow_service.render_now()

    # --- 팝업 생성 및 가이드 로직 ---

    def _show_warning(self, title, text, parent_window=None):
        if parent_window is not None and hasattr(parent_window, "show_warning"):
            parent_window.show_warning(title, text)
            return
        self.view.show_warning(title, text)

    def _show_critical(self, title, text, parent_window=None):
        if parent_window is not None and hasattr(parent_window, "show_critical"):
            parent_window.show_critical(title, text)
            return
        self.view.show_critical(title, text)

    def open_guide(self):
        """데이터 파일 준비 가이드 팝업 표시"""
        self.window_coordinator.open_guide(self.ui)

    def open_single_plot(self):
        """현재 데이터로 시각화 창(PlotPopup)을 생성합니다."""
        self.sync_analysis_settings_from_view()
        self._cleanup_popups()
        if not self.plot_data_list:
            self.view.show_warning("데이터 없음", "분석할 데이터를 먼저 로드해 주세요.")
            return

        return self.single_plot_service.open()

    def open_vowel_analysis_window(self, popup_window):
        """popup_plot 또는 compare_plot의 '모음 상세 분석' 클릭 시 호출. 해당 창의 파일(들)에 대한 분석 창을 연다."""
        return self.popup_workflow_service.open_vowel_analysis(popup_window)

    # --- 다중 비교 팝업 및 제어 로직 ---

    def open_compare_dialog(self, current_idx, parent_window=None):
        """다중 비교를 위한 대상 파일 선택 창(SelectCompareDialog)을 호출합니다."""
        return self.popup_workflow_service.open_compare_dialog(current_idx, parent_window)

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
        return self.open_compare_plot_for_source_groups(
            [left_indices, right_indices],
            normalization=normalization,
            parent_window=parent_window,
        )

    def open_compare_plot_for_source_groups(
        self,
        source_groups: list[list[int]],
        normalization=None,
        parent_window=None,
    ):
        """Open a compare window from two or more groups of real source indices."""
        return self.popup_workflow_service.open_compare_for_source_groups(
            source_groups, normalization, parent_window
        )

    def open_compare_plot_for_indices(
        self,
        indices: list[int],
        normalization=None,
        parent_window=None,
        *,
        virtual_indices: tuple[int, ...] | None = None,
        source_groups: tuple[tuple[int, ...], ...] | None = None,
    ):
        """N개 데이터 인덱스로 compare 창을 연다. UI 탭은 0·1번만, 렌더는 session 전체."""
        self.sync_analysis_settings_from_view()
        if len(indices) < 2:
            self._show_warning(
                "비교 불가",
                "compare에는 2개 이상의 데이터가 필요합니다.",
                parent_window,
            )
            return

        return self.compare_window_service.open_for_indices(
            indices,
            normalization=normalization,
            parent_window=parent_window,
            virtual_indices=virtual_indices,
            source_groups=source_groups,
        )

    def _present_popup_canvas(self, popup_window, canvas):
        """플롯 재렌더 후 그리기 레이어를 함께 올려 한 번에 표시한다."""
        if hasattr(popup_window, "_redraw_draw_layer"):
            popup_window._redraw_draw_layer()
        elif canvas is not None:
            canvas.draw()

    def _sync_popup_tool_contexts(self, popup_window, figure, canvas):
        """플롯·그리기 레이어 갱신 뒤 눈금자/라벨 이동 툴 컨텍스트를 재연결한다."""
        self.plot_interaction_service.sync_contexts(popup_window, figure, canvas)

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
        self.plot_render_workflow_service.refresh_compare(
            figure, canvas, range_widgets, popup_window, session
        )

    # --- 팝업 UI 내부에서 호출되는 액션 핸들러들 ---

    def _sync_plot_session_from_popup(
        self, popup_window, manual_ranges, design_settings, filter_state, layer_overrides
    ):
        """Commit trusted PySide editor state to the shared plot session."""
        PlotSessionService.sync_from_popup(
            self.plot_session_state,
            popup_window,
            fallback_index=self.current_idx,
            manual_ranges=manual_ranges,
            design_settings=design_settings,
            filter_state=filter_state,
            layer_overrides=layer_overrides,
        )

    def refresh_plot(self, figure, canvas, range_widgets, lbl_info, popup_window):
        """[범위 적용] 버튼 클릭 또는 필터/디자인 적용 시 현재 입력된 상태로 플롯을 갱신합니다."""
        self.plot_render_workflow_service.refresh_single(
            figure, canvas, range_widgets, lbl_info, popup_window
        )

    def navigate_plot(
        self, direction, figure, canvas, lbl_info, popup_window, range_widgets
    ):
        """이전/다음 버튼 클릭 시 데이터셋 전환. 떠나는 파일의 라벨 커스텀 위치는 리셋."""
        return self.single_plot_service.navigate(
            direction, figure, canvas, lbl_info, popup_window, range_widgets
        )

    def toggle_ruler(self, popup_window):
        return self.plot_interaction_service.toggle_ruler(popup_window)

    def _refresh_single_popup_after_label_move(self, popup_window):
        """단일 플롯 라벨 위치 변경 후 현재 팝업을 다시 그린다."""
        self.refresh_plot(
            popup_window.figure,
            popup_window.canvas,
            popup_window.range_widgets,
            popup_window.lbl_info,
            popup_window,
        )
        if hasattr(popup_window, "_rebind_draw_tool_if_active"):
            popup_window._rebind_draw_tool_if_active()

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
        if hasattr(popup_window, "_rebind_draw_tool_if_active"):
            popup_window._rebind_draw_tool_if_active()

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

    def _clear_label_offset(self, popup_window, arg):
        """우클릭 원상복귀: 해당 모음의 사용자 지정 오프셋을 제거하면 refresh 시 자동 배치로 복귀."""
        vowel = arg.get("vowel") if isinstance(arg, dict) else arg
        if vowel is None:
            return
        key = getattr(popup_window, "_plot_key", None)
        if not key:
            return
        self.custom_label_offsets.get(key, {}).pop(vowel, None)
        self._refresh_single_popup_after_label_move(popup_window)

    def toggle_label_move(self, popup_window):
        return self.plot_interaction_service.toggle_single_label_move(popup_window)

    def _save_compare_label_offset(self, dragging, popup_window):
        series = dragging.get("series", 0)
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

    def _clear_compare_label_offset_from_arg(self, popup_window, arg):
        if isinstance(arg, dict):
            series = arg.get("series", 0)
            vowel = arg.get("vowel")
        else:
            series = 0
            vowel = arg
        if vowel is None:
            return
        self._clear_compare_label_offset(popup_window, series, vowel)

    def toggle_compare_label_move(self, popup_window):
        return self.plot_interaction_service.toggle_compare_label_move(popup_window)

    def _get_outlier_save_suffix(self):
        """현재 이상치 제거 모드에 맞는 저장 파일명 suffix를 반환."""
        outlier_mode = self.get_analysis_settings().outlier_mode
        if outlier_mode == "mahalanobis_2sigma":
            return "_이상치 제거 2σ"
        if outlier_mode == "tukey_iqr":
            return "_이상치 제거 TukeyIQR"
        return ""

    def _get_initial_save_dir(self):
        """저장 다이얼로그의 초기 디렉터리를 반환 (세션 메모리 → path_prefs.json)."""
        return self.export_workflow_service.initial_dir()

    def _normalize_tag_for_filename(self, norm):
        """정규화 이름을 파일명용 태그로 변환."""
        return self.export_workflow_service.normalize_tag(norm)

    def _build_default_save_name(self, fmt, parent_window=None):
        """현재 상태/팝업 문맥을 기반으로 저장 기본 파일명을 생성."""
        return self.export_workflow_service.default_save_name(fmt, parent_window)

    def get_default_save_path(self, fmt, parent_window=None):
        """단일 이미지 저장의 기본 경로 및 디렉터리 반환."""
        return self.export_workflow_service.default_save_path(fmt, parent_window)

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
        return self.export_workflow_service.default_combined_txt_path(parent_window)

    def export_combined_txt(self, file_path, parent_window=None, parent_widget=None):
        """현재 Combined plot_data의 df를 입력 형식 .txt로 저장."""
        return self.export_workflow_service.export_combined_txt(file_path, parent_window)

    def save_plot_to_file(self, figure, file_path, fmt, parent_window=None):
        """실제 파일 저장만을 수행, 오류시 예외 발생."""
        return self.export_workflow_service.save_plot(
            figure, file_path, fmt, parent_window
        )

    def get_default_batch_save_dir(self):
        """일괄 저장에 사용할 기본 디렉터리 반환."""
        return self.export_workflow_service.initial_dir()

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
        return self.export_workflow_service.create_batch_worker(
            save_dir,
            ranges,
            sigma,
            img_format,
            design_settings,
            parent_popup,
            batch_options,
        )

    # --- 공개 API (View는 이 메서드들만 사용) ---

    def get_analysis_settings(self) -> AnalysisSettings:
        """Return the current UI-independent analysis settings."""
        return self._analysis_settings

    def sync_analysis_settings_from_view(self) -> AnalysisSettings:
        """Pull settings at the presentation boundary after a UI event."""
        if not hasattr(self, "view"):
            return self._analysis_settings
        self._analysis_settings = self.view.get_analysis_settings()
        return self._analysis_settings

    def apply_analysis_settings(self, settings: AnalysisSettings) -> None:
        """Apply analysis settings through the active presentation adapter."""
        self._analysis_settings = settings
        self.view.apply_analysis_settings(settings)

    def get_plot_type(self):
        """현재 플롯 타입(메인 UI 기준)."""
        return self.get_analysis_settings().plot_type

    def get_outlier_mode(self):
        """이상치 제거 모드: None, '1sigma', '2sigma'."""
        return self.get_analysis_settings().outlier_mode

    def get_plot_data_list(self) -> list[PlotDataItem]:
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
        return self.workspace_service.current_item()

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
        self.workspace_service.set_current_index(index)

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
        self.legacy_windows.cleanup()

    # --- 유틸리티 메서드 ---

    def _get_smart_ranges(
        self, plot_type, use_bark=False, f1_scale=None, f2_scale=None
    ):
        """플롯 타입과 스케일에 따른 지능형 범위 설정 (각 축의 단위를 독립적으로 반영)"""
        if f1_scale is None or f2_scale is None:
            params = self._get_current_plot_params()
            f1_scale = f1_scale or params.get("f1_scale", "linear")
            f2_scale = f2_scale or params.get("f2_scale", "linear")
        return self.plot_configuration_service.smart_ranges(
            plot_type, use_bark, f1_scale, f2_scale
        )

    def _get_main_ui_plot_params(self) -> PlotParams:
        """Build render params from the UI-independent analysis state."""
        return self.get_analysis_settings().to_plot_params()

    def _get_current_plot_params(self, popup_window=None) -> PlotParams:
        """팝업이 있으면 해당 창의 고정 파라미터, 없으면 메인 UI 설정값을 반환한다. Scale과 Unit은 별도 필드로 유지."""
        return self.plot_configuration_service.popup_params(
            popup_window,
            self._get_main_ui_plot_params(),
            self.get_analysis_settings().normalization,
        )
