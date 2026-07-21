import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { open, save } from "@tauri-apps/plugin-dialog";
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Layers3,
  Palette,
  PanelLeftClose,
  PanelRightClose,
  PenLine,
  SlidersHorizontal,
  X,
} from "lucide-react";
import type { ApplicationState } from "../../ipc/protocol";
import { callSidecar } from "../sidecarClient";
import { cacheMapSet } from "../cacheMap";
import { sortVowels } from "../vowelSort";
import {
  resolvePlotUnits,
  smartAxisRanges,
} from "../plotUnits";
import {
  BARK_RANGE_DEFAULTS,
  EMPTY_DESIGN,
  NORM_RANGE_DEFAULTS,
  RANGE_DEFAULTS,
  rangesLookCompatible,
} from "./interactivePlot/designDefaults";
import { MAX_CACHED_FILE_DESIGNS } from "./interactivePlot/layerCache";
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
import { PlotStage } from "./interactivePlot/PlotStage";
import { ShortcutHelpDialog } from "./interactivePlot/ShortcutHelpDialog";
import { useDrawSession } from "./interactivePlot/useDrawSession";
import { useLayerSession } from "./interactivePlot/useLayerSession";
import {
  type InteractiveRenderOverrides,
  usePlotRender,
} from "./interactivePlot/usePlotRender";
import { useRulerSession } from "./interactivePlot/useRulerSession";
import { VowelAnalysisShell } from "./interactivePlot/VowelAnalysisShell";
import { FileSelectMenu } from "./interactivePlot/widgets";
import type {
  DesignSettings,
  DrawObject,
  DrawTool,
  LeftPanel,
  Ranges,
  RightPanel,
  RulerContext,
  SidecarEvent,
  Tool,
} from "./interactivePlot/types";
import "./InteractivePlotWindow.css";

