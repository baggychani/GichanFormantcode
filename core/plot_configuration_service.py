"""Range and render-parameter policy independent of Qt widgets."""

from __future__ import annotations

import config
from utils.math_utils import hz_to_bark


class PlotConfigurationService:
    @staticmethod
    def axis_units(params):
        use_bark = params.get("use_bark_units", False)
        return (
            "Bark" if params.get("f1_scale", "linear") == "bark" and use_bark else "Hz",
            "Bark" if params.get("f2_scale", "linear") == "bark" and use_bark else "Hz",
        )

    @staticmethod
    def read_ranges(widgets):
        return {key: widgets[key].text() for key in ("y_min", "y_max", "x_min", "x_max")}

    @staticmethod
    def apply_ranges(widgets, ranges):
        for key in ("y_min", "y_max", "x_min", "x_max"):
            widgets[key].setText(ranges[key])

    def smart_ranges(self, plot_type, use_bark=False, f1_scale="linear", f2_scale="linear"):
        hz = config.HZ_RANGES.get(plot_type, config.HZ_RANGES["f1_f2"])
        bark = config.BARK_RANGES.get(plot_type, config.BARK_RANGES["f1_f2"])
        y_range = bark if f1_scale == "bark" and use_bark else hz
        x_range = bark if f2_scale == "bark" and use_bark else hz
        x_min = x_range["x_min"]
        if plot_type in ("f1_f2_minus_f1", "f1_f2_prime_minus_f1") and f2_scale == "log":
            x_min = 100 if x_range is hz else max(0, int(round(hz_to_bark(100.0))))
        return {"y_min": str(y_range["y_min"]), "y_max": str(y_range["y_max"]), "x_min": str(x_min), "x_max": str(x_range["x_max"])}

    @staticmethod
    def popup_params(popup, main_params, normalization):
        if not popup or not hasattr(popup, "fixed_plot_params"):
            return main_params
        params = popup.fixed_plot_params.copy()
        if hasattr(popup, "get_sigma"):
            try:
                params["sigma"] = float(popup.get_sigma())
            except (TypeError, ValueError):
                pass
        use_bark = params.get("use_bark_units", False)
        params.setdefault("f1_unit", "Bark" if params.get("f1_scale") == "bark" and use_bark else "Hz")
        params.setdefault("f2_unit", "Bark" if params.get("f2_scale") == "bark" and use_bark else "Hz")
        if getattr(popup, "uses_main_normalization", False):
            params["normalization"] = normalization
            popup.normalization = normalization
        return params
