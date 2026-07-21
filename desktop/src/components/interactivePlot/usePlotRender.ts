import { useCallback, useEffect, useRef, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import { callSidecar } from "../../sidecarClient";
import type { DesignSettings, DrawObject, LayerOverrides, LayerVisibility, Ranges } from "./types";

export type InteractiveRenderOverrides = {
  design?: DesignSettings;
  layers?: Record<string, LayerVisibility>;
  ranges?: Ranges;
  sigma?: string;
  showEllipse?: boolean;
  layerOverrides?: LayerOverrides;
  layerOrder?: string[];
  labelOffsets?: Record<string, [number, number]>;
  drawObjects?: DrawObject[];
  /** Shown when this render's preview_ready arrives (overrides the generic status). */
  successMessage?: string;
};

type UsePlotRenderParams = {
  aliveRef: MutableRefObject<boolean>;
  canPlot: boolean;
  setMessage: (message: string) => void;
  ranges: Ranges;
  sigma: string;
  showEllipse: boolean;
  design: DesignSettings;
  layerState: Record<string, LayerVisibility>;
  layerOverrides: LayerOverrides;
  layerOrder: string[];
  lockedLayers: Set<string>;
  currentDrawObjects: DrawObject[];
  unitModeKey: string;
  normalization: string | null;
  defaultRanges: Ranges;
  setDesign: Dispatch<SetStateAction<DesignSettings>>;
  setRanges: Dispatch<SetStateAction<Ranges>>;
};

export function usePlotRender({
  aliveRef,
  canPlot,
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
}: UsePlotRenderParams) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewInfo, setPreviewInfo] = useState("");
  const [previewLoading, setPreviewLoading] = useState(true);
  // A reopened Tauri window must not accept an older preview event from the
  // same sidecar just because its local counter started at zero again.
  const renderRequestRef = useRef(Date.now() * 1000);
  const renderTimerRef = useRef<number | null>(null);
  const pendingSuccessByRequestRef = useRef(new Map<number, string>());
  const unitModeKeyRef = useRef(unitModeKey);
  const previousNormRef = useRef<string | null>(normalization);

  const isStalePreviewRequest = useCallback((requestId: number): boolean => (
    Number.isFinite(requestId) && requestId > 0 && requestId < renderRequestRef.current
  ), []);

  const nextRenderRequestId = useCallback((): number => ++renderRequestRef.current, []);

  const invalidatePendingRender = useCallback(() => {
    ++renderRequestRef.current;
    if (renderTimerRef.current !== null) {
      window.clearTimeout(renderTimerRef.current);
      renderTimerRef.current = null;
    }
  }, []);

  const applyPreviewReady = useCallback(({
    imagePath,
    imageBase64,
    info,
  }: {
    imagePath: string;
    imageBase64: string;
    info: string;
  }) => {
    setPreviewUrl(imagePath ? convertFileSrc(imagePath) : imageBase64 ? `data:image/png;base64,${imageBase64}` : null);
    setPreviewLoading(false);
    setPreviewInfo(info);
  }, []);

  const applyPreviewFailed = useCallback((message: string) => {
    setPreviewLoading(false);
    setMessage(`렌더링 오류: ${message}`);
  }, [setMessage]);

  const applyPreviewCleared = useCallback(() => {
    setPreviewUrl(null);
    setPreviewLoading(false);
    setPreviewInfo("");
  }, []);

  useEffect(() => {
    if (!canPlot) return;
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
  }, [
    aliveRef,
    canPlot,
    currentDrawObjects,
    defaultRanges,
    design,
    layerOrder,
    layerOverrides,
    layerState,
    lockedLayers,
    normalization,
    setDesign,
    setMessage,
    setRanges,
    showEllipse,
    sigma,
    unitModeKey,
  ]);

  const consumePreviewSuccessMessage = useCallback((requestId: number): string | null => {
    const pending = pendingSuccessByRequestRef.current;
    const message = pending.get(requestId) ?? null;
    pending.delete(requestId);
    // Drop stale entries for superseded requests so the map cannot grow forever.
    for (const id of pending.keys()) {
      if (id < requestId) pending.delete(id);
    }
    return message;
  }, []);

  const renderInteractive = async (overrides: InteractiveRenderOverrides = {}) => {
    if (!canPlot) return;
    if (renderTimerRef.current !== null) {
      window.clearTimeout(renderTimerRef.current);
      renderTimerRef.current = null;
    }
    const requestId = ++renderRequestRef.current;
    if (overrides.successMessage) {
      pendingSuccessByRequestRef.current.set(requestId, overrides.successMessage);
    }
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
      pendingSuccessByRequestRef.current.delete(requestId);
      setMessage(`설정을 적용하지 못했습니다: ${String(err)}`);
    }
  };

  const scheduleInteractiveRender = (overrides: InteractiveRenderOverrides = {}) => {
    if (renderTimerRef.current !== null) window.clearTimeout(renderTimerRef.current);
    renderTimerRef.current = window.setTimeout(() => {
      renderTimerRef.current = null;
      if (!aliveRef.current) return;
      void renderInteractive(overrides);
    }, 70);
  };

  useEffect(() => () => {
    if (renderTimerRef.current !== null) {
      window.clearTimeout(renderTimerRef.current);
      renderTimerRef.current = null;
    }
  }, []);

  return {
    previewUrl,
    previewInfo,
    previewLoading,
    setPreviewLoading,
    renderRequestRef,
    renderInteractive,
    scheduleInteractiveRender,
    consumePreviewSuccessMessage,
    isStalePreviewRequest,
    nextRenderRequestId,
    invalidatePendingRender,
    applyPreviewReady,
    applyPreviewFailed,
    applyPreviewCleared,
  };
}
