# GichanFormant Working Rules

## MANDATORY: No Checkbox UI

- Never use checkbox controls in the application UI. Use a visible toggle switch
  with `role="switch"` and `aria-checked` for binary settings, including modal
  dialogs and export options. This is a shared project rule and must remain in
  this tracked file, not only in local ignored agent instructions.

## Desktop Shell: Keep Orchestrators Thin

Shared, versioned rule (this file). Do not rely only on local Cursor/user rules
that may be gitignored.

Two thin orchestrators remain after the interactive-plot / main-window split:

- Plot window: `desktop/src/components/InteractivePlotWindow.tsx`
- Main window: `desktop/src/components/mainWorkspace/MainWorkspace.tsx`
- App router only: `desktop/src/App.tsx` (hash → plot vs main)

### Placement map (put new work here, not in the orchestrator)

| Feature | Own module |
|---------|------------|
| Layer session / DnD | `interactivePlot/useLayerSession.ts`, `LayersPanel.tsx` |
| Draw session / styles | `interactivePlot/useDrawSession.ts`, `DrawingPanel.tsx`, `DrawStyleEditor.tsx` |
| Ruler / plot-label session | `interactivePlot/useRulerSession.ts` |
| Preview render / schedule | `interactivePlot/usePlotRender.ts` |
| Plot runtime / navigation | `interactivePlot/usePlotWindowSession.ts`, `usePlotNavigation.ts` |
| Plot save / export actions | `interactivePlot/usePlotWindowActions.ts` |
| Batch export session | `interactivePlot/useBatchExportSession.ts`, `BatchExportDialog.tsx` |
| Plot shell layout | `interactivePlot/PlotWindowHeader.tsx`, `PlotControlRail.tsx`, `PlotInspector.tsx`, `PlotWindowOverlays.tsx` |
| Canvas overlays / pointers | `interactivePlot/PlotStage.tsx`, `plotGeometry.ts` |
| Hz↔Bark converter plugin | `interactivePlot/UnitConverterPopover.tsx` |
| Left analysis / global design | `AnalysisToolsPanel.tsx`, `GlobalDesignPanel.tsx` |
| Main file sidebar | `mainWorkspace/SourceSidebar.tsx` |
| Main preview | `mainWorkspace/PreviewStage.tsx` |
| Main analysis settings | `mainWorkspace/AnalysisSettingsPanel.tsx` |
| Main runtime / theme | `mainWorkspace/useMainWorkspaceSession.ts`, `useThemePreference.ts` |
| Main file / project actions | `mainWorkspace/useWorkspaceActions.ts` |

### Hard constraints

- Orchestrators may **wire** hooks/panels and pass props. Do not add new feature
  `useState`, long handlers, or large JSX blocks there.
- If a change would grow an orchestrator by roughly **80+ lines** of real logic
  or JSX, extract a module/hook/panel first, then wire it.
- Prefer extending an existing map row over inventing a parallel path in the
  orchestrator. Add a new row to this table when a new domain appears.

## Text Encoding

- Store all source code, JSON, TOML, Markdown, and test fixtures as UTF-8.
- The desktop sidecar protocol is NDJSON encoded as UTF-8 bytes. Never rely on
  the Windows ANSI code page or the active terminal locale for this boundary.
- Keep Python sidecar standard input and output explicitly configured as UTF-8.
  Do not remove `PYTHONUTF8`, `PYTHONIOENCODING`, or the sidecar stdio setup
  without an equivalent end-to-end guarantee.

## Changes To IPC

- When changing sidecar request parsing or process spawning, add or update a
  regression test that sends a non-ASCII Windows path as UTF-8 bytes.
- Do not treat terminal display output as evidence of the underlying byte
  encoding. Use byte-level assertions or Unicode escape test data when the
  shell code page could alter pasted characters.
- Preserve a request id whenever a malformed request can still be identified,
  so the Rust caller fails promptly instead of waiting for its timeout.
