"""Analysis-setting propagation across workspace, preview, and plot popups."""

from __future__ import annotations

import config
from utils import app_logger


class AnalysisWorkflowService:
    def __init__(self, host) -> None:
        self.host = host

    def outlier_changed(self, mahalanobis_filter, tukey_filter) -> None:
        host = self.host
        settings = host.sync_analysis_settings_from_view()
        previous = host.last_outlier_mode
        host.last_outlier_mode = settings.outlier_mode
        if not host.plot_data_list:
            return
        service = host.outlier_processing_service
        service.mahalanobis_filter = mahalanobis_filter
        service.tukey_filter = tukey_filter
        result = service.apply(
            host.plot_data_list,
            mode=settings.outlier_mode,
            plot_type=settings.plot_type,
            scope=settings.outlier_scope or "combined",
        )
        if settings.outlier_mode is None and previous is not None:
            app_logger.info(config.LOG_MSG["OUTLIER_OFF"])
        message = self._outlier_message(result)
        if message:
            app_logger.info(message)
        host._rebuild_combined_entry()
        host.update_live_preview()

    @staticmethod
    def _outlier_message(result):
        if result.total_removed:
            entries = sorted(result.file_removed, key=lambda item: -item[1])
            detail = " (" + ", ".join(f"{name}: {count}개" for name, count in entries[:5])
            detail += " … 외)" if len(entries) > 5 else ")"
            return config.LOG_MSG["OUTLIER_REMOVED_SUMMARY"].format(
                file_count=len(entries), total_removed=result.total_removed, detail=detail
            )
        if result.files_with_small_labels:
            details = []
            for name, labels in result.files_with_small_labels[:5]:
                details.append(f"{name}: {', '.join(labels[:5])}{' …' if len(labels) > 5 else ''}")
            return config.LOG_MSG["OUTLIER_NOT_REMOVED_MIN_LABELS"].format(detail=" / ".join(details))
        return config.LOG_MSG["OUTLIER_NOT_REMOVED_NONE"] if result.any_label_tested else None

    def sync_single_popup_normalization(self, popup) -> None:
        if not getattr(popup, "uses_main_normalization", False):
            return
        normalization = self.host.get_analysis_settings().normalization
        changed = normalization != getattr(popup, "_last_synced_normalization", "__unset__")
        popup.normalization = normalization
        popup._last_synced_normalization = normalization
        if hasattr(popup, "lbl_norm_value"):
            popup.lbl_norm_value.setText(normalization or "없음")
        if changed:
            if normalization:
                self.host._apply_ranges_to_widgets(
                    popup.range_widgets, self.host._norm_ranges_for_widgets(normalization)
                )
            elif hasattr(popup, "_reset_ranges_to_default"):
                popup._reset_ranges_to_default(apply_plot=False)
        if hasattr(popup, "_apply_normalization_axis_ui"):
            popup._apply_normalization_axis_ui()

    def request_preview(self) -> None:
        host = self.host
        if not hasattr(host, "view"):
            return
        host.sync_analysis_settings_from_view()
        if not host.view.supports_preview():
            return
        if not host.plot_data_list:
            host._set_preview_empty()
            return
        host._live_preview_debouncer.trigger(150)
