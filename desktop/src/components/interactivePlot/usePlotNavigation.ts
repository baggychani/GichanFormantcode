import { useCallback } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import type { ApplicationState } from "../../../ipc/protocol";
import { cacheMapSet } from "../../cacheMap";
import { callSidecar } from "../../sidecarClient";
import { MAX_CACHED_FILE_DESIGNS } from "./layerCache";
import { rangesLookCompatible } from "./designDefaults";
import type { DesignSettings, Ranges } from "./types";

type PlotSession = ApplicationState["plot_session"];

type PlotNavigationParams = {
  aliveRef: MutableRefObject<boolean>;
  navigatingRef: MutableRefObject<boolean>;
  currentIndexRef: MutableRefObject<number>;
  sources: ApplicationState["sources"];
  currentFileKey: string;
  analysisUseBark: boolean;
  normalization: string | null;
  ranges: Ranges;
  defaultRanges: Ranges;
  sigma: string;
  showEllipse: boolean;
  design: DesignSettings;
  canonicalDesign: DesignSettings;
  globalDesignLocked: boolean;
  globalDesignByFileRef: MutableRefObject<Map<string, DesignSettings>>;
  setNavigating: Dispatch<SetStateAction<boolean>>;
  setPreviewLoading: Dispatch<SetStateAction<boolean>>;
  setRanges: Dispatch<SetStateAction<Ranges>>;
  setSigma: Dispatch<SetStateAction<string>>;
  setShowEllipse: Dispatch<SetStateAction<boolean>>;
  setDesign: Dispatch<SetStateAction<DesignSettings>>;
  setState: Dispatch<SetStateAction<ApplicationState | null>>;
  setMessage: Dispatch<SetStateAction<string>>;
  invalidatePendingRender: () => void;
  nextRenderRequestId: () => number;
  resetTransientRuler: () => void;
  resetTransientDraw: () => void;
  cacheCurrentLayerSession: (fileKey: string) => void;
  applyLayersAfterNavigate: (input: {
    fileKey: string;
    vowels: string[];
    sessionKey: string;
    plotSession: PlotSession;
  }) => void;
};

export function usePlotNavigation({
  aliveRef,
  navigatingRef,
  currentIndexRef,
  sources,
  currentFileKey,
  analysisUseBark,
  normalization,
  ranges,
  defaultRanges,
  sigma,
  showEllipse,
  design,
  canonicalDesign,
  globalDesignLocked,
  globalDesignByFileRef,
  setNavigating,
  setPreviewLoading,
  setRanges,
  setSigma,
  setShowEllipse,
  setDesign,
  setState,
  setMessage,
  invalidatePendingRender,
  nextRenderRequestId,
  resetTransientRuler,
  resetTransientDraw,
  cacheCurrentLayerSession,
  applyLayersAfterNavigate,
}: PlotNavigationParams) {
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
        cacheMapSet(
          globalDesignByFileRef.current,
          currentFileKey,
          design,
          MAX_CACHED_FILE_DESIGNS,
        );
        cacheCurrentLayerSession(currentFileKey);
      }
      const nextFileKey = String(nextSource.path ?? `${nextSource.index}:${nextSource.name}`);
      const nextDesignForFile = globalDesignLocked
        ? design
        : globalDesignByFileRef.current.get(nextFileKey) ?? canonicalDesign;
      const requestId = nextRenderRequestId();
      const navRanges = rangesLookCompatible(ranges, normalization, analysisUseBark)
        ? ranges
        : defaultRanges;
      const response = await callSidecar<{ state: ApplicationState }>(
        "navigate_interactive_preview",
        {
          index: target,
          options: {
            ranges: navRanges,
            sigma,
            show_ellipse: showEllipse,
            design: nextDesignForFile,
            request_id: requestId,
          },
        },
      );
      const next = response.state;
      if (!aliveRef.current) return;
      currentIndexRef.current = target;
      const nextVowels = next.current_vowels ?? [];
      const nextStateSource = next.sources.find((source) => source.index === target);
      const resolvedNextFileKey = nextStateSource
        ? String(nextStateSource.path ?? `${nextStateSource.index}:${nextStateSource.name}`)
        : nextFileKey;
      const sessionKey = String(target);
      const nextSession = next.plot_session;
      applyLayersAfterNavigate({
        fileKey: nextFileKey,
        vowels: nextVowels,
        sessionKey,
        plotSession: nextSession,
      });
      const sessionNextRanges = nextSession.ranges as Ranges | undefined;
      const nextRanges = sessionNextRanges
        && Object.keys(sessionNextRanges).length === 4
        && rangesLookCompatible(
          sessionNextRanges,
          next.analysis?.normalization ?? null,
          next.analysis?.use_bark_units ?? false,
        )
        ? sessionNextRanges
        : defaultRanges;
      const nextDesign = globalDesignLocked
        ? design
        : globalDesignByFileRef.current.get(resolvedNextFileKey)
          ?? ({ ...canonicalDesign, ...(nextSession.design_settings ?? {}) } as DesignSettings);
      const nextSigma = nextSession.sigma ?? "2";
      const nextShowEllipse = nextSession.show_ellipse ?? true;
      setRanges(nextRanges);
      setDesign(nextDesign);
      cacheMapSet(
        globalDesignByFileRef.current,
        resolvedNextFileKey,
        nextDesign,
        MAX_CACHED_FILE_DESIGNS,
      );
      setSigma(nextSigma);
      setShowEllipse(nextShowEllipse);
      setState(next);
      setMessage(`${nextStateSource?.name ?? nextSource.name ?? "파일"}을 불러왔습니다.`);
    } catch (err) {
      if (aliveRef.current) {
        setMessage(`파일을 이동하지 못했습니다: ${String(err)}`);
        setPreviewLoading(false);
      }
    } finally {
      navigatingRef.current = false;
      if (aliveRef.current) setNavigating(false);
    }
  }, [
    aliveRef,
    analysisUseBark,
    applyLayersAfterNavigate,
    cacheCurrentLayerSession,
    canonicalDesign,
    currentFileKey,
    currentIndexRef,
    defaultRanges,
    design,
    globalDesignByFileRef,
    globalDesignLocked,
    invalidatePendingRender,
    navigatingRef,
    nextRenderRequestId,
    normalization,
    ranges,
    resetTransientDraw,
    resetTransientRuler,
    setDesign,
    setMessage,
    setNavigating,
    setPreviewLoading,
    setRanges,
    setShowEllipse,
    setSigma,
    setState,
    showEllipse,
    sigma,
    sources,
  ]);

  const navigateByPosition = useCallback((position: number) => {
    const target = sources[Math.max(0, Math.min(position, sources.length - 1))];
    if (target) void navigateTo(target.index);
  }, [navigateTo, sources]);

  return { navigateTo, navigateByPosition };
}
