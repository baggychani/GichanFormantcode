import "./App.css";
import { useCallback, useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { open } from "@tauri-apps/plugin-dialog";
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  FolderOpen,
  Plus,
  RotateCcw,
  Trash2,
} from "lucide-react";
import type { ApplicationState, HealthStatus } from "../ipc/protocol";

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

const PLOT_TYPES: Array<{
  id: PlotType;
  label: string;
  short: string;
  needsF3?: boolean;
}> = [
  { id: "f1_f2", label: "F1 vs F2", short: "F1·F2" },
  { id: "f1_f2_minus_f1", label: "F1 vs (F2-F1)", short: "F2−F1" },
  { id: "f1_f3", label: "F1 vs F3", short: "F1·F3", needsF3: true },
  { id: "f1_f2_prime", label: "F1 vs F2'", short: "F2'", needsF3: true },
  {
    id: "f1_f2_prime_minus_f1",
    label: "F1 vs (F2'-F1)",
    short: "F2'−F1",
    needsF3: true,
  },
];

const X_AXIS_LABEL: Record<PlotType, string> = {
  f1_f2: "F2",
  f1_f2_minus_f1: "F2 − F1",
  f1_f3: "F3",
  f1_f2_prime: "F2'",
  f1_f2_prime_minus_f1: "F2' − F1",
};

