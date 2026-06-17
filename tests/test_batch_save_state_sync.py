import os
import sys

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.windows.popup_plot import PlotPopup
import ui.windows.popup_plot as popup_plot_module


class _FakeEdit:
    def __init__(self, value: str):
        self._value = value

    def text(self):
        return self._value


class _FakeCombo:
    def __init__(self, value: str):
        self._value = value

    def currentText(self):
        return self._value


class _FakeController:
    pass


def test_on_batch_save_flushes_current_file_state(monkeypatch):
    class _FakePopup:
        def __init__(self):
            self.controller = _FakeController()
            self.range_widgets = {
                "y_min": _FakeEdit("200"),
                "y_max": _FakeEdit("900"),
                "x_min": _FakeEdit("400"),
                "x_max": _FakeEdit("3200"),
            }
            self.cb_sigma = _FakeCombo("2.0")
            self.lbl_f1_unit = _FakeEdit("(Hz)")
            self.lbl_f2_unit = _FakeEdit("(Hz)")
            self.x_axis_label = "F2"
            self._saved_overrides = False
            self._saved_filters = False

        def _save_layer_overrides_for_current_file(self):
            self._saved_overrides = True

        def _save_filter_state_for_current_file(self):
            self._saved_filters = True

    created = {"called": False}

    class _FakeBatchSaveDialog:
        def __init__(
            self,
            parent,
            controller,
            current_ranges,
            f1_unit_text,
            f2_unit_text,
            x_axis_label,
            current_sigma,
        ):
            assert parent._saved_overrides is True
            assert parent._saved_filters is True
            created["called"] = True
            # 생성 인자도 기본적으로 정상 전달되는지 간단히 확인
            assert current_ranges["y_min"] == "200"
            assert f1_unit_text == "Hz"
            assert x_axis_label == "F2"
            assert current_sigma == "2.0"

        def exec(self):
            return 0

    monkeypatch.setattr(popup_plot_module, "BatchSaveDialog", _FakeBatchSaveDialog)

    popup = _FakePopup()
    PlotPopup.on_batch_save(popup)

    assert created["called"] is True
    assert popup._saved_overrides is True
    assert popup._saved_filters is True
