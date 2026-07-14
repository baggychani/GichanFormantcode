"""Host-bound service assembly for ``MainController``."""

from __future__ import annotations

from dataclasses import dataclass

from core.compare_render_service import CompareRenderService
from core.compare_window_service import CompareWindowService
from core.export_workflow_service import ExportWorkflowService
from core.file_load_presentation_service import FileLoadPresentationService
from core.main_preview_workflow_service import MainPreviewWorkflowService
from core.main_workflow_service import MainWorkflowService
from core.analysis_workflow_service import AnalysisWorkflowService
from core.popup_lifecycle_service import PopupLifecycleService
from core.outlier_processing_service import OutlierProcessingService
from core.path_preference_service import PathPreferenceService
from core.plot_configuration_service import PlotConfigurationService
from core.plot_interaction_service import PlotInteractionService
from core.plot_render_workflow_service import PlotRenderWorkflowService
from core.popup_workflow_service import PopupWorkflowService
from core.project_restore_service import ProjectRestoreService
from core.single_plot_service import SinglePlotService


@dataclass
class ControllerServiceBundle:
    project_restore: ProjectRestoreService
    outlier_processing: OutlierProcessingService
    export_workflow: ExportWorkflowService
    popup_workflow: PopupWorkflowService
    plot_configuration: PlotConfigurationService
    file_load_presentation: FileLoadPresentationService
    plot_render_workflow: PlotRenderWorkflowService
    path_preferences: PathPreferenceService
    main_preview_workflow: MainPreviewWorkflowService
    main_workflow: MainWorkflowService
    analysis_workflow: AnalysisWorkflowService
    popup_lifecycle: PopupLifecycleService
    compare_render: CompareRenderService
    compare_window: CompareWindowService
    single_plot: SinglePlotService
    plot_interaction: PlotInteractionService

    @classmethod
    def create(cls, host):
        return cls(
            project_restore=ProjectRestoreService(host),
            outlier_processing=OutlierProcessingService(),
            export_workflow=ExportWorkflowService(host),
            popup_workflow=PopupWorkflowService(host),
            plot_configuration=PlotConfigurationService(),
            file_load_presentation=FileLoadPresentationService(host),
            plot_render_workflow=PlotRenderWorkflowService(host),
            path_preferences=PathPreferenceService(host),
            main_preview_workflow=MainPreviewWorkflowService(host),
            main_workflow=MainWorkflowService(host),
            analysis_workflow=AnalysisWorkflowService(host),
            popup_lifecycle=PopupLifecycleService(host),
            compare_render=CompareRenderService(host),
            compare_window=CompareWindowService(host),
            single_plot=SinglePlotService(host),
            plot_interaction=PlotInteractionService(host),
        )

    def attach(self, host) -> None:
        host.project_restore_service = self.project_restore
        host.outlier_processing_service = self.outlier_processing
        host.export_workflow_service = self.export_workflow
        host.popup_workflow_service = self.popup_workflow
        host.plot_configuration_service = self.plot_configuration
        host.file_load_presentation_service = self.file_load_presentation
        host.plot_render_workflow_service = self.plot_render_workflow
        host.path_preference_service = self.path_preferences
        host.main_preview_workflow_service = self.main_preview_workflow
        host.main_workflow_service = self.main_workflow
        host.analysis_workflow_service = self.analysis_workflow
        host.popup_lifecycle_service = self.popup_lifecycle
        host.compare_render_service = self.compare_render
        host.compare_window_service = self.compare_window
        host.single_plot_service = self.single_plot
        host.plot_interaction_service = self.plot_interaction
