# MainController boundary

`MainController` is the composition root for the legacy desktop UI.  It may
own presentation-facing state, select a service, and retain a small
compatibility facade for existing widgets.  It must not grow back into the
implementation home for a workflow.

## Rules for new work

1. Put file/project lifecycle in `MainWorkflowService` or
   `ProjectRestoreService`.
2. Put analysis-state normalization, ranges, and preview requests in
   `AnalysisWorkflowService`, `PlotConfigurationService`, or
   `MainPreviewWorkflowService`.
3. Put popup construction, rendering, interaction, and lifecycle work in the
   corresponding popup/plot service.
4. Put saving and batch export work in `ExportWorkflowService`.
5. A new Controller method is allowed only when it is a UI/legacy adapter. It
   should delegate to one service and stay small; otherwise add or extend a
   service first.

## Enforced guardrails

`tests/test_controller_architecture.py` enforces all of the following:

- Controller source stays at or below 1,000 lines.
- Service construction remains centralized in `ControllerServiceBundle`.
- The main file/project, popup, render, interaction, and export entry points
  continue to delegate to their owning services.
- The Controller cannot import PySide widgets or `ui.*` modules directly.

When a legitimate change needs to alter one of these rules, update this
document and the architecture test in the same change.  That makes the
decision explicit in review instead of silently reintroducing a God Object.

## Line endings

`.gitattributes` stores source and contract files as LF.  Existing Windows
worktrees may show a one-time conversion warning until a dedicated, clean-tree
normalization change is made.  Do not mix that normalization with feature work:
make it a separate maintenance commit so a real code review stays readable.
