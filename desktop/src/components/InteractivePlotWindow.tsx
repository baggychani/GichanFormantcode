import { useCallback, useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import {
  ArrowUpRight,
  Eye,
  Layers3,
  MousePointer2,
  Palette,
  PenLine,
  Ruler,
  SlidersHorizontal,
} from "lucide-react";
import type { ApplicationState } from "../../ipc/protocol";
import "./InteractivePlotWindow.css";

type SidecarEvent = { event: string; payload: Record<string, unknown> };
type Tool = "select" | "ruler" | "draw";
type Inspector = "analysis" | "design";

const PLOT_TYPES = [
  ["f1_f2", "F1·F2", "기본 모음 공간"],
  ["f1_f2_minus_f1", "F2−F1", "청각적 거리"],
  ["f1_f3", "F1·F3", "제3포먼트 공간"],
  ["f1_f2_prime", "F2′", "유효 F2 공간"],
  ["f1_f2_prime_minus_f1", "F2′−F1", "유효 F2 거리"],
] as const;

async function callSidecar<T>(method: string, params: Record<string, unknown> = {}) {
  return invoke<T>("sidecar_call", { method, params });
}

export function InteractivePlotWindow() {
  const [state, setState] = useState<ApplicationState | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [tool, setTool] = useState<Tool>("select");
  const [inspector, setInspector] = useState<Inspector>("analysis");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const next = await callSidecar<ApplicationState>("get_state");
    setState(next);
    if (next.capabilities.can_plot) await callSidecar("request_preview");
  }, []);

  useEffect(() => {
    void refresh();
    const unlisten = listen<SidecarEvent>("sidecar-event", ({ payload }) => {
      if (payload.event === "preview_ready") {
        const image = String(payload.payload.png_base64 ?? "");
        setPreviewUrl(image ? `data:image/png;base64,${image}` : null);
      }
      if (payload.event === "state_changed" || payload.event === "files_changed") {
        const next = payload.payload.state as ApplicationState | undefined;
        if (next) setState(next);
      }
    });
    return () => void unlisten.then((dispose) => dispose());
  }, [refresh]);

  const analysis = state?.analysis;
  const sources = state?.sources ?? [];
  const activeType = analysis?.type ?? "f1_f2";
  const activeLabel = useMemo(
    () => PLOT_TYPES.find(([id]) => id === activeType)?.[1] ?? "F1·F2",
    [activeType],
  );

  const updateAnalysis = async (settings: Record<string, unknown>) => {
    setBusy(true);
    try {
      const next = await callSidecar<ApplicationState>("set_analysis_settings", { settings });
      setState(next);
      await callSidecar("request_preview");
    } finally {
      setBusy(false);
    }
  };

  const openLegacyPlot = async () => {
    setBusy(true);
    try {
      await callSidecar("open_single_plot");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="plot-workspace">
      <header className="plot-header">
        <div>
          <span className="plot-kicker">단일 분석 · 대화형 플롯</span>
          <h1>{activeLabel}</h1>
        </div>
        <div className="plot-header-actions">
          <span className="plot-status"><i /> 분석 엔진 연결됨</span>
          <button className="legacy-launch" onClick={() => void openLegacyPlot()} disabled={busy}>
            기존 PySide 플롯 열기 <ArrowUpRight size={15} />
          </button>
        </div>
      </header>

      <aside className="plot-left-rail">
        <div className="rail-heading"><Layers3 size={16} /> 데이터 · 레이어</div>
        <div className="source-count">{sources.length}개 데이터 파일</div>
        <div className="source-list">
          {sources.length ? sources.map((source, index) => (
            <button className={`source-row ${index === state?.current_index ? "is-current" : ""}`} key={source.index}>
              <Eye size={15} /><span>{source.name || `데이터 ${index + 1}`}</span>
            </button>
          )) : <p className="plot-empty">메인 창에서 데이터 파일을 추가하면 레이어가 표시됩니다.</p>}
        </div>
        <div className="rail-note">레이어별 디자인, 순서, 잠금은 현재 기존 PySide 플롯에서도 그대로 사용할 수 있습니다.</div>
      </aside>

      <section className="plot-stage">
        <div className="plot-toolbar" aria-label="플롯 도구">
          <button className={tool === "select" ? "is-active" : ""} onClick={() => setTool("select")}><MousePointer2 size={16} /> 선택</button>
          <button className={tool === "ruler" ? "is-active" : ""} onClick={() => setTool("ruler")}><Ruler size={16} /> 눈금자</button>
          <button className={tool === "draw" ? "is-active" : ""} onClick={() => setTool("draw")}><PenLine size={16} /> 그리기</button>
          <span>현재 도구: {tool === "select" ? "선택" : tool === "ruler" ? "눈금자" : "그리기"}</span>
        </div>
        <div className="plot-canvas">
          {previewUrl ? <img src={previewUrl} alt="현재 분석 플롯 미리보기" /> : (
            <div className="plot-placeholder"><div className="plot-grid" /><strong>데이터 파일을 추가하면 플롯이 표시됩니다.</strong><span>현재 분석 설정을 중앙 캔버스에서 확인합니다.</span></div>
          )}
        </div>
        <footer className="plot-stage-footer"><span>미리보기는 분석 엔진의 실제 렌더 결과입니다.</span><span>{analysis?.origin === "top_right" ? "Praat 좌표" : "Math 좌표"}</span></footer>
      </section>

      <aside className="plot-right-rail">
        <div className="inspector-tabs">
          <button className={inspector === "analysis" ? "is-active" : ""} onClick={() => setInspector("analysis")}><SlidersHorizontal size={15} /> 분석</button>
          <button className={inspector === "design" ? "is-active" : ""} onClick={() => setInspector("design")}><Palette size={15} /> 디자인</button>
        </div>
        {inspector === "analysis" ? <div className="inspector-body">
          <p className="inspector-label">01 · 공간 구성</p>
          {PLOT_TYPES.map(([id, short, description]) => <button key={id} disabled={busy} className={`plot-type-option ${activeType === id ? "is-active" : ""}`} onClick={() => void updateAnalysis({ type: id })}><strong>{short}</strong><span>{description}</span></button>)}
          <p className="inspector-label">02 · 축과 처리</p>
          <label>F1 축<select value={analysis?.f1_scale ?? "linear"} onChange={(event) => void updateAnalysis({ f1_scale: event.target.value })}><option value="linear">선형</option><option value="log">로그</option><option value="bark">Bark</option></select></label>
          <label>F2 축<select value={analysis?.f2_scale ?? "linear"} onChange={(event) => void updateAnalysis({ f2_scale: event.target.value })}><option value="linear">선형</option><option value="log">로그</option><option value="bark">Bark</option></select></label>
        </div> : <div className="inspector-body design-handoff"><Palette size={24} /><h2>디자인 도구 이전 중</h2><p>글꼴, 모음별 레이어, 라벨 이동, 그리기, 내보내기는 기능 손실 없이 기존 PySide 플롯을 계속 사용합니다.</p><button className="legacy-launch" onClick={() => void openLegacyPlot()} disabled={busy}>기존 디자인 도구 열기 <ArrowUpRight size={15} /></button></div>}
      </aside>
    </main>
  );
}
