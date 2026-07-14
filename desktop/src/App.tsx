import "./App.css";
import { useCallback, useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { open } from "@tauri-apps/plugin-dialog";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  Check,
  ChevronRight,
  CircleDot,
  Database,
  FilePlus2,
  FolderOpen,
  Gauge,
  Layers3,
  Moon,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  RotateCcw,
  SlidersHorizontal,
  Sparkles,
  Sun,
  Trash2,
  X,
} from "lucide-react";
import type { ApplicationState, HealthStatus } from "../ipc/protocol";
import appIconUrl from "../../assets/icon.ico";
import { DataGuide } from "./components/DataGuide";
import { InteractivePlotWindow } from "./components/InteractivePlotWindow";

type SidecarEvent = {
  event: string;
  payload: Record<string, unknown>;
};

type PlotType =
  | "f1_f2"
  | "f1_f2_minus_f1"
  | "f1_f3"
  | "f1_f2_prime"
  | "f1_f2_prime_minus_f1";

type Theme = "dark" | "light";

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
    short: "F2−F1",
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
    short: "F2′",
    needsF3: true,
  },
  {
    id: "f1_f2_prime_minus_f1",
    label: "유효 F2 거리",
    description: "F2′−F1 차이로 지각적 거리를 살펴봅니다.",
    short: "F2′−F1",
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

async function callSidecar<T>(
  method: string,
  params: Record<string, unknown> = {},
): Promise<T> {
  return invoke<T>("sidecar_call", { method, params });
}

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

function MainWorkspace() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [state, setState] = useState<ApplicationState | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewInfo, setPreviewInfo] = useState("");
  const [status, setStatus] = useState("분석 엔진을 연결하고 있습니다");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
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

  const analysis = state?.analysis;
  const sources = state?.sources ?? [];
  const hasFiles = sources.length > 0;
  const hasF3 = sources.some((source) => source.has_f3);
  const canPlot = state?.capabilities.can_plot ?? false;
  const plotType = (analysis?.type as PlotType) || "f1_f2";
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

  const refresh = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const nextHealth = await invoke<HealthStatus>("sidecar_ensure");
      setHealth(nextHealth);
      const nextState = await callSidecar<ApplicationState>("get_state");
      setState(nextState);
      pushStatus(`엔진 연결됨 · GichanFormant ${nextHealth.version}`);
      if (nextState.capabilities.can_plot) {
        await callSidecar("request_preview");
      }
    } catch (err) {
      setError(String(err));
      pushStatus("분석 엔진 연결 실패");
    } finally {
      setBusy(false);
    }
  }, [pushStatus]);

  const loadPaths = useCallback(
    async (paths: string[]) => {
      if (!paths.length) return;
      setBusy(true);
      setError(null);
      try {
        await callSidecar("load_files", { paths });
        await callSidecar("request_preview");
        pushStatus(`${paths.length}개 소스를 작업 공간에 추가했습니다`);
      } catch (err) {
        setError(String(err));
      } finally {
        setBusy(false);
      }
    },
    [pushStatus],
  );

  useEffect(() => {
    void refresh();
    const unlistenEvent = listen<SidecarEvent>("sidecar-event", (event) => {
      const { event: name, payload } = event.payload;
      if (name === "state_changed" || name === "files_changed") {
        const next = payload.state as ApplicationState | undefined;
        if (next) setState(next);
      }
      if (name === "preview_ready") {
        setPreviewUrl(
          `data:image/png;base64,${String(payload.png_base64 ?? "")}`,
        );
        setPreviewInfo(String(payload.info ?? ""));
      }
      if (name === "preview_cleared") {
        setPreviewUrl(null);
        setPreviewInfo("");
      }
      if (name === "preview_failed" || name === "operation_failed") {
        setError(String(payload.message ?? "작업을 완료하지 못했습니다"));
      }
    });

    let unlistenDrag: (() => void) | undefined;
    void getCurrentWebview()
      .onDragDropEvent((event) => {
        if (event.payload.type === "over") setDragOver(true);
        if (event.payload.type === "leave") setDragOver(false);
        if (event.payload.type === "drop") {
          setDragOver(false);
          void loadPaths(event.payload.paths);
        }
      })
      .then((fn) => {
        unlistenDrag = fn;
      });

    return () => {
      void unlistenEvent.then((fn) => fn());
      unlistenDrag?.();
    };
  }, [refresh, loadPaths]);

  useEffect(() => {
    if (!error) return;
    const timer = window.setTimeout(() => setError(null), 7000);
    return () => window.clearTimeout(timer);
  }, [error]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    window.localStorage.setItem("gichanformant-theme", theme);
  }, [theme]);

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
      setBusy(true);
      await callSidecar("load_project", { path: selected });
      await callSidecar("request_preview");
      pushStatus("프로젝트를 불러왔습니다");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const resetWorkspace = async () => {
    if (!window.confirm("모든 데이터와 설정을 초기화하시겠습니까?")) return;
    setError(null);
    setBusy(true);
    try {
      await callSidecar("reset");
      setPreviewUrl(null);
      setPreviewInfo("");
      pushStatus("새 작업 공간을 준비했습니다");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const removeFile = async (index: number, name: string) => {
    if (!window.confirm(`'${name}' 파일을 삭제하시겠습니까?`)) return;
    setError(null);
    setBusy(true);
    try {
      await callSidecar("remove_file", { index });
      await callSidecar("request_preview");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const patchSettings = async (patch: Record<string, unknown>) => {
    setError(null);
    try {
      const next = await callSidecar<ApplicationState>("set_analysis_settings", {
        settings: patch,
      });
      setState(next);
    } catch (err) {
      setError(String(err));
    }
  };

  const createPlot = async () => {
    setError(null);
    setBusy(true);
    try {
      await invoke("open_interactive_plot");
      pushStatus("새 포먼트 플롯 창을 열었습니다");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
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
            onClick={() => setTheme((value) => value === "dark" ? "light" : "dark")}
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
                {!source.is_combined ? (
                  <button
                    type="button"
                    className="icon-button danger"
                    onClick={() => void removeFile(source.index, source.name)}
                    disabled={busy}
                    aria-label={`${source.name} 삭제`}
                  >
                    <Trash2 size={14} />
                  </button>
                ) : null}
              </div>
            ))
          )}
        </div>

        <div className="sidebar-project-actions">
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
            <h1>{hasFiles ? "모음 공간을 살펴볼 준비가 됐습니다." : "모음 공간을 더 선명하게 살펴보세요."}</h1>
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

      <aside className="settings-panel">
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
              <div className="field-grid two-up">
                <label className="select-field">
                  <span>F1 눈금</span>
                  <select
                    value={analysis?.f1_scale ?? "linear"}
                    disabled={busy || !hasFiles}
                    onChange={(event) =>
                      void patchSettings({ f1_scale: event.target.value })
                    }
                  >
                    <option value="linear">선형</option>
                    <option value="log">로그</option>
                    <option value="bark">Bark</option>
                  </select>
                </label>
                <label className="select-field">
                  <span>{X_AXIS_LABEL[plotType]} 눈금</span>
                  <select
                    value={analysis?.f2_scale ?? "linear"}
                    disabled={busy || !hasFiles}
                    onChange={(event) =>
                      void patchSettings({ f2_scale: event.target.value })
                    }
                  >
                    <option value="linear">선형</option>
                    <option value="log">로그</option>
                    <option value="bark">Bark</option>
                  </select>
                </label>
              </div>
              <label className="select-field wide">
                <span>좌표 원점</span>
                <select
                  value={analysis?.origin ?? "top_right"}
                  disabled={busy || !hasFiles}
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
                  <small>주파수 눈금을 지각 척도로 바꿉니다</small>
                </span>
                <input
                  type="checkbox"
                  checked={Boolean(analysis?.use_bark_units)}
                  disabled={busy || !hasFiles}
                  onChange={(event) =>
                    void patchSettings({ use_bark_units: event.target.checked })
                  }
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
                  disabled={busy || !hasFiles}
                  onChange={(event) =>
                    void patchSettings({ normalization: event.target.value || null })
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
        <span>{busy ? "처리 중…" : settingsSummary}</span>
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
    return <InteractivePlotWindow />;
  }
  return <MainWorkspace />;
}

export default App;
