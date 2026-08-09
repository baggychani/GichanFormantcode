import { useCallback, useEffect } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { listen } from "@tauri-apps/api/event";
import type { ApplicationState } from "../../../ipc/protocol";
import { callSidecar } from "../../sidecarClient";
import { smartAxisRanges } from "../../plotUnits";
import {
  BARK_RANGE_DEFAULTS,
  NORM_RANGE_DEFAULTS,
  RANGE_DEFAULTS,
  rangesLookCompatible,
} from "./designDefaults";
import type { Ranges, RulerContext, SidecarEvent } from "./types";

type PreviewReadyInput = {
  imagePath: string;
  imageBase64: string;
  info: string;
};

type PlotWindowSessionParams = {
  aliveRef: MutableRefObject<boolean>;
  navigatingRef: MutableRefObject<boolean>;
  setState: Dispatch<SetStateAction<ApplicationState | null>>;
  setEngineConnected: Dispatch<SetStateAction<boolean>>;
  setMessage: Dispatch<SetStateAction<string>>;
  setPreviewLoading: Dispatch<SetStateAction<boolean>>;
  setRanges: Dispatch<SetStateAction<Ranges>>;
  nextRenderRequestId: () => number;
  isStalePreviewRequest: (requestId: number) => boolean;
  applyPreviewReady: (input: PreviewReadyInput) => void;
  applyPreviewFailed: (message: string) => void;
  applyPreviewCleared: () => void;
  consumePreviewSuccessMessage: (requestId: number) => string | null;
  setRulerContextRef: MutableRefObject<(context: RulerContext | null) => void>;
  applyLegendBoundsRef: MutableRefObject<(
    legendBounds: Record<string, { width_frac: number; height_frac: number }>,
  ) => void>;
  clearLegendDragPreviewRef: MutableRefObject<() => void>;
  clearRulerOnPreviewReadyRef: MutableRefObject<() => void>;
  clearRulerOnPreviewClearedRef: MutableRefObject<() => void>;
};

export function usePlotWindowSession({
  aliveRef,
  navigatingRef,
  setState,
  setEngineConnected,
  setMessage,
  setPreviewLoading,
  setRanges,
  nextRenderRequestId,
  isStalePreviewRequest,
  applyPreviewReady,
  applyPreviewFailed,
  applyPreviewCleared,
  consumePreviewSuccessMessage,
  setRulerContextRef,
  applyLegendBoundsRef,
  clearLegendDragPreviewRef,
  clearRulerOnPreviewReadyRef,
  clearRulerOnPreviewClearedRef,
}: PlotWindowSessionParams) {
  const refresh = useCallback(async () => {
    setPreviewLoading(true);
    try {
      const next = await callSidecar<ApplicationState>("get_state");
      if (!aliveRef.current) return;
      setState(next);
      setEngineConnected(true);
      if (!next.capabilities.can_plot) {
        setPreviewLoading(false);
        return;
      }
      const requestId = nextRenderRequestId();
      const nextNorm = next.analysis?.normalization ?? null;
      const nextPlotType = next.analysis?.type ?? "f1_f2";
      const useBark = next.analysis?.use_bark_units ?? false;
      const bootRanges = nextNorm
        ? NORM_RANGE_DEFAULTS[nextNorm] ?? NORM_RANGE_DEFAULTS.Lobanov
        : smartAxisRanges(nextPlotType, next.analysis, RANGE_DEFAULTS, BARK_RANGE_DEFAULTS);
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
    } catch (err) {
      if (!aliveRef.current) return;
      setEngineConnected(false);
      setMessage(`플롯을 불러오지 못했습니다: ${String(err)}`);
      setPreviewLoading(false);
    }
  }, [
    aliveRef,
    nextRenderRequestId,
    setEngineConnected,
    setMessage,
    setPreviewLoading,
    setRanges,
    setState,
  ]);

  useEffect(() => {
    aliveRef.current = true;
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
        if (legendBounds) applyLegendBoundsRef.current(legendBounds);
        clearLegendDragPreviewRef.current();
        clearRulerOnPreviewReadyRef.current();
        const success = consumePreviewSuccessMessage(requestId);
        if (success) setMessage(success);
      } else if (payload.event === "preview_failed" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (!isStalePreviewRequest(requestId)) {
          applyPreviewFailed(String(payload.payload.message ?? "알 수 없는 오류"));
        }
      } else if (payload.event === "preview_cleared" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (isStalePreviewRequest(requestId)) return;
        applyPreviewCleared();
        clearRulerOnPreviewClearedRef.current();
      } else if (payload.event === "state_changed") {
        const reason = String(payload.payload.reason ?? "");
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
      else {
        disposeEvent = dispose;
        void refresh();
      }
    }).catch((err) => {
      if (!disposed && aliveRef.current) setMessage(String(err));
    });
    return () => {
      disposed = true;
      aliveRef.current = false;
      disposeEvent?.();
    };
  }, [
    aliveRef,
    applyLegendBoundsRef,
    applyPreviewCleared,
    applyPreviewFailed,
    applyPreviewReady,
    clearLegendDragPreviewRef,
    clearRulerOnPreviewClearedRef,
    clearRulerOnPreviewReadyRef,
    consumePreviewSuccessMessage,
    isStalePreviewRequest,
    navigatingRef,
    refresh,
    setEngineConnected,
    setMessage,
    setRulerContextRef,
    setState,
  ]);
}
