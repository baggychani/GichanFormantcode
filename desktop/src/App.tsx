import "./App.css";
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { convertFileSrc, invoke } from "@tauri-apps/api/core";
import { emit, listen } from "@tauri-apps/api/event";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { open, save } from "@tauri-apps/plugin-dialog";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  Check,
  ChevronRight,
  CircleDot,
  Database,
  Eye,
  EyeOff,
  FilePlus2,
  FolderOpen,
  Gauge,
  Layers3,
  Loader2,
  Moon,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  RotateCcw,
  Save,
  SlidersHorizontal,
  Sparkles,
  Sun,
  Trash2,
  X,
} from "lucide-react";
import type { ApplicationState, HealthStatus } from "../ipc/protocol";
import { callSidecar } from "./sidecarClient";
import appIconUrl from "../../assets/icon.ico";
import { DataGuide } from "./components/DataGuide";

const InteractivePlotWindow = lazy(async () => {
  const module = await import("./components/InteractivePlotWindow");
  return { default: module.InteractivePlotWindow };
});

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

type PlotType =
  | "f1_f2"
  | "f1_f2_minus_f1"
  | "f1_f3"
  | "f1_f2_prime"
  | "f1_f2_prime_minus_f1";

type Theme = "dark" | "light";

function SettingsSwitch({ checked, onChange, disabled = false }: { checked: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      className="settings-switch-control"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      disabled={disabled}
      aria-label={checked ? "켜짐" : "꺼짐"}
    >
      <i className={checked ? "is-on" : ""}><b /></i>
    </button>
  );
}

const PLOT_TYPES: Array<{
  id: PlotType;
  label: string;
  description: string;
  short: string;
  needsF3?: boolean;
}> = [
  {
    id: "f1_f2",
    label: "기본 모음 공간",
    description: "F1과 F2로 가장 익숙한 모음 공간을 그립니다.",
    short: "F1·F2",
  },
  {
    id: "f1_f2_minus_f1",
    label: "청각적 거리",
    description: "F2−F1 차이로 모음 사이의 거리를 살펴봅니다.",
    short: "F1·F2−F1",
  },
  {
    id: "f1_f3",
    label: "제3포먼트 공간",
    description: "F1과 F3의 관계를 함께 살펴봅니다.",
    short: "F1·F3",
    needsF3: true,
  },
  {
    id: "f1_f2_prime",
    label: "유효 F2 공간",
    description: "F2′ 값을 사용해 지각적 모음 공간을 그립니다.",
    short: "F1·F2′",
    needsF3: true,
  },
  {
    id: "f1_f2_prime_minus_f1",
    label: "유효 F2 거리",
    description: "F2′−F1 차이로 지각적 거리를 살펴봅니다.",
    short: "F1·F2′−F1",
    needsF3: true,
  },
];

const X_AXIS_LABEL: Record<PlotType, string> = {
  f1_f2: "F2",
  f1_f2_minus_f1: "F2 − F1",
  f1_f3: "F3",
  f1_f2_prime: "F2′",
  f1_f2_prime_minus_f1: "F2′ − F1",
};

const scaleLabel = (value?: string) => {
  if (value === "log") return "로그";
  if (value === "bark") return "Bark";
  return "선형";
};