export function InteractivePlotWindow() {
  const [state, setState] = useState<ApplicationState | null>(null);
  const [combinedVisible, setCombinedVisible] = useState(() => window.localStorage.getItem("gichanformant-show-combined") === "true");
  const [batchExportOpen, setBatchExportOpen] = useState(false);
  const [batchExportFormat, setBatchExportFormat] = useState<"png" | "jpg" | "svg">("png");
  const [batchExportDirectory, setBatchExportDirectory] = useState("");
  const [batchExportBusy, setBatchExportBusy] = useState(false);
  const [batchApplyGlobalDesign, setBatchApplyGlobalDesign] = useState(true);
  const [batchApplyLayerDesign, setBatchApplyLayerDesign] = useState(true);
  const [batchApplyVisibility, setBatchApplyVisibility] = useState(true);
  const [batchApplyLabelPositions, setBatchApplyLabelPositions] = useState(true);
  const [batchApplyLegend, setBatchApplyLegend] = useState(true);
  const [batchApplyDrawAnnotations, setBatchApplyDrawAnnotations] = useState(true);
  const [tool, setTool] = useState<Tool>("select");
  const [leftPanel, setLeftPanel] = useState<LeftPanel>("analysis");
  const [rightPanel, setRightPanel] = useState<RightPanel>("layers");
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
  const renderInteractiveRef = useRef<(overrides?: InteractiveRenderOverrides) => void | Promise<void>>(async () => {});
  const scheduleInteractiveRenderRef = useRef<(overrides?: InteractiveRenderOverrides) => void>(() => {});
  const applyLegendBoundsRef = useRef<(legendBounds: Record<string, { width_frac: number; height_frac: number }>) => void>(() => {});
  const setRulerContextRef = useRef<(context: RulerContext | null) => void>(() => {});
  const clearRulerOnPreviewReadyRef = useRef<() => void>(() => {});
  const clearRulerOnPreviewClearedRef = useRef<() => void>(() => {});
  const resetCanvasDrawPreviewRef = useRef<() => void>(() => {});
  const clearLegendDragPreviewRef = useRef<() => void>(() => {});
  const globalDesignByFileRef = useRef(new Map<string, DesignSettings>());
  const designInitializedRef = useRef(false);

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
    rulerSettingsOpen,
    setRulerSettingsOpen,
    rulerGeometryMode,
    setRulerGeometryMode,
    rulerDisplayMode,
    setRulerDisplayMode,
    rulerContext,
    setRulerContext,
    rulerStart,
    setRulerStart,
    rulerHover,
    setRulerHover,
    rulerPointer,
    setRulerPointer,
    rulerMeasurements,
    setRulerMeasurements,
    draggingRulerLabel,
    setDraggingRulerLabel,
    draggingPlotLabel,
    setDraggingPlotLabel,
    hoveredPlotLabel,
    setHoveredPlotLabel,
    plotLabelPointer,
    setPlotLabelPointer,
    plotLabelPreviewVowel,
    setPlotLabelPreviewVowel,
    plotLabelFrameRef,
    plotLabelDragStartRef,
    plotLabelHasMovedRef,
    rulerTooltip,
    rulerDistanceLabelWithSettings,
    rulerTriangleLabels,
    resetTransientRuler,
    clearRulerOnPreviewReady,
    clearRulerOnPreviewCleared,
  } = useRulerSession({ plotUnits, tool });
  setRulerContextRef.current = setRulerContext;
  clearRulerOnPreviewReadyRef.current = clearRulerOnPreviewReady;
  clearRulerOnPreviewClearedRef.current = clearRulerOnPreviewCleared;
  const {
    drawTool,
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
    exitDrawMode,
    toggleDrawMode,
    activateDrawTool,
    hydrateDrawObjectsForFile,
    applyLegendBounds,
    beginTextInput,
    resetTransientDraw,
  } = useDrawSession({
    currentIndex,
    currentSourceName: currentSource?.name,
    normalization: analysis?.normalization ?? null,
    tool,
    setMessage,
    setTool,
    setRightPanel,
    setRightOpen,
    renderInteractive: (overrides) => renderInteractiveRef.current(overrides),
    onResetCanvasDrawPreview: () => {
      resetCanvasDrawPreviewRef.current();
    },
  });
  applyLegendBoundsRef.current = applyLegendBounds;

  const toggleRulerMode = () => {
    if (tool === "ruler") {
      resetTransientRuler();
      setRulerSettingsOpen(false);
      setTool("select");
      return;
    }
    if (tool === "label" || tool === "draw") return;
    setTool("ruler");
  };

  const toggleLabelMode = () => {
    if (tool === "label") {
      setTool("select");
      return;
    }
    if (tool === "ruler" || tool === "draw") return;
    setTool("label");
    setMessage("라벨 이동 모드 · 라벨을 드래그하세요.");
  };

  const selectNeutralTool = () => {
    if (tool === "draw") exitDrawMode();
    else if (tool === "ruler") {
      resetTransientRuler();
      setRulerSettingsOpen(false);
      setTool("select");
    } else setTool("select");
  };
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

  const {
    previewUrl,
    previewInfo,
    previewLoading,
    setPreviewLoading,
    renderInteractive,
    scheduleInteractiveRender,
    consumePreviewSuccessMessage,
    isStalePreviewRequest,
    nextRenderRequestId,
    invalidatePendingRender,
    applyPreviewReady,
    applyPreviewFailed,
    applyPreviewCleared,
  } = usePlotRender({
    aliveRef,
    canPlot: Boolean(state?.capabilities.can_plot),
    setMessage,
    ranges,
    sigma,
    showEllipse,
    design,
    layerState,
    layerOverrides,
    layerOrder,
    lockedLayers,
    currentDrawObjects,
    unitModeKey,
    normalization,
    defaultRanges,
    setDesign,
    setRanges,
  });
  renderInteractiveRef.current = renderInteractive;
  scheduleInteractiveRenderRef.current = scheduleInteractiveRender;

  const refresh = useCallback(async () => {
    setPreviewLoading(true);
    try {
      const next = await callSidecar<ApplicationState>("get_state");
      if (!aliveRef.current) return;
      setState(next);
      setEngineConnected(true);
      if (next.capabilities.can_plot) {
        const requestId = nextRenderRequestId();
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
  }, [nextRenderRequestId, setPreviewLoading]);

  useEffect(() => {
    aliveRef.current = true;
    void refresh();
    let disposed = false;
    let disposeEvent: (() => void) | undefined;
    void listen<SidecarEvent>("sidecar-event", ({ payload }) => {
      if (disposed || !aliveRef.current) return;
      if (payload.event === "preview_ready" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (isStalePreviewRequest(requestId)) return;
        applyPreviewReady({
          imagePath: String(payload.payload.png_path ?? ""),
          imageBase64: String(payload.payload.png_base64 ?? ""),
          info: String(payload.payload.info ?? ""),
        });
        const nextRuler = (payload.payload.ruler_context as RulerContext | undefined) ?? null;
        setRulerContextRef.current(nextRuler);
        const legendBounds = nextRuler?.legend_bounds;
        if (legendBounds) {
          applyLegendBoundsRef.current(legendBounds);
        }
        clearLegendDragPreviewRef.current();
        clearRulerOnPreviewReadyRef.current();
        setMessage(consumePreviewSuccessMessage(requestId) ?? "플롯을 업데이트했습니다.");
      } else if (payload.event === "preview_failed" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (isStalePreviewRequest(requestId)) return;
        applyPreviewFailed(String(payload.payload.message ?? "알 수 없는 오류"));
      } else if (payload.event === "preview_cleared" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (isStalePreviewRequest(requestId)) return;
        applyPreviewCleared();
        clearRulerOnPreviewClearedRef.current();
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
  }, [applyPreviewCleared, applyPreviewFailed, applyPreviewReady, consumePreviewSuccessMessage, isStalePreviewRequest, refresh]);

  const navigateTo = useCallback(async (sourceIndex: number) => {
    if (!sources.length || navigatingRef.current) return;
    const nextSource = sources.find((source) => source.index === sourceIndex);
    if (!nextSource) return;
    const target = nextSource.index;
    if (target === currentIndexRef.current) return;
    navigatingRef.current = true;
    invalidatePendingRender();
    setNavigating(true);
    setPreviewLoading(true);
    resetTransientRuler();
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
       const requestId = nextRenderRequestId();
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
  }, [analysis?.use_bark_units, applyLayersAfterNavigate, cacheCurrentLayerSession, canonicalDesign, currentFileKey, defaultRanges, design, globalDesignLocked, invalidatePendingRender, nextRenderRequestId, normalization, ranges, resetTransientDraw, resetTransientRuler, setPreviewLoading, showEllipse, sigma, sources]);

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
          exitDrawMode();
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
        toggleRulerMode();
        return;
      }
      if (event.key.toLowerCase() === "t") {
        event.preventDefault();
        toggleLabelMode();
        return;
      }
      if (event.key.toLowerCase() === "p") {
        event.preventDefault();
        toggleDrawMode();
        return;
      }
      if (event.key === "Escape" && tool === "ruler") {
        event.preventDefault();
        resetTransientRuler();
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
        exitDrawMode();
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
  }, [analysis?.normalization, canNavigate, currentSourcePosition, drawArrowHead, drawArrowMode, drawColor, drawEditorOpen, drawLineStyle, drawTool, drawWidth, drawingPoints, exitDrawMode, finishDrawLine, finishDrawPolygon, navigateByPosition, navigating, resetTransientRuler, rulerSettingsOpen, setRulerSettingsOpen, shortcutHelpOpen, sources, toggleDrawMode, toggleLabelMode, toggleRulerMode, tool]);

  const updateDesign = (patch: Partial<DesignSettings>) => {
    const next = { ...design, ...patch };
    setDesign(next);
    if (currentFileKey) cacheMapSet(globalDesignByFileRef.current, currentFileKey, next, MAX_CACHED_FILE_DESIGNS);
    scheduleInteractiveRender({ design: next });
  };

  const resetPlot = (successMessage = "좌표축 범위와 신뢰 타원을 초기화했습니다.") => {
    const nextRanges = defaultRanges;
    const nextLayers = resetLayers(currentVowels);
    setRanges(nextRanges);
    setSigma("2.0");
    setShowEllipse(true);
    setDesign(canonicalDesign);
    setGlobalDesignLocked(false);
    void renderInteractive({
      design: canonicalDesign,
      layers: nextLayers,
      ranges: nextRanges,
      sigma: "2",
      showEllipse: true,
      layerOverrides: {},
      layerOrder: sortVowels(currentVowels),
      successMessage,
    });
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
        options: { ranges, sigma, show_ellipse: showEllipse, design, filter_state: layerState, layer_overrides: layerOverrides, layer_order: layerOrder, locked_layers: [...lockedLayers], draw_objects: currentDrawObjects, batch_options: { apply_global_design: batchApplyGlobalDesign, apply_layer_design: batchApplyLayerDesign, apply_layer_visibility: batchApplyVisibility, apply_label_positions: batchApplyLabelPositions, apply_legend: batchApplyLegend, apply_draw_annotations: batchApplyDrawAnnotations } },
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
                void renderInteractive({
                  sigma: next,
                  successMessage: `신뢰 타원 범위를 ${next}σ로 바꿨습니다.`,
                });
              }}
              showEllipse={showEllipse}
              onShowEllipseChange={(next) => {
                setShowEllipse(next);
                void renderInteractive({
                  showEllipse: next,
                  successMessage: next ? "신뢰 타원을 표시합니다." : "신뢰 타원을 숨겼습니다.",
                });
              }}
              onReset={() => resetPlot()}
              onApplyRanges={() => void renderInteractive({
                successMessage: "좌표축 범위를 플롯에 반영했습니다.",
              })}
              busy={busy}
              sourceCount={sources.length}
              canCompare={sources.filter((source) => !source.is_combined).length >= 2}
              tool={tool}
              onOpenVowelAnalysis={() => setVowelAnalysisOpen(true)}
              onOpenCompare={() => void openComparePlot()}
              onToggleRuler={toggleRulerMode}
              onEnterDraw={toggleDrawMode}
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
              onReset={() => resetPlot("광역 디자인을 초기화했습니다.")}
              globalDesignLocked={globalDesignLocked}
              onToggleLock={() => setGlobalDesignLocked((locked) => !locked)}
            />
          )}
        </div>
      </aside>

      <PlotStage
        previewUrl={previewUrl}
        previewLoading={previewLoading}
        previewInfo={previewInfo}
        message={message}
        currentSourceName={currentSource?.name}
        currentIndex={currentIndex}
        tool={tool}
        selectNeutralTool={selectNeutralTool}
        toggleRulerMode={toggleRulerMode}
        toggleLabelMode={toggleLabelMode}
        toggleDrawMode={toggleDrawMode}
        setMessage={setMessage}
        leftOpen={leftOpen}
        setLeftOpen={setLeftOpen}
        rightOpen={rightOpen}
        setRightOpen={setRightOpen}
        design={design}
        layerOverrides={layerOverrides}
        analysisNormalization={analysis?.normalization}
        analysisF1Scale={analysis?.f1_scale}
        analysisF2Scale={analysis?.f2_scale}
        analysisOrigin={analysis?.origin}
        plotUnits={plotUnits}
        drawIdRef={drawIdRef}
        resetCanvasDrawPreviewRef={resetCanvasDrawPreviewRef}
        clearLegendDragPreviewRef={clearLegendDragPreviewRef}
        renderInteractive={renderInteractive}
        drawTool={drawTool}
        drawingPoints={drawingPoints}
        setDrawingPoints={setDrawingPoints}
        drawHover={drawHover}
        setDrawHover={setDrawHover}
        currentDrawObjects={currentDrawObjects}
        currentLegend={currentLegend}
        persistDrawObjects={persistDrawObjects}
        focusDrawObject={focusDrawObject}
        finishDrawLine={finishDrawLine}
        finishDrawPolygon={finishDrawPolygon}
        beginTextInput={beginTextInput}
        referenceMode={referenceMode}
        drawRefStyle={drawRefStyle}
        drawRefColor={drawRefColor}
        drawColor={drawColor}
        drawWidth={drawWidth}
        drawPolyBorderColor={drawPolyBorderColor}
        drawPolyFillColor={drawPolyFillColor}
        drawPolyFillOpacity={drawPolyFillOpacity}
        rulerSettingsOpen={rulerSettingsOpen}
        setRulerSettingsOpen={setRulerSettingsOpen}
        rulerGeometryMode={rulerGeometryMode}
        setRulerGeometryMode={setRulerGeometryMode}
        rulerDisplayMode={rulerDisplayMode}
        setRulerDisplayMode={setRulerDisplayMode}
        rulerContext={rulerContext}
        rulerStart={rulerStart}
        setRulerStart={setRulerStart}
        rulerHover={rulerHover}
        setRulerHover={setRulerHover}
        rulerPointer={rulerPointer}
        setRulerPointer={setRulerPointer}
        rulerMeasurements={rulerMeasurements}
        setRulerMeasurements={setRulerMeasurements}
        draggingRulerLabel={draggingRulerLabel}
        setDraggingRulerLabel={setDraggingRulerLabel}
        draggingPlotLabel={draggingPlotLabel}
        setDraggingPlotLabel={setDraggingPlotLabel}
        hoveredPlotLabel={hoveredPlotLabel}
        setHoveredPlotLabel={setHoveredPlotLabel}
        plotLabelPointer={plotLabelPointer}
        setPlotLabelPointer={setPlotLabelPointer}
        plotLabelPreviewVowel={plotLabelPreviewVowel}
        setPlotLabelPreviewVowel={setPlotLabelPreviewVowel}
        plotLabelFrameRef={plotLabelFrameRef}
        plotLabelDragStartRef={plotLabelDragStartRef}
        plotLabelHasMovedRef={plotLabelHasMovedRef}
        rulerTooltip={rulerTooltip}
        rulerDistanceLabelWithSettings={rulerDistanceLabelWithSettings}
        rulerTriangleLabels={rulerTriangleLabels}
      />

      <aside className="layer-inspector">
        <header className="layer-inspector-header"><div><span className="section-eyebrow">{rightPanel === "layers" ? "레이어 디자인" : "그리기 디자인"}</span><strong>{rightPanel === "layers" ? `${currentVowels.length}개 모음` : "주석 도구"}</strong></div><button className="rail-collapse" aria-label="오른쪽 패널 접기" onClick={() => setRightOpen(false)}><PanelRightClose size={16} /></button></header>
        <div className="layer-panel-tabs"><button type="button" className={rightPanel === "layers" ? "is-active" : ""} onClick={() => setRightPanel("layers")}><Layers3 size={15} /> 레이어</button><button type="button" className={rightPanel === "drawing" ? "is-active" : ""} onClick={() => { if (tool === "ruler" || tool === "label") return; enterDrawMode(drawTool); }}><PenLine size={15} /> 그리기</button></div>
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
          applyLegend={batchApplyLegend}
          onApplyLegendChange={() => setBatchApplyLegend((value) => !value)}
          applyDrawAnnotations={batchApplyDrawAnnotations}
          onApplyDrawAnnotationsChange={() => setBatchApplyDrawAnnotations((value) => !value)}
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
