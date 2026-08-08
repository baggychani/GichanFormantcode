import { useCallback, useEffect, useRef, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { convertFileSrc, invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { ApplicationState, HealthStatus } from "../../../ipc/protocol";
import { callSidecar } from "../../sidecarClient";

type SidecarEvent = {
  event: string;
  payload: Record<string, unknown>;
};

export type MainWorkspaceSession = {
  aliveRef: MutableRefObject<boolean>;
  health: HealthStatus | null;
  state: ApplicationState | null;
  setState: Dispatch<SetStateAction<ApplicationState | null>>;
  previewUrl: string | null;
  previewInfo: string;
  clearPreview: () => void;
  status: string;
  pushStatus: (message: string) => void;
  error: string | null;
  setError: Dispatch<SetStateAction<string | null>>;
  busy: boolean;
  beginBusy: () => void;
  endBusySafe: () => void;
  requestMainPreview: () => void;
};

export function useMainWorkspaceSession(): MainWorkspaceSession {
  const aliveRef = useRef(true);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [state, setState] = useState<ApplicationState | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewInfo, setPreviewInfo] = useState("");
  const [status, setStatus] = useState("분석 엔진을 연결하고 있습니다");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const busyCountRef = useRef(0);
  // Keep ids newer than events left behind by a previous main window.
  const previewRequestRef = useRef(Date.now() * 1000);

  const pushStatus = useCallback((message: string) => setStatus(message), []);

  const beginBusy = useCallback(() => {
    busyCountRef.current += 1;
    setBusy(true);
  }, []);

  const endBusySafe = useCallback(() => {
    busyCountRef.current = Math.max(0, busyCountRef.current - 1);
    if (aliveRef.current) setBusy(busyCountRef.current > 0);
  }, []);

  const requestMainPreview = useCallback(() => {
    void callSidecar("request_preview", { request_id: ++previewRequestRef.current }).catch((err) => {
      if (aliveRef.current) setError(String(err));
    });
  }, []);

  const clearPreview = useCallback(() => {
    setPreviewUrl(null);
    setPreviewInfo("");
  }, []);

  const refresh = useCallback(async () => {
    beginBusy();
    setError(null);
    try {
      const nextHealth = await invoke<HealthStatus>("sidecar_ensure");
      if (!aliveRef.current) return;
      setHealth(nextHealth);
      const nextState = await callSidecar<ApplicationState>("get_state");
      if (!aliveRef.current) return;
      setState(nextState);
      pushStatus(`엔진 연결됨 · GichanFormant ${nextHealth.version}`);
      if (nextState.capabilities.can_plot) requestMainPreview();
    } catch (err) {
      if (!aliveRef.current) return;
      setError(String(err));
      pushStatus("분석 엔진 연결 실패");
    } finally {
      endBusySafe();
    }
  }, [beginBusy, endBusySafe, pushStatus, requestMainPreview]);

  useEffect(() => {
    aliveRef.current = true;
    console.info("[GichanFormant] runtime", {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      tauri: "__TAURI_INTERNALS__" in window,
    });
    let disposed = false;
    let disposeEvent: (() => void) | undefined;
    void listen<SidecarEvent>("sidecar-event", (event) => {
      if (disposed || !aliveRef.current) return;
      const { event: name, payload } = event.payload;
      if (name === "state_changed") {
        const next = payload.state as ApplicationState | undefined;
        if (next) setState(next);
      }
      if (name === "operation_progress") {
        const operation = String(payload.operation ?? "작업");
        const progress = payload.status === "completed" ? "완료" : "처리 중";
        pushStatus(`${operation} ${progress}`);
      }
      if (name === "preview_ready" && (payload.target ?? "main") === "main") {
        const requestId = Number(payload.request_id ?? 0);
        if (Number.isFinite(requestId) && requestId > 0 && requestId < previewRequestRef.current) return;
        const imagePath = String(payload.png_path ?? "");
        const image = String(payload.png_base64 ?? "");
        setPreviewUrl(imagePath ? convertFileSrc(imagePath) : image ? `data:image/png;base64,${image}` : null);
        setPreviewInfo(String(payload.info ?? ""));
      }
      if (name === "preview_cleared" && (payload.target ?? "main") === "main") {
        clearPreview();
      }
      if ((name === "preview_failed" && (payload.target ?? "main") === "main") || name === "operation_failed") {
        setError(String(payload.message ?? "작업을 완료하지 못했습니다"));
      }
    }).then((dispose) => {
      if (disposed) dispose();
      else {
        disposeEvent = dispose;
        // A warm sidecar may finish the first preview immediately.
        void refresh();
      }
    }).catch((err) => {
      if (!disposed && aliveRef.current) setError(String(err));
    });

    return () => {
      disposed = true;
      aliveRef.current = false;
      disposeEvent?.();
    };
  }, [clearPreview, pushStatus, refresh]);

  useEffect(() => {
    if (!error) return;
    const timer = window.setTimeout(() => setError(null), 7000);
    return () => window.clearTimeout(timer);
  }, [error]);

  return {
    aliveRef,
    health,
    state,
    setState,
    previewUrl,
    previewInfo,
    clearPreview,
    status,
    pushStatus,
    error,
    setError,
    busy,
    beginBusy,
    endBusySafe,
    requestMainPreview,
  };
}
