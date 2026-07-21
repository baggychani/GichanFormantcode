import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open, save } from "@tauri-apps/plugin-dialog";
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Layers3,
  Loader2,
  MousePointer2,
  Palette,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  PenLine,
  Ruler,
  SlidersHorizontal,
  X,
} from "lucide-react";
import type { ApplicationState } from "../../ipc/protocol";
import { callSidecar } from "../sidecarClient";
import { cacheMapSet } from "../cacheMap";
import { sortVowels } from "../vowelSort";
import {
  barkToHz,
  formatRulerDistance,
  formatRulerPointTooltip,
  formatRulerTriangleLegs,
  hzToBark,
  resolvePlotUnits,
  smartAxisRanges,
} from "../plotUnits";
import {
  axisPreviewFontFamily,
  BARK_RANGE_DEFAULTS,
  EMPTY_DESIGN,
  fontFamilyStyle,
  NORM_RANGE_DEFAULTS,
  RANGE_DEFAULTS,
  rangesLookCompatible,
} from "./interactivePlot/designDefaults";
import {
  clampDrawLineWidth,
  clampDrawTextFontSize,
  clampDrawTextLineSpacing,
  DRAW_LINE_DEFAULT_COLOR,
  DRAW_TEXT_DEFAULT_COLOR,
  DRAW_TEXT_DEFAULT_FAMILY,
  DRAW_TEXT_DEFAULT_LINE_SPACING,
  formatRefLabel,
  roundRefValue,
} from "./interactivePlot/drawDefaults";
import { MAX_CACHED_FILE_DESIGNS } from "./interactivePlot/layerCache";
import * as plotGeometry from "./interactivePlot/plotGeometry";
import {
  clearVowelAnalysisCache,
  fetchVowelAnalysisSections,
  getCachedVowelAnalysis,
  hasVowelAnalysisSection,
  vowelAnalysisCacheKey,
} from "./interactivePlot/vowelAnalysisCache";
import { AnalysisToolsPanel } from "./interactivePlot/AnalysisToolsPanel";
import { BatchExportDialog } from "./interactivePlot/BatchExportDialog";
import { DrawStyleEditor } from "./interactivePlot/DrawStyleEditor";
import { DrawingPanel } from "./interactivePlot/DrawingPanel";
import { GlobalDesignPanel } from "./interactivePlot/GlobalDesignPanel";
import { LayersPanel } from "./interactivePlot/LayersPanel";
import { ShortcutHelpDialog } from "./interactivePlot/ShortcutHelpDialog";
import { useDrawSession } from "./interactivePlot/useDrawSession";
import {
  type InteractiveRenderOverrides,
  useLayerSession,
} from "./interactivePlot/useLayerSession";
import { VowelAnalysisShell } from "./interactivePlot/VowelAnalysisShell";
import { FileSelectMenu } from "./interactivePlot/widgets";
import type {
  DesignSettings,
  DrawHoverState,
  DrawLegendObject,
  DrawObject,
  DrawPoint,
  DrawReferenceObject,
  DrawTextObject,
  DrawTool,
  LeftPanel,
  PlotLabel,
  Ranges,
  ReferencePreview,
  RightPanel,
  RulerContext,
  RulerDisplayMode,
  RulerGeometryMode,
  RulerMeasurement,
  RulerPoint,
  SidecarEvent,
  Tool,
} from "./interactivePlot/types";
import "./InteractivePlotWindow.css";

