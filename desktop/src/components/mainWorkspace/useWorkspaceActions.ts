import { useCallback, useEffect, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { open, save } from "@tauri-apps/plugin-dialog";
import type { ApplicationState } from "../../../ipc/protocol";
import { callSidecar } from "../../sidecarClient";

type LoadFilesResponse = {
  load_result: {
    success_count: number;
    failed: Array<{ name: string; errors: Array<{ path: string; message: string }> }>;
  };
  state: ApplicationState;
};

type WorkspaceActionsParams = {
  aliveRef: MutableRefObject<boolean>;
  setState: Dispatch<SetStateAction<ApplicationState | null>>;
  setError: Dispatch<SetStateAction<string | null>>;
  beginBusy: () => void;
  endBusySafe: () => void;
  pushStatus: (message: string) => void;
  requestMainPreview: () => void;
  clearPreview: () => void;
  signalSettingsAttention: () => void;
  signalGuideAttention: () => void;
};

const SUPPORTED_DATA_EXTENSIONS = new Set(["txt", "csv", "tsv", "xlsx", "xls"]);

function isSupportedDataPath(path: string) {
  const leaf = path.split(/[\\/]/).pop() ?? path;
  const extension = leaf.includes(".") ? leaf.split(".").pop()?.toLowerCase() : "";
  return extension ? SUPPORTED_DATA_EXTENSIONS.has(extension) : false;
}

export function useWorkspaceActions({
  aliveRef,
  setState,
  setError,
  beginBusy,
  endBusySafe,
  pushStatus,
  requestMainPreview,
  clearPreview,
  signalSettingsAttention,
  signalGuideAttention,
}: WorkspaceActionsParams) {
  const [dragOver, setDragOver] = useState(false);
  const [combinedVisible, setCombinedVisible] = useState(
    () => window.localStorage.getItem("gichanformant-show-combined") === "true",
  );

  const loadPaths = useCallback(async (paths: string[]) => {
    if (!aliveRef.current) return;
    const normalizedPaths = paths.map((path) => String(path).trim()).filter(Boolean);
    if (!normalizedPaths.length) {
      setError("파일 경로를 받지 못했습니다. 파일 선택 버튼으로 추가해 주세요.");
      pushStatus("파일 드롭 실패 · 파일 선택 버튼을 사용해 주세요");
      return;
    }
    const loadablePaths = normalizedPaths.filter(isSupportedDataPath);
    const skippedCount = normalizedPaths.length - loadablePaths.length;
    if (!loadablePaths.length) {
      setError("지원하지 않는 파일 형식입니다. TXT, CSV, TSV, XLSX, XLS 파일만 불러올 수 있습니다.");
      signalGuideAttention();
      return;
    }
    beginBusy();
    setError(null);
    try {
      const response = await callSidecar<LoadFilesResponse>("load_files", { paths: loadablePaths });
      if (!aliveRef.current) return;
      setState(response.state);
      if (response.load_result.success_count > 0 || response.state.capabilities.can_plot) {
        requestMainPreview();
      }
      if (response.load_result.success_count > 0) signalSettingsAttention();
      if (!aliveRef.current) return;
      if (response.load_result.failed.length > 0 || skippedCount > 0) {
        const failedCount = response.load_result.failed.length + skippedCount;
        setError(`${failedCount}개 파일을 건너뛰었습니다. 지원 형식(TXT, CSV, TSV, XLSX, XLS)인지 확인해 주세요.`);
        signalGuideAttention();
      }
      pushStatus(`${response.load_result.success_count}개 소스를 작업 공간에 추가했습니다`);
    } catch (err) {
      if (aliveRef.current) {
        setError(String(err));
        signalGuideAttention();
      }
    } finally {
      endBusySafe();
    }
  }, [
    aliveRef,
    beginBusy,
    endBusySafe,
    pushStatus,
    requestMainPreview,
    setError,
    setState,
    signalGuideAttention,
    signalSettingsAttention,
  ]);

  useEffect(() => {
    let disposed = false;
    let disposeDrag: (() => void) | undefined;
    void getCurrentWebview().onDragDropEvent((event) => {
      if (disposed || !aliveRef.current) return;
      console.info("[GichanFormant] drag-drop event", {
        type: event.payload.type,
        pathCount: event.payload.type === "drop" ? event.payload.paths?.length ?? 0 : undefined,
      });
      if (event.payload.type === "over") {
        setDragOver(true);
        pushStatus("파일을 놓으면 추가됩니다");
      }
      if (event.payload.type === "leave") setDragOver(false);
      if (event.payload.type === "drop") {
        setDragOver(false);
        const paths = Array.isArray(event.payload.paths) ? event.payload.paths : [];
        if (!paths.length) {
          setError("파일 드롭 이벤트는 받았지만 경로가 전달되지 않았습니다. 앱을 관리자 권한 없이 실행하거나 파일 선택 버튼을 사용해 주세요.");
          pushStatus("파일 경로 전달 실패 · 파일 선택 버튼을 사용해 주세요");
          return;
        }
        void loadPaths(paths);
      }
    }).then((dispose) => {
      if (disposed) dispose();
      else disposeDrag = dispose;
    }).catch((err) => {
      if (!disposed && aliveRef.current) setError(String(err));
    });
    return () => {
      disposed = true;
      disposeDrag?.();
    };
  }, [aliveRef, loadPaths, pushStatus, setError]);

  const openFiles = useCallback(async () => {
    setError(null);
    try {
      const selected = await open({
        multiple: true,
        title: "분석할 데이터 선택",
        filters: [{ name: "Data", extensions: ["txt", "csv", "xlsx", "xls", "tsv"] }],
      });
      if (!aliveRef.current) return;
      const paths = Array.isArray(selected) ? selected : selected ? [selected] : [];
      await loadPaths(paths);
    } catch (err) {
      if (aliveRef.current) setError(String(err));
    }
  }, [aliveRef, loadPaths, setError]);

  const openProject = useCallback(async () => {
    setError(null);
    try {
      const selected = await open({
        multiple: false,
        title: "프로젝트 열기",
        filters: [{ name: "GichanFormant Project", extensions: ["gfproj"] }],
      });
      if (!selected || Array.isArray(selected)) return;
      if (!aliveRef.current) return;
      beginBusy();
      try {
        const next = await callSidecar<ApplicationState>("load_project", { path: selected });
        if (aliveRef.current) {
          setState(next);
          requestMainPreview();
          pushStatus("프로젝트를 불러왔습니다");
        }
      } catch (err) {
        if (aliveRef.current) setError(String(err));
      } finally {
        endBusySafe();
      }
    } catch (err) {
      if (aliveRef.current) setError(String(err));
    }
  }, [aliveRef, beginBusy, endBusySafe, pushStatus, requestMainPreview, setError, setState]);

  const resetWorkspace = useCallback(async () => {
    if (!window.confirm("모든 데이터와 설정을 초기화하시겠습니까?")) return;
    setError(null);
    beginBusy();
    try {
      await callSidecar("reset");
      if (aliveRef.current) {
        clearPreview();
        pushStatus("새 작업 공간을 준비했습니다");
      }
    } catch (err) {
      if (aliveRef.current) setError(String(err));
    } finally {
      endBusySafe();
    }
  }, [aliveRef, beginBusy, clearPreview, endBusySafe, pushStatus, setError]);

  const removeFile = useCallback(async (index: number, name: string) => {
    if (!window.confirm(`'${name}' 파일을 삭제하시겠습니까?`)) return;
    setError(null);
    beginBusy();
    try {
      await callSidecar("remove_file", { index });
      if (aliveRef.current) requestMainPreview();
    } catch (err) {
      if (aliveRef.current) setError(String(err));
    } finally {
      endBusySafe();
    }
  }, [aliveRef, beginBusy, endBusySafe, requestMainPreview, setError]);

  const toggleCombinedVisibility = useCallback(() => {
    setCombinedVisible((current) => {
      const next = !current;
      window.localStorage.setItem("gichanformant-show-combined", String(next));
      pushStatus(next ? "Combined 데이터를 표시합니다" : "Combined 데이터를 숨겼습니다");
      return next;
    });
  }, [pushStatus]);

  const saveProject = useCallback(async () => {
    const selected = await save({
      title: "프로젝트 저장",
      defaultPath: "analysis.gfproj",
      filters: [{ name: "GichanFormant Project", extensions: ["gfproj"] }],
    });
    if (!selected) return;
    if (!aliveRef.current) return;
    beginBusy();
    try {
      await callSidecar("save_project", { path: selected });
      if (aliveRef.current) pushStatus("프로젝트를 저장했습니다");
    } catch (err) {
      if (aliveRef.current) setError(String(err));
    } finally {
      endBusySafe();
    }
  }, [aliveRef, beginBusy, endBusySafe, pushStatus, setError]);

  const createPlot = useCallback(async () => {
    setError(null);
    beginBusy();
    try {
      await invoke("open_interactive_plot");
      if (aliveRef.current) pushStatus("새 포먼트 플롯 창을 열었습니다");
    } catch (err) {
      if (aliveRef.current) setError(String(err));
    } finally {
      endBusySafe();
    }
  }, [aliveRef, beginBusy, endBusySafe, pushStatus, setError]);

  return {
    dragOver,
    combinedVisible,
    loadPaths,
    openFiles,
    openProject,
    resetWorkspace,
    removeFile,
    toggleCombinedVisibility,
    saveProject,
    createPlot,
  };
}
