import { useCallback, useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, MutableRefObject, PointerEvent as ReactPointerEvent } from "react";
import type { ApplicationState } from "../../../ipc/protocol";
import { callSidecar } from "../../sidecarClient";
import { sortVowels } from "../../vowelSort";
import { cacheLayerSession, clampLayerListHeight } from "./layerCache";
import type { DesignSettings, DrawObject, LayerOverrides, LayerSession, LayerVisibility, Ranges } from "./types";

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
};

type PlotSession = ApplicationState["plot_session"];

type UseLayerSessionParams = {
  currentVowels: string[];
  aliveRef: MutableRefObject<boolean>;
  setMessage: (message: string) => void;
  design: DesignSettings;
  renderInteractive: (overrides?: InteractiveRenderOverrides) => void | Promise<void>;
  scheduleInteractiveRender: (overrides?: InteractiveRenderOverrides) => void;
};

export function useLayerSession({
  currentVowels,
  aliveRef,
  setMessage,
  design,
  renderInteractive,
  scheduleInteractiveRender,
}: UseLayerSessionParams) {
  const [layerState, setLayerState] = useState<Record<string, LayerVisibility>>({});
  const [layerOverrides, setLayerOverrides] = useState<LayerOverrides>({});
  const [layerOrder, setLayerOrder] = useState<string[]>([]);
  const [selectedLayer, setSelectedLayer] = useState("");
  const [selectedLayers, setSelectedLayers] = useState<Set<string>>(new Set());
  const selectionAnchorRef = useRef("");
  const [expandedLayers, setExpandedLayers] = useState<Set<string>>(new Set());
  const [lockedLayers, setLockedLayers] = useState<Set<string>>(new Set());
  const [draggingLayer, setDraggingLayer] = useState<string | null>(null);
  const [dropTarget, setDropTarget] = useState<{ vowel: string; after: boolean } | null>(null);
  const [layerListHeight, setLayerListHeight] = useState(() =>
    clampLayerListHeight(Math.min(460, Math.max(360, Math.round(window.innerHeight * 0.46)))),
  );

  const layerRowRefs = useRef(new Map<string, HTMLDivElement>());
  const layerListRef = useRef<HTMLDivElement | null>(null);
  const layerOrderRef = useRef<string[]>([]);
  const dragStartOrderRef = useRef<string[]>([]);
  const dragCandidateOrderRef = useRef<string[]>([]);
  const draggedLayersRef = useRef<string[]>([]);
  const draggingLayerRef = useRef<string | null>(null);
  const dragMovedRef = useRef(false);
  const dragPointerYRef = useRef(0);
  const dragScrollFrameRef = useRef<number | null>(null);
  const flipFrameRef = useRef<number | null>(null);
  const dragListenersRef = useRef<{
    move: (event: PointerEvent) => void;
    up: (event: PointerEvent) => void;
    cancel: (event: PointerEvent) => void;
  } | null>(null);
  const resizeRef = useRef<{ startY: number; startHeight: number } | null>(null);
  const layerSessionsRef = useRef(new Map<string, LayerSession>());

  const selectedOverride = selectedLayer ? layerOverrides[selectedLayer] ?? {} : {};
  const selectedLocked = selectedLayer ? lockedLayers.has(selectedLayer) : false;
  const effective = <K extends keyof DesignSettings>(key: K): DesignSettings[K] =>
    (selectedOverride[key] ?? design[key]) as DesignSettings[K];

  const removeLayerDragListeners = () => {
    const listeners = dragListenersRef.current;
    if (!listeners) return;
    window.removeEventListener("pointermove", listeners.move);
    window.removeEventListener("pointerup", listeners.up);
    window.removeEventListener("pointercancel", listeners.cancel);
    dragListenersRef.current = null;
  };

  useEffect(() => () => {
    removeLayerDragListeners();
    if (dragScrollFrameRef.current !== null) cancelAnimationFrame(dragScrollFrameRef.current);
    if (flipFrameRef.current !== null) cancelAnimationFrame(flipFrameRef.current);
    dragScrollFrameRef.current = null;
    flipFrameRef.current = null;
    draggingLayerRef.current = null;
  }, []);

  useEffect(() => {
    const clampOnResize = () => setLayerListHeight((height) => clampLayerListHeight(height));
    window.addEventListener("resize", clampOnResize);
    return () => window.removeEventListener("resize", clampOnResize);
  }, []);

  const cacheCurrentLayerSession = useCallback((fileKey: string) => {
    cacheLayerSession(layerSessionsRef.current, fileKey, {
      state: { ...layerState },
      overrides: { ...layerOverrides },
      locked: new Set(lockedLayers),
      order: [...layerOrderRef.current],
      expanded: new Set(expandedLayers),
    });
  }, [expandedLayers, layerOverrides, layerState, lockedLayers]);

  const hydrateLayersForFile = useCallback(({
    fileKey,
    vowels,
    sessionKey,
    plotSession,
  }: {
    fileKey: string;
    vowels: string[];
    sessionKey: string;
    plotSession: PlotSession | undefined;
  }) => {
    const defaultOrder = sortVowels(vowels);
    const cached = fileKey ? layerSessionsRef.current.get(fileKey) : undefined;
    const sessionState = plotSession?.vowel_filter_state_by_file?.[sessionKey] as Record<string, LayerVisibility> | undefined;
    const sessionOverrides = plotSession?.layer_design_overrides_by_file?.[sessionKey] as LayerOverrides | undefined;
    const sessionLocked = plotSession?.layer_locked_vowels_by_file?.[sessionKey];
    const sessionOrder = plotSession?.layer_order_by_file?.[sessionKey];
    setLayerState(sessionState ?? cached?.state ?? Object.fromEntries(vowels.map((vowel) => [vowel, "ON" as LayerVisibility])));
    setLayerOverrides(sessionOverrides ?? cached?.overrides ?? {});
    setSelectedLayer(defaultOrder[0] ?? "");
    setSelectedLayers(new Set(defaultOrder[0] ? [defaultOrder[0]] : []));
    selectionAnchorRef.current = defaultOrder[0] ?? "";
    setExpandedLayers(cached?.expanded ? new Set(cached.expanded) : new Set());
    setLockedLayers(sessionLocked ? new Set(sessionLocked) : cached ? new Set(cached.locked) : new Set());
    const storedOrder = sessionOrder ?? cached?.order ?? layerOrderRef.current;
    const sameSet = storedOrder.length === defaultOrder.length && storedOrder.every((vowel) => defaultOrder.includes(vowel));
    const nextOrder = sameSet ? storedOrder : defaultOrder;
    layerOrderRef.current = nextOrder;
    setLayerOrder(nextOrder);
  }, []);

  const applyLayersAfterNavigate = useCallback(({
    fileKey,
    vowels,
    sessionKey,
    plotSession,
  }: {
    fileKey: string;
    vowels: string[];
    sessionKey: string;
    plotSession: PlotSession;
  }) => {
    const cached = fileKey ? layerSessionsRef.current.get(fileKey) : undefined;
    const defaultOrder = sortVowels(vowels);
    const previousOrder = layerOrderRef.current;
    const storedOrder = plotSession.layer_order_by_file?.[sessionKey] ?? cached?.order ?? previousOrder;
    const storedSameSet = storedOrder.length === defaultOrder.length && storedOrder.every((vowel) => defaultOrder.includes(vowel));
    const nextOrder = storedSameSet ? storedOrder : defaultOrder;
    const nextLayers = (plotSession.vowel_filter_state_by_file?.[sessionKey] as Record<string, LayerVisibility> | undefined)
      ?? cached?.state
      ?? Object.fromEntries(vowels.map((vowel) => [vowel, "ON" as LayerVisibility]));
    const nextOverrides = (plotSession.layer_design_overrides_by_file?.[sessionKey] as LayerOverrides | undefined)
      ?? cached?.overrides
      ?? {};
    const nextExpanded = cached?.expanded ? new Set(cached.expanded) : new Set<string>();
    layerOrderRef.current = nextOrder;
    setLayerOrder(nextOrder);
    setLayerState(nextLayers);
    setLayerOverrides(nextOverrides);
    setExpandedLayers(nextExpanded);
    const nextLocked = new Set(plotSession.layer_locked_vowels_by_file?.[sessionKey] ?? cached?.locked ?? []);
    setLockedLayers(nextLocked);
  }, []);

  const resetLayers = useCallback((vowels: string[]) => {
    const nextLayers = Object.fromEntries(vowels.map((vowel) => [vowel, "ON" as LayerVisibility]));
    setLayerState(nextLayers);
    setLayerOverrides({});
    return nextLayers;
  }, []);

  const selectLayer = (vowel: string, event: ReactMouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    const order = layerOrderRef.current;
    const anchor = selectionAnchorRef.current;
    const withRange = event.shiftKey && anchor && order.includes(anchor);
    if (withRange) {
      const start = order.indexOf(anchor);
      const end = order.indexOf(vowel);
      const range = order.slice(Math.min(start, end), Math.max(start, end) + 1);
      setSelectedLayers((previous) => {
        if (event.ctrlKey || event.metaKey) return new Set([...previous, ...range]);
        return new Set(range);
      });
      setSelectedLayer(vowel);
      return;
    }
    if (event.ctrlKey || event.metaKey) {
      setSelectedLayers((previous) => {
        const next = new Set(previous);
        if (next.has(vowel)) next.delete(vowel);
        else next.add(vowel);
        const nextPrimary = next.has(vowel) ? vowel : [...next][0] ?? "";
        setSelectedLayer(nextPrimary);
        if (next.size) selectionAnchorRef.current = nextPrimary;
        return next;
      });
      return;
    }
    if (selectedLayer === vowel) {
      setSelectedLayer("");
      setSelectedLayers(new Set());
      selectionAnchorRef.current = "";
      return;
    }
    setSelectedLayers(new Set([vowel]));
    setSelectedLayer(vowel);
    selectionAnchorRef.current = vowel;
  };

  const updateLayerDesign = (patch: Partial<DesignSettings>) => {
    if (!selectedLayer || selectedLocked) return;
    const next = { ...layerOverrides, [selectedLayer]: { ...selectedOverride, ...patch } };
    setLayerOverrides(next);
    setExpandedLayers((previous) => new Set(previous).add(selectedLayer));
    scheduleInteractiveRender({ layerOverrides: next });
  };

  const toggleLayerEye = (vowel: string) => {
    const nextState: LayerVisibility = (layerState[vowel] ?? "ON") === "OFF" ? "ON" : "OFF";
    const next = { ...layerState, [vowel]: nextState };
    setLayerState(next);
    void renderInteractive({ layers: next });
  };

  const toggleLayerSemi = (vowel: string) => {
    const nextState: LayerVisibility = (layerState[vowel] ?? "ON") === "SEMI" ? "ON" : "SEMI";
    const next = { ...layerState, [vowel]: nextState };
    setLayerState(next);
    void renderInteractive({ layers: next });
  };

  const toggleAllLayerEyes = () => {
    const allOff = currentVowels.length > 0 && currentVowels.every((vowel) => layerState[vowel] === "OFF");
    const next = { ...layerState };
    currentVowels.forEach((vowel) => { next[vowel] = allOff ? "ON" : "OFF"; });
    setLayerState(next);
    void renderInteractive({ layers: next });
  };

  const toggleAllLayerSemi = () => {
    const visible = currentVowels.filter((vowel) => layerState[vowel] !== "OFF");
    const allSemi = visible.length > 0 && visible.every((vowel) => layerState[vowel] === "SEMI");
    const next = { ...layerState };
    visible.forEach((vowel) => { next[vowel] = allSemi ? "ON" : "SEMI"; });
    setLayerState(next);
    void renderInteractive({ layers: next });
  };

  const toggleLock = async (vowel: string) => {
    const previous = new Set(lockedLayers);
    const next = new Set(previous);
    if (next.has(vowel)) next.delete(vowel);
    else next.add(vowel);
    setLockedLayers(next);
    try {
      await callSidecar("update_interactive_session", { options: { locked_layers: [...next] } });
    } catch (err) {
      setLockedLayers(previous);
      setMessage(`레이어 잠금 상태를 저장하지 못했습니다. ${String(err)}`);
    }
  };

  const resetSelectedLayer = () => {
    if (!selectedLayer || selectedLocked) return;
    const next = { ...layerOverrides };
    delete next[selectedLayer];
    setLayerOverrides(next);
    setExpandedLayers((previous) => {
      const expanded = new Set(previous);
      expanded.delete(selectedLayer);
      return expanded;
    });
    void renderInteractive({ layerOverrides: next });
  };

  const removeLayerEffect = (vowel: string, key: keyof DesignSettings) => {
    if (lockedLayers.has(vowel)) return;
    const current = layerOverrides[vowel];
    if (!current || !(key in current)) return;
    const nextLayer = { ...current };
    delete nextLayer[key];
    const next = { ...layerOverrides };
    if (Object.keys(nextLayer).length) next[vowel] = nextLayer;
    else delete next[vowel];
    setLayerOverrides(next);
    if (!Object.keys(nextLayer).length) {
      setExpandedLayers((previous) => {
        const expanded = new Set(previous);
        expanded.delete(vowel);
        return expanded;
      });
    }
    void renderInteractive({ layerOverrides: next });
  };

  const cancelFlipFrame = () => {
    if (flipFrameRef.current !== null) cancelAnimationFrame(flipFrameRef.current);
    flipFrameRef.current = null;
  };

  const animateLayerOrder = (nextOrder: string[]) => {
    cancelFlipFrame();
    const previousTops = new Map<string, number>();
    layerRowRefs.current.forEach((element, vowel) => previousTops.set(vowel, element.offsetTop));
    layerOrderRef.current = nextOrder;
    setLayerOrder(nextOrder);
    flipFrameRef.current = requestAnimationFrame(() => {
      flipFrameRef.current = null;
      if (!aliveRef.current) return;
      layerRowRefs.current.forEach((element, vowel) => {
        element.getAnimations().forEach((animation) => animation.cancel());
        if (vowel === draggingLayerRef.current) return;
        const previousTop = previousTops.get(vowel);
        if (previousTop === undefined) return;
        const delta = previousTop - element.offsetTop;
        if (Math.abs(delta) < 1) return;
        element.animate(
          [{ transform: `translateY(${delta}px)` }, { transform: "translateY(0)" }],
          { duration: 210, easing: "cubic-bezier(.22,.8,.24,1)" },
        );
      });
    });
  };

  const stopLayerDragScroll = () => {
    if (dragScrollFrameRef.current !== null) cancelAnimationFrame(dragScrollFrameRef.current);
    dragScrollFrameRef.current = null;
  };

  const repositionDraggedLayer = (clientY: number) => {
    const source = draggingLayerRef.current;
    const list = layerListRef.current;
    if (!source || !list) return;
    const dragged = draggedLayersRef.current.length ? draggedLayersRef.current : [source];
    const order = layerOrderRef.current;
    const without = order.filter((vowel) => !dragged.includes(vowel));
    const listBounds = list.getBoundingClientRect();
    const pointerY = clientY - listBounds.top + list.scrollTop;
    const visualRows = without
      .map((vowel) => ({ vowel, element: layerRowRefs.current.get(vowel) }))
      .filter((row): row is { vowel: string; element: HTMLDivElement } => Boolean(row.element))
      .sort((left, right) => left.element.offsetTop - right.element.offsetTop);
    const visualTarget = visualRows.find(
      ({ element }) => pointerY < element.offsetTop + element.offsetHeight / 2,
    );
    const anchor = visualTarget?.vowel ?? visualRows[visualRows.length - 1]?.vowel;
    let insertAt = anchor ? without.indexOf(anchor) : without.length;
    if (!visualTarget && anchor) insertAt += 1;
    insertAt = Math.max(0, Math.min(without.length, insertAt));

    if (anchor) {
      setDropTarget({ vowel: anchor, after: !visualTarget });
    } else {
      setDropTarget(null);
    }

    const next = [...without];
    next.splice(insertAt, 0, ...dragged);
    dragCandidateOrderRef.current = next;
    dragMovedRef.current = next.join("\u0000") !== dragStartOrderRef.current.join("\u0000");
  };

  const commitLayerDrag = (event: { pointerId?: number; preventDefault?: () => void }) => {
    if (!draggingLayerRef.current) return;
    event.preventDefault?.();
    const moved = dragMovedRef.current;
    const committedOrder = [...dragCandidateOrderRef.current];
    draggingLayerRef.current = null;
    dragMovedRef.current = false;
    stopLayerDragScroll();
    cancelFlipFrame();
    removeLayerDragListeners();
    draggedLayersRef.current = [];
    if (moved) {
      animateLayerOrder(committedOrder);
      setMessage("레이어 순서를 플롯에 반영했습니다.");
      void renderInteractive({ layerOrder: committedOrder });
    }
    setDraggingLayer(null);
    setDropTarget(null);
  };

  const cancelLayerDrag = () => {
    cancelFlipFrame();
    draggingLayerRef.current = null;
    stopLayerDragScroll();
    dragMovedRef.current = false;
    removeLayerDragListeners();
    draggedLayersRef.current = [];
    setDraggingLayer(null);
    setDropTarget(null);
  };

  const beginLayerDrag = (event: ReactPointerEvent<HTMLButtonElement>, vowel: string) => {
    if (event.button !== 0) return;
    event.preventDefault();
    stopLayerDragScroll();
    cancelFlipFrame();
    dragStartOrderRef.current = [...layerOrderRef.current];
    dragCandidateOrderRef.current = [...layerOrderRef.current];
    draggedLayersRef.current = selectedLayers.has(vowel) && selectedLayers.size > 1
      ? layerOrderRef.current.filter((item) => selectedLayers.has(item))
      : [vowel];
    draggingLayerRef.current = vowel;
    dragMovedRef.current = false;
    dragPointerYRef.current = event.clientY;
    setDraggingLayer(vowel);
    const pointerId = event.pointerId;
    const onMove = (nativeEvent: PointerEvent) => {
      if (nativeEvent.pointerId !== pointerId || !draggingLayerRef.current) return;
      nativeEvent.preventDefault();
      dragPointerYRef.current = nativeEvent.clientY;
      repositionDraggedLayer(nativeEvent.clientY);
    };
    const onUp = (nativeEvent: PointerEvent) => {
      if (nativeEvent.pointerId !== pointerId) return;
      nativeEvent.preventDefault();
      commitLayerDrag(nativeEvent);
    };
    const onCancel = (nativeEvent: PointerEvent) => {
      if (nativeEvent.pointerId !== pointerId) return;
      cancelLayerDrag();
    };
    dragListenersRef.current = { move: onMove, up: onUp, cancel: onCancel };
    window.addEventListener("pointermove", onMove, { passive: false });
    window.addEventListener("pointerup", onUp, { passive: false });
    window.addEventListener("pointercancel", onCancel);
    const autoScroll = () => {
      const list = layerListRef.current;
      if (!aliveRef.current || !draggingLayerRef.current || !list) {
        dragScrollFrameRef.current = null;
        return;
      }
      const bounds = list.getBoundingClientRect();
      const edge = 34;
      const pointerY = dragPointerYRef.current;
      const speed = pointerY < bounds.top + edge
        ? -Math.min(14, Math.max(2, (bounds.top + edge - pointerY) * 0.32))
        : pointerY > bounds.bottom - edge
          ? Math.min(14, Math.max(2, (pointerY - (bounds.bottom - edge)) * 0.32))
          : 0;
      if (speed) {
        const previousScroll = list.scrollTop;
        list.scrollTop += speed;
        if (list.scrollTop !== previousScroll) repositionDraggedLayer(pointerY);
      }
      dragScrollFrameRef.current = requestAnimationFrame(autoScroll);
    };
    dragScrollFrameRef.current = requestAnimationFrame(autoScroll);
  };

  // Keep the local handler for browsers that continue dispatching to the
  // handle, while the window listeners cover pointer movement outside it.
  const moveLayerDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (!draggingLayerRef.current) return;
    event.preventDefault();
    dragPointerYRef.current = event.clientY;
    repositionDraggedLayer(event.clientY);
  };

  const resetLayerOrder = () => {
    const next = sortVowels(currentVowels);
    animateLayerOrder(next);
    setMessage("레이어 순서를 기본 순서로 되돌렸습니다.");
    void renderInteractive({ layerOrder: next });
  };

  const moveLayerByStep = (vowel: string, direction: -1 | 1) => {
    const order = [...layerOrderRef.current];
    const from = order.indexOf(vowel);
    const to = from + direction;
    if (from < 0 || to < 0 || to >= order.length) return;
    [order[from], order[to]] = [order[to], order[from]];
    animateLayerOrder(order);
    setMessage(`${vowel} 레이어 순서를 이동했습니다.`);
    void renderInteractive({ layerOrder: order });
  };

  const beginLayerPanelResize = (event: ReactPointerEvent<HTMLDivElement>) => {
    resizeRef.current = { startY: event.clientY, startHeight: layerListHeight };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const resizeLayerPanels = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!resizeRef.current || !event.currentTarget.hasPointerCapture(event.pointerId)) return;
    const next = resizeRef.current.startHeight + (resizeRef.current.startY - event.clientY);
    setLayerListHeight(clampLayerListHeight(next));
  };

  const cancelLayerPanelResize = () => {
    resizeRef.current = null;
  };

  const endLayerPanelResize = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    resizeRef.current = null;
  };

  return {
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
    selectedOverride,
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
  };
}
