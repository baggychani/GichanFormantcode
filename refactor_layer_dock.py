import ast

def replace_layer_dock():
    filepath = "c:/Users/woori/Desktop/GichanFormant/ui/widgets/layer_dock.py"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Add import for LayerDataModel
    if "from ui.widgets.layer_data_model import LayerDataModel" not in content:
        content = content.replace("from ui.widgets.label_manager import LabelManager\nfrom ui.widgets.draw_manager import DrawManager", 
                                  "from ui.widgets.layer_data_model import LayerDataModel\nfrom ui.widgets.label_manager import LabelManager\nfrom ui.widgets.draw_manager import DrawManager")

    # Update __init__
    old_init = """        self.label_manager = LabelManager(self.popup, state_key=self._state_key)
        self.draw_manager = DrawManager(self.popup)"""
    new_init = """        self.label_manager = LabelManager(self.popup, state_key=self._state_key)
        self.draw_manager = DrawManager(self.popup)
        self.data_model = LayerDataModel(self.label_manager, self.draw_manager, self)
        
        # Connect internal signal to data_model (for backward compatibility if needed)
        self.data_model.filter_state_changed.connect(self.filter_state_changed.emit)
        self.data_model.layer_overrides_changed.connect(self.overrides_changed.emit)
        self.data_model.layer_order_changed.connect(self.order_changed.emit)"""
    content = content.replace(old_init, new_init)

    # _get_current_filter_state
    old_get_filter = """    def _get_current_filter_state(self):
        return self.label_manager.get_filter_state()"""
    new_get_filter = """    def _get_current_filter_state(self):
        return self.data_model.get_filter_state()"""
    content = content.replace(old_get_filter, new_get_filter)
    
    # _set_filter_state
    old_set_filter = """    def _set_filter_state(self, state):
        self.label_manager.set_filter_state(state)
        self.filter_state_changed.emit(state)
        self._update_global_row_state()"""
    new_set_filter = """    def _set_filter_state(self, state):
        self.data_model.set_filter_state(state)
        self._update_global_row_state()"""
    content = content.replace(old_set_filter, new_set_filter)
    
    # _get_layer_overrides
    old_get_overrides = """    def _get_layer_overrides(self):
        return self.label_manager.get_layer_overrides()"""
    new_get_overrides = """    def _get_layer_overrides(self):
        return self.data_model.get_layer_overrides()"""
    content = content.replace(old_get_overrides, new_get_overrides)
    
    # _set_layer_overrides
    old_set_overrides = """    def _set_layer_overrides(self, overrides):
        self.label_manager.set_layer_overrides(overrides)"""
    new_set_overrides = """    def _set_layer_overrides(self, overrides):
        self.data_model.set_layer_overrides(overrides)"""
    content = content.replace(old_set_overrides, new_set_overrides)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("layer_dock.py successfully refactored.")

if __name__ == "__main__":
    replace_layer_dock()
