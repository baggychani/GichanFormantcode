import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { convertFileSrc, invoke } from "@tauri-apps/api/core";
import { emit, listen } from "@tauri-apps/api/event";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { open, save } from "@tauri-apps/plugin-dialog";
import {
  BookOpen,
  ChevronRight,
  Layers3,
  Loader2,
  Moon,
  Sun,
  X,
} from "lucide-react";
import type { ApplicationState, HealthStatus } from "../../../ipc/protocol";
import { callSidecar } from "../../sidecarClient";
import appIconUrl from "../../../../assets/icon.ico";
import { DataGuide } from "../DataGuide";
import { SupportPanel } from "../../SupportPanel";
import { SUPPORT_LABEL, SUPPORT_TITLE } from "../../support";
import { AnalysisSettingsPanel } from "./AnalysisSettingsPanel";
import { PreviewStage } from "./PreviewStage";
import { PLOT_TYPES, type PlotType } from "./plotTypes";
import { SourceSidebar } from "./SourceSidebar";

type SidecarEvent = {
  event: string;
  payload: Record<string, unknown>;
};

type LoadFilesResponse = {
  load_result: {
    success_count: number;
    failed: Array<{ name: string; errors: Array<{ path: string; message: string }> }>;
  };
  state: ApplicationState;
};

const SUPPORTED_DATA_EXTENSIONS = new Set(["txt", "csv", "tsv", "xlsx", "xls"]);

const isSupportedDataPath = (path: string) => {
  const leaf = path.split(/[\\/]/).pop() ?? path;
  const extension = leaf.includes(".") ? leaf.split(".").pop()?.toLowerCase() : "";
  return extension ? SUPPORTED_DATA_EXTENSIONS.has(extension) : false;
};

type Theme = "dark" | "light";