function EmptyVisualization() {
  return (
    <div className="empty-visual" aria-hidden>
      <div className="empty-orbit orbit-a" />
      <div className="empty-orbit orbit-b" />
      <svg viewBox="0 0 620 360" className="formant-ghost">
        <defs>
          <linearGradient id="trace" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0" stopColor="#77f2d2" stopOpacity="0.15" />
            <stop offset="0.48" stopColor="#74d8ff" stopOpacity="0.9" />
            <stop offset="1" stopColor="#8c8cff" stopOpacity="0.25" />
          </linearGradient>
        </defs>
        <path
          d="M95 93 C 170 55, 260 77, 302 142 S 420 290, 535 225"
          fill="none"
          stroke="url(#trace)"
          strokeWidth="2"
          strokeDasharray="5 8"
        />
        <path
          d="M112 255 C 215 305, 325 248, 351 185 S 438 82, 526 111"
          fill="none"
          stroke="url(#trace)"
          strokeWidth="1.5"
          opacity="0.62"
        />
        {[
          [111, 99, 7],
          [177, 82, 4],
          [244, 105, 5],
          [302, 151, 8],
          [351, 187, 5],
          [410, 250, 6],
          [475, 260, 4],
          [535, 226, 8],
          [114, 256, 5],
          [212, 280, 7],
          [302, 248, 4],
          [394, 126, 6],
          [465, 96, 4],
          [526, 111, 7],
        ].map(([cx, cy, radius], index) => (
          <g key={`${cx}-${cy}`}>
            <circle
              cx={cx}
              cy={cy}
              r={radius + 7}
              fill="#74d8ff"
              opacity={index % 3 === 0 ? 0.08 : 0.035}
            />
            <circle
              cx={cx}
              cy={cy}
              r={radius}
              fill={index % 2 === 0 ? "#77f2d2" : "#74d8ff"}
              opacity={index % 3 === 0 ? 0.9 : 0.58}
            />
          </g>
        ))}
      </svg>
    </div>
  );
}

function ReelLine({
  text,
  tone,
}: {
  text: string;
  tone: "static" | "incoming" | "outgoing";
}) {
  return (
    <span className={`reel-line is-${tone}`} aria-hidden={tone !== "static"}>
      {Array.from(text).map((character, index) => (
        <span
          key={`${tone}-${character}-${index}`}
          className="reel-char"
          style={{ ["--reel-i" as string]: index }}
        >
          {character === " " ? "\u00a0" : character}
        </span>
      ))}
    </span>
  );
}

function InteractiveHeadline({ text }: { text: string }) {
  const [current, setCurrent] = useState(text);
  const [outgoing, setOutgoing] = useState<string | null>(null);
  const currentRef = useRef(text);

  useEffect(() => {
    if (text === currentRef.current) return;

    const previous = currentRef.current;
    currentRef.current = text;
    setOutgoing(previous);
    setCurrent(text);

    const staggerMs = 22;
    const duration = 380 + Math.max(previous.length, text.length) * staggerMs;
    const done = window.setTimeout(() => setOutgoing(null), duration);
    return () => window.clearTimeout(done);
  }, [text]);

  return (
    <h1 className="interactive-headline" aria-label={text}>
      <span className={`headline-reel ${outgoing ? "is-animating" : ""}`}>
        {outgoing ? (
          <>
            <ReelLine text={current} tone="incoming" />
            <ReelLine text={outgoing} tone="outgoing" />
          </>
        ) : (
          <ReelLine text={current} tone="static" />
        )}
      </span>
    </h1>
  );
}

