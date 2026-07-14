"""Regression guards for the MainController composition boundary."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from core.controller import MainController
from core.runtime_port import HeadlessRuntime
from core.view_port import NullMainView


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER_PATH = ROOT / "core" / "controller.py"
CONTROLLER_LINE_BUDGET = 1000


def _controller_source() -> str:
    return CONTROLLER_PATH.read_text(encoding="utf-8")


def test_controller_stays_within_composition_root_budget():
    line_count = len(_controller_source().splitlines())
    assert line_count <= CONTROLLER_LINE_BUDGET, (
        "MainController exceeded its composition-root budget "
        f"({line_count} > {CONTROLLER_LINE_BUDGET}). Move the workflow to its "
        "own service instead of expanding core/controller.py."
    )


def test_controller_has_no_direct_widget_imports_and_uses_service_bundle():
    source = _controller_source()
    module = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(module)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(
        module_name == "ui" or module_name.startswith(("ui.", "PySide6"))
        for module_name in imported_modules
    )

    controller = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "MainController"
    )
    initializer = next(
        node for node in controller.body if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    initializer_source = ast.get_source_segment(source, initializer) or ""
    assert "ControllerServiceBundle.create(self).attach(self)" in initializer_source


def test_service_bundle_attaches_host_bound_services_to_controller():
    view = NullMainView()
    controller = MainController(
        view_factory=lambda *_args: view,
        runtime=HeadlessRuntime(),
        render_initial_preview=False,
    )

    service_names = (
        "project_restore_service",
        "outlier_processing_service",
        "export_workflow_service",
        "popup_workflow_service",
        "plot_configuration_service",
        "file_load_presentation_service",
        "plot_render_workflow_service",
        "path_preference_service",
        "main_preview_workflow_service",
        "main_workflow_service",
        "analysis_workflow_service",
        "popup_lifecycle_service",
        "compare_render_service",
        "compare_window_service",
        "single_plot_service",
        "plot_interaction_service",
    )
    for service_name in service_names:
        assert getattr(controller, service_name) is not None

    host_bound = set(service_names) - {
        "outlier_processing_service",
        "plot_configuration_service",
    }
    for service_name in host_bound:
        assert getattr(controller, service_name).host is controller


def test_major_controller_entrypoints_remain_service_delegates():
    expected_delegates = {
        "handle_file_drop": "main_workflow_service",
        "save_project_document": "main_workflow_service",
        "load_project_document": "main_workflow_service",
        "load_files": "main_workflow_service",
        "remove_file": "main_workflow_service",
        "reset_data": "main_workflow_service",
        "open_vowel_analysis_window": "popup_workflow_service",
        "open_compare_plot_for_source_groups": "popup_workflow_service",
        "open_compare_plot_for_indices": "compare_window_service",
        "refresh_plot": "plot_render_workflow_service",
        "navigate_plot": "single_plot_service",
        "toggle_ruler": "plot_interaction_service",
        "save_plot_to_file": "export_workflow_service",
        "create_batch_save_worker": "export_workflow_service",
    }

    for method_name, service_name in expected_delegates.items():
        source = inspect.getsource(getattr(MainController, method_name))
        assert f"self.{service_name}" in source, (
            f"{method_name} must stay a {service_name} adapter; "
            "move implementation work out of MainController."
        )