export function MainWorkspace() {
  const aliveRef = useRef(true);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [state, setState] = useState<ApplicationState | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewInfo, setPreviewInfo] = useState("");
  const [status, setStatus] = useState("분석 엔진을 연결하고 있습니다");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const busyCountRef = useRef(0);
  // Keep request ids newer than events left behind by a previous window.
  const previewRequestRef = useRef(Date.now() * 1000);
  const [dragOver, setDragOver] = useState(false);
  const [settingsAttention, setSettingsAttention] = useState(false);
  const settingsAttentionTimersRef = useRef<number[]>([]);
  const [combinedVisible, setCombinedVisible] = useState(() => {
    const saved = window.localStorage.getItem("gichanformant-show-combined");
    return saved === "true";
  });
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [guideOpen, setGuideOpen] = useState(false);
  const [supportOpen, setSupportOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = window.localStorage.getItem("gichanformant-theme");
    const initialTheme =
      saved === "dark" || saved === "light"
        ? saved
        : window.matchMedia("(prefers-color-scheme: light)").matches
          ? "light"
          : "dark";
    document.documentElement.dataset.theme = initialTheme;
    document.documentElement.style.colorScheme = initialTheme;
    return initialTheme;
  });

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const syncSystemTheme = (event: MediaQueryListEvent) => {
      if (window.localStorage.getItem("gichanformant-theme")) return;
      setTheme(event.matches ? "dark" : "light");
    };
    media.addEventListener?.("change", syncSystemTheme);
    return () => media.removeEventListener?.("change", syncSystemTheme);
  }, []);

  const analysis = state?.analysis;
  const sources = state?.sources ?? [];
  const realSources = sources.filter((source) => !source.is_combined);
  const hasFiles = realSources.length > 0;
  /** PySide workspace_service._has_f3_all: every real file must expose F3. */
  const hasF3 = hasFiles && realSources.every((source) => source.has_f3);
  /** PySide all_real_items_pre_lobanov → Lobanov combo locked. */
  const preLobanovLocked = hasFiles && realSources.every((source) => source.is_pre_lobanov);
  const canPlot = state?.capabilities.can_plot ?? false;
  const plotType = (analysis?.type as PlotType) || "f1_f2";
  const derivedPlotUnsupportedNorm =
    plotType === "f1_f2_minus_f1" || plotType === "f1_f2_prime_minus_f1";
  const activePlot =
    PLOT_TYPES.find((plot) => plot.id === plotType) ?? PLOT_TYPES[0];

  const settingsSummary = useMemo(() => {
    if (!analysis) return "분석 설정 대기";
    const outlier = analysis.outlier_mode
      ? analysis.outlier_mode === "tukey_iqr"
        ? "Tukey"
        : "2σ"
      : "원본 데이터";
    const norm = analysis.normalization ?? "정규화 없음";
    return `${activePlot.short} · ${outlier} · ${norm}`;
  }, [activePlot.short, analysis]);

  const pushStatus = useCallback((message: string) => {
    setStatus(message);
  }, []);

  const beginBusy = useCallback(() => {
    busyCountRef.current += 1;
    setBusy(true);
  }, []);

  // Always balance beginBusy — even if the component unmounted mid-request
  // (StrictMode remount / window close). Only skip React state updates when dead.
  const endBusySafe = useCallback(() => {
    busyCountRef.current = Math.max(0, busyCountRef.current - 1);
    if (aliveRef.current) setBusy(busyCountRef.current > 0);
  }, []);

  const signalSettingsAttention = useCallback(() => {
    settingsAttentionTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    setSettingsAttention(false);
    const startTimer = window.setTimeout(() => setSettingsAttention(true), 280);
    const endTimer = window.setTimeout(() => setSettingsAttention(false), 1980);
    settingsAttentionTimersRef.current = [startTimer, endTimer];
  }, []);

  useEffect(() => () => {
    settingsAttentionTimersRef.current.forEach((timer) => window.clearTimeout(timer));
  }, []);

  const requestMainPreview = useCallback(() => {
    void callSidecar("request_preview", { request_id: ++previewRequestRef.current }).catch((err) => {
      if (aliveRef.current) setError(String(err));
    });
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
      if (nextState.capabilities.can_plot) {
        requestMainPreview();
      }
    } catch (err) {
      if (!aliveRef.current) return;
      setError(String(err));
      pushStatus("분석 엔진 연결 실패");
    } finally {
      endBusySafe();
    }
  }, [beginBusy, endBusySafe, pushStatus, requestMainPreview]);

  const loadPaths = useCallback(
    async (paths: string[]) => {
      const normalizedPaths = paths
        .map((path) => String(path).trim())
        .filter(Boolean);
      if (!normalizedPaths.length) {
        setError("파일 경로를 받지 못했습니다. 파일 선택 버튼으로 추가해 주세요.");
        pushStatus("파일 드롭 실패 · 파일 선택 버튼을 사용해 주세요");
        return;
      }
      const loadablePaths = normalizedPaths.filter(isSupportedDataPath);
      const skippedCount = normalizedPaths.length - loadablePaths.length;
      if (!loadablePaths.length) {
        setError("지원하지 않는 파일 형식입니다. TXT, CSV, TSV, XLSX, XLS 파일만 불러올 수 있습니다.");
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
        if (response.load_result.success_count > 0) {
          signalSettingsAttention();
        }
        if (!aliveRef.current) return;
        if (response.load_result.failed.length > 0 || skippedCount > 0) {
          const failedCount = response.load_result.failed.length + skippedCount;
          setError(`${failedCount}개 파일을 건너뛰었습니다. 지원 형식(TXT, CSV, TSV, XLSX, XLS)인지 확인해 주세요.`);
        }
        pushStatus(`${response.load_result.success_count}개 소스를 작업 공간에 추가했습니다`);
      } catch (err) {
        if (aliveRef.current) setError(String(err));
      } finally {
        endBusySafe();
      }
    },
    [beginBusy, endBusySafe, pushStatus, requestMainPreview, signalSettingsAttention],
  );

  useEffect(() => {
    aliveRef.current = true;
    console.info("[GichanFormant] runtime", {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      tauri: "__TAURI_INTERNALS__" in window,
    });
    void refresh();
    let disposed = false;
    let disposeEvent: (() => void) | undefined;
    let disposeDrag: (() => void) | undefined;
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
        setPreviewUrl(null);
        setPreviewInfo("");
      }
      if ((name === "preview_failed" && (payload.target ?? "main") === "main") || name === "operation_failed") {
        setError(String(payload.message ?? "작업을 완료하지 못했습니다"));
      }
    }).then((dispose) => {
      if (disposed) dispose();
      else disposeEvent = dispose;
    }).catch((err) => {
      if (!disposed && aliveRef.current) setError(String(err));
    });

    void getCurrentWebview()
      .onDragDropEvent((event) => {
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
      })
      .then((fn) => {
        if (disposed) fn();
        else disposeDrag = fn;
      })
      .catch((err) => {
        if (!disposed && aliveRef.current) setError(String(err));
      });

    return () => {
      disposed = true;
      aliveRef.current = false;
      disposeEvent?.();
      disposeDrag?.();
    };
  }, [refresh, loadPaths, pushStatus]);

  useEffect(() => {
    if (!error) return;
    const timer = window.setTimeout(() => setError(null), 7000);
    return () => window.clearTimeout(timer);
  }, [error]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    // Do not write localStorage here — only the explicit toggle persists a preference,
    // so OS theme changes keep applying until the user picks one.
    void emit("gichan-theme", theme);
  }, [theme]);

  const toggleThemePreference = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    window.localStorage.setItem("gichanformant-theme", next);
    setTheme(next);
  };

  const openFiles = async () => {
    setError(null);
    try {
      const selected = await open({
        multiple: true,
        title: "분석할 데이터 선택",
        filters: [
          { name: "Data", extensions: ["txt", "csv", "xlsx", "xls", "tsv"] },
        ],
      });
      const paths = Array.isArray(selected)
        ? selected
        : selected
          ? [selected]
          : [];
      await loadPaths(paths);
    } catch (err) {
      setError(String(err));
    }
  };

  const openProject = async () => {
    setError(null);
    try {
      const selected = await open({
        multiple: false,
        title: "프로젝트 열기",
        filters: [{ name: "GichanFormant Project", extensions: ["gfproj"] }],
      });
      if (!selected || Array.isArray(selected)) return;
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
      setError(String(err));
    }
  };

  const resetWorkspace = async () => {
    if (!window.confirm("모든 데이터와 설정을 초기화하시겠습니까?")) return;
    setError(null);
    beginBusy();
    try {
      await callSidecar("reset");
      setPreviewUrl(null);
      setPreviewInfo("");
      pushStatus("새 작업 공간을 준비했습니다");
    } catch (err) {
      setError(String(err));
    } finally {
      endBusySafe();
    }
  };

  const removeFile = async (index: number, name: string) => {
    if (!window.confirm(`'${name}' 파일을 삭제하시겠습니까?`)) return;
    setError(null);
    beginBusy();
    try {
      await callSidecar("remove_file", { index });
      requestMainPreview();
    } catch (err) {
      setError(String(err));
    } finally {
      endBusySafe();
    }
  };

  const toggleCombinedVisibility = () => {
    const next = !combinedVisible;
    setCombinedVisible(next);
    window.localStorage.setItem("gichanformant-show-combined", String(next));
    pushStatus(next ? "Combined 데이터를 표시합니다" : "Combined 데이터를 숨겼습니다");
  };

  const settingsPatchRef = useRef<Record<string, unknown>>({});
  const settingsTimerRef = useRef<number | null>(null);
  /** PySide `_integer_bark_scale_backup` — restore when Bark display turns off. */
  const barkScaleBackupRef = useRef<{ f1_scale: string; f2_scale: string } | null>(null);
  useEffect(() => () => {
    if (settingsTimerRef.current !== null) window.clearTimeout(settingsTimerRef.current);
  }, []);
  const patchSettings = (patch: Record<string, unknown>) => {
    setError(null);
    settingsPatchRef.current = { ...settingsPatchRef.current, ...patch };
    if (settingsTimerRef.current !== null) window.clearTimeout(settingsTimerRef.current);
    settingsTimerRef.current = window.setTimeout(() => {
      const settings = settingsPatchRef.current;
      settingsPatchRef.current = {};
      settingsTimerRef.current = null;
      if (!aliveRef.current) return;
      void callSidecar<ApplicationState>("set_analysis_settings", { settings })
        .then((next) => { if (aliveRef.current) setState(next); })
        .catch((err) => { if (aliveRef.current) setError(String(err)); });
    }, 90);
  };

  const barkDisplayLocked = Boolean(analysis?.use_bark_units) && !analysis?.normalization;
  const axisControlsLocked = Boolean(analysis?.normalization) || preLobanovLocked;
  const scaleButtonsLocked = axisControlsLocked || barkDisplayLocked;
  const toggleBarkDisplayUnits = () => {
    if (axisControlsLocked) return;
    const turningOn = !(analysis?.use_bark_units ?? false);
    if (turningOn) {
      barkScaleBackupRef.current = {
        f1_scale: analysis?.f1_scale ?? "linear",
        f2_scale: analysis?.f2_scale ?? "bark",
      };
      // Same as PySide get_f*_scale while checkbox is on.
      void patchSettings({ use_bark_units: true, f1_scale: "bark", f2_scale: "bark" });
      return;
    }
    const backup = barkScaleBackupRef.current;
    barkScaleBackupRef.current = null;
    void patchSettings({
      use_bark_units: false,
      f1_scale: backup?.f1_scale ?? "linear",
      f2_scale: backup?.f2_scale ?? "bark",
    });
  };

  // PySide toggle_f3_options: drop F3-only plot types when F3 is unavailable.
  useEffect(() => {
    if (!analysis) return;
    const needsF3 = plotType === "f1_f3" || plotType === "f1_f2_prime" || plotType === "f1_f2_prime_minus_f1";
    if (needsF3 && !hasF3) void patchSettings({ type: "f1_f2" });
  }, [analysis, hasF3, plotType]);

  // PySide: derived plots clear normalization; pre-Lobanov forces Lobanov.
  useEffect(() => {
    if (!analysis || !hasFiles) return;
    if (preLobanovLocked && analysis.normalization !== "Lobanov") {
      void patchSettings({ normalization: "Lobanov" });
      return;
    }
    if (derivedPlotUnsupportedNorm && analysis.normalization) {
      void patchSettings({ normalization: null });
    }
  }, [analysis, derivedPlotUnsupportedNorm, hasFiles, preLobanovLocked]);

  const saveProject = async () => {
    const selected = await save({
      title: "프로젝트 저장",
      defaultPath: "analysis.gfproj",
      filters: [{ name: "GichanFormant Project", extensions: ["gfproj"] }],
    });
    if (!selected) return;
    beginBusy();
    try {
      await callSidecar("save_project", { path: selected });
      pushStatus("프로젝트를 저장했습니다");
    } catch (err) {
      setError(String(err));
    } finally {
      endBusySafe();
    }
  };

  const createPlot = async () => {
    setError(null);
    beginBusy();
    try {
      await invoke("open_interactive_plot");
      pushStatus("새 포먼트 플롯 창을 열었습니다");
    } catch (err) {
      setError(String(err));
    } finally {
      endBusySafe();
    }
  };

  const previewLines = previewInfo.split("\n").filter(Boolean);

  return (
    <div
      className={`workbench ${inspectorOpen ? "" : "settings-hidden"} ${dragOver ? "is-dragging" : ""}`}
    >
      <header className="app-header">
        <div className="app-identity">
          <img className="brand-icon" src={appIconUrl} alt="" aria-hidden />
          <div>
            <div className="app-name">GichanFormant</div>
            <div className="app-edition">모음 음향 분석</div>
          </div>
        </div>

        <div className="workspace-crumb">
          <span>작업 공간</span>
          <ChevronRight size={13} />
          <strong>{hasFiles ? "이름 없는 분석" : "새 분석"}</strong>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="icon-button theme-toggle"
            onClick={toggleThemePreference}
            aria-label={theme === "dark" ? "밝은 테마로 전환" : "어두운 테마로 전환"}
            title={theme === "dark" ? "밝은 테마" : "어두운 테마"}
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <button
            type="button"
            className="quiet-button"
            onClick={() => setGuideOpen(true)}
            disabled={busy}
          >
            <BookOpen size={15} />
            데이터 가이드
          </button>
        </div>
      </header>

      <SourceSidebar
        sources={sources}
        hasF3={hasF3}
        hasFiles={hasFiles}
        busy={busy}
        combinedVisible={combinedVisible}
        onOpenFiles={() => void openFiles()}
        onRemoveFile={(index, name) => void removeFile(index, name)}
        onToggleCombinedVisibility={toggleCombinedVisibility}
        onSaveProject={() => void saveProject()}
        onOpenProject={() => void openProject()}
        onResetWorkspace={() => void resetWorkspace()}
      />

      <PreviewStage
        hasFiles={hasFiles}
        sourcesCount={sources.length}
        activePlot={activePlot}
        health={health}
        previewUrl={previewUrl}
        previewLines={previewLines}
        settingsSummary={settingsSummary}
        analysis={analysis}
        canPlot={canPlot}
        busy={busy}
        onOpenFiles={() => void openFiles()}
        onCreatePlot={() => void createPlot()}
      />

      <AnalysisSettingsPanel
        inspectorOpen={inspectorOpen}
        onToggleInspector={() => setInspectorOpen((open) => !open)}
        onOpenInspector={() => setInspectorOpen(true)}
        settingsAttention={settingsAttention}
        busy={busy}
        hasFiles={hasFiles}
        hasF3={hasF3}
        plotType={plotType}
        analysis={analysis}
        scaleButtonsLocked={scaleButtonsLocked}
        axisControlsLocked={axisControlsLocked}
        barkDisplayLocked={barkDisplayLocked}
        derivedPlotUnsupportedNorm={derivedPlotUnsupportedNorm}
        preLobanovLocked={preLobanovLocked}
        onPatchSettings={patchSettings}
        onToggleBarkDisplayUnits={toggleBarkDisplayUnits}
      />

      <footer className="status-line">
        <span className={`connection-dot ${health?.ok ? "online" : ""}`} />
        <span>{status}</span>
        <span className="status-spacer" />
        <span className="status-copyright">© 2025-2026 Bae Gichan</span>
        <span className="status-divider" />
        <button
          type="button"
          className="status-support"
          title={SUPPORT_TITLE}
          aria-label={SUPPORT_TITLE}
          aria-expanded={supportOpen}
          onClick={() => setSupportOpen(true)}
        >
          {SUPPORT_LABEL}
        </button>
        <span className="status-divider" />
        <span className="status-busy">{busy ? <><Loader2 size={12} className="is-spinning" aria-hidden /> 처리 중…</> : settingsSummary}</span>
        <span className="status-divider" />
        <span className="status-mono">v3.0.0 · 파일 {sources.length}개</span>
      </footer>

      {busy ? <div className="progress-line" aria-label="작업 진행 중" /> : null}

      {error ? (
        <div className="toast" role="alert" aria-live="assertive">
          <span className="toast-icon">
            <X size={15} />
          </span>
          <div>
            <strong>작업을 완료하지 못했습니다</strong>
            <p>{error}</p>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={() => setError(null)}
            aria-label="알림 닫기"
          >
            <X size={14} />
          </button>
        </div>
      ) : null}

      {dragOver ? (
        <div className="drag-overlay" aria-hidden>
          <span>
            <Layers3 size={23} />
          </span>
          <strong>놓아서 데이터 추가</strong>
          <p>파일 형식을 확인한 뒤 작업 공간에 불러옵니다.</p>
        </div>
      ) : null}

      <DataGuide open={guideOpen} onClose={() => setGuideOpen(false)} />
      <SupportPanel
        open={supportOpen}
        onClose={() => setSupportOpen(false)}
        onCopied={() => pushStatus("후원 계좌번호를 복사했습니다")}
      />
    </div>
  );
}