export function InteractivePlotWindow() {
  const [state, setState] = useState<ApplicationState | null>(null);
  const [combinedVisible, setCombinedVisible] = useState(() => window.localStorage.getItem("gichanformant-show-combined") === "true");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewInfo, setPreviewInfo] = useState("");
  const [batchExportOpen, setBatchExportOpen] = useState(false);
  const [batchExportFormat, setBatchExportFormat] = useState<"png" | "jpg" | "svg">("png");
  const [batchExportDirectory, setBatchExportDirectory] = useState("");
  const [batchExportBusy, setBatchExportBusy] = useState(false);
  const [rulerSettingsOpen, setRulerSettingsOpen] = useState(false);
  const [rulerGeometryMode, setRulerGeometryMode] = useState<RulerGeometryMode>("direct");
  const [rulerDisplayMode, setRulerDisplayMode] = useState<RulerDisplayMode>("hz");
  const [batchApplyGlobalDesign, setBatchApplyGlobalDesign] = useState(true);
  const [batchApplyLayerDesign, setBatchApplyLayerDesign] = useState(true);
  const [batchApplyVisibility, setBatchApplyVisibility] = useState(true);
  const [batchApplyLabelPositions, setBatchApplyLabelPositions] = useState(true);
  const [rulerContext, setRulerContext] = useState<RulerContext | null>(null);
  const [rulerStart, setRulerStart] = useState<RulerPoint | null>(null);
  const [rulerHover, setRulerHover] = useState<RulerPoint | null>(null);
  const [rulerPointer, setRulerPointer] = useState<{ x: number; y: number } | null>(null);
  const [rulerMeasurements, setRulerMeasurements] = useState<RulerMeasurement[]>([]);
  const [draggingRulerLabel, setDraggingRulerLabel] = useState<number | null>(null);
  const [draggingPlotLabel, setDraggingPlotLabel] = useState<string | null>(null);
  const [hoveredPlotLabel, setHoveredPlotLabel] = useState<string | null>(null);
  const [plotLabelPointer, setPlotLabelPointer] = useState<{ x: number; y: number } | null>(null);
  const [plotLabelPreviewVowel, setPlotLabelPreviewVowel] = useState<string | null>(null);
  const [tool, setTool] = useState<Tool>("select");
  const [leftPanel, setLeftPanel] = useState<LeftPanel>("analysis");
  const [rightPanel, setRightPanel] = useState<RightPanel>("layers");
  const [draggingTextId, setDraggingTextId] = useState<string | null>(null);
  const [hoveredDrawTextId, setHoveredDrawTextId] = useState<string | null>(null);
  const [textDragPointer, setTextDragPointer] = useState<{ x: number; y: number } | null>(null);
  const textDragRef = useRef<{ id: string; offsetX: number; offsetY: number } | null>(null);
  const textDragFrameRef = useRef<number | null>(null);
  const textHasMovedRef = useRef(false);
  const [draggingLegend, setDraggingLegend] = useState(false);
  const [legendDragPreview, setLegendDragPreview] = useState<Pick<DrawLegendObject, "fx" | "fy" | "width_frac" | "height_frac"> | null>(null);
  const [referencePreview, setReferencePreview] = useState<ReferencePreview | null>(null);
  const [globalDesignLocked, setGlobalDesignLocked] = useState(true);
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [ranges, setRanges] = useState<Ranges>(RANGE_DEFAULTS.f1_f2);
  const [sigma, setSigma] = useState("2.0");
  const [showEllipse, setShowEllipse] = useState(true);
  const [design, setDesign] = useState<DesignSettings>(EMPTY_DESIGN);
  const [navigating, setNavigating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [engineConnected, setEngineConnected] = useState(false);
  const [vowelAnalysisOpen, setVowelAnalysisOpen] = useState(false);
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false);
  const [message, setMessage] = useState("분석 엔진과 연결하는 중입니다.");
  const aliveRef = useRef(true);
  const navigatingRef = useRef(false);
  const currentIndexRef = useRef(0);
  // A reopened Tauri window must not accept an older preview event from the
  // same sidecar just because its local counter started at zero again.
  const renderRequestRef = useRef(Date.now() * 1000);
  const renderTimerRef = useRef<number | null>(null);
  const renderInteractiveRef = useRef<(overrides?: InteractiveRenderOverrides) => void | Promise<void>>(async () => {});
  const scheduleInteractiveRenderRef = useRef<(overrides?: InteractiveRenderOverrides) => void>(() => {});
  const applyLegendBoundsRef = useRef<(legendBounds: Record<string, { width_frac: number; height_frac: number }>) => void>(() => {});
  const plotPaperRef = useRef<HTMLDivElement | null>(null);
  const plotImageRef = useRef<HTMLImageElement | null>(null);
  const plotLabelFrameRef = useRef<number | null>(null);
  const plotLabelDragStartRef = useRef<{ x: number; y: number } | null>(null);
  const plotLabelHasMovedRef = useRef(false);
  const legendDragRef = useRef<{ startX: number; startY: number; fx: number; fy: number } | null>(null);
  const legendFrameRef = useRef<number | null>(null);
  const referencePointerRef = useRef<ReferencePreview | null>(null);
  const referenceMoveRef = useRef<(clientX: number, clientY: number) => void>(() => {});
  const lineMoveRef = useRef<(clientX: number, clientY: number) => void>(() => {});
  const areaMoveRef = useRef<(clientX: number, clientY: number) => void>(() => {});
  const legendPointerRef = useRef<Pick<DrawLegendObject, "fx" | "fy" | "width_frac" | "height_frac"> | null>(null);
  const globalDesignByFileRef = useRef(new Map<string, DesignSettings>());
  const designInitializedRef = useRef(false);
  const [previewLoading, setPreviewLoading] = useState(true);

  const refresh = useCallback(async () => {
    setPreviewLoading(true);
    try {
      const next = await callSidecar<ApplicationState>("get_state");
      if (!aliveRef.current) return;
      setState(next);
      setEngineConnected(true);
      if (next.capabilities.can_plot) {
        const requestId = ++renderRequestRef.current;
        const nextNorm = next.analysis?.normalization ?? null;
        const nextPlotType = next.analysis?.type ?? "f1_f2";
        const useBark = next.analysis?.use_bark_units ?? false;
        let bootRanges: Ranges;
        if (nextNorm) {
          bootRanges = NORM_RANGE_DEFAULTS[nextNorm] ?? NORM_RANGE_DEFAULTS.Lobanov;
        } else {
          bootRanges = smartAxisRanges(nextPlotType, next.analysis, RANGE_DEFAULTS, BARK_RANGE_DEFAULTS);
        }
        const sessionRanges = next.plot_session?.ranges as Ranges | undefined;
        const rangesForBoot = sessionRanges
          && Object.keys(sessionRanges).length === 4
          && rangesLookCompatible(sessionRanges, nextNorm, useBark)
          ? sessionRanges
          : bootRanges;
        setRanges(rangesForBoot);
        await callSidecar("render_interactive_preview", {
          options: { request_id: requestId, ranges: rangesForBoot },
        });
      } else {
        setPreviewLoading(false);
      }
    } catch (err) {
      setEngineConnected(false);
      setMessage(`플롯을 불러오지 못했습니다: ${String(err)}`);
      setPreviewLoading(false);
    }
  }, []);

  useEffect(() => {
    aliveRef.current = true;
    void refresh();
    let disposed = false;
    let disposeEvent: (() => void) | undefined;
    void listen<SidecarEvent>("sidecar-event", ({ payload }) => {
      if (disposed || !aliveRef.current) return;
      if (payload.event === "preview_ready" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (Number.isFinite(requestId) && requestId > 0 && requestId < renderRequestRef.current) return;
        const imagePath = String(payload.payload.png_path ?? "");
        const image = String(payload.payload.png_base64 ?? "");
        setPreviewUrl(imagePath ? convertFileSrc(imagePath) : image ? `data:image/png;base64,${image}` : null);
        setPreviewLoading(false);
        const nextRuler = (payload.payload.ruler_context as RulerContext | undefined) ?? null;
        setRulerContext(nextRuler);
        const legendBounds = nextRuler?.legend_bounds;
        if (legendBounds) {
          applyLegendBoundsRef.current(legendBounds);
        }
        setLegendDragPreview(null);
        setPlotLabelPreviewVowel(null);
        setPlotLabelPointer(null);
        setRulerStart(null);
        setRulerHover(null);
        setRulerMeasurements([]);
        setPreviewInfo(String(payload.payload.info ?? ""));
        setMessage("현재 설정을 플롯에 반영했습니다.");
      } else if (payload.event === "preview_failed" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (requestId && requestId < renderRequestRef.current) return;
        setPreviewLoading(false);
        setMessage(`렌더링 오류: ${String(payload.payload.message ?? "알 수 없는 오류")}`);
      } else if (payload.event === "preview_cleared" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (requestId && requestId < renderRequestRef.current) return;
        setPreviewUrl(null);
        setPreviewLoading(false);
        setRulerContext(null);
        setRulerStart(null);
        setRulerMeasurements([]);
        setPreviewInfo("");
      } else if (payload.event === "state_changed") {
        const reason = String(payload.payload.reason ?? "");
        // Navigation returns the authoritative snapshot in its IPC response.
        // Ignore the matching broadcast so controls do not reset once before
        // the response applies the new file state.
        if (navigatingRef.current && reason === "current_file_changed") return;
        const next = payload.payload.state as ApplicationState | undefined;
        if (next) setState(next);
      } else if (payload.event === "plot_session_changed") {
        const nextSession = payload.payload.plot_session as ApplicationState["plot_session"] | undefined;
        if (!nextSession || typeof nextSession.revision !== "number") return;
        setState((previous) => {
          if (!previous) return previous;
          if (nextSession.revision <= (previous.plot_session?.revision ?? -1)) return previous;
          return { ...previous, plot_session: nextSession };
        });
      } else if (payload.event === "sidecar_shutting_down") {
        setEngineConnected(false);
      }
    }).then((dispose) => {
      if (disposed) dispose();
      else disposeEvent = dispose;
    }).catch((err) => {
      if (!disposed && aliveRef.current) setMessage(String(err));
    });
    return () => {
      disposed = true;
      aliveRef.current = false;
      disposeEvent?.();
    };
  }, [refresh]);

  useEffect(() => {
    const applySharedTheme = () => {
      const saved = window.localStorage.getItem("gichanformant-theme");
      const theme = saved === "dark" || saved === "light"
        ? saved
        : window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      document.documentElement.dataset.theme = theme;
      document.documentElement.style.colorScheme = theme;
    };
    applySharedTheme();
    window.addEventListener("storage", applySharedTheme);
    window.addEventListener("focus", applySharedTheme);
    let themeDisposed = false;
    let unlistenTheme: (() => void) | undefined;
    void listen<string>("gichan-theme", ({ payload }) => {
      if (payload !== "light" && payload !== "dark") return;
      document.documentElement.dataset.theme = payload;
      document.documentElement.style.colorScheme = payload;
    }).then((dispose) => {
      if (themeDisposed) dispose();
      else unlistenTheme = dispose;
    });
    return () => {
      themeDisposed = true;
      window.removeEventListener("storage", applySharedTheme);
      window.removeEventListener("focus", applySharedTheme);
      unlistenTheme?.();
    };
  }, []);

  useEffect(() => () => {
    if (renderTimerRef.current !== null) window.clearTimeout(renderTimerRef.current);
    if (textDragFrameRef.current !== null) cancelAnimationFrame(textDragFrameRef.current);
    if (legendFrameRef.current !== null) cancelAnimationFrame(legendFrameRef.current);
    if (plotLabelFrameRef.current !== null) cancelAnimationFrame(plotLabelFrameRef.current);
    textDragFrameRef.current = null;
    legendFrameRef.current = null;
    plotLabelFrameRef.current = null;
  }, []);

  const analysis = state?.analysis;
  const allSources = state?.sources ?? [];
  const sources = combinedVisible ? allSources : allSources.filter((source) => !source.is_combined);
  const rawCurrentIndex = state?.current_index ?? 0;
  const currentIndex = sources.some((source) => source.index === rawCurrentIndex)
    ? rawCurrentIndex
    : sources[0]?.index ?? rawCurrentIndex;
  const currentSource = sources.find((source) => source.index === currentIndex);
  const currentSourcePosition = Math.max(0, sources.findIndex((source) => source.index === currentIndex));
  const hasCombined = currentSource?.is_combined === true;
  const currentFileKey = currentSource ? String(currentSource.path ?? `${currentSource.index}:${currentSource.name}`) : "";
  const currentVowels = state?.current_vowels ?? [];
  const {
    layerState,
    layerOverrides,
    layerOrder,
    selectedLayer,
    selectedLayers,
    expandedLayers,
    setExpandedLayers,
    lockedLayers,
    draggingLayer,
    dropTarget,
    layerListHeight,
    selectedLocked,
    effective,
    layerRowRefs,
    layerListRef,
    draggingLayerRef,
    selectLayer,
    updateLayerDesign,
    toggleLayerEye,
    toggleLayerSemi,
    toggleAllLayerEyes,
    toggleAllLayerSemi,
    toggleLock,
    resetSelectedLayer,
    removeLayerEffect,
    beginLayerDrag,
    moveLayerDrag,
    commitLayerDrag,
    cancelLayerDrag,
    resetLayerOrder,
    moveLayerByStep,
    beginLayerPanelResize,
    resizeLayerPanels,
    endLayerPanelResize,
    cancelLayerPanelResize,
    cacheCurrentLayerSession,
    hydrateLayersForFile,
    applyLayersAfterNavigate,
    resetLayers,
  } = useLayerSession({
    currentVowels,
    aliveRef,
    setMessage,
    design,
    renderInteractive: (overrides) => renderInteractiveRef.current(overrides),
    scheduleInteractiveRender: (overrides) => scheduleInteractiveRenderRef.current(overrides),
  });
  const plotType = analysis?.type ?? "f1_f2";
  const plotUnits = useMemo(() => resolvePlotUnits(analysis), [analysis]);
  const {
    drawTool,
    setDrawTool,
    drawColor,
    drawWidth,
    drawLineStyle,
    drawArrowMode,
    drawArrowHead,
    drawRefColor,
    drawRefStyle,
    drawPolyBorderColor,
    drawPolyFillColor,
    drawPolyFillOpacity,
    drawingPoints,
    setDrawingPoints,
    drawHover,
    setDrawHover,
    draggingDrawObject,
    drawDropTarget,
    selectedDrawObjectIds,
    referenceMode,
    setReferenceMode,
    drawEditorOpen,
    drawEditorMode,
    drawEditorKind,
    lineDraft,
    setLineDraft,
    polygonDraft,
    setPolygonDraft,
    referenceDraft,
    setReferenceDraft,
    legendDraft,
    setLegendDraft,
    textDraft,
    setTextDraft,
    textInput,
    setTextInput,
    drawIdRef,
    currentDrawObjects,
    currentDrawLines,
    currentLegend,
    drawObjectsTopFirst,
    persistDrawObjects,
    selectDrawObject,
    focusDrawObject,
    deleteDrawObjects,
    toggleDrawObjectVisibility,
    toggleDrawObjectSemi,
    toggleAllDrawVisibility,
    toggleAllDrawSemi,
    beginDrawObjectDrag,
    moveDrawObjectDrag,
    commitDrawObjectDrag,
    cancelDrawObjectDrag,
    closeDrawEditor,
    openDrawDefaultsEditor,
    openDrawLayerEditor,
    saveDrawEditor,
    finishDrawLine,
    finishDrawPolygon,
    confirmTextInput,
    enterDrawMode,
    activateDrawTool,
    hydrateDrawObjectsForFile,
    applyLegendBounds,
    beginTextInput,
    resetTransientDraw,
  } = useDrawSession({
    currentIndex,
    currentSourceName: currentSource?.name,
    normalization: analysis?.normalization ?? null,
    setMessage,
    setTool,
    setRightPanel,
    setRightOpen,
    renderInteractive: (overrides) => renderInteractiveRef.current(overrides),
    onResetCanvasDrawPreview: () => {
      referencePointerRef.current = null;
      setReferencePreview(null);
    },
  });
  applyLegendBoundsRef.current = applyLegendBounds;
  const normalization = plotUnits.normalization;
  const xAxis = plotUnits.xAxisName;
  const yAxis = plotUnits.yAxisName;
  const rangeUnitLabel = plotUnits.rangeBadge;
  const rangesReadOnly = normalization === "Gerstman";
  const defaultRanges = useMemo(() => {
    if (normalization) {
      return NORM_RANGE_DEFAULTS[normalization] ?? NORM_RANGE_DEFAULTS.Lobanov;
    }
    return smartAxisRanges(plotType, analysis, RANGE_DEFAULTS, BARK_RANGE_DEFAULTS);
  }, [analysis, normalization, plotType]);
  const canonicalDesign = useMemo(
    () => ({ ...(state?.design_defaults ?? {}) }) as DesignSettings,
    [state?.design_defaults],
  );
  const canNavigate = sources.length > 1;
  const sourcesFingerprint = sources
    .map((source) => `${source.index}:${source.path ?? source.name}`)
    .join("|");

  useEffect(() => {
    clearVowelAnalysisCache();
  }, [sourcesFingerprint]);

  useEffect(() => {
    if (vowelAnalysisOpen || !sources.length) return;
    const cacheKey = vowelAnalysisCacheKey(currentIndex, normalization, plotType);
    if (hasVowelAnalysisSection(getCachedVowelAnalysis(cacheKey), "core")) return;
    let cancelled = false;
    const runPrefetch = () => {
      if (cancelled) return;
      void fetchVowelAnalysisSections(currentIndex, ["core"], cacheKey).catch(() => {
        // Prefetch is best-effort; the analysis shell will retry on open.
      });
    };
    let idleHandle: number;
    if (typeof window.requestIdleCallback === "function") {
      idleHandle = window.requestIdleCallback(runPrefetch, { timeout: 1500 });
    } else {
      idleHandle = window.setTimeout(runPrefetch, 400);
    }
    return () => {
      cancelled = true;
      if (typeof window.cancelIdleCallback === "function") {
        window.cancelIdleCallback(idleHandle);
      } else {
        window.clearTimeout(idleHandle);
      }
    };
  }, [currentIndex, normalization, plotType, sources.length, vowelAnalysisOpen]);

  useEffect(() => {
    const syncCombinedVisibility = () => setCombinedVisible(window.localStorage.getItem("gichanformant-show-combined") === "true");
    window.addEventListener("storage", syncCombinedVisibility);
    return () => window.removeEventListener("storage", syncCombinedVisibility);
  }, []);

  useEffect(() => {
    if (!combinedVisible && rawCurrentIndex !== currentIndex && sources.length) {
      void navigateTo(currentIndex);
    }
  }, [combinedVisible, currentIndex, rawCurrentIndex, sources.length]);

  useEffect(() => {
    currentIndexRef.current = currentIndex;
  }, [currentIndex]);

  useEffect(() => {
    const session = state?.plot_session;
    const sessionKey = String(currentIndex);
    const sessionDrawObjects = session?.draw_objects_by_file?.[sessionKey] as DrawObject[] | undefined;
    hydrateLayersForFile({
      fileKey: currentFileKey,
      vowels: currentVowels,
      sessionKey,
      plotSession: session,
    });
    const sessionRanges = session?.ranges as Ranges | undefined;
    const useBark = analysis?.use_bark_units ?? false;
    const canReuseSessionRanges = sessionRanges
      && Object.keys(sessionRanges).length === 4
      && rangesLookCompatible(sessionRanges, normalization, useBark);
    setRanges(canReuseSessionRanges ? sessionRanges : defaultRanges);
    setSigma(session?.sigma ?? "2");
    setShowEllipse(session?.show_ellipse ?? true);
    const sessionDesign = ({ ...canonicalDesign, ...(session?.design_settings ?? {}) }) as DesignSettings;
    if (currentFileKey && !designInitializedRef.current) {
      cacheMapSet(globalDesignByFileRef.current, currentFileKey, sessionDesign, MAX_CACHED_FILE_DESIGNS);
      setDesign(sessionDesign);
      designInitializedRef.current = true;
    }
    hydrateDrawObjectsForFile({ index: currentIndex, sessionDrawObjects });
    // Hydrate from durable session when the *file* changes — not on every
    // plot_session revision (those arrive while local controls are mid-edit).
  }, [analysis?.use_bark_units, canonicalDesign, currentFileKey, currentIndex, currentVowels.join("\u0000"), defaultRanges, hydrateDrawObjectsForFile, hydrateLayersForFile, normalization]);

  const unitModeKey = [
    normalization ?? "",
    analysis?.use_bark_units ? "bark" : "hz",
    analysis?.f1_scale ?? "",
    analysis?.f2_scale ?? "",
    analysis?.origin ?? "",
    analysis?.outlier_mode ?? "",
    analysis?.outlier_scope ?? "",
    plotType,
  ].join("|");
  const unitModeKeyRef = useRef(unitModeKey);
  const previousNormRef = useRef<string | null>(normalization);
  useEffect(() => {
    if (!state?.capabilities.can_plot) return;
    if (unitModeKeyRef.current === unitModeKey) return;
    unitModeKeyRef.current = unitModeKey;
    const enteredNorm = Boolean(normalization) && !previousNormRef.current;
    previousNormRef.current = normalization;
    // PySide design_panel is_normalized defaults when entering speaker norm.
    const nextDesign = enteredNorm
      ? {
          ...design,
          box_spines: true,
          show_grid: true,
          y_label_rotation: true,
          axis_position_swap: true,
        }
      : design;
    if (enteredNorm) setDesign(nextDesign);
    setRanges(defaultRanges);
    setPreviewLoading(true);
    void callSidecar("render_interactive_preview", {
      options: {
        ranges: defaultRanges,
        sigma,
        show_ellipse: showEllipse,
        design: nextDesign,
        filter_state: layerState,
        layer_overrides: layerOverrides,
        layer_order: layerOrder,
        locked_layers: [...lockedLayers],
        draw_objects: currentDrawObjects,
        request_id: ++renderRequestRef.current,
      },
    }).catch((err) => {
      if (aliveRef.current) setMessage(`설정 전환 반영에 실패했습니다: ${String(err)}`);
    });
  }, [currentDrawObjects, defaultRanges, design, layerOrder, layerOverrides, layerState, lockedLayers, normalization, showEllipse, sigma, state?.capabilities.can_plot, unitModeKey]);

  const renderInteractive = async (overrides: InteractiveRenderOverrides = {}) => {
    if (!state?.capabilities.can_plot) return;
    if (renderTimerRef.current !== null) {
      window.clearTimeout(renderTimerRef.current);
      renderTimerRef.current = null;
    }
    const requestId = ++renderRequestRef.current;
    try {
      await callSidecar("render_interactive_preview", {
        options: {
          ranges: overrides.ranges ?? ranges,
          sigma: overrides.sigma ?? sigma,
          show_ellipse: overrides.showEllipse ?? showEllipse,
          design: overrides.design ?? design,
          filter_state: overrides.layers ?? layerState,
          layer_overrides: overrides.layerOverrides ?? layerOverrides,
          layer_order: overrides.layerOrder ?? layerOrder,
          locked_layers: [...lockedLayers],
          draw_objects: overrides.drawObjects ?? currentDrawObjects,
          ...(overrides.labelOffsets ? { label_offsets: overrides.labelOffsets } : {}),
          request_id: requestId,
        },
      });
    } catch (err) {
      setMessage(`설정을 적용하지 못했습니다: ${String(err)}`);
    }
  };
  renderInteractiveRef.current = renderInteractive;

  const scheduleInteractiveRender = (overrides: InteractiveRenderOverrides = {}) => {
    if (renderTimerRef.current !== null) window.clearTimeout(renderTimerRef.current);
    renderTimerRef.current = window.setTimeout(() => {
      renderTimerRef.current = null;
      if (!aliveRef.current) return;
      void renderInteractive(overrides);
    }, 70);
  };
  scheduleInteractiveRenderRef.current = scheduleInteractiveRender;

  const navigateTo = useCallback(async (sourceIndex: number) => {
    if (!sources.length || navigatingRef.current) return;
    const nextSource = sources.find((source) => source.index === sourceIndex);
    if (!nextSource) return;
    const target = nextSource.index;
    if (target === currentIndexRef.current) return;
    navigatingRef.current = true;
    ++renderRequestRef.current;
    if (renderTimerRef.current !== null) {
      window.clearTimeout(renderTimerRef.current);
      renderTimerRef.current = null;
    }
    setNavigating(true);
    setPreviewLoading(true);
    setRulerStart(null);
    setRulerHover(null);
    setRulerPointer(null);
    resetTransientDraw();
    try {
       if (currentFileKey) {
         cacheMapSet(globalDesignByFileRef.current, currentFileKey, design, MAX_CACHED_FILE_DESIGNS);
         cacheCurrentLayerSession(currentFileKey);
      }
       const nextFileKey = nextSource ? String(nextSource.path ?? `${nextSource.index}:${nextSource.name}`) : "";
       const nextDesignForFile = globalDesignLocked
         ? design
         : globalDesignByFileRef.current.get(nextFileKey) ?? canonicalDesign;
       const requestId = ++renderRequestRef.current;
      const navRanges = rangesLookCompatible(ranges, normalization, analysis?.use_bark_units ?? false)
        ? ranges
        : defaultRanges;
      const response = await callSidecar<{ state: ApplicationState }>("navigate_interactive_preview", {
        index: target,
        options: {
          ranges: navRanges,
          sigma,
          show_ellipse: showEllipse,
           design: nextDesignForFile,
          request_id: requestId,
        },
      });
      const next = response.state;
      if (!aliveRef.current) return;
      currentIndexRef.current = target;
      const nextVowels = next.current_vowels ?? [];
       const nextStateSource = next.sources.find((source) => source.index === target);
       const resolvedNextFileKey = nextStateSource ? String(nextStateSource.path ?? `${nextStateSource.index}:${nextStateSource.name}`) : nextFileKey;
      const sessionKey = String(target);
      const nextSession = next.plot_session;
      applyLayersAfterNavigate({
        fileKey: nextFileKey,
        vowels: nextVowels,
        sessionKey,
        plotSession: nextSession,
      });
      // Ranges and global design are intentionally shared across files in PlotSessionState.
      const sessionNextRanges = nextSession.ranges as Ranges | undefined;
      const nextRanges = sessionNextRanges
        && Object.keys(sessionNextRanges).length === 4
        && rangesLookCompatible(sessionNextRanges, next.analysis?.normalization ?? null, next.analysis?.use_bark_units ?? false)
        ? sessionNextRanges
        : defaultRanges;
       const nextDesign = globalDesignLocked
         ? design
         : globalDesignByFileRef.current.get(resolvedNextFileKey) ?? ({ ...canonicalDesign, ...(nextSession.design_settings ?? {}) } as DesignSettings);
      const nextSigma = nextSession.sigma ?? "2";
      const nextShowEllipse = nextSession.show_ellipse ?? true;
      setRanges(nextRanges);
       setDesign(nextDesign);
       cacheMapSet(globalDesignByFileRef.current, resolvedNextFileKey, nextDesign, MAX_CACHED_FILE_DESIGNS);
      setSigma(nextSigma);
      setShowEllipse(nextShowEllipse);
      setState(next);
      setMessage(`${nextStateSource?.name ?? nextSource.name ?? "파일"}을 불러오는 중입니다.`);
    } catch (err) {
      setMessage(`파일을 이동하지 못했습니다: ${String(err)}`);
      setPreviewLoading(false);
    } finally {
      navigatingRef.current = false;
      if (aliveRef.current) setNavigating(false);
    }
  }, [analysis?.use_bark_units, applyLayersAfterNavigate, cacheCurrentLayerSession, canonicalDesign, currentFileKey, defaultRanges, design, globalDesignLocked, normalization, ranges, resetTransientDraw, showEllipse, sigma, sources]);

  const navigateByPosition = useCallback((position: number) => {
    const target = sources[Math.max(0, Math.min(position, sources.length - 1))];
    if (target) void navigateTo(target.index);
  }, [navigateTo, sources]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (shortcutHelpOpen) {
        if (event.key === "?" || (event.shiftKey && event.key === "/")) {
          event.preventDefault();
          setShortcutHelpOpen(false);
        }
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        const target = event.target as HTMLElement | null;
        if (!target?.closest("input, textarea, select, [contenteditable='true']")) {
          event.preventDefault();
          void saveProject();
        }
        return;
        }
      if (tool === "draw" && (drawTool === "line" || drawTool === "area") && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        setDrawingPoints((previous) => previous.slice(0, -1));
        setMessage(drawTool === "area" ? "현재 영역의 마지막 점을 되돌렸습니다." : "현재 선의 마지막 점을 되돌렸습니다.");
        return;
      }
      if (tool === "draw" && (drawTool === "line" || drawTool === "area") && event.key === "Escape") {
        event.preventDefault();
        if (drawingPoints.length > 0) {
          setDrawingPoints([]);
          setDrawHover(null);
          setMessage(drawTool === "area" ? "영역 그리기를 취소했습니다." : "선 그리기를 취소했습니다.");
        } else {
          setDrawTool(null);
          setDrawHover(null);
          setReferencePreview(null);
          setTool("select");
          setMessage("그리기 모드를 종료했습니다.");
        }
        return;
      }
      if (tool === "draw" && (event.key === "Enter" || event.key === "Return")) {
        if (drawEditorOpen) return;
        const keyTarget = event.target as HTMLElement | null;
        if (keyTarget?.closest("textarea, select, [contenteditable='true']")) return;
        event.preventDefault();
        if (drawTool === "area") finishDrawPolygon(drawingPoints);
        else if (drawTool === "line") finishDrawLine(drawingPoints);
        return;
      }
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, [contenteditable='true']")) return;
      if (event.key.toLowerCase() === "a") {
        event.preventDefault();
        setLeftPanel("analysis");
        return;
      }
      if (event.key.toLowerCase() === "d") {
        event.preventDefault();
        setLeftPanel("global-design");
        return;
      }
      if (event.key.toLowerCase() === "m") {
        if (sources.filter((source) => !source.is_combined).length < 2) return;
        event.preventDefault();
        void callSidecar("open_compare", { source_groups: sources.filter((source) => !source.is_combined).map((source) => [source.index]), normalization: analysis?.normalization ?? null });
        return;
      }
      if (event.key === "?" || (event.shiftKey && event.key === "/")) {
        const helpTarget = event.target as HTMLElement | null;
        if (helpTarget?.closest("input, textarea, select, [contenteditable='true']")) return;
        event.preventDefault();
        setShortcutHelpOpen((previous) => !previous);
        return;
      }
      if (event.key === "`" || event.code === "Backquote") {
        event.preventDefault();
        setLeftOpen((previous) => !previous);
        setRightOpen((previous) => !previous);
        return;
      }
      if (event.key.toLowerCase() === "r") {
        event.preventDefault();
        setTool((previous) => previous === "ruler" ? "select" : "ruler");
        return;
      }
      if (event.key.toLowerCase() === "t") {
        event.preventDefault();
        setTool((previous) => previous === "label" ? "select" : "label");
        setMessage("라벨 이동 모드 · 라벨을 드래그하세요.");
        return;
      }
      if (event.key.toLowerCase() === "p") {
        event.preventDefault();
        setTool((previous) => {
          if (previous === "draw") {
            setDrawTool(null);
            setReferencePreview(null);
            return "select";
          }
          setDrawTool(null);
          setRightPanel("drawing");
          setRightOpen(true);
          setMessage("그리기 도구를 선택하세요.");
          return "draw";
        });
        return;
      }
      if (event.key === "Escape" && tool === "ruler") {
        event.preventDefault();
        setRulerStart(null);
        setRulerHover(null);
        setRulerPointer(null);
        setRulerSettingsOpen(false);
        return;
      }
      if (event.key === "Escape" && rulerSettingsOpen) {
        event.preventDefault();
        setRulerSettingsOpen(false);
        return;
      }
      if (event.key === "Escape" && tool === "draw") {
        event.preventDefault();
        setDrawTool(null);
        setReferencePreview(null);
        setTool("select");
        return;
      }
      if (tool === "draw" && ["1", "2", "3", "4", "5"].includes(event.key)) {
        event.preventDefault();
        const next = (event.key === "1" ? "line" : event.key === "2" ? "area" : event.key === "3" ? "text" : event.key === "4" ? "reference" : "legend") as DrawTool;
        void activateDrawTool(next);
        return;
      }
      if (event.key === "Home" || event.key === "End") {
        event.preventDefault();
        navigateByPosition(event.key === "Home" ? 0 : sources.length - 1);
        return;
      }
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      if (!canNavigate || navigatingRef.current) return;
      event.preventDefault();
      navigateByPosition(currentSourcePosition + (event.key === "ArrowLeft" ? -1 : 1));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [analysis?.normalization, canNavigate, currentSourcePosition, drawArrowHead, drawArrowMode, drawColor, drawEditorOpen, drawLineStyle, drawTool, drawWidth, drawingPoints, navigateByPosition, navigating, rulerSettingsOpen, shortcutHelpOpen, sources, tool]);

  const updateDesign = (patch: Partial<DesignSettings>) => {
    const next = { ...design, ...patch };
    setDesign(next);
    if (currentFileKey) cacheMapSet(globalDesignByFileRef.current, currentFileKey, next, MAX_CACHED_FILE_DESIGNS);
    scheduleInteractiveRender({ design: next });
  };

  const resetPlot = () => {
    const nextRanges = defaultRanges;
    const nextLayers = resetLayers(currentVowels);
    setRanges(nextRanges);
    setSigma("2.0");
    setShowEllipse(true);
    setDesign(canonicalDesign);
    setGlobalDesignLocked(false);
    void renderInteractive({ design: canonicalDesign, layers: nextLayers, ranges: nextRanges, sigma: "2", showEllipse: true, layerOverrides: {}, layerOrder: sortVowels(currentVowels) });
  };

  const openLegacyPlot = async () => {
    setBusy(true);
    try { await callSidecar("open_single_plot"); } finally { setBusy(false); }
  };

  const openComparePlot = async () => {
    const real = sources.filter((source) => !source.is_combined);
    if (real.length < 2) {
      setMessage("다중 플롯은 파일이 2개 이상일 때 사용할 수 있습니다.");
      return;
    }
    setBusy(true);
    try {
      await callSidecar("open_compare", {
        source_groups: real.map((source) => [source.index]),
        normalization: analysis?.normalization ?? null,
      });
      setMessage("다중 플롯 창을 요청했습니다.");
    } catch (err) {
      setMessage(`다중 플롯을 열지 못했습니다: ${String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const saveProject = async () => {
    const path = await save({ title: "GichanFormant 프로젝트 저장", defaultPath: "analysis.gfproj", filters: [{ name: "GichanFormant 프로젝트", extensions: ["gfproj"] }] });
    if (!path) return;
    setBusy(true);
    try {
      await callSidecar("update_interactive_session", { options: {
        ranges,
        sigma,
        show_ellipse: showEllipse,
        design,
        filter_state: layerState,
        layer_overrides: layerOverrides,
        layer_order: layerOrder,
        locked_layers: [...lockedLayers],
        draw_objects: currentDrawObjects,
      } });
      await callSidecar("save_project", { path });
      setMessage("프로젝트를 저장했습니다.");
    } catch (err) {
      setMessage(`프로젝트를 저장하지 못했습니다: ${String(err)}`);
    } finally { setBusy(false); }
  };

  const exportInteractive = async (format: "png" | "jpg" | "svg") => {
    if (!sources.length) return;
    const path = await save({
      title: `${format.toUpperCase()} 내보내기`,
      defaultPath: `${(currentSource?.name ?? "plot").replace(/\.[^.]+$/, "")}.${format}`,
      filters: [{ name: format.toUpperCase(), extensions: [format] }],
    });
    if (!path) return;
    setBusy(true);
    try {
      await callSidecar("export_interactive_preview", {
        path,
        format,
        options: { ranges, sigma, show_ellipse: showEllipse, design, filter_state: layerState, layer_overrides: layerOverrides, layer_order: layerOrder, locked_layers: [...lockedLayers], draw_objects: currentDrawObjects },
      });
      setMessage(`${format.toUpperCase()} 파일을 저장했습니다.`);
    } catch (err) {
      setMessage(`내보내기 실패: ${String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const exportCombinedTxt = async () => {
    if (!hasCombined) return;
    const path = await save({
      title: "결합 데이터 TXT 저장",
      defaultPath: "Combined.txt",
      filters: [{ name: "GichanFormant TXT", extensions: ["txt"] }],
    });
    if (!path) return;
    setBusy(true);
    try {
      await callSidecar("export_combined_txt", { path });
      setMessage("결합 데이터를 TXT로 저장했습니다.");
    } catch (err) {
      setMessage(`TXT 저장 실패: ${String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const chooseBatchDirectory = async () => {
    const selected = await open({ directory: true, multiple: false, title: "일괄 저장 폴더 선택" });
    if (typeof selected === "string") setBatchExportDirectory(selected);
  };

  const runBatchExport = async () => {
    if (!batchExportDirectory || !sources.length) return;
    setBatchExportBusy(true);
    try {
      const result = await callSidecar<{ exported?: string[]; errors?: Array<{ name: string; message: string }> }>("export_interactive_batch", {
        directory: batchExportDirectory,
        format: batchExportFormat,
        options: { ranges, sigma, show_ellipse: showEllipse, design, filter_state: layerState, layer_overrides: layerOverrides, layer_order: layerOrder, locked_layers: [...lockedLayers], draw_objects: currentDrawObjects, batch_options: { apply_global_design: batchApplyGlobalDesign, apply_layer_design: batchApplyLayerDesign, apply_layer_visibility: batchApplyVisibility, apply_label_positions: batchApplyLabelPositions } },
      });
      const count = result.exported?.length ?? 0;
      setMessage(`${count}개 파일을 일괄 저장했습니다${result.errors?.length ? ` · 실패 ${result.errors.length}개` : ""}.`);
      setBatchExportOpen(false);
    } catch (err) {
      setMessage(`일괄 저장 실패: ${String(err)}`);
    } finally {
      setBatchExportBusy(false);
    }
  };

  const rulerImageGeometry = () => {
    const image = plotImageRef.current;
    if (!image) return null;
    // PNG 픽셀 공간과 ruler_context(axes_bbox)를 반드시 같은 기준으로 맞춤
    const srcW = rulerContext?.image_width || image.naturalWidth;
    const srcH = rulerContext?.image_height || image.naturalHeight;
    return plotGeometry.computeImageGeometry(image.getBoundingClientRect(), srcW, srcH);
  };

  const legendClientRect = (legend: DrawLegendObject, useMeasured = true) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.legendClientRect(geometry, rulerContext, legend, useMeasured);
  };

  const defaultLegendClientRect = (legend: DrawLegendObject) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.defaultLegendClientRect(geometry, rulerContext, legend);
  };

  const legendFromPointer = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext || !legendDragRef.current) return null;
    const legend = currentLegend;
    if (!legend) return null;
    return plotGeometry.legendFromPointer(geometry, rulerContext, legend, legendDragRef.current, clientX, clientY);
  };

  const rulerPointClient = (point: RulerPoint) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.rulerPointClient(geometry, rulerContext, point);
  };

  const plotLabelClient = (label: PlotLabel) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.plotLabelClient(geometry, rulerContext, label);
  };

  const plotLabelBoxClient = (label: PlotLabel) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !label.bbox) return null;
    return plotGeometry.plotLabelBoxClient(geometry, label);
  };

  const plotDataFromClient = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.plotDataFromClient(geometry, rulerContext, clientX, clientY);
  };

  /** PySide event.inaxes — 축 안 더블클릭만 텍스트 배치 */
  const plotDataInAxesFromClient = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.plotDataInAxesFromClient(geometry, rulerContext, clientX, clientY);
  };

  /** 라벨 plotLabelClient / plotLabelBoxClient 와 동일 좌표계 */
  const drawTextAnchorClient = (object: DrawTextObject) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.drawTextAnchorClient(geometry, rulerContext, object);
  };

  const drawTextBoxClient = (object: DrawTextObject) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.drawTextBoxClient(geometry, rulerContext, object);
  };

  const hitDrawTextAt = (clientX: number, clientY: number): DrawTextObject | null => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.hitDrawTextAt(geometry, rulerContext, currentDrawObjects, clientX, clientY);
  };

  const openTextInputAt = (clientX: number, clientY: number) => {
    if (hitDrawTextAt(clientX, clientY)) return;
    const data = plotDataInAxesFromClient(clientX, clientY);
    if (!data) {
      setMessage("축 영역 안에서 더블클릭하세요.");
      return;
    }
    beginTextInput({
      x: data.x,
      y: data.y,
      axis_units: plotUnits.drawAxisUnits,
    });
  };

  const nearestPlotLabel = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.nearestPlotLabel(geometry, rulerContext, clientX, clientY);
  };

  const nearestRulerPoint = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.nearestRulerPoint(geometry, rulerContext, clientX, clientY);
  };

  /** 호버용: 스냅 우선(transData px/py 포함), 없으면 커서 data(가이드만). 클릭은 스냅만. */
  const drawHoverAtClient = (clientX: number, clientY: number): DrawHoverState | null => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.drawHoverAtClient(geometry, rulerContext, clientX, clientY);
  };

  const rulerLocalPoint = (clientX: number, clientY: number) => {
    const box = plotPaperRef.current?.getBoundingClientRect();
    return box ? plotGeometry.clientToLocal(clientX, clientY, box) : null;
  };

  /** 축 bbox를 paper-local 픽셀로 — 프리뷰 선 끝점은 항상 여기서 잡음 (PySide ax.get_xlim/ylim 대응) */
  const axesRectLocal = () => {
    const geometry = rulerImageGeometry();
    const paper = plotPaperRef.current?.getBoundingClientRect();
    if (!geometry || !paper || !rulerContext) return null;
    return plotGeometry.axesRectLocal(geometry, paper, rulerContext);
  };

  const referenceAxesSpan = (paperWidth: number, paperHeight: number) => {
    const axes = axesRectLocal();
    return plotGeometry.referenceAxesSpan(axes, paperWidth, paperHeight);
  };

  /**
   * plotValue(축 data) → paper-local 선. axesRectLocal 비율만 사용.
   * ylim/xlim에 가까우면 축 박스 안으로 clamp → 항상 보임 + 눈금과 같은 비율.
   * 단위가 완전히 어긋난 값(축 밖 멀리)은 null → 커서 fallback(라벨 없음).
   * Matplotlib: ylim[0]=축 하단 data, ylim[1]=축 상단 data.
   */
  const referenceLineFromPlotValue = (plotValue: number, horizontal: boolean, paperWidth: number, paperHeight: number) => {
    const axes = axesRectLocal();
    const span = referenceAxesSpan(paperWidth, paperHeight);
    if (!rulerContext || !axes) return null;
    return plotGeometry.referenceLineFromPlotValue(rulerContext, axes, span, plotValue, horizontal);
  };

  const resolveReferencePlacement = (clientX: number, clientY: number): { object: DrawReferenceObject; preview: ReferencePreview } | null => {
    const data = plotDataFromClient(clientX, clientY);
    if (!data || !rulerContext) return null;
    const normalization = analysis?.normalization ?? rulerContext.params.normalization ?? null;
    const horizontal = referenceMode === "horizontal";
    const scale = normalization
      ? "linear"
      : horizontal
        ? (analysis?.f1_scale ?? rulerContext.params.f1_scale ?? "linear")
        : (analysis?.f2_scale ?? rulerContext.params.f2_scale ?? "linear");
    const unit = plotUnits.drawAxisUnits;
    const axisName = horizontal ? plotUnits.yAxisName : plotUnits.xAxisName;
    const plotCoord = horizontal ? data.y : data.x;
    const means = (rulerContext.points || []).filter((point) => point.type === "mean");
    const extra = means.map((point) => {
      const coord = horizontal ? point.y : point.x;
      if (scale === "bark" && unit.toLowerCase() === "hz") return barkToHz(coord);
      return coord;
    });
    const { value, snapped } = roundRefValue(plotCoord, scale, unit, extra, normalization);
    let plotValue = value;
    if (scale === "bark" && unit.toLowerCase() === "hz") plotValue = hzToBark(value);
    const paper = plotPaperRef.current?.getBoundingClientRect();
    if (!paper) return null;
    // 선·라벨 동일 plotValue. 축 비율 투영 → 보이기 + 눈금 정렬 동시.
    const line = referenceLineFromPlotValue(plotValue, horizontal, paper.width, paper.height);
    if (!line) return null;
    return {
      object: {
        type: "reference",
        id: `react-ref-${currentIndex}-${Date.now()}-${drawIdRef.current++}`,
        mode: referenceMode,
        value,
        axis_units: unit,
        axis_name: axisName,
        axis_scale: scale,
        line_style: drawRefStyle,
        line_color: drawRefColor,
        visible: true,
        semi: false,
      },
      preview: {
        mode: referenceMode,
        plotValue,
        label: formatRefLabel(value, unit, snapped, normalization),
        snapped,
        ...line,
      },
    };
  };

  const pushReferencePreview = (preview: ReferencePreview | null) => {
    referencePointerRef.current = preview;
    setReferencePreview(preview);
  };

  /**
   * 둘 다 만족:
   * 1) paper 위면 선은 항상 보임
   * 2) 스냅 라벨이 있으면 선은 그 plotValue 축 위치(커서와 라벨 혼합 금지)
   */
  referenceMoveRef.current = (clientX: number, clientY: number) => {
    if (tool !== "draw" || drawTool !== "reference") return;
    const paper = plotPaperRef.current?.getBoundingClientRect();
    const local = rulerLocalPoint(clientX, clientY);
    if (!paper || !local) {
      pushReferencePreview(null);
      return;
    }
    if (local.x < 0 || local.y < 0 || local.x > paper.width || local.y > paper.height) {
      pushReferencePreview(null);
      return;
    }
    const horizontal = referenceMode === "horizontal";
    const span = referenceAxesSpan(paper.width, paper.height);
    const cursorLine = {
      x1: horizontal ? span.x1 : local.x,
      y1: horizontal ? local.y : span.y1,
      x2: horizontal ? span.x2 : local.x,
      y2: horizontal ? local.y : span.y2,
    };
    const placed = resolveReferencePlacement(clientX, clientY);
    if (placed) {
      pushReferencePreview(placed.preview);
      return;
    }
    // 투영 실패: 커서로 보이게 하되 스냅 라벨은 붙이지 않음
    pushReferencePreview({
      mode: referenceMode,
      plotValue: 0,
      label: "",
      snapped: false,
      ...cursorLine,
    });
  };

  useEffect(() => {
    if (tool !== "draw" || drawTool !== "reference") {
      referencePointerRef.current = null;
      setReferencePreview(null);
      return;
    }
    const onMove = (event: PointerEvent) => referenceMoveRef.current(event.clientX, event.clientY);
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [tool, drawTool]);

  /** PySide DrawLineTool / DrawPolygonTool._on_move: paper 안이면 스냅/커서 hover */
  const assignSnapDrawMove = (clientX: number, clientY: number) => {
    const paper = plotPaperRef.current?.getBoundingClientRect();
    const local = rulerLocalPoint(clientX, clientY);
    if (!paper || !local) {
      setDrawHover(null);
      return;
    }
    if (local.x < 0 || local.y < 0 || local.x > paper.width || local.y > paper.height) {
      setDrawHover(null);
      return;
    }
    setDrawHover(drawHoverAtClient(clientX, clientY));
  };

  lineMoveRef.current = (clientX: number, clientY: number) => {
    if (tool !== "draw" || drawTool !== "line") return;
    assignSnapDrawMove(clientX, clientY);
  };

  areaMoveRef.current = (clientX: number, clientY: number) => {
    if (tool !== "draw" || drawTool !== "area") return;
    assignSnapDrawMove(clientX, clientY);
  };

  useEffect(() => {
    if (tool !== "draw" || (drawTool !== "line" && drawTool !== "area")) {
      if (drawTool !== "line" && drawTool !== "area") setDrawHover(null);
      return;
    }
    const onMove = (event: PointerEvent) => {
      if (drawTool === "area") areaMoveRef.current(event.clientX, event.clientY);
      else lineMoveRef.current(event.clientX, event.clientY);
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [tool, drawTool]);

  const handleRulerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (tool === "draw") {
      if (textDragRef.current) {
        const local = rulerLocalPoint(event.clientX, event.clientY);
        if (local) {
          textHasMovedRef.current = true;
          if (textDragFrameRef.current === null) {
            textDragFrameRef.current = requestAnimationFrame(() => {
              textDragFrameRef.current = null;
              setTextDragPointer(local);
            });
          }
        }
        return;
      }
      setHoveredDrawTextId(hitDrawTextAt(event.clientX, event.clientY)?.id ?? null);
      if (drawTool === "reference") {
        referenceMoveRef.current(event.clientX, event.clientY);
        return;
      }
      if (drawTool === "line") {
        lineMoveRef.current(event.clientX, event.clientY);
        return;
      }
      if (drawTool === "area") {
        areaMoveRef.current(event.clientX, event.clientY);
        return;
      }
      if (drawTool === "legend" && draggingLegend) {
        const nextLegend = legendFromPointer(event.clientX, event.clientY);
        if (nextLegend) {
          legendPointerRef.current = {
            fx: nextLegend.fx,
            fy: nextLegend.fy,
            width_frac: nextLegend.width_frac,
            height_frac: nextLegend.height_frac,
          };
          if (legendFrameRef.current === null) {
            legendFrameRef.current = requestAnimationFrame(() => {
              legendFrameRef.current = null;
              const latest = legendPointerRef.current;
              if (latest) setLegendDragPreview(latest);
            });
          }
        }
        return;
      }
      if (drawTool === "legend" || drawTool === "text") return;
      setDrawHover(drawHoverAtClient(event.clientX, event.clientY));
      return;
    }
    if (tool === "label" && draggingPlotLabel) {
      const local = rulerLocalPoint(event.clientX, event.clientY);
      const start = plotLabelDragStartRef.current;
      if (start && Math.hypot(event.clientX - start.x, event.clientY - start.y) > 4) {
        plotLabelHasMovedRef.current = true;
      }
      if (!plotLabelHasMovedRef.current) return;
      if (local && plotLabelFrameRef.current === null) {
        plotLabelFrameRef.current = requestAnimationFrame(() => {
          plotLabelFrameRef.current = null;
          setPlotLabelPointer(local);
        });
      }
      return;
    }
    if (tool === "label") {
      setHoveredPlotLabel(nearestPlotLabel(event.clientX, event.clientY)?.vowel ?? null);
      return;
    }
    if (tool !== "ruler") return;
    const local = rulerLocalPoint(event.clientX, event.clientY);
    if (draggingRulerLabel !== null && local) {
      setRulerMeasurements((previous) => previous.map((measurement, index) => index === draggingRulerLabel ? { ...measurement, labelX: local.x, labelY: local.y } : measurement));
      return;
    }
    setRulerPointer(local);
    setRulerHover(nearestRulerPoint(event.clientX, event.clientY));
  };

  const handleRulerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (tool === "draw" && event.button === 0) {
      event.preventDefault();
      const hitText = hitDrawTextAt(event.clientX, event.clientY);
      if (hitText) {
        const data = plotDataFromClient(event.clientX, event.clientY);
        if (!data) return;
        focusDrawObject(hitText.id);
        textDragRef.current = {
          id: hitText.id,
          offsetX: hitText.x - data.x,
          offsetY: hitText.y - data.y,
        };
        textHasMovedRef.current = false;
        setDraggingTextId(hitText.id);
        setTextDragPointer(null);
        event.currentTarget.setPointerCapture(event.pointerId);
        return;
      }
      if (drawTool === "reference") {
        const placed = resolveReferencePlacement(event.clientX, event.clientY);
        if (!placed) {
          setMessage("플롯 영역 안에서 클릭해 기준선을 놓으세요.");
          return;
        }
        persistDrawObjects([...currentDrawObjects, placed.object]);
        focusDrawObject(placed.object.id);
        // 클릭 직후 백엔드 렌더 전까지도 프리뷰를 유지 (PySide는 canvas artist로 즉시 보임)
        pushReferencePreview(placed.preview);
        setMessage(`${placed.object.mode === "horizontal" ? "수평" : "수직"} 기준선 ${placed.preview.label.trim()} 을(를) 추가했습니다.`);
        return;
      }
      if (drawTool === "legend") {
        if (!currentLegend) return;
        const rect = legendClientRect(currentLegend);
        if (!rect || event.clientX < rect.left || event.clientX > rect.left + rect.width || event.clientY < rect.top || event.clientY > rect.top + rect.height) {
          setMessage("범례 박스를 드래그하면 위치를 옮길 수 있습니다.");
          return;
        }
        const measured = rulerContext?.legend_bounds?.[currentLegend.id];
        legendDragRef.current = { startX: event.clientX, startY: event.clientY, fx: measured?.fx ?? currentLegend.fx, fy: measured?.fy ?? currentLegend.fy };
        setLegendDragPreview({
          fx: measured?.fx ?? currentLegend.fx,
          fy: measured?.fy ?? currentLegend.fy,
          width_frac: measured?.width_frac ?? currentLegend.width_frac,
          height_frac: measured?.height_frac ?? currentLegend.height_frac,
        });
        setDraggingLegend(true);
        event.currentTarget.setPointerCapture(event.pointerId);
        return;
      }
      if (drawTool === "area") {
        const snapped = nearestRulerPoint(event.clientX, event.clientY);
        if (!snapped) {
          setMessage("데이터 점 가까이에서 클릭하면 영역의 점으로 스냅합니다.");
          return;
        }
        const point: DrawPoint = {
          x: snapped.x,
          y: snapped.y,
          label: snapped.label,
          px: snapped.px,
          py: snapped.py,
        };
        if (drawingPoints.length >= 3) {
          const firstLocal = drawPointLocal(drawingPoints[0]);
          const snapLocal = drawPointLocal(point);
          if (firstLocal && snapLocal && Math.hypot(firstLocal.x - snapLocal.x, firstLocal.y - snapLocal.y) < 20) {
            finishDrawPolygon(drawingPoints);
            return;
          }
        }
        setDrawingPoints([...drawingPoints, point]);
        setMessage(`${snapped.label || "점"}에 스냅했습니다. 다음 점을 선택하세요.`);
        return;
      }
      if (drawTool !== "line") return;
      const snapped = nearestRulerPoint(event.clientX, event.clientY);
      if (!snapped) {
        setMessage("데이터 점 가까이에서 클릭하면 선의 점으로 스냅합니다.");
        return;
      }
      const point: DrawPoint = {
        x: snapped.x,
        y: snapped.y,
        label: snapped.label,
        px: snapped.px,
        py: snapped.py,
      };
      const nextPoints = [...drawingPoints, point];
      setDrawingPoints(nextPoints);
      setMessage(`${snapped.label || "점"}에 스냅했습니다. 다음 점을 선택하세요.`);
      if (event.detail >= 2) finishDrawLine(nextPoints);
      return;
    }
    if (tool === "label" && event.button === 0) {
      event.preventDefault();
      event.stopPropagation();
      const label = nearestPlotLabel(event.clientX, event.clientY);
      if (label) {
        setDraggingPlotLabel(label.vowel);
        setPlotLabelPreviewVowel(label.vowel);
        setHoveredPlotLabel(label.vowel);
        plotLabelDragStartRef.current = { x: event.clientX, y: event.clientY };
        plotLabelHasMovedRef.current = false;
        setPlotLabelPointer(null);
        event.currentTarget.setPointerCapture(event.pointerId);
      }
      return;
    }
    if (tool !== "ruler" || event.button !== 0) return;
    const local = rulerLocalPoint(event.clientX, event.clientY);
    if (!local) return;
    const labelIndex = rulerMeasurements.findIndex((measurement) => Math.hypot(local.x - measurement.labelX, local.y - measurement.labelY) < 24);
    if (labelIndex >= 0) { setDraggingRulerLabel(labelIndex); event.currentTarget.setPointerCapture(event.pointerId); return; }
    const point = nearestRulerPoint(event.clientX, event.clientY);
    if (!point) return;
    if (!rulerStart) { setRulerStart(point); return; }
    if (rulerStart === point || (rulerStart.type === point.type && rulerStart.x === point.x && rulerStart.y === point.y)) return;
    const first = rulerStart;
    const measurement: RulerMeasurement = { p1: first, p2: point, labelX: local.x, labelY: local.y - 18, distance: rulerDistanceLabelWithSettings(first, point) };
    setRulerMeasurements((previous) => [...previous, measurement]);
    setRulerStart(null);
  };

  const resetPlotLabel = (event: React.MouseEvent<HTMLDivElement>) => {
    if (tool !== "label") return;
    event.preventDefault();
    const label = nearestPlotLabel(event.clientX, event.clientY);
    if (!label) return;
    void renderInteractive({ labelOffsets: { [label.vowel]: [0, 0] } });
    setDraggingPlotLabel(null);
    plotLabelDragStartRef.current = null;
    plotLabelHasMovedRef.current = false;
    setPlotLabelPreviewVowel(null);
    setPlotLabelPointer(null);
    setMessage(`${label.vowel} 라벨을 기본 위치로 되돌렸습니다.`);
  };

  const handleRulerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (tool === "draw") {
      if (textDragRef.current) {
        const drag = textDragRef.current;
        const data = plotDataFromClient(event.clientX, event.clientY);
        if (data && textHasMovedRef.current) {
          persistDrawObjects(currentDrawObjects.map((object) => (
            object.type === "text" && object.id === drag.id
              ? { ...object, x: data.x + drag.offsetX, y: data.y + drag.offsetY }
              : object
          )));
          setMessage("텍스트 위치를 옮겼습니다.");
        }
        textDragRef.current = null;
        textHasMovedRef.current = false;
        setDraggingTextId(null);
        setTextDragPointer(null);
        if (textDragFrameRef.current !== null) {
          cancelAnimationFrame(textDragFrameRef.current);
          textDragFrameRef.current = null;
        }
        if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
        return;
      }
      if (drawTool === "legend" && draggingLegend) {
        const nextLegend = legendFromPointer(event.clientX, event.clientY);
        if (nextLegend) {
          setLegendDragPreview({
            fx: nextLegend.fx,
            fy: nextLegend.fy,
            width_frac: nextLegend.width_frac,
            height_frac: nextLegend.height_frac,
          });
          persistDrawObjects([...currentDrawObjects.filter((object) => object.type !== "legend"), nextLegend]);
        } else {
          setLegendDragPreview(null);
        }
        legendDragRef.current = null;
        setDraggingLegend(false);
        if (legendFrameRef.current !== null) {
          cancelAnimationFrame(legendFrameRef.current);
          legendFrameRef.current = null;
        }
        if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
      }
      return;
    }
    if (tool === "label" && draggingPlotLabel && rulerContext) {
      const label = rulerContext.labels.find((item) => item.vowel === draggingPlotLabel);
      const data = plotDataFromClient(event.clientX, event.clientY);
      if (label && data && plotLabelHasMovedRef.current) {
        const offsets = { [label.vowel]: [data.x - label.cx, data.y - label.cy] as [number, number] };
        void renderInteractive({ labelOffsets: offsets });
        setMessage(`${label.vowel} 라벨 위치를 저장했습니다.`);
      }
      setDraggingPlotLabel(null);
      // Keep the optimistic preview in place until preview_ready replaces the image.
      setPlotLabelPreviewVowel(plotLabelHasMovedRef.current ? label?.vowel ?? null : null);
      plotLabelDragStartRef.current = null;
      plotLabelHasMovedRef.current = false;
    }
    if (plotLabelFrameRef.current !== null) {
      cancelAnimationFrame(plotLabelFrameRef.current);
      plotLabelFrameRef.current = null;
    }
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    setDraggingRulerLabel(null);
  };

  const handleRulerContextMenu = (event: React.MouseEvent<HTMLDivElement>) => {
    if (tool !== "ruler") return;
    event.preventDefault();
    const local = rulerLocalPoint(event.clientX, event.clientY);
    const hit = local ? rulerMeasurements.findIndex((measurement) => {
      const a = rulerPointClient(measurement.p1); const b = rulerPointClient(measurement.p2);
      if (!a || !b) return false;
      const abx = b.x - a.x; const aby = b.y - a.y;
      const t = Math.max(0, Math.min(1, ((event.clientX - a.x) * abx + (event.clientY - a.y) * aby) / Math.max(1, abx * abx + aby * aby)));
      return Math.hypot(local.x - measurement.labelX, local.y - measurement.labelY) < 24 || Math.hypot(event.clientX - (a.x + t * abx), event.clientY - (a.y + t * aby)) < 12;
    }) : -1;
    if (hit >= 0) setRulerMeasurements((previous) => previous.filter((_, index) => index !== hit));
  };

  const rulerTooltip = (point: RulerPoint) => formatRulerPointTooltip(point, plotUnits);

  const rulerDistanceLabelWithSettings = (first: RulerPoint, second: RulerPoint) =>
    formatRulerDistance(first, second, plotUnits, {
      preference: rulerDisplayMode,
      geometry: rulerGeometryMode,
    });

  const rulerTriangleLabels = (first: RulerPoint, second: RulerPoint) =>
    formatRulerTriangleLegs(first, second, plotUnits, rulerDisplayMode);

  useEffect(() => {
    if (!plotUnits.rulerUnitChoiceEnabled) return;
    setRulerDisplayMode(plotUnits.defaultRulerPreference);
  }, [plotUnits.defaultRulerPreference, plotUnits.rulerUnitChoiceEnabled]);

  useEffect(() => {
    if (tool !== "ruler") {
      setRulerStart(null);
      setRulerHover(null);
      setRulerPointer(null);
      setRulerMeasurements([]);
    }
    if (tool !== "label") {
      setDraggingPlotLabel(null);
      setHoveredPlotLabel(null);
      setPlotLabelPointer(null);
      plotLabelDragStartRef.current = null;
      plotLabelHasMovedRef.current = false;
    }
  }, [tool]);

  useEffect(() => {
    setRulerMeasurements((previous) => previous.map((measurement) => ({
      ...measurement,
      distance: rulerDistanceLabelWithSettings(measurement.p1, measurement.p2),
    })));
  }, [plotUnits, rulerDisplayMode, rulerGeometryMode]);

  /** paper-local. 스냅 점은 px/py(transData) 우선 — 선형 drawPointClient는 마커와 어긋남. */
  const drawPointLocal = (point: DrawPoint) => {
    const paper = plotPaperRef.current?.getBoundingClientRect();
    if (!paper) return null;
    const geometry = rulerImageGeometry();
    if (!geometry) return null;
    return plotGeometry.drawPointLocal(geometry, paper, rulerContext, point);
  };

  const fileCounter = useMemo(
    () => `${sources.length ? currentSourcePosition + 1 : 0} / ${sources.length}`,
    [currentSourcePosition, sources.length],
  );

  return (
    <main className={`interactive-plot-workspace ${leftOpen ? "" : "left-is-collapsed"} ${rightOpen ? "" : "right-is-collapsed"}`}>
      <header className="interactive-plot-header">
        <div className="plot-title-block"><span>단일 분석 · 대화형 플롯</span><h1 title={currentSource?.name}>{currentSource?.name ?? "데이터를 불러와 주세요"}</h1></div>
        <div className="plot-header-meta"><span className={`engine-state ${engineConnected ? "" : "is-offline"}`}><i /> 분석 엔진 {engineConnected ? "연결됨" : "연결 확인 중"}</span><span className="plot-notation">{xAxis} × {yAxis} · {fileCounter}</span><button type="button" className="shortcut-help-launch" onClick={() => setShortcutHelpOpen(true)} aria-label="단축키 도움말" title="단축키 (?)"><CircleHelp size={15} /></button><button className="legacy-launch" onClick={() => void openLegacyPlot()} disabled={busy || !sources.length}>PySide 고급 편집 <ArrowUpRight size={14} /></button></div>
      </header>

      <aside className="plot-control-rail">
        <section className="file-navigator">
          <div className="navigator-topline"><div><span className="section-eyebrow">파일 탐색</span><strong>{fileCounter}</strong></div><button className="rail-collapse" aria-label="왼쪽 패널 접기" onClick={() => setLeftOpen(false)}><PanelLeftClose size={16} /></button></div>
          <div className="file-select-row"><button aria-label="이전 파일" onClick={() => navigateByPosition(currentSourcePosition - 1)} disabled={!canNavigate || currentSourcePosition === 0}><ChevronLeft size={17} /></button><FileSelectMenu sources={sources} currentIndex={currentIndex} onNavigate={(index) => void navigateTo(index)} disabled={!sources.length} /><button aria-label="다음 파일" onClick={() => navigateByPosition(currentSourcePosition + 1)} disabled={!canNavigate || currentSourcePosition >= sources.length - 1}><ChevronRight size={17} /></button></div>
        </section>

        <div className="control-tabs"><button className={leftPanel === "analysis" ? "is-active" : ""} onClick={() => setLeftPanel("analysis")}><SlidersHorizontal size={15} /> 분석 도구</button><button className={leftPanel === "global-design" ? "is-active" : ""} onClick={() => setLeftPanel("global-design")}><Palette size={15} /> 광역 디자인</button></div>

        <div className="control-scroll">
          {leftPanel === "analysis" ? (
            <AnalysisToolsPanel
              rangeUnitLabel={rangeUnitLabel}
              xAxis={xAxis}
              yAxis={yAxis}
              ranges={ranges}
              rangesReadOnly={rangesReadOnly}
              onRangesChange={setRanges}
              sigma={sigma}
              onSigmaChange={(next) => {
                setSigma(next);
                void renderInteractive({ sigma: next });
              }}
              showEllipse={showEllipse}
              onShowEllipseChange={(next) => {
                setShowEllipse(next);
                void renderInteractive({ showEllipse: next });
              }}
              onReset={resetPlot}
              onApplyRanges={() => void renderInteractive()}
              busy={busy}
              sourceCount={sources.length}
              canCompare={sources.filter((source) => !source.is_combined).length >= 2}
              tool={tool}
              onOpenVowelAnalysis={() => setVowelAnalysisOpen(true)}
              onOpenCompare={() => void openComparePlot()}
              onToggleRuler={() => setTool(tool === "ruler" ? "select" : "ruler")}
              onEnterDraw={() => enterDrawMode(null)}
              hasCombined={hasCombined}
              hasPreview={Boolean(previewUrl)}
              onExport={(format) => void exportInteractive(format)}
              onExportCombinedTxt={() => void exportCombinedTxt()}
              onSaveProject={() => void saveProject()}
              onOpenBatchExport={() => setBatchExportOpen(true)}
            />
          ) : (
            <GlobalDesignPanel
              design={design}
              onUpdateDesign={updateDesign}
              onReset={resetPlot}
              globalDesignLocked={globalDesignLocked}
              onToggleLock={() => setGlobalDesignLocked((locked) => !locked)}
            />
          )}
        </div>
      </aside>

      <section className={`interactive-plot-stage tool-${tool}${tool === "draw" ? ` draw-tool-${drawTool ?? "none"}` : ""}`}>
        <div className="plot-toolbar"><div className="toolbar-leading">{!leftOpen ? <button className="sidebar-reopen" onClick={() => setLeftOpen(true)}><PanelLeftOpen size={16} /> 도구</button> : null}<div className="toolbar-group"><button className={tool === "select" ? "is-active" : ""} onClick={() => setTool("select")}><MousePointer2 size={16} /> 선택</button><div className="ruler-tool-cluster"><button className={tool === "ruler" ? "is-active" : ""} onClick={() => setTool("ruler")}><Ruler size={16} /> 눈금자</button><button type="button" className={`tool-settings-button ${rulerSettingsOpen ? "is-active" : ""}`} onClick={() => setRulerSettingsOpen((previous) => !previous)} aria-label="눈금자 설정" title="눈금자 설정"><SlidersHorizontal size={14} /></button>{rulerSettingsOpen ? <div className="ruler-settings-popover"><div className="ruler-settings-header"><strong>눈금자 설정</strong><span>측정 방식</span></div><div className="ruler-mode-choices"><button type="button" className={`ruler-mode-choice ${rulerGeometryMode === "direct" ? "is-active" : ""}`} onClick={() => setRulerGeometryMode("direct")}><svg viewBox="0 0 44 22" aria-hidden><line x1="5" y1="17" x2="39" y2="5" /><circle cx="5" cy="17" r="2" /><circle cx="39" cy="5" r="2" /></svg><span>직선</span></button><button type="button" className={`ruler-mode-choice ${rulerGeometryMode === "right-triangle" ? "is-active" : ""}`} onClick={() => setRulerGeometryMode("right-triangle")}><svg viewBox="0 0 44 22" aria-hidden><path d="M5 17H39V5" /><line className="hypotenuse" x1="5" y1="17" x2="39" y2="5" /><path className="right-angle" d="M34 17v-5h5" /></svg><span>Δx · Δy</span></button></div><div className="ruler-unit-row"><span>표시 단위</span>{plotUnits.rulerUnitChoiceEnabled ? <div className="ruler-unit-toggles"><button type="button" className={`ruler-unit-toggle ${rulerDisplayMode === "hz" ? "is-on" : ""}`} aria-pressed={rulerDisplayMode === "hz"} onClick={() => setRulerDisplayMode("hz")}>Hz</button><button type="button" className={`ruler-unit-toggle ${rulerDisplayMode === "bark" ? "is-on" : ""}`} aria-pressed={rulerDisplayMode === "bark"} onClick={() => setRulerDisplayMode("bark")}>Bark</button></div> : <strong className="ruler-unit-locked">{plotUnits.normalization ?? "정규화 좌표"}</strong>}</div></div> : null}</div><button className={tool === "label" ? "is-active" : ""} onClick={() => { setTool("label"); setMessage("라벨 이동 모드 · 라벨을 드래그하세요."); }}><MousePointer2 size={16} /> 라벨 이동</button><button className={tool === "draw" ? "is-active" : ""} onClick={() => enterDrawMode(null)}><PenLine size={16} /> 그리기</button></div></div><div className="toolbar-context"><span>{analysis?.normalization ?? "정규화 없음"}</span><span>{analysis?.origin === "top_right" ? "Praat 좌표" : "수학 좌표"}</span>{!rightOpen ? <button className="sidebar-reopen" onClick={() => setRightOpen(true)}>레이어 <PanelRightOpen size={16} /></button> : null}</div></div>
        <div className="plot-canvas-shell"><div className="plot-paper" ref={plotPaperRef}>{previewUrl ? <><img ref={plotImageRef} src={previewUrl} alt={`${currentSource?.name ?? "현재 파일"} 포먼트 플롯`} draggable={false} onLoad={() => { if (referencePointerRef.current) setReferencePreview({ ...referencePointerRef.current }); }} /><div className="ruler-overlay" onPointerMove={handleRulerMove} onPointerDown={handleRulerDown} onPointerUp={handleRulerUp} onPointerCancel={handleRulerUp} onDoubleClick={(event) => {
                  if (tool === "draw" && drawTool === "line") {
                    event.preventDefault();
                    finishDrawLine(drawingPoints);
                  } else if (tool === "draw" && drawTool === "text") {
                    event.preventDefault();
                    openTextInputAt(event.clientX, event.clientY);
                  } else if (tool !== "draw") {
                    resetPlotLabel(event);
                  }
                }} onContextMenu={tool === "label" ? resetPlotLabel : handleRulerContextMenu}>
          <svg className="draw-line-layer" aria-hidden>
            {tool === "draw" && drawTool === "line" ? (() => {
              const paper = plotPaperRef.current?.getBoundingClientRect();
              const locals = drawingPoints
                .map((point) => drawPointLocal(point))
                .filter((point): point is { x: number; y: number } => Boolean(point));
              // 스냅: transData(px/py). 비스냅: 커서 paper-local (선형 axes_bbox면 가이드가 비뚤어짐)
              const hoverLocal = drawHover
                ? (drawHover.snapped
                  ? drawPointLocal(drawHover.point)
                  : (paper
                    ? { x: drawHover.clientX - paper.left, y: drawHover.clientY - paper.top }
                    : null))
                : null;
              const stroke = drawColor ?? DRAW_LINE_DEFAULT_COLOR;
              const last = locals[locals.length - 1];
              return (
                <>
                  {/* PySide _line_artist: 확정 점 ≥2 → 실선 alpha 0.4 */}
                  {locals.length >= 2 ? (
                    <polyline
                      className="draw-line-live"
                      points={locals.map((point) => `${point.x},${point.y}`).join(" ")}
                      fill="none"
                      stroke={stroke}
                      strokeWidth={Math.max(0.75, clampDrawLineWidth(drawWidth))}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      vectorEffect="non-scaling-stroke"
                    />
                  ) : null}
                  {/* PySide 가이드: 점 ≥1 + hover → 마지막점→호버, gray dotted */}
                  {last && hoverLocal ? (
                    <line
                      className="draw-line-guide"
                      x1={last.x}
                      y1={last.y}
                      x2={hoverLocal.x}
                      y2={hoverLocal.y}
                      stroke="#888888"
                      strokeWidth={1.25}
                      strokeDasharray="4 4"
                      strokeLinecap="round"
                      vectorEffect="non-scaling-stroke"
                    />
                  ) : null}
                  {locals.map((local, index) => (
                    <circle
                      key={`draw-point-${index}`}
                      className="draw-line-point"
                      cx={local.x}
                      cy={local.y}
                      r={index === locals.length - 1 ? 5 : 3.5}
                      fill="white"
                      stroke={stroke}
                      strokeWidth="2"
                    />
                  ))}
                </>
              );
            })() : null}
            {tool === "draw" && drawTool === "area" ? (() => {
              const paper = plotPaperRef.current?.getBoundingClientRect();
              const locals = drawingPoints
                .map((point) => drawPointLocal(point))
                .filter((point): point is { x: number; y: number } => Boolean(point));
              const hoverLocal = drawHover
                ? (drawHover.snapped
                  ? drawPointLocal(drawHover.point)
                  : (paper
                    ? { x: drawHover.clientX - paper.left, y: drawHover.clientY - paper.top }
                    : null))
                : null;
              const last = locals[locals.length - 1];
              const stroke = drawPolyBorderColor;
              const fill = drawPolyFillColor
                ? (() => {
                  const hex = drawPolyFillColor.replace("#", "");
                  if (hex.length !== 6) return "rgba(51, 102, 204, 0.15)";
                  const r = Number.parseInt(hex.slice(0, 2), 16);
                  const g = Number.parseInt(hex.slice(2, 4), 16);
                  const b = Number.parseInt(hex.slice(4, 6), 16);
                  return `rgba(${r}, ${g}, ${b}, ${drawPolyFillOpacity})`;
                })()
                : "transparent";
              return (
                <>
                  {locals.length >= 3 ? (
                    <polygon
                      className="draw-area-fill"
                      points={locals.map((point) => `${point.x},${point.y}`).join(" ")}
                      fill={fill}
                      stroke="none"
                    />
                  ) : null}
                  {locals.length >= 2 ? (
                    <polyline
                      className="draw-line-live"
                      points={locals.map((point) => `${point.x},${point.y}`).join(" ")}
                      fill="none"
                      stroke={stroke}
                      strokeWidth={1.5}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      vectorEffect="non-scaling-stroke"
                    />
                  ) : null}
                  {last && hoverLocal ? (
                    <line
                      className="draw-line-guide"
                      x1={last.x}
                      y1={last.y}
                      x2={hoverLocal.x}
                      y2={hoverLocal.y}
                      stroke="#888888"
                      strokeWidth={1.25}
                      strokeDasharray="4 4"
                      strokeLinecap="round"
                      vectorEffect="non-scaling-stroke"
                    />
                  ) : null}
                  {locals.map((local, index) => (
                    <circle
                      key={`area-point-${index}`}
                      className="draw-line-point"
                      cx={local.x}
                      cy={local.y}
                      r={index === 0 ? 5.5 : index === locals.length - 1 ? 5 : 3.5}
                      fill="white"
                      stroke={stroke}
                      strokeWidth="2"
                    />
                  ))}
                </>
              );
            })() : null}
          </svg>
          {tool === "draw" && (drawTool === "line" || drawTool === "area") && drawHover?.snapped && drawHover.rulerPoint ? (() => {
            const screen = rulerPointClient(drawHover.rulerPoint);
            const paper = plotPaperRef.current?.getBoundingClientRect();
            if (!screen || !paper) return null;
            return (
              <>
                <span
                  className={`ruler-snap-marker ${drawHover.rulerPoint.type === "mean" ? "is-mean" : "is-raw"}`}
                  style={{ left: screen.x - paper.left, top: screen.y - paper.top, borderColor: drawHover.rulerPoint.color }}
                />
                <span className="ruler-tooltip" style={{ left: screen.x - paper.left + 12, top: screen.y - paper.top - 30 }}>
                  {rulerTooltip(drawHover.rulerPoint)}
                </span>
              </>
            );
          })() : null}
          {tool === "draw" && drawTool === "reference" && referencePreview ? (
            <div
              className={`reference-preview ${referencePreview.mode === "horizontal" ? "is-horizontal" : "is-vertical"}${referencePreview.snapped ? " is-snapped" : ""}`}
              aria-hidden
            >
              <div
                className="reference-preview-line"
                style={
                  referencePreview.mode === "horizontal"
                    ? {
                      left: Math.min(referencePreview.x1, referencePreview.x2),
                      top: referencePreview.y1,
                      width: Math.max(1, Math.abs(referencePreview.x2 - referencePreview.x1)),
                      height: 2,
                      transform: "translateY(-50%)",
                    }
                    : {
                      left: referencePreview.x1,
                      top: Math.min(referencePreview.y1, referencePreview.y2),
                      width: 2,
                      height: Math.max(1, Math.abs(referencePreview.y2 - referencePreview.y1)),
                      transform: "translateX(-50%)",
                    }
                }
              />
              {referencePreview.label.trim() ? (
                <div
                  className="reference-preview-label"
                  style={{
                    left: referencePreview.mode === "horizontal" ? Math.min(referencePreview.x1, referencePreview.x2) + 4 : referencePreview.x1,
                    top: referencePreview.mode === "horizontal" ? referencePreview.y1 : Math.min(referencePreview.y1, referencePreview.y2),
                    fontFamily: axisPreviewFontFamily(design),
                    fontSize: Number(design.tick_label_size ?? 12),
                    fontWeight: 400,
                  }}
                >
                  {referencePreview.label.trim()}
                </div>
              ) : null}
            </div>
          ) : null}
          {tool === "draw" && drawTool === "legend" && currentLegend?.visible ? (() => {
            const liveLegend = legendDragPreview ? { ...currentLegend, ...legendDragPreview } : currentLegend;
            const rect = legendClientRect(liveLegend, !legendDragPreview);
            const defaultRect = draggingLegend || legendDragPreview ? defaultLegendClientRect(liveLegend) : null;
            const paper = plotPaperRef.current?.getBoundingClientRect();
            if (!rect || !paper) return null;
            const style = { left: rect.left - paper.left, top: rect.top - paper.top, width: rect.width, height: rect.height };
            return (
              <>
                <div className={`legend-live-hit ${draggingLegend || legendDragPreview ? "is-dragging" : ""}`} style={style} title="드래그하여 범례 이동" />
                {legendDragPreview ? <div className="legend-drag-preview" style={style} aria-hidden /> : null}
                {defaultRect ? <div className="legend-default-guide" style={{ left: defaultRect.left - paper.left, top: defaultRect.top - paper.top, width: defaultRect.width, height: defaultRect.height }} /> : null}
              </>
            );
          })() : null}
          {tool === "draw" ? currentDrawObjects.filter((object): object is DrawTextObject => object.type === "text" && object.visible).map((object) => {
            const paper = plotPaperRef.current?.getBoundingClientRect();
            const screen = drawTextAnchorClient(object);
            const box = drawTextBoxClient(object);
            if (!paper || !screen) return null;
            const isDragging = draggingTextId === object.id && textDragPointer !== null;
            const isHovered = hoveredDrawTextId === object.id;
            const anchorOffsetX = box ? box.left - screen.x : 0;
            const anchorOffsetY = box ? box.top - screen.y : 0;
            const left = isDragging ? textDragPointer.x + anchorOffsetX : box ? box.left - paper.left : screen.x - paper.left;
            const top = isDragging ? textDragPointer.y + anchorOffsetY : box ? box.top - paper.top : screen.y - paper.top;
            const weight = object.font_weight || (object.font_bold ? "bold" : "regular");
            const previewStyle = {
              color: object.text_color || DRAW_TEXT_DEFAULT_COLOR,
              fontSize: `${clampDrawTextFontSize(object.font_size)}pt`,
              fontWeight: weight === "bold" || weight === "semibold" ? 700 : weight === "medium" ? 500 : 400,
              fontStyle: object.font_italic ? "italic" as const : "normal" as const,
              fontFamily: axisPreviewFontFamily({ font_style: fontFamilyStyle(object.font_family || DRAW_TEXT_DEFAULT_FAMILY), font_family: object.font_family || DRAW_TEXT_DEFAULT_FAMILY }),
              lineHeight: clampDrawTextLineSpacing(object.line_spacing ?? DRAW_TEXT_DEFAULT_LINE_SPACING),
            };
            const boxStyle = box ? { width: box.width, height: box.height } : {};
            return (
              <span
                className={`draw-text-hit-target ${isDragging ? "is-dragging" : ""} ${isHovered ? "is-hovered" : ""}`}
                key={object.id}
                style={{ left, top, ...boxStyle }}
                title="드래그하여 텍스트 이동"
              >
                {/* 히트용 투명 텍스트 — opacity는 CSS만 (인라인 opacity 금지: 프리뷰와 겹침) */}
                <span className="draw-text-hit-text" style={previewStyle} aria-hidden>
                  {object.text.split("\n").map((line, index) => (
                    <span key={`${object.id}-hit-${index}`}>{line || "\u00a0"}</span>
                  ))}
                </span>
                {isDragging ? (
                  <span
                    className="draw-text-drag-preview"
                    style={{ ...previewStyle, opacity: object.semi ? 0.35 : 1 }}
                    aria-hidden
                  >
                    {object.text.split("\n").map((line, index) => (
                      <span key={`${object.id}-prev-${index}`}>{line || "\u00a0"}</span>
                    ))}
                  </span>
                ) : null}
              </span>
            );
          }) : null}
          {tool === "label" && rulerContext ? rulerContext.labels.map((label) => { const screen = plotLabelClient(label); const box = plotLabelBoxClient(label); const paper = plotPaperRef.current?.getBoundingClientRect(); if (!screen || !paper) return null; const isDragging = draggingPlotLabel === label.vowel && plotLabelPointer !== null; const isPreviewing = plotLabelPreviewVowel === label.vowel && plotLabelPointer !== null; const isHovered = hoveredPlotLabel === label.vowel; const anchorOffsetX = box ? box.left - screen.x : 0; const anchorOffsetY = box ? box.top - screen.y : 0; const left = isPreviewing ? plotLabelPointer.x + anchorOffsetX : box ? box.left - paper.left : screen.x - paper.left; const top = isPreviewing ? plotLabelPointer.y + anchorOffsetY : box ? box.top - paper.top : screen.y - paper.top; const labelDesign = { ...design, ...(layerOverrides[label.vowel] ?? {}) }; const rawWeight = String(labelDesign.font_weight ?? ""); const rawBold = String(labelDesign.lbl_bold); const isBold = rawWeight === "bold" || (!rawWeight && (rawBold === "true" || rawBold === "bold" || rawBold === "medium")); const previewStyle = { color: String(label.lbl_color ?? labelDesign.lbl_color ?? "#ff0000"), fontSize: `${Number(label.fontsize ?? labelDesign.lbl_size ?? 18)}pt`, fontWeight: isBold ? 700 : 400, fontStyle: label.lbl_italic ?? labelDesign.lbl_italic ? "italic" as const : "normal" as const, fontFamily: labelDesign.font_style === "sans" ? "var(--gf-font-sans)" : "var(--gf-font-serif)" }; const boxStyle = box ? { width: box.width, height: box.height } : {}; return <span className={`plot-label-hit-target ${isDragging ? "is-dragging" : ""} ${isHovered ? "is-hovered" : ""}`} key={`label-${label.vowel}`} style={{ left, top, ...boxStyle }} title={`${label.vowel} 라벨 이동`}><span className="plot-label-hit-text" style={previewStyle}>{label.display_vowel ?? label.vowel}</span>{isPreviewing ? <span className="plot-label-drag-preview" style={previewStyle}>{label.display_vowel ?? label.vowel}</span> : null}</span>; }) : null}
         {tool === "ruler" ? rulerMeasurements.map((measurement, index) => { const a = rulerPointClient(measurement.p1); const b = rulerPointClient(measurement.p2); const paper = plotPaperRef.current?.getBoundingClientRect(); if (!a || !b || !paper) return null; const x1 = a.x - paper.left; const y1 = a.y - paper.top; const x2 = b.x - paper.left; const y2 = b.y - paper.top; const triangleLabels = rulerGeometryMode === "right-triangle" ? rulerTriangleLabels(measurement.p1, measurement.p2) : null; const dx = x2 - x1; const dy = y2 - y1; const length = Math.max(1, Math.hypot(dx, dy)); const hypotenuseAngle = Math.atan2(dy, dx) * 180 / Math.PI; const readableAngle = hypotenuseAngle > 90 || hypotenuseAngle < -90 ? hypotenuseAngle + 180 : hypotenuseAngle; const hypotenuseOffset = 18; const hypotenuseLabelX = (x1 + x2) / 2 - (dy / length) * hypotenuseOffset; const hypotenuseLabelY = (y1 + y2) / 2 + (dx / length) * hypotenuseOffset; return <div className="ruler-measurement" key={`${measurement.p1.x}-${measurement.p2.x}-${index}`}><svg className="ruler-line-layer" aria-hidden>{rulerGeometryMode === "right-triangle" ? <><polyline points={`${x1},${y1} ${x2},${y1} ${x2},${y2}`} /><line x1={x1} y1={y1} x2={x2} y2={y2} /></> : <line x1={x1} y1={y1} x2={x2} y2={y2} />}</svg><span className="ruler-point ruler-point-start" style={{ left: x1, top: y1, borderColor: measurement.p1.color }} /><span className="ruler-point ruler-point-end" style={{ left: x2, top: y2, borderColor: measurement.p2.color }} />{triangleLabels ? <><span className="ruler-side-label ruler-side-label-horizontal" style={{ left: (x1 + x2) / 2, top: y1 + 6 }}>{triangleLabels.horizontal}</span><span className="ruler-side-label ruler-side-label-vertical" style={{ left: x2 + 6, top: (y1 + y2) / 2 }}>{triangleLabels.vertical}</span><span className="ruler-side-label ruler-side-label-hypotenuse" style={{ left: hypotenuseLabelX, top: hypotenuseLabelY, transform: `translate(-50%, -50%) rotate(${readableAngle}deg)` }}>{triangleLabels.hypotenuse}</span></> : <button type="button" tabIndex={-1} aria-label={`거리 ${measurement.distance}`} className="ruler-label" style={{ left: measurement.labelX, top: measurement.labelY }} onPointerDown={(event) => { event.stopPropagation(); setDraggingRulerLabel(index); event.currentTarget.setPointerCapture(event.pointerId); }}>{measurement.distance}</button>}</div>; }) : null}
          {tool === "ruler" && rulerStart ? (() => { const screen = rulerPointClient(rulerStart); const paper = plotPaperRef.current?.getBoundingClientRect(); return screen && paper ? <span className={`ruler-snap-marker ${rulerStart.type === "mean" ? "is-mean" : "is-raw"}`} style={{ left: screen.x - paper.left, top: screen.y - paper.top, borderColor: rulerStart.color }} /> : null; })() : null}
          {tool === "ruler" && rulerStart && rulerPointer ? <svg className="ruler-guide-layer" aria-hidden><line x1={rulerPointClient(rulerStart) ? (rulerPointClient(rulerStart)!.x - (plotPaperRef.current?.getBoundingClientRect().left ?? 0)) : 0} y1={rulerPointClient(rulerStart) ? (rulerPointClient(rulerStart)!.y - (plotPaperRef.current?.getBoundingClientRect().top ?? 0)) : 0} x2={rulerPointer.x} y2={rulerPointer.y} /></svg> : null}
          {tool === "ruler" && rulerHover ? (() => { const screen = rulerPointClient(rulerHover); const paper = plotPaperRef.current?.getBoundingClientRect(); return screen && paper ? <><span className={`ruler-snap-marker ${rulerHover.type === "mean" ? "is-mean" : "is-raw"}`} style={{ left: screen.x - paper.left, top: screen.y - paper.top, borderColor: rulerHover.color }} /><span className="ruler-tooltip" style={{ left: screen.x - paper.left + 12, top: screen.y - paper.top - 30 }}>{rulerTooltip(rulerHover)}</span></> : null; })() : null}
        </div></> : <div className="plot-placeholder">{previewLoading ? <><Loader2 size={30} className="is-spinning" aria-hidden /><strong>플롯을 준비하는 중</strong><span>분석 엔진에서 미리보기를 그리는 동안 잠시만 기다려 주세요.</span></> : <><Layers3 size={30} /><strong>표시할 플롯이 없습니다</strong><span>메인 창에서 데이터 파일을 불러와 주세요.</span></>}</div>}</div></div>
        <footer className="plot-stage-footer"><span>{message}</span><span title={previewInfo}>{previewInfo || currentSource?.name || "대기 중"}</span></footer>
      </section>

      <aside className="layer-inspector">
        <header className="layer-inspector-header"><div><span className="section-eyebrow">{rightPanel === "layers" ? "레이어 디자인" : "그리기 디자인"}</span><strong>{rightPanel === "layers" ? `${currentVowels.length}개 모음` : "주석 도구"}</strong></div><button className="rail-collapse" aria-label="오른쪽 패널 접기" onClick={() => setRightOpen(false)}><PanelRightClose size={16} /></button></header>
        <div className="layer-panel-tabs"><button type="button" className={rightPanel === "layers" ? "is-active" : ""} onClick={() => setRightPanel("layers")}><Layers3 size={15} /> 레이어</button><button type="button" className={rightPanel === "drawing" ? "is-active" : ""} onClick={() => enterDrawMode(drawTool)}><PenLine size={15} /> 그리기</button></div>
        {rightPanel === "layers" ? (
          <LayersPanel
            layerListHeight={layerListHeight}
            selectedLayer={selectedLayer}
            selectedLocked={selectedLocked}
            effective={effective}
            updateLayerDesign={updateLayerDesign}
            resetSelectedLayer={resetSelectedLayer}
            beginLayerPanelResize={beginLayerPanelResize}
            resizeLayerPanels={resizeLayerPanels}
            endLayerPanelResize={endLayerPanelResize}
            cancelLayerPanelResize={cancelLayerPanelResize}
            toggleAllLayerEyes={toggleAllLayerEyes}
            toggleAllLayerSemi={toggleAllLayerSemi}
            resetLayerOrder={resetLayerOrder}
            layerListRef={layerListRef}
            layerOrder={layerOrder}
            layerState={layerState}
            lockedLayers={lockedLayers}
            layerOverrides={layerOverrides}
            expandedLayers={expandedLayers}
            setExpandedLayers={setExpandedLayers}
            selectedLayers={selectedLayers}
            draggingLayer={draggingLayer}
            dropTarget={dropTarget}
            layerRowRefs={layerRowRefs}
            draggingLayerRef={draggingLayerRef}
            cancelLayerDrag={cancelLayerDrag}
            beginLayerDrag={beginLayerDrag}
            moveLayerDrag={moveLayerDrag}
            commitLayerDrag={commitLayerDrag}
            moveLayerByStep={moveLayerByStep}
            toggleLayerEye={toggleLayerEye}
            toggleLayerSemi={toggleLayerSemi}
            selectLayer={selectLayer}
            toggleLock={toggleLock}
            removeLayerEffect={removeLayerEffect}
          />
        ) : (
          <DrawingPanel
            layerListHeight={layerListHeight}
            drawTool={drawTool}
            activateDrawTool={activateDrawTool}
            openDrawDefaultsEditor={openDrawDefaultsEditor}
            referenceMode={referenceMode}
            setReferenceMode={setReferenceMode}
            setMessage={setMessage}
            beginLayerPanelResize={beginLayerPanelResize}
            resizeLayerPanels={resizeLayerPanels}
            endLayerPanelResize={endLayerPanelResize}
            cancelLayerPanelResize={cancelLayerPanelResize}
            toggleAllDrawVisibility={toggleAllDrawVisibility}
            toggleAllDrawSemi={toggleAllDrawSemi}
            persistDrawObjects={persistDrawObjects}
            currentDrawObjects={currentDrawObjects}
            drawObjectsTopFirst={drawObjectsTopFirst}
            currentDrawLines={currentDrawLines}
            normalization={analysis?.normalization ?? null}
            selectedDrawObjectIds={selectedDrawObjectIds}
            draggingDrawObject={draggingDrawObject}
            drawDropTarget={drawDropTarget}
            beginDrawObjectDrag={beginDrawObjectDrag}
            moveDrawObjectDrag={moveDrawObjectDrag}
            commitDrawObjectDrag={commitDrawObjectDrag}
            cancelDrawObjectDrag={cancelDrawObjectDrag}
            toggleDrawObjectVisibility={toggleDrawObjectVisibility}
            toggleDrawObjectSemi={toggleDrawObjectSemi}
            selectDrawObject={selectDrawObject}
            openDrawLayerEditor={openDrawLayerEditor}
            deleteDrawObjects={deleteDrawObjects}
          />
        )}
      </aside>
      {batchExportOpen ? (
        <BatchExportDialog
          sourceCount={sources.length}
          format={batchExportFormat}
          onFormatChange={setBatchExportFormat}
          directory={batchExportDirectory}
          onChooseDirectory={() => void chooseBatchDirectory()}
          busy={batchExportBusy}
          applyGlobalDesign={batchApplyGlobalDesign}
          onApplyGlobalDesignChange={() => setBatchApplyGlobalDesign((value) => !value)}
          applyLayerDesign={batchApplyLayerDesign}
          onApplyLayerDesignChange={() => setBatchApplyLayerDesign((value) => !value)}
          applyVisibility={batchApplyVisibility}
          onApplyVisibilityChange={() => setBatchApplyVisibility((value) => !value)}
          applyLabelPositions={batchApplyLabelPositions}
          onApplyLabelPositionsChange={() => setBatchApplyLabelPositions((value) => !value)}
          onClose={() => setBatchExportOpen(false)}
          onExport={() => void runBatchExport()}
        />
      ) : null}
      {textInput ? (
        <div className="legend-editor-backdrop" role="presentation">
          <section className="legend-editor-dialog draw-text-input-dialog" role="dialog" aria-modal="true" aria-labelledby="draw-text-input-title">
            <header>
              <div>
                <span className="section-eyebrow">TEXT</span>
                <h2 id="draw-text-input-title">텍스트 입력</h2>
                <p>여러 줄 가능 · Enter로 줄바꿈</p>
              </div>
              <button type="button" onClick={() => setTextInput(null)} aria-label="닫기"><X size={18} /></button>
            </header>
            <div className="legend-editor-body">
              <label className="draw-text-content-field">
                <span>표시할 텍스트</span>
                <textarea
                  autoFocus
                  value={textInput.draft}
                  onChange={(event) => setTextInput({ ...textInput, draft: event.target.value })}
                  rows={6}
                />
              </label>
            </div>
            <footer>
              <button type="button" className="wide-action" onClick={() => setTextInput(null)}>취소</button>
              <button type="button" className="wide-action primary" onClick={confirmTextInput}>확인</button>
            </footer>
          </section>
        </div>
      ) : null}
      {drawEditorOpen ? (
        <DrawStyleEditor
          kind={drawEditorKind}
          mode={drawEditorMode}
          lineDraft={lineDraft}
          onLineDraftChange={setLineDraft}
          polygonDraft={polygonDraft}
          onPolygonDraftChange={setPolygonDraft}
          referenceDraft={referenceDraft}
          onReferenceDraftChange={setReferenceDraft}
          textDraft={textDraft}
          onTextDraftChange={setTextDraft}
          legendDraft={legendDraft}
          onLegendDraftChange={setLegendDraft}
          onClose={closeDrawEditor}
          onSave={saveDrawEditor}
        />
      ) : null}
      {vowelAnalysisOpen ? (
        <VowelAnalysisShell
          currentSource={currentSource}
          sources={sources}
          currentIndex={currentIndex}
          displayIndex={Math.max(0, sources.findIndex((source) => source.index === currentIndex))}
          normalization={normalization}
          plotType={plotType}
          onNavigate={(index) => void navigateTo(index)}
          onClose={() => setVowelAnalysisOpen(false)}
        />
      ) : null}
      {shortcutHelpOpen ? (
        <ShortcutHelpDialog onClose={() => setShortcutHelpOpen(false)} />
      ) : null}
    </main>
  );
}