async function callSidecar<T>(
  method: string,
  params: Record<string, unknown> = {},
): Promise<T> {
  return invoke<T>("sidecar_call", { method, params });
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [state, setState] = useState<ApplicationState | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewInfo, setPreviewInfo] = useState("");
  const [status, setStatus] = useState("엔진 연결 중…");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(true);

  const analysis = state?.analysis;
  const sources = state?.sources ?? [];
  const hasFiles = sources.length > 0;
  const hasF3 = sources.some((s) => s.has_f3);
  const canPlot = state?.capabilities.can_plot ?? false;
  const plotType = (analysis?.type as PlotType) || "f1_f2";

  const settingsSummary = useMemo(() => {
    if (!analysis) return "설정 없음";
    const outlier = analysis.outlier_mode
      ? analysis.outlier_mode === "tukey_iqr"
        ? "Tukey"
        : "2σ"
      : "이상치 없음";
    const norm = analysis.normalization ?? "정규화 없음";
    return `${PLOT_TYPES.find((p) => p.id === plotType)?.short ?? plotType} · ${analysis.f1_scale}/${analysis.f2_scale} · ${outlier} · ${norm}`;
  }, [analysis, plotType]);

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
      pushStatus(`엔진 연결 · v${nextHealth.version}`);
      if (nextState.capabilities.can_plot) {
        await callSidecar("request_preview");
      }
    } catch (err) {
      setError(String(err));
      pushStatus("엔진 연결 실패");
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
        pushStatus(`${paths.length}개 파일 로드`);
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
        setPreviewUrl(`data:image/png;base64,${String(payload.png_base64 ?? "")}`);
        setPreviewInfo(String(payload.info ?? ""));
      }
      if (name === "preview_cleared") {
        setPreviewUrl(null);
        setPreviewInfo("");
      }
      if (name === "preview_failed" || name === "operation_failed") {
        setError(String(payload.message ?? "작업 실패"));
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

  const openFiles = async () => {
    const selected = await open({
      multiple: true,
      title: "데이터 파일 선택",
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
  };

  const openProject = async () => {
    const selected = await open({
      multiple: false,
      title: "프로젝트 열기",
      filters: [{ name: "GichanFormant Project", extensions: ["gfproj"] }],
    });
    if (!selected || Array.isArray(selected)) return;
    setBusy(true);
    try {
      await callSidecar("load_project", { path: selected });
      await callSidecar("request_preview");
      pushStatus("프로젝트 로드됨");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const resetWorkspace = async () => {
    if (!window.confirm("모든 데이터와 설정을 초기화하시겠습니까?")) return;
    setBusy(true);
    try {
      await callSidecar("reset");
      setPreviewUrl(null);
      setPreviewInfo("");
      pushStatus("작업 공간 초기화");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const removeFile = async (index: number, name: string) => {
    if (!window.confirm(`'${name}' 파일을 삭제하시겠습니까?`)) return;
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
    setBusy(true);
    setError(null);
    try {
      const next = await callSidecar<ApplicationState>("set_analysis_settings", {
        settings: patch,
      });
      setState(next);
      await callSidecar("request_preview");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const createPlot = async () => {
    setBusy(true);
    try {
      await callSidecar("open_single_plot");
      pushStatus("플롯 창 요청");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const openGuide = async () => {
    try {
      await callSidecar("open_guide");
      pushStatus("데이터 가이드");
    } catch (err) {
      setError(String(err));
    }
  };

  const previewLines = previewInfo.split("\n").filter(Boolean);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden />
          <div>
            <div className="brand-name">GichanFormant</div>
            <div className="brand-sub">Workbench</div>
          </div>
        </div>

        <div className="side-actions">
          <button type="button" className="side-btn primary" onClick={() => void openFiles()} disabled={busy}>
            <Plus size={15} />
            파일 추가
          </button>
          <button type="button" className="side-btn" onClick={() => void openProject()} disabled={busy}>
            <FolderOpen size={15} />
            프로젝트
          </button>
          <button type="button" className="side-btn" onClick={() => void openGuide()} disabled={busy}>
            <BookOpen size={15} />
            가이드
          </button>
        </div>

        <div className="side-section">
          <div className="side-label">Sources · {sources.length}</div>
          <div className="file-list">
            {sources.length === 0 ? (
              <div className="side-empty">파일을 추가하세요</div>
            ) : (
              sources.map((source) => (
                <div className="file-item" key={`${source.index}-${source.name}`}>
                  <div className="file-meta">
                    <span className="file-idx">{String(source.index + 1).padStart(2, "0")}</span>
                    <span className="file-name" title={source.path ?? source.name}>
                      {source.name}
                    </span>
                  </div>
                  {!source.is_combined ? (
                    <button
                      type="button"
                      className="icon-btn danger"
                      onClick={() => void removeFile(source.index, source.name)}
                      disabled={busy}
                      aria-label="삭제"
                    >
                      <Trash2 size={14} />
                    </button>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>

        <div className="side-footer">
          <button type="button" className="side-btn ghost" onClick={() => void resetWorkspace()} disabled={busy}>
            <RotateCcw size={14} />
            초기화
          </button>
        </div>
      </aside>

      <main className={`stage ${dragOver ? "drag-over" : ""}`}>
        <header className="stage-bar">
          <div>
            <div className="stage-title">LIVE</div>
            <div className="stage-sub">{previewLines[0] ?? "미리보기 대기"}</div>
          </div>
          <button
            type="button"
            className="cta"
            disabled={busy || !canPlot}
            onClick={() => void createPlot()}
          >
            포먼트 플롯 생성
          </button>
        </header>

        <div
          className="stage-canvas"
          onClick={!hasFiles ? () => void openFiles() : undefined}
          role={!hasFiles ? "button" : undefined}
        >
          {previewUrl ? (
            <img src={previewUrl} alt="Formant live preview" className="preview-img" />
          ) : (
            <div className="empty-state">
              <img src="/brand-mesh.png" alt="" className="empty-mesh" />
              <p>파일을 놓거나 클릭해서 분석을 시작하세요</p>
            </div>
          )}
        </div>

        {previewLines[1] ? <div className="stage-caption">{previewLines[1]}</div> : null}
        {error ? <div className="error-strip">{error}</div> : null}
      </main>

      <aside className={`inspector ${inspectorOpen ? "open" : "collapsed"}`}>
        <button
          type="button"
          className="inspector-toggle"
          onClick={() => setInspectorOpen((v) => !v)}
        >
          {inspectorOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <span>Inspector</span>
          {!inspectorOpen ? <span className="inspector-summary">{settingsSummary}</span> : null}
        </button>

        {inspectorOpen ? (
          <div className="inspector-body">
            <section className="insp-block">
              <div className="insp-label">Plot</div>
              <div className="chip-grid">
                {PLOT_TYPES.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`chip ${plotType === item.id ? "active" : ""}`}
                    disabled={busy || !hasFiles || (item.needsF3 && !hasF3)}
                    onClick={() => void patchSettings({ type: item.id })}
                  >
                    {item.short}
                  </button>
                ))}
              </div>
            </section>

            <section className="insp-block">
              <div className="insp-label">Axes</div>
              <label className="insp-field">
                <span>F1</span>
                <select
                  value={analysis?.f1_scale ?? "linear"}
                  disabled={busy || !hasFiles}
                  onChange={(e) => void patchSettings({ f1_scale: e.target.value })}
                >
                  <option value="linear">Linear</option>
                  <option value="log">Log</option>
                  <option value="bark">Bark</option>
                </select>
              </label>
              <label className="insp-field">
                <span>{X_AXIS_LABEL[plotType]}</span>
                <select
                  value={analysis?.f2_scale ?? "linear"}
                  disabled={busy || !hasFiles}
                  onChange={(e) => void patchSettings({ f2_scale: e.target.value })}
                >
                  <option value="linear">Linear</option>
                  <option value="log">Log</option>
                  <option value="bark">Bark</option>
                </select>
              </label>
              <label className="insp-field">
                <span>Origin</span>
                <select
                  value={analysis?.origin ?? "top_right"}
                  disabled={busy || !hasFiles}
                  onChange={(e) => void patchSettings({ origin: e.target.value })}
                >
                  <option value="top_right">Praat</option>
                  <option value="bottom_left">Math</option>
                </select>
              </label>
              <label className="insp-check">
                <input
                  type="checkbox"
                  checked={Boolean(analysis?.use_bark_units)}
                  disabled={busy || !hasFiles}
                  onChange={(e) =>
                    void patchSettings({ use_bark_units: e.target.checked })
                  }
                />
                Bark 단위 표시
              </label>
            </section>

            <section className="insp-block">
              <div className="insp-label">Processing</div>
              <div className="chip-grid">
                <button
                  type="button"
                  className={`chip ${analysis?.outlier_mode === "tukey_iqr" ? "active" : ""}`}
                  disabled={busy || !hasFiles}
                  onClick={() =>
                    void patchSettings({
                      outlier_mode:
                        analysis?.outlier_mode === "tukey_iqr" ? null : "tukey_iqr",
                      outlier_scope:
                        analysis?.outlier_mode === "tukey_iqr" ? null : "combined",
                    })
                  }
                >
                  Tukey
                </button>
                <button
                  type="button"
                  className={`chip ${analysis?.outlier_mode === "mahalanobis_2sigma" ? "active" : ""}`}
                  disabled={busy || !hasFiles}
                  onClick={() =>
                    void patchSettings({
                      outlier_mode:
                        analysis?.outlier_mode === "mahalanobis_2sigma"
                          ? null
                          : "mahalanobis_2sigma",
                      outlier_scope:
                        analysis?.outlier_mode === "mahalanobis_2sigma"
                          ? null
                          : "combined",
                    })
                  }
                >
                  2σ
                </button>
              </div>
              {analysis?.outlier_mode ? (
                <label className="insp-field">
                  <span>Scope</span>
                  <select
                    value={analysis.outlier_scope ?? "combined"}
                    disabled={busy || !hasFiles}
                    onChange={(e) =>
                      void patchSettings({ outlier_scope: e.target.value })
                    }
                  >
                    <option value="individual">개별</option>
                    <option value="combined">통합</option>
                  </select>
                </label>
              ) : null}
              <label className="insp-field">
                <span>Norm</span>
                <select
                  value={analysis?.normalization ?? ""}
                  disabled={busy || !hasFiles}
                  onChange={(e) =>
                    void patchSettings({
                      normalization: e.target.value || null,
                    })
                  }
                >
                  <option value="">없음</option>
                  <option value="Lobanov">Lobanov</option>
                </select>
              </label>
            </section>
          </div>
        ) : null}
      </aside>

      <footer className="statusbar">
        <span className={`dot ${health?.ok ? "ok" : ""}`} />
        <span>{status}</span>
        <span className="spacer" />
        <span className="mono">{sources.length} sources</span>
        <span className="mono">{hasFiles ? "ready" : "idle"}</span>
      </footer>
    </div>
  );
}

export default App;
