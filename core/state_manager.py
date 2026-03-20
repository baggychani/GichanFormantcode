"""
StateManager - 중앙 집중식 상태 관리 시스템

컴포넌트 간 통신을 단순화하기 위한 EventBus/StateManager 패턴 구현.
각 컴포넌트는 StateManager를 구독(Subscribe)하여 상태 변경을 알림 받습니다.
"""

from PySide6.QtCore import QObject, Signal


class StateManager(QObject):
    """
    싱글톤 패턴의 중앙 상태 관리자.

    사용법:
        state = StateManager.instance()
        state.filter_changed.connect(my_handler)
        state.emit_filter_changed({'vowel': 'a', 'visible': True})
    """

    filter_changed = Signal(dict)
    design_changed = Signal(dict)
    data_changed = Signal(object)
    tool_state_changed = Signal(str, bool)
    plot_refresh_requested = Signal()
    layer_order_changed = Signal(list)
    lock_state_changed = Signal(bool)

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, parent=None):
        if self._initialized:
            return
        super().__init__(parent)
        self._initialized = True

        self._filter_state = {}
        self._design_state = {}
        self._tool_states = {}
        self._lock_state = False

    @classmethod
    def instance(cls):
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """테스트용: 인스턴스 초기화"""
        cls._instance = None

    def get_filter_state(self) -> dict:
        return self._filter_state.copy()

    def get_design_state(self) -> dict:
        return self._design_state.copy()

    def get_tool_state(self, tool_name: str) -> bool:
        return self._tool_states.get(tool_name, False)

    def get_lock_state(self) -> bool:
        return self._lock_state

    def emit_filter_changed(self, filter_state: dict):
        """필터 상태 변경 알림"""
        self._filter_state = filter_state.copy()
        self.filter_changed.emit(filter_state)

    def emit_design_changed(self, design_state: dict):
        """디자인 설정 변경 알림"""
        self._design_state = design_state.copy()
        self.design_changed.emit(design_state)

    def emit_data_changed(self, data):
        """데이터 변경 알림"""
        self.data_changed.emit(data)

    def emit_tool_state_changed(self, tool_name: str, is_active: bool):
        """도구 상태 변경 알림"""
        self._tool_states[tool_name] = is_active
        self.tool_state_changed.emit(tool_name, is_active)

    def emit_plot_refresh_requested(self):
        """플롯 갱신 요청"""
        self.plot_refresh_requested.emit()

    def emit_layer_order_changed(self, order: list):
        """레이어 순서 변경 알림"""
        self.layer_order_changed.emit(order)

    def emit_lock_state_changed(self, is_locked: bool):
        """설정 잠금 상태 변경 알림"""
        self._lock_state = is_locked
        self.lock_state_changed.emit(is_locked)