function MainWorkspace() {
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

      <aside className="source-sidebar">
        <div className="sidebar-heading">
          <div>
            <span className="section-kicker">프로젝트</span>
            <h2>데이터 파일</h2>
          </div>
          <button
            type="button"
            className="icon-button accent"
            onClick={() => void openFiles()}
            disabled={busy}
            aria-label="파일 추가"
          >
            <Plus size={16} />
          </button>
        </div>

        <button
          type="button"
          className="source-drop-card"
          onClick={() => void openFiles()}
          disabled={busy}
        >
          <span className="drop-icon">
            <FilePlus2 size={18} />
          </span>
          <span>
            <strong>데이터 불러오기</strong>
            <small>TXT, CSV, Excel · 끌어놓기 가능</small>
          </span>
        </button>

        <div className="source-count-row">
          <span>파일 {sources.length}개</span>
          {hasF3 ? <span className="mini-badge">F3 사용 가능</span> : null}
        </div>

        <div className="source-list">
          {sources.length === 0 ? (
            <div className="source-empty">
              <Database size={18} />
              <p>아직 불러온 데이터가 없습니다</p>
              <span>측정 파일을 추가해 분석을 시작하세요.</span>
            </div>
          ) : (
            sources.map((source) => (
              <div className="source-item" key={`${source.index}-${source.name}`}>
                <span className="source-index">
                  {String(source.index + 1).padStart(2, "0")}
                </span>
                <div className="source-copy">
                  <strong title={source.path ?? source.name}>{source.name}</strong>
                  <span>
                    {source.is_combined
                      ? "결합 데이터"
                      : source.has_f3
                        ? "F1 · F2 · F3"
                        : "F1 · F2"}
                  </span>
                </div>
                {source.is_combined ? (
                  <button
                    type="button"
                    className="icon-button"
                    onClick={toggleCombinedVisibility}
                    disabled={busy}
                    aria-pressed={combinedVisible}
                    aria-label={combinedVisible ? "Combined 데이터 숨기기" : "Combined 데이터 표시"}
                    title={combinedVisible ? "Combined 데이터 숨기기" : "Combined 데이터 표시"}
                  >
                    {combinedVisible ? <Eye size={14} /> : <EyeOff size={14} />}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="icon-button danger"
                    onClick={() => void removeFile(source.index, source.name)}
                    disabled={busy}
                    aria-label={`${source.name} 삭제`}
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            ))
          )}
        </div>

        <div className="sidebar-project-actions">
          <button
            type="button"
            className="project-link"
            onClick={() => void saveProject()}
            disabled={busy || !hasFiles}
          >
            <Save size={15} />
            프로젝트 저장
          </button>
          <button
            type="button"
            className="project-link"
            onClick={() => void openProject()}
            disabled={busy}
          >
            <FolderOpen size={15} />
            프로젝트 열기
          </button>
          <button
            type="button"
            className="project-link muted"
            onClick={() => void resetWorkspace()}
            disabled={busy}
          >
            <RotateCcw size={14} />
            초기화
          </button>
        </div>
      </aside>

      <main className="workspace-main">
        <div className="workspace-stage">
          <div className="intro-copy">
            <span className="section-kicker accent-text">분석 작업 공간</span>
            <InteractiveHeadline
              text={hasFiles ? "모음 공간을 살펴볼 준비가 됐습니다." : "모음 공간을 더 선명하게 살펴보세요."}
            />
            <p>
              {hasFiles
                ? "현재 분석 조건을 확인하고 필요한 설정만 다듬은 뒤 대화형 플롯을 열어 보세요."
                : "음향 측정값을 불러오면 정확하고 보기 좋은 모음 공간으로 정리해 드립니다."}
            </p>
          </div>

          <div className="overview-metrics">
            <div className="metric">
              <span className="metric-icon cyan">
                <Database size={15} />
              </span>
              <div>
                <strong>{String(sources.length).padStart(2, "0")}</strong>
                <span>데이터 파일</span>
              </div>
            </div>
            <div className="metric">
              <span className="metric-icon violet">
                <BarChart3 size={15} />
              </span>
              <div>
                <strong>{activePlot.short}</strong>
                <span>분석 유형</span>
              </div>
            </div>
            <div className="metric">
              <span className={`metric-icon ${health?.ok ? "green" : "amber"}`}>
                <Activity size={15} />
              </span>
              <div>
                <strong>{health?.ok ? "연결됨" : "연결 중"}</strong>
                <span>분석 엔진</span>
              </div>
            </div>
          </div>

          <article className="preview-card">
            <div className="panel-heading">
              <div>
                <div className="panel-title-row">
                  <CircleDot size={15} />
                  <h2>포먼트 공간</h2>
                </div>
                <p>{previewLines[0] ?? "현재 설정으로 만든 간단한 미리보기"}</p>
              </div>
              <span className="preview-badge">미리보기</span>
            </div>

            <div className="preview-body">
              <div
                className={`preview-surface ${hasFiles ? "has-data" : "is-empty"}`}
                onClick={!hasFiles ? () => void openFiles() : undefined}
                onKeyDown={(event) => {
                  if (!hasFiles && (event.key === "Enter" || event.key === " ")) {
                    void openFiles();
                  }
                }}
                role={!hasFiles ? "button" : undefined}
                tabIndex={!hasFiles ? 0 : undefined}
              >
                {previewUrl ? (
                  <div className="preview-plot-frame">
                    <img src={previewUrl} alt="현재 포먼트 분석 미리보기" />
                  </div>
                ) : (
                  <>
                    <EmptyVisualization />
                    <div className="empty-callout">
                      <span className="callout-icon">
                        <Sparkles size={16} />
                      </span>
                      <div>
                        <strong>측정 파일을 여기에 놓으세요</strong>
                        <span>포먼트 열을 확인해 자동으로 불러옵니다.</span>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="preview-footer">
              <span>{previewLines[1] ?? settingsSummary}</span>
              <span className="preview-scale">
                {analysis?.origin === "bottom_left" ? "수학적 좌표" : "Praat 좌표"}
              </span>
            </div>
          </article>

          <aside className="launch-card">
            <div className="launch-glow" aria-hidden />
            <div className="launch-icon">
              <Gauge size={20} />
            </div>
            <span className="section-kicker">현재 분석</span>
            <h2>{activePlot.label}</h2>
            <p>{activePlot.description}</p>

            <div className="recipe-stack">
              <div>
                <span>눈금</span>
                <strong>
                  {scaleLabel(analysis?.f1_scale)} / {scaleLabel(analysis?.f2_scale)}
                </strong>
              </div>
              <div>
                <span>이상치</span>
                <strong>
                  {analysis?.outlier_mode === "tukey_iqr"
                    ? "Tukey IQR"
                    : analysis?.outlier_mode === "mahalanobis_2sigma"
                      ? "2σ Mahalanobis"
                      : "모두 포함"}
                </strong>
              </div>
              <div>
                <span>정규화</span>
                <strong>{analysis?.normalization ?? "사용 안 함"}</strong>
              </div>
            </div>

            <div className={`readiness ${canPlot ? "is-ready" : ""}`}>
              <span>{canPlot ? <Check size={13} /> : <CircleDot size={13} />}</span>
              {canPlot ? "대화형 플롯을 열 수 있습니다" : "데이터 파일을 먼저 추가하세요"}
            </div>

            <button
              type="button"
              className="primary-button launch"
              disabled={busy || !canPlot}
              onClick={() => void createPlot()}
            >
              대화형 플롯 열기
              <ArrowUpRight size={16} />
            </button>
          </aside>
        </div>
      </main>

      <aside className={`settings-panel ${settingsAttention ? "is-attention" : ""}`}>
        <div className="settings-header">
          <div className="settings-title">
            <SlidersHorizontal size={16} />
            <div>
              <span className="section-kicker">설정</span>
              <h2>분석 설정</h2>
            </div>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={() => setInspectorOpen((open) => !open)}
            aria-label={inspectorOpen ? "설정 패널 닫기" : "설정 패널 열기"}
          >
            {inspectorOpen ? (
              <PanelRightClose size={16} />
            ) : (
              <PanelRightOpen size={16} />
            )}
          </button>
        </div>

        {inspectorOpen ? (
          <div className="settings-scroll">
            <section className="settings-section">
              <div className="settings-section-title">
                <span>01</span>
                <div>
                  <strong>공간 구성</strong>
                  <small>살펴볼 포먼트 관계를 선택합니다</small>
                </div>
              </div>
              <div className="plot-mode-list">
                {PLOT_TYPES.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`plot-mode ${plotType === item.id ? "active" : ""}`}
                    disabled={busy || !hasFiles || (item.needsF3 && !hasF3)}
                    onClick={() => void patchSettings({ type: item.id })}
                    aria-pressed={plotType === item.id}
                  >
                    <span className="mode-radio" />
                    <span className="mode-copy">
                      <strong>{item.short}</strong>
                      <small>{item.label}</small>
                    </span>
                    {item.needsF3 ? <span className="requirement">F3</span> : null}
                  </button>
                ))}
              </div>
            </section>

            <section className="settings-section">
              <div className="settings-section-title">
                <span>02</span>
                <div>
                  <strong>축과 방향</strong>
                  <small>눈금과 좌표 방향을 정합니다</small>
                </div>
              </div>
              <div className="field-grid">
                <div className="scale-field">
                  <span className="field-caption">F1 눈금</span>
                  <div className="segmented-control three">
                    <button
                      type="button"
                      className={(analysis?.f1_scale ?? "linear") === "linear" ? "active" : ""}
                      disabled={busy || !hasFiles || scaleButtonsLocked}
                      onClick={() => void patchSettings({ f1_scale: "linear" })}
                      aria-pressed={(analysis?.f1_scale ?? "linear") === "linear"}
                    >
                      선형
                    </button>
                    <button
                      type="button"
                      className={analysis?.f1_scale === "log" ? "active" : ""}
                      disabled={busy || !hasFiles || scaleButtonsLocked}
                      onClick={() => void patchSettings({ f1_scale: "log" })}
                      aria-pressed={analysis?.f1_scale === "log"}
                    >
                      로그
                    </button>
                    <button
                      type="button"
                      className={analysis?.f1_scale === "bark" ? "active" : ""}
                      disabled={busy || !hasFiles || scaleButtonsLocked}
                      onClick={() => void patchSettings({ f1_scale: "bark" })}
                      aria-pressed={analysis?.f1_scale === "bark"}
                    >
                      Bark
                    </button>
                  </div>
                </div>
                <div className="scale-field">
                  <span className="field-caption">{X_AXIS_LABEL[plotType]} 눈금</span>
                  <div className="segmented-control three">
                    <button
                      type="button"
                      className={(analysis?.f2_scale ?? "bark") === "linear" ? "active" : ""}
                      disabled={busy || !hasFiles || scaleButtonsLocked}
                      onClick={() => void patchSettings({ f2_scale: "linear" })}
                      aria-pressed={(analysis?.f2_scale ?? "bark") === "linear"}
                    >
                      선형
                    </button>
                    <button
                      type="button"
                      className={analysis?.f2_scale === "log" ? "active" : ""}
                      disabled={busy || !hasFiles || scaleButtonsLocked}
                      onClick={() => void patchSettings({ f2_scale: "log" })}
                      aria-pressed={analysis?.f2_scale === "log"}
                    >
                      로그
                    </button>
                    <button
                      type="button"
                      className={(analysis?.f2_scale ?? "bark") === "bark" ? "active" : ""}
                      disabled={busy || !hasFiles || scaleButtonsLocked}
                      onClick={() => void patchSettings({ f2_scale: "bark" })}
                      aria-pressed={(analysis?.f2_scale ?? "bark") === "bark"}
                    >
                      Bark
                    </button>
                  </div>
                </div>
              </div>
              <label className="select-field wide">
                <span>좌표 원점</span>
                <select
                  value={analysis?.origin ?? "top_right"}
                  disabled={busy || !hasFiles || axisControlsLocked}
                  onChange={(event) =>
                    void patchSettings({ origin: event.target.value })
                  }
                >
                  <option value="top_right">Praat 방식 · 오른쪽 위</option>
                  <option value="bottom_left">수학적 좌표 · 왼쪽 아래</option>
                </select>
              </label>
              <label className="switch-row">
                <span>
                  <strong>Bark 단위로 표시</strong>
                  <small>
                    {axisControlsLocked
                      ? "정규화 중에는 축·Bark 설정이 잠깁니다"
                      : barkDisplayLocked
                        ? "양쪽 축 Bark 고정 · 눈금 버튼 잠금"
                        : "주파수 눈금을 지각 척도로 바꿉니다"}
                  </small>
                </span>
                <SettingsSwitch
                  checked={analysis?.use_bark_units ?? false}
                  disabled={busy || !hasFiles || axisControlsLocked}
                  onChange={toggleBarkDisplayUnits}
                />
              </label>
            </section>

            <section className="settings-section">
              <div className="settings-section-title">
                <span>03</span>
                <div>
                  <strong>데이터 처리</strong>
                  <small>이상치와 화자 차이를 보정합니다</small>
                </div>
              </div>
              <span className="field-caption">이상치 처리</span>
              <div className="segmented-control three">
                <button
                  type="button"
                  className={!analysis?.outlier_mode ? "active" : ""}
                  disabled={busy || !hasFiles}
                  onClick={() =>
                    void patchSettings({ outlier_mode: null, outlier_scope: null })
                  }
                  aria-pressed={!analysis?.outlier_mode}
                >
                  사용 안 함
                </button>
                <button
                  type="button"
                  className={analysis?.outlier_mode === "tukey_iqr" ? "active" : ""}
                  disabled={busy || !hasFiles}
                  onClick={() =>
                    void patchSettings({
                      outlier_mode: "tukey_iqr",
                      outlier_scope: analysis?.outlier_scope ?? "combined",
                    })
                  }
                  aria-pressed={analysis?.outlier_mode === "tukey_iqr"}
                >
                  Tukey
                </button>
                <button
                  type="button"
                  className={
                    analysis?.outlier_mode === "mahalanobis_2sigma" ? "active" : ""
                  }
                  disabled={busy || !hasFiles}
                  onClick={() =>
                    void patchSettings({
                      outlier_mode: "mahalanobis_2sigma",
                      outlier_scope: analysis?.outlier_scope ?? "combined",
                    })
                  }
                  aria-pressed={analysis?.outlier_mode === "mahalanobis_2sigma"}
                >
                  2σ
                </button>
              </div>
              {analysis?.outlier_mode ? (
                <label className="select-field wide compact-field">
                  <span>적용 범위</span>
                  <select
                    value={analysis.outlier_scope ?? "combined"}
                    disabled={busy || !hasFiles}
                    onChange={(event) =>
                      void patchSettings({ outlier_scope: event.target.value })
                    }
                  >
                    <option value="individual">파일별로 계산</option>
                    <option value="combined">전체 데이터를 함께 계산</option>
                  </select>
                </label>
              ) : null}
              <label className="select-field wide compact-field">
                <span>화자 정규화</span>
                <select
                  value={analysis?.normalization ?? ""}
                  disabled={busy || !hasFiles || derivedPlotUnsupportedNorm || preLobanovLocked}
                  onChange={(event) =>
                    void patchSettings({ normalization: event.target.value || null })
                  }
                  title={
                    preLobanovLocked
                      ? "사전 Lobanov 데이터 · Lobanov 고정"
                      : derivedPlotUnsupportedNorm
                        ? "이 플롯 유형에서는 정규화를 쓸 수 없습니다"
                        : undefined
                  }
                >
                  <option value="">사용 안 함</option>
                  <option value="Lobanov">Lobanov</option>
                </select>
              </label>
            </section>
          </div>
        ) : (
          <button
            type="button"
            className="collapsed-settings-trigger"
            onClick={() => setInspectorOpen(true)}
            aria-label="설정 패널 열기"
          >
            <SlidersHorizontal size={17} />
            <span>분석 설정</span>
          </button>
        )}
      </aside>

      <footer className="status-line">
        <span className={`connection-dot ${health?.ok ? "online" : ""}`} />
        <span>{status}</span>
        <span className="status-spacer" />
        <span className="status-copyright">© 2025-2026 Bae Gichan</span>
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
    </div>
  );
}

function App() {
  if (window.location.hash === "#single-plot") {
    return (
      <Suspense fallback={<div className="window-loading">플롯 창을 여는 중…</div>}>
        <InteractivePlotWindow />
      </Suspense>
    );
  }
  return <MainWorkspace />;
}

export default App;
