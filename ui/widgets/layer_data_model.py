from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Any, List

class LayerDataModel(QObject):
    """
    layer_dock.py에서 분리된 레이어 순서 및 데이터 관리 모델.
    UI 없이 데이터 상태만 관리하며, 상태가 변경되면 Signal을 발생시킵니다.
    """
    filter_state_changed = pyqtSignal(dict)
    layer_overrides_changed = pyqtSignal(dict)
    layer_order_changed = pyqtSignal(list)
    draw_objects_changed = pyqtSignal()
    
    def __init__(self, label_manager, draw_manager, parent=None):
        super().__init__(parent)
        self.label_manager = label_manager
        self.draw_manager = draw_manager

    def get_filter_state(self) -> Dict[str, str]:
        return self.label_manager.get_filter_state()

    def set_filter_state(self, state: Dict[str, str]):
        self.label_manager.set_filter_state(state)
        self.filter_state_changed.emit(state)

    def get_layer_overrides(self) -> Dict[str, Dict[str, Any]]:
        return self.label_manager.get_layer_overrides()

    def set_layer_overrides(self, overrides: Dict[str, Dict[str, Any]]):
        self.label_manager.set_layer_overrides(overrides)
        self.layer_overrides_changed.emit(overrides)

    def get_layer_order(self) -> List[str]:
        return self.label_manager.get_layer_order()

    def set_layer_order(self, order: List[str]):
        self.label_manager.set_layer_order(order)
        self.layer_order_changed.emit(order)
        
    def get_draw_objects(self) -> List[object]:
        return self.draw_manager.get_draw_objects()
        
    def set_draw_objects(self, objs: List[object]):
        self.draw_manager.set_draw_objects(objs)
        self.draw_objects_changed.emit()
        
    def update_single_vowel_filter(self, vowel: str, new_state: str):
        st = self.get_filter_state()
        st[vowel] = new_state
        self.set_filter_state(st)
        
    def get_locked_vowels(self) -> set[str]:
        return self.label_manager.get_locked_vowels_set()
        
    def set_locked_vowel(self, vowel: str, checked: bool):
        self.label_manager.set_locked_vowel(vowel, checked)
        
    def redraw_plot(self):
        self.draw_manager.redraw()
        
    def apply_draw_item_state(self, draw_index: int, key: str, value: Any, sync_children=False) -> object:
        objs = self.get_draw_objects()
        if not (0 <= draw_index < len(objs)):
            return None
        obj = objs[draw_index]
        setattr(obj, key, value)
        
        if sync_children and getattr(obj, "type", "") == "polygon":
            from ui.widgets.layer_logic import get_children_indices
            for child_idx in get_children_indices(objs, draw_index):
                if 0 <= child_idx < len(objs):
                    setattr(objs[child_idx], key, value)
                    
        self.set_draw_objects(objs)
        self.redraw_plot()
        return obj
