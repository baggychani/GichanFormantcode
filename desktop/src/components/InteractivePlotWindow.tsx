import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open, save } from "@tauri-apps/plugin-dialog";
import {
  ArrowUpRight,
  BarChart3,
  Bold,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
  EyeOff,
  GripVertical,
  Italic,
  Layers3,
  Lock,
  MousePointer2,
  Palette,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  PenLine,
  RefreshCcw,
  Ruler,
  Save,
  ScanSearch,
  SlidersHorizontal,
  Sparkles,
  Unlock,
  X,
} from "lucide-react";
import type { ApplicationState, SourceInfo } from "../../ipc/protocol";
import { callSidecar } from "../sidecarClient";
import "./InteractivePlotWindow.css";

type SidecarEvent = { event: string; payload: Record<string, unknown> };
type Tool = "select" | "ruler" | "label" | "draw";
type RulerPoint = { x: number; y: number; px: number; py: number; type: "raw" | "mean"; label: string; color: string; raw_f1?: number; raw_f2?: number };
type PlotLabel = { vowel: string; cx: number; cy: number; lx: number; ly: number; px: number; py: number; lpx: number; lpy: number };
type RulerContext = { image_width: number; image_height: number; axes_bbox: { left: number; bottom: number; width: number; height: number }; points: RulerPoint[]; labels: PlotLabel[]; xlim: [number, number]; ylim: [number, number]; params: { normalization?: string | null; use_bark_units?: boolean; f2_scale?: string } };
type RulerMeasurement = { p1: RulerPoint; p2: RulerPoint; labelX: number; labelY: number; distance: string };
type RulerGeometryMode = "direct" | "right-triangle";
type RulerDisplayMode = "hz" | "bark";
type LeftPanel = "analysis" | "global-design";
type RightPanel = "layers" | "drawing";
type DrawTool = "text" | "line" | "area" | "reference";
type VowelAnalysisPage = "formant" | "distance" | "pillai";
type VowelAnalysisResult = {
  index: number;
  name: string;
  x_label?: string;
  y_label?: string;
  statistics: Record<string, { x_mean: number; x_std: number; x_min: number; x_max: number; y_mean: number; y_std: number; y_min: number; y_max: number; count: number }>;
  centroid_distances: Record<string, { distance_to_centroid: number }>;
  pairwise_euclidean: Record<string, number>;
  pairwise_mahalanobis: Record<string, number>;
  pillai_scores: Record<string, { score: number | null; p_value: number | null }>;
  metadata: { total_points?: number; vowel_count?: number };
};
type LayerVisibility = "ON" | "SEMI" | "OFF";
type Ranges = { y_min: string; y_max: string; x_min: string; x_max: string };
type DesignSettings = {
  show_raw: boolean;
  show_centroid: boolean;
  raw_marker: string;
  raw_color: string;
  centroid_marker: string;
  lbl_color: string;
  lbl_size: number;
  lbl_bold: boolean;
  lbl_italic: boolean;
  ell_thick: number;
  ell_style: string;
  ell_color: string | null;
  ell_fill_color: string | null;
  ell_fill_opacity: number;
  box_spines: boolean;
  show_grid: boolean;
  grid_opacity: number;
  y_label_rotation: boolean;
  axis_position_swap: boolean;
  show_axis_units: boolean;
  show_minor_ticks: boolean;
  font_style: string;
  label_slash_wrap: boolean;
};
type LayerOverrides = Record<string, Partial<DesignSettings>>;
type LayerSession = {
  state: Record<string, LayerVisibility>;
  overrides: LayerOverrides;
  locked: Set<string>;
  order: string[];
  expanded: Set<string>;
};

const MAX_CACHED_LAYER_SESSIONS = 32;

function cacheLayerSession(cache: Map<string, LayerSession>, key: string, session: LayerSession) {
  if (!key) return;
  cache.delete(key);
  cache.set(key, session);
  while (cache.size > MAX_CACHED_LAYER_SESSIONS) {
    const oldest = cache.keys().next().value as string | undefined;
    if (oldest === undefined) break;
    cache.delete(oldest);
  }
}

function clampLayerListHeight(value: number) {
  const maxHeight = Math.max(60, window.innerHeight - 310);
  const minHeight = Math.min(150, maxHeight);
  return Math.max(minHeight, Math.min(maxHeight, value));
}

const RANGE_DEFAULTS: Record<string, Ranges> = {
  f1_f2: { y_min: "200", y_max: "1000", x_min: "500", x_max: "3500" },
  f1_f2_minus_f1: { y_min: "200", y_max: "1000", x_min: "0", x_max: "3000" },
  f1_f3: { y_min: "200", y_max: "1000", x_min: "1500", x_max: "4500" },
  f1_f2_prime: { y_min: "200", y_max: "1000", x_min: "500", x_max: "4000" },
  f1_f2_prime_minus_f1: { y_min: "200", y_max: "1000", x_min: "0", x_max: "3500" },
};

const BARK_RANGE_DEFAULTS: Record<string, Ranges> = {
  f1_f2: { y_min: "2", y_max: "9", x_min: "4", x_max: "16" },
  f1_f2_minus_f1: { y_min: "2", y_max: "9", x_min: "0", x_max: "12" },
  f1_f3: { y_min: "2", y_max: "9", x_min: "12", x_max: "19" },
  f1_f2_prime: { y_min: "2", y_max: "9", x_min: "4", x_max: "18" },
  f1_f2_prime_minus_f1: { y_min: "2", y_max: "9", x_min: "0", x_max: "14" },
};

const X_AXIS_LABEL: Record<string, string> = {
  f1_f2: "F2",
  f1_f2_minus_f1: "F2 − F1",
  f1_f3: "F3",
  f1_f2_prime: "F2′",
  f1_f2_prime_minus_f1: "F2′ − F1",
};

// Safe first paint before the sidecar snapshot arrives.  Avoids undefined
// select values and NaN percentages in controls during window startup.
const EMPTY_DESIGN: DesignSettings = {
  show_raw: true, show_centroid: true, raw_marker: "o", raw_color: "#202938",
  centroid_marker: "o", lbl_color: "#202938", lbl_size: 18, lbl_bold: false,
  lbl_italic: false, ell_thick: 1, ell_style: "-", ell_color: "#606060",
  ell_fill_color: null, ell_fill_opacity: 0.15, box_spines: false,
  show_grid: false, grid_opacity: 0.15, y_label_rotation: false,
  axis_position_swap: false, show_axis_units: true, show_minor_ticks: false,
  font_style: "sans", label_slash_wrap: false,
};

const MARKERS = [["o", "●"], ["s", "■"], ["^", "▲"], ["D", "◆"], ["wo", "○"], ["ws", "□"]] as const;
const MARKER_DISPLAY_LABELS: Record<string, string> = { o: "원", s: "사각형", "^": "삼각형", D: "마름모", wo: "빈 원", ws: "빈 사각형", x: "가위표", a: "라벨" };
const IPA_VOWEL_SEQUENCE = ["a", "ɑ", "æ", "ɐ", "ɑ̃", "e", "ə", "ɚ", "ɵ", "ɘ", "ɛ", "ɜ", "ɝ", "ɛ̃", "ɞ", "i", "ɪ", "ɨ", "ɪ̈", "o", "ɔ", "œ", "ɒ", "ɔ̃", "ɶ", "ø", "u", "ʊ", "ʉ", "ʌ", "w", "ɯ", "ʍ", "ɰ", "y", "ɣ", "ʎ", "ʏ", "ɤ"];
const DESIGN_EFFECT_ORDER: (keyof DesignSettings)[] = ["lbl_color", "lbl_size", "lbl_bold", "lbl_italic", "centroid_marker", "ell_thick", "ell_style", "ell_color", "ell_fill_color", "ell_fill_opacity", "raw_color", "raw_marker", "label_slash_wrap"];
const DESIGN_EFFECT_LABELS: Partial<Record<keyof DesignSettings, string>> = {
  lbl_color: "라벨 색", lbl_size: "라벨 크기", lbl_bold: "라벨 굵기", lbl_italic: "라벨 기울임",
  centroid_marker: "중심점 모양", ell_thick: "타원 선 두께", ell_style: "타원 선 모양",
  ell_color: "타원 선 색", ell_fill_color: "타원 내부 색", ell_fill_opacity: "타원 불투명도",
  raw_color: "원자료 색", raw_marker: "원자료 모양", label_slash_wrap: "슬래시 감싸기",
};

function sortVowels(vowels: string[]) {
  const rank = new Map(IPA_VOWEL_SEQUENCE.map((vowel, index) => [vowel, index]));
  const bases = [...IPA_VOWEL_SEQUENCE].sort((a, b) => b.length - a.length);
  return [...vowels].sort((left, right) => {
    const leftBase = bases.find((base) => left.startsWith(base));
    const rightBase = bases.find((base) => right.startsWith(base));
    if (leftBase && rightBase) return (rank.get(leftBase) ?? 0) - (rank.get(rightBase) ?? 0) || left.slice(leftBase.length).localeCompare(right.slice(rightBase.length));
    if (leftBase) return -1;
    if (rightBase) return 1;
    return left.localeCompare(right);
  });
}

function effectDisplayValue(key: keyof DesignSettings, value: DesignSettings[keyof DesignSettings]) {
  if (value === null) return "투명";
  if (key === "lbl_size") return `${value}pt`;
  if (key === "lbl_bold") return value ? "굵게" : "보통";
  if (key === "lbl_italic") return value ? "기울임" : "보통";
  if (key === "label_slash_wrap") return value ? "사용" : "사용 안 함";
  if (key === "ell_fill_opacity") return `${Math.round(Number(value) * 100)}%`;
  if (key === "ell_style") return value === "-" ? "실선" : value === "--" ? "파선" : "점선";
  if (key === "ell_thick") return Number(value) <= 0.5 ? "얇게" : Number(value) >= 2 ? "굵게" : "보통";
  if (key === "centroid_marker" || key === "raw_marker") return MARKER_DISPLAY_LABELS[String(value)] ?? String(value);
  return String(value);
}

function ToggleSwitch({ label, checked, onChange, disabled = false }: { label: string; checked: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button type="button" className="setting-switch" role="switch" aria-checked={checked} onClick={onChange} disabled={disabled}>
      <span>{label}</span><i className={checked ? "is-on" : ""}><b /></i>
    </button>
  );
}

function MarkerPicker({ value, onChange, disabled = false }: { value: string; onChange: (marker: string) => void; disabled?: boolean }) {
  const icon = (marker: string) => {
    const common = { stroke: "currentColor", strokeWidth: 1.6 };
    if (marker === "s" || marker === "ws") return <rect x="7" y="7" width="10" height="10" rx="1" fill={marker === "s" ? "currentColor" : "none"} {...common} />;
    if (marker === "^") return <path d="M12 6 18 17H6Z" fill="currentColor" {...common} />;
    if (marker === "D") return <path d="m12 5 7 7-7 7-7-7Z" fill="currentColor" {...common} />;
    return <circle cx="12" cy="12" r="5.5" fill={marker === "o" ? "currentColor" : "none"} {...common} />;
  };
  return (
    <div className="marker-options">
      {MARKERS.map(([marker]) => <button key={marker} type="button" disabled={disabled} className={value === marker ? "is-active" : ""} onClick={() => onChange(marker)}><svg viewBox="0 0 24 24" aria-hidden>{icon(marker)}</svg></button>)}
    </div>
  );
}

function PalettePicker({ label, value, onChange, allowTransparent = false, disabled = false }: { label: string; value: string | null; onChange: (color: string | null) => void; allowTransparent?: boolean; disabled?: boolean }) {
  const colors = ["#202938", "#606060", "#9ca3af", "#FF0000", "#ef2929", "#f97316", "#eab308", "#16a34a", "#0891b2", "#2563eb", "#7c3aed"];
  return (
    <details className="palette-picker">
      <summary aria-disabled={disabled}><span>{label}</span><i className={!value ? "is-transparent" : ""} style={value ? { background: value } : undefined} /></summary>
      {!disabled ? <div className="palette-popover">{allowTransparent ? <button type="button" className={`transparent-swatch ${value === null ? "is-selected" : ""}`} onClick={(event) => { onChange(null); event.currentTarget.closest("details")?.removeAttribute("open"); }} aria-label="투명" /> : null}{colors.map((color) => <button key={color} type="button" className={value === color ? "is-selected" : ""} style={{ background: color }} onClick={(event) => { onChange(color); event.currentTarget.closest("details")?.removeAttribute("open"); }} aria-label={color} />)}</div> : null}
    </details>
  );
}

function FileSelectMenu({ sources, currentIndex, onNavigate, disabled = false }: { sources: SourceInfo[]; currentIndex: number; onNavigate: (index: number) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const current = sources[currentIndex];

  useEffect(() => {
    if (!open) return;
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener("pointerdown", closeOnOutsidePointer);
    return () => window.removeEventListener("pointerdown", closeOnOutsidePointer);
  }, [open]);

  return (
    <div className={`file-select-menu ${open ? "is-open" : ""}`} ref={rootRef}>
      <button type="button" className="file-select-trigger" disabled={disabled} aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen((previous) => !previous)}>
        <span>{current?.name ?? "데이터 파일을 불러오세요"}</span><ChevronDown size={14} />
      </button>
      {open ? <div className="file-option-menu" role="listbox" aria-label="파일 선택">
        {sources.map((source, index) => <button type="button" role="option" aria-selected={index === currentIndex} className={index === currentIndex ? "is-selected" : ""} key={`${source.index}-${source.name}`} onClick={() => { setOpen(false); onNavigate(index); }}>{source.name}</button>)}
      </div> : null}
    </div>
  );
}

function AnalysisFigure({ page }: { page: VowelAnalysisPage }) {
  return (
    <div className={`analysis-figure analysis-figure-${page}`} aria-label={`${page} 분석 시각화`}>
      <svg viewBox="0 0 320 220" role="img">
        <path className="figure-axis figure-axis-x" d="M35 186H285" /><path className="figure-axis figure-axis-y" d="M35 186V28" />
        {page === "formant" ? <>
          <ellipse className="figure-ellipse ellipse-a" cx="91" cy="82" rx="35" ry="51" /><ellipse className="figure-ellipse ellipse-b" cx="205" cy="104" rx="57" ry="35" />
          <g className="figure-cloud cloud-a">{[[80, 72], [91, 81], [99, 93], [87, 101], [104, 78], [73, 91]].map(([cx, cy]) => <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="3" />)}</g>
          <g className="figure-cloud cloud-b">{[[176, 100], [193, 111], [205, 98], [217, 91], [229, 108], [211, 119]].map(([cx, cy]) => <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="3" />)}</g>
          <circle className="figure-centroid centroid-a" cx="91" cy="85" r="6" /><circle className="figure-centroid centroid-b" cx="205" cy="104" r="6" /><text x="80" y="55">i</text><text x="218" y="82">a</text>
        </> : page === "distance" ? <>
          <ellipse className="figure-ellipse distance-ellipse" cx="155" cy="108" rx="83" ry="48" />
          <circle className="figure-centroid centroid-a" cx="91" cy="83" r="6" /><circle className="figure-centroid centroid-b" cx="224" cy="143" r="6" />
          <path className="figure-distance-line" d="M91 83L224 143" /><path className="figure-distance-arrow" d="m213 132 11 11-15 2" /><text x="143" y="103">d(a, u)</text><text x="78" y="67">a</text><text x="229" y="160">u</text>
        </> : <>
          <g className="pillai-group pillai-group-a"><circle cx="73" cy="85" r="5" /><circle cx="89" cy="98" r="5" /><circle cx="80" cy="112" r="5" /><circle cx="101" cy="88" r="5" /></g>
          <g className="pillai-group pillai-group-b"><circle cx="214" cy="77" r="5" /><circle cx="232" cy="91" r="5" /><circle cx="222" cy="109" r="5" /><circle cx="245" cy="83" r="5" /></g>
          <path className="pillai-separation" d="M137 48V164" /><text x="61" y="54">/i, e/</text><text x="211" y="54">/a, u/</text><text x="143" y="38">Pillai</text>
        </>}
        <text className="figure-axis-label" x="276" y="204">F2</text><text className="figure-axis-label" x="14" y="34">F1</text>
      </svg>
      <span className="figure-caption">{page === "formant" ? "모음별 중심점과 분포" : page === "distance" ? "중심점 사이의 실제 거리" : "모음 조합 사이의 분리"}</span>
    </div>
  );
}

function VowelAnalysisShell({ currentSource, sources, currentIndex, onNavigate, onClose }: { currentSource: SourceInfo | undefined; sources: SourceInfo[]; currentIndex: number; onNavigate: (index: number) => void; onClose: () => void }) {
  const [page, setPage] = useState<VowelAnalysisPage>("formant");
  const [analysisData, setAnalysisData] = useState<VowelAnalysisResult | null>(null);
  const analysisBodyRef = useRef<HTMLDivElement | null>(null);
  const analysisScrollByFileRef = useRef(new Map<number, number>());
  const previousAnalysisIndexRef = useRef(currentIndex);
  useEffect(() => {
    setAnalysisData(null);
    let active = true;
    void callSidecar<VowelAnalysisResult>("get_vowel_analysis", { index: currentIndex }).then((result) => {
      if (active) setAnalysisData(result);
    }).catch(() => {
      // Keep the shell hidden when the replacement analysis cannot be loaded.
    });
    return () => { active = false; };
  }, [currentIndex]);
  useEffect(() => {
    const body = analysisBodyRef.current;
    const previousIndex = previousAnalysisIndexRef.current;
    if (body && previousIndex !== currentIndex) analysisScrollByFileRef.current.set(previousIndex, body.scrollTop);
    previousAnalysisIndexRef.current = currentIndex;
    const frame = window.requestAnimationFrame(() => {
      if (analysisBodyRef.current) analysisBodyRef.current.scrollTop = analysisScrollByFileRef.current.get(currentIndex) ?? 0;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [currentIndex]);
  if (!analysisData) return null;
  const analysisPairs = analysisData ? Object.keys(analysisData.statistics).flatMap((left, index, vowels) => vowels.slice(index + 1).map((right) => ({ left, right, key: `${left}::${right}` }))) : [];
  const pages: Array<{ id: VowelAnalysisPage; label: string; detail: string }> = [
    { id: "formant", label: "모음별 통계", detail: "중심점과 분포" },
    { id: "distance", label: "중심점 거리", detail: "Euclidean / Mahalanobis" },
    { id: "pillai", label: "Pillai Score", detail: "모음 조합 비교" },
  ];
  const hero = page === "formant"
    ? { kicker: "01 · FORMANT PROFILE", title: "모음 공간의 모양을 읽습니다", copy: "각 모음의 평균 위치와 개별 토큰의 퍼짐을 한 화면에서 확인하는 분석 공간입니다." }
    : page === "distance"
      ? { kicker: "02 · VOWEL DISTANCE", title: "모음 사이의 간격을 비교합니다", copy: "중심점 간 거리와 모음 내부 분산을 함께 살펴볼 수 있도록 준비 중입니다." }
      : { kicker: "03 · GROUP SEPARATION", title: "모음 조합의 분리도를 확인합니다", copy: "선택한 모음 조합이 통계적으로 얼마나 분리되는지 보여주는 분석 페이지입니다." };

  return (
    <div className="vowel-analysis-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="vowel-analysis-shell" role="dialog" aria-modal="true" aria-labelledby="vowel-analysis-title">
        <header className="vowel-analysis-header">
          <div className="vowel-analysis-title"><div className="vowel-analysis-mark"><BarChart3 size={18} /></div><div><span className="section-eyebrow">모음 공간 분석실</span><h2 id="vowel-analysis-title">모음 상세 분석</h2><p>{currentSource?.name ?? "현재 데이터"}의 모음 공간을 수치와 분포로 읽습니다.</p></div></div>
          <button type="button" className="vowel-analysis-close" onClick={onClose} aria-label="분석 창 닫기"><X size={18} /></button>
        </header>
        <div className="analysis-file-switcher"><button type="button" onClick={() => onNavigate(currentIndex - 1)} disabled={currentIndex <= 0} aria-label="이전 파일">‹</button><div><span>분석 파일</span><strong>{currentIndex + 1} / {sources.length}</strong><b title={currentSource?.name}>{currentSource?.name ?? "-"}</b></div><button type="button" onClick={() => onNavigate(currentIndex + 1)} disabled={currentIndex >= sources.length - 1} aria-label="다음 파일">›</button></div>
        <nav className="vowel-analysis-tabs" aria-label="모음 분석 페이지">{pages.map((item) => <button key={item.id} type="button" className={page === item.id ? "is-active" : ""} onClick={() => setPage(item.id)}><strong>{item.label}</strong><small>{item.detail}</small></button>)}</nav>
        <div className="vowel-analysis-body" ref={analysisBodyRef}>
          <div className="vowel-analysis-hero"><div className="analysis-hero-copy"><span className="analysis-kicker">{hero.kicker}</span><h3>{hero.title}</h3><p>{hero.copy}</p></div><AnalysisFigure page={page} /></div>
          <section className="analysis-detail-panel"><div className="analysis-detail-heading"><div><span className="analysis-kicker">RESULTS</span><h4>{page === "formant" ? "모음별 통계" : page === "distance" ? "선택 모음 간 거리" : "모음 조합별 Pillai Score"}</h4></div><span>{analysisData ? String(analysisData.metadata.total_points ?? 0) + " tokens" : "계산 중"}</span></div>{analysisData ? page === "formant" ? <div className="analysis-result-table analysis-formant-table"><div className="analysis-result-row analysis-result-head"><span>모음</span><span>F1 평균 ± SD</span><span>F1 범위</span><span>{analysisData.x_label ?? "F2"} 평균 ± SD</span><span>{analysisData.x_label ?? "F2"} 범위</span><span>중심 거리</span><span>n</span></div>{Object.entries(analysisData.statistics).map(([vowel, stat]) => <div className="analysis-result-row" key={vowel}><strong>{vowel}</strong><span>{stat.y_mean.toFixed(1)} ± {stat.y_std.toFixed(1)}</span><span>{stat.y_min.toFixed(1)}–{stat.y_max.toFixed(1)}</span><span>{stat.x_mean.toFixed(1)} ± {stat.x_std.toFixed(1)}</span><span>{stat.x_min.toFixed(1)}–{stat.x_max.toFixed(1)}</span><span>{(analysisData.centroid_distances[vowel]?.distance_to_centroid ?? 0).toFixed(1)}</span><span>{stat.count}</span></div>)}</div> : analysisPairs.length ? <div className="analysis-result-table"><div className="analysis-result-row analysis-result-head"><span>모음 조합</span><span>{page === "distance" ? "Euclidean" : "Pillai Score"}</span><span>{page === "distance" ? "Mahalanobis" : "p-value"}</span></div>{analysisPairs.map((pair) => { const euclidean = analysisData.pairwise_euclidean[pair.key]; const mahalanobis = analysisData.pairwise_mahalanobis[pair.key]; const pillai = analysisData.pillai_scores[pair.key]; return <div className="analysis-result-row" key={pair.key}><strong>{pair.left} - {pair.right}</strong><span>{page === "distance" ? (euclidean ?? 0).toFixed(3) : pillai?.score == null ? "N/A" : pillai.score.toFixed(4)}</span><span>{page === "distance" ? (mahalanobis ?? 0).toFixed(3) : pillai?.p_value == null ? "N/A" : pillai.p_value.toFixed(4)}</span></div>; })}</div> : <div className="analysis-result-empty">모음 두 개 이상을 선택하면 조합별 결과가 표시됩니다.</div> : <div className="analysis-result-empty">분석 데이터를 불러오는 중입니다.</div>}</section>
        </div>
      </section>
    </div>
  );
}

export function InteractivePlotWindow() {
  const [state, setState] = useState<ApplicationState | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewInfo, setPreviewInfo] = useState("");
  const [batchExportOpen, setBatchExportOpen] = useState(false);
  const [batchExportFormat, setBatchExportFormat] = useState<"png" | "jpg" | "svg">("png");
  const [batchExportDirectory, setBatchExportDirectory] = useState("");
  const [batchExportBusy, setBatchExportBusy] = useState(false);
  const [rulerSettingsOpen, setRulerSettingsOpen] = useState(false);
  const [rulerGeometryMode, setRulerGeometryMode] = useState<RulerGeometryMode>("direct");
  const [rulerDisplayMode, setRulerDisplayMode] = useState<RulerDisplayMode>("hz");
  const [batchApplyGlobalDesign, setBatchApplyGlobalDesign] = useState(true);
  const [batchApplyLayerDesign, setBatchApplyLayerDesign] = useState(true);
  const [batchApplyVisibility, setBatchApplyVisibility] = useState(true);
  const [batchApplyLabelPositions, setBatchApplyLabelPositions] = useState(true);
  const [rulerContext, setRulerContext] = useState<RulerContext | null>(null);
  const [rulerStart, setRulerStart] = useState<RulerPoint | null>(null);
  const [rulerHover, setRulerHover] = useState<RulerPoint | null>(null);
  const [rulerPointer, setRulerPointer] = useState<{ x: number; y: number } | null>(null);
  const [rulerMeasurements, setRulerMeasurements] = useState<RulerMeasurement[]>([]);
  const [draggingRulerLabel, setDraggingRulerLabel] = useState<number | null>(null);
  const [draggingPlotLabel, setDraggingPlotLabel] = useState<string | null>(null);
  const [plotLabelPointer, setPlotLabelPointer] = useState<{ x: number; y: number } | null>(null);
  const [tool, setTool] = useState<Tool>("select");
  const [leftPanel, setLeftPanel] = useState<LeftPanel>("analysis");
  const [rightPanel, setRightPanel] = useState<RightPanel>("layers");
  const [drawTool, setDrawTool] = useState<DrawTool>("line");
  const [drawColor, setDrawColor] = useState<string | null>("#2563eb");
  const [drawWidth, setDrawWidth] = useState(2);
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [ranges, setRanges] = useState<Ranges>(RANGE_DEFAULTS.f1_f2);
  const [sigma, setSigma] = useState("2.0");
  const [showEllipse, setShowEllipse] = useState(true);
  const [design, setDesign] = useState<DesignSettings>(EMPTY_DESIGN);
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
  const [layerListHeight, setLayerListHeight] = useState(() => clampLayerListHeight(Math.min(460, Math.max(360, Math.round(window.innerHeight * 0.46)))));
  const [navigating, setNavigating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [engineConnected, setEngineConnected] = useState(false);
  const [vowelAnalysisOpen, setVowelAnalysisOpen] = useState(false);
  const [message, setMessage] = useState("분석 엔진과 연결하는 중입니다.");
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
  const aliveRef = useRef(true);
  const navigatingRef = useRef(false);
  const currentIndexRef = useRef(0);
  const resizeRef = useRef<{ startY: number; startHeight: number } | null>(null);
  const renderRequestRef = useRef(0);
  const renderTimerRef = useRef<number | null>(null);
  const layerSessionsRef = useRef(new Map<string, LayerSession>());
  const plotPaperRef = useRef<HTMLDivElement | null>(null);
  const plotImageRef = useRef<HTMLImageElement | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await callSidecar<ApplicationState>("get_state");
      if (!aliveRef.current) return;
      setState(next);
      setEngineConnected(true);
      if (next.capabilities.can_plot) {
        const requestId = ++renderRequestRef.current;
        await callSidecar("render_interactive_preview", { options: { request_id: requestId } });
      }
    } catch (err) {
      setEngineConnected(false);
      setMessage(`플롯을 불러오지 못했습니다: ${String(err)}`);
    }
  }, []);

  useEffect(() => {
    aliveRef.current = true;
    void refresh();
    let disposed = false;
    let disposeEvent: (() => void) | undefined;
    void listen<SidecarEvent>("sidecar-event", ({ payload }) => {
      if (disposed || !aliveRef.current) return;
      if (payload.event === "preview_ready" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (requestId && requestId < renderRequestRef.current) return;
        const imagePath = String(payload.payload.png_path ?? "");
        const image = String(payload.payload.png_base64 ?? "");
        setPreviewUrl(imagePath ? convertFileSrc(imagePath) : image ? `data:image/png;base64,${image}` : null);
        setRulerContext((payload.payload.ruler_context as RulerContext | undefined) ?? null);
        setRulerStart(null);
        setRulerHover(null);
        setRulerMeasurements([]);
        setPreviewInfo(String(payload.payload.info ?? ""));
        setMessage("현재 설정을 플롯에 반영했습니다.");
      } else if (payload.event === "preview_failed" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (requestId && requestId < renderRequestRef.current) return;
        setMessage(`렌더링 오류: ${String(payload.payload.message ?? "알 수 없는 오류")}`);
      } else if (payload.event === "preview_cleared" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (requestId && requestId < renderRequestRef.current) return;
        setPreviewUrl(null);
        setRulerContext(null);
        setRulerStart(null);
        setRulerMeasurements([]);
        setPreviewInfo("");
      } else if (payload.event === "state_changed") {
        const reason = String(payload.payload.reason ?? "");
        // Navigation returns the authoritative snapshot in its IPC response.
        // Ignore the matching broadcast so controls do not reset once before
        // the response applies the new file state.
        if (navigatingRef.current && reason === "current_file_changed") return;
        const next = payload.payload.state as ApplicationState | undefined;
        if (next) setState(next);
      } else if (payload.event === "sidecar_shutting_down") {
        setEngineConnected(false);
      }
    }).then((dispose) => {
      if (disposed) dispose();
      else disposeEvent = dispose;
    }).catch((err) => {
      if (!disposed && aliveRef.current) setMessage(String(err));
    });
    return () => {
      disposed = true;
      aliveRef.current = false;
      disposeEvent?.();
    };
  }, [refresh]);

  useEffect(() => {
    if (!batchExportOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || batchExportBusy) return;
      event.preventDefault();
      setBatchExportOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [batchExportBusy, batchExportOpen]);

  useEffect(() => {
    if (!vowelAnalysisOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setVowelAnalysisOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [vowelAnalysisOpen]);

  useEffect(() => {
    const applySharedTheme = () => {
      const saved = window.localStorage.getItem("gichanformant-theme");
      const theme = saved === "dark" || saved === "light"
        ? saved
        : window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      document.documentElement.dataset.theme = theme;
      document.documentElement.style.colorScheme = theme;
    };
    applySharedTheme();
    window.addEventListener("storage", applySharedTheme);
    window.addEventListener("focus", applySharedTheme);
    let unlistenTheme: (() => void) | undefined;
    void listen<string>("gichan-theme", ({ payload }) => {
      if (payload !== "light" && payload !== "dark") return;
      document.documentElement.dataset.theme = payload;
      document.documentElement.style.colorScheme = payload;
    }).then((dispose) => { unlistenTheme = dispose; });
    return () => {
      window.removeEventListener("storage", applySharedTheme);
      window.removeEventListener("focus", applySharedTheme);
      unlistenTheme?.();
    };
  }, []);

  useEffect(() => () => {
    if (renderTimerRef.current !== null) window.clearTimeout(renderTimerRef.current);
    removeLayerDragListeners();
    if (dragScrollFrameRef.current !== null) cancelAnimationFrame(dragScrollFrameRef.current);
    if (flipFrameRef.current !== null) cancelAnimationFrame(flipFrameRef.current);
    dragScrollFrameRef.current = null;
    flipFrameRef.current = null;
    draggingLayerRef.current = null;
  }, []);

  const analysis = state?.analysis;
  const sources = state?.sources ?? [];
  const currentIndex = Math.min(state?.current_index ?? 0, Math.max(0, sources.length - 1));
  const currentSource = sources[currentIndex];
  const currentFileKey = currentSource ? String(currentSource.path ?? `${currentSource.index}:${currentSource.name}`) : "";
  const currentVowels = state?.current_vowels ?? [];
  const plotType = analysis?.type ?? "f1_f2";
  const xAxis = X_AXIS_LABEL[plotType] ?? "F2";
  const defaultRanges = useMemo(() => {
    const hz = RANGE_DEFAULTS[plotType] ?? RANGE_DEFAULTS.f1_f2;
    const bark = BARK_RANGE_DEFAULTS[plotType] ?? BARK_RANGE_DEFAULTS.f1_f2;
    const useBark = analysis?.use_bark_units ?? false;
    return {
      y_min: useBark && analysis?.f1_scale === "bark" ? bark.y_min : hz.y_min,
      y_max: useBark && analysis?.f1_scale === "bark" ? bark.y_max : hz.y_max,
      x_min: useBark && (analysis?.f2_scale ?? "bark") === "bark" ? bark.x_min : hz.x_min,
      x_max: useBark && (analysis?.f2_scale ?? "bark") === "bark" ? bark.x_max : hz.x_max,
    };
  }, [analysis?.f1_scale, analysis?.f2_scale, analysis?.use_bark_units, plotType]);
  const canonicalDesign = useMemo(
    () => ({ ...(state?.design_defaults ?? {}) }) as DesignSettings,
    [state?.design_defaults],
  );
  const canNavigate = sources.length > 1;
  const selectedOverride = selectedLayer ? layerOverrides[selectedLayer] ?? {} : {};
  const selectedLocked = selectedLayer ? lockedLayers.has(selectedLayer) : false;

  useEffect(() => {
    currentIndexRef.current = currentIndex;
  }, [currentIndex]);

  useEffect(() => {
    const clampOnResize = () => setLayerListHeight((height) => clampLayerListHeight(height));
    window.addEventListener("resize", clampOnResize);
    return () => window.removeEventListener("resize", clampOnResize);
  }, []);

  useEffect(() => {
    const defaultOrder = sortVowels(currentVowels);
    const cached = currentFileKey ? layerSessionsRef.current.get(currentFileKey) : undefined;
    const session = state?.plot_session;
    const sessionKey = String(currentIndex);
    const sessionState = session?.vowel_filter_state_by_file?.[sessionKey] as Record<string, LayerVisibility> | undefined;
    const sessionOverrides = session?.layer_design_overrides_by_file?.[sessionKey] as LayerOverrides | undefined;
    const sessionLocked = session?.layer_locked_vowels_by_file?.[sessionKey];
    const sessionOrder = session?.layer_order_by_file?.[sessionKey];
    setLayerState(sessionState ?? cached?.state ?? Object.fromEntries(currentVowels.map((vowel) => [vowel, "ON"])));
    setLayerOverrides(sessionOverrides ?? cached?.overrides ?? {});
    setRanges(Object.keys(session?.ranges ?? {}).length === 4 ? session!.ranges as Ranges : defaultRanges);
    setSigma(session?.sigma ?? "2");
    setShowEllipse(session?.show_ellipse ?? true);
    setDesign(({ ...canonicalDesign, ...(session?.design_settings ?? {}) }) as DesignSettings);
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
  }, [canonicalDesign, currentFileKey, currentIndex, currentVowels.join("\u0000"), defaultRanges, state?.plot_session.revision]);

  const renderInteractive = async (overrides: {
    design?: DesignSettings;
    layers?: Record<string, LayerVisibility>;
    ranges?: Ranges;
    sigma?: string;
    showEllipse?: boolean;
    layerOverrides?: LayerOverrides;
    layerOrder?: string[];
    labelOffsets?: Record<string, [number, number]>;
  } = {}) => {
    if (!state?.capabilities.can_plot) return;
    if (renderTimerRef.current !== null) {
      window.clearTimeout(renderTimerRef.current);
      renderTimerRef.current = null;
    }
    const requestId = ++renderRequestRef.current;
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
          ...(overrides.labelOffsets ? { label_offsets: overrides.labelOffsets } : {}),
          request_id: requestId,
        },
      });
    } catch (err) {
      setMessage(`설정을 적용하지 못했습니다: ${String(err)}`);
    }
  };

  const scheduleInteractiveRender = (overrides: Parameters<typeof renderInteractive>[0]) => {
    if (renderTimerRef.current !== null) window.clearTimeout(renderTimerRef.current);
    renderTimerRef.current = window.setTimeout(() => {
      renderTimerRef.current = null;
      void renderInteractive(overrides);
    }, 70);
  };

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

  const navigateTo = useCallback(async (index: number) => {
    if (!sources.length || navigatingRef.current) return;
    const target = Math.max(0, Math.min(index, sources.length - 1));
    if (target === currentIndexRef.current) return;
    navigatingRef.current = true;
    ++renderRequestRef.current;
    if (renderTimerRef.current !== null) {
      window.clearTimeout(renderTimerRef.current);
      renderTimerRef.current = null;
    }
    setNavigating(true);
    try {
      if (currentFileKey) {
        cacheLayerSession(layerSessionsRef.current, currentFileKey, {
          state: { ...layerState },
          overrides: { ...layerOverrides },
          locked: new Set(lockedLayers),
          order: [...layerOrderRef.current],
          expanded: new Set(expandedLayers),
        });
      }
      const requestId = ++renderRequestRef.current;
      const response = await callSidecar<{ state: ApplicationState }>("navigate_interactive_preview", {
        index: target,
        options: {
          ranges,
          sigma,
          show_ellipse: showEllipse,
          design,
          request_id: requestId,
        },
      });
      const next = response.state;
      if (!aliveRef.current) return;
      currentIndexRef.current = target;
      const nextVowels = next.current_vowels ?? [];
      const nextSource = next.sources[target];
      const nextFileKey = nextSource ? String(nextSource.path ?? `${nextSource.index}:${nextSource.name}`) : "";
      const cached = nextFileKey ? layerSessionsRef.current.get(nextFileKey) : undefined;
      const sessionKey = String(target);
      const nextSession = next.plot_session;
      const defaultOrder = sortVowels(nextVowels);
      const previousOrder = layerOrderRef.current;
      const storedOrder = nextSession.layer_order_by_file?.[sessionKey] ?? cached?.order ?? previousOrder;
      const storedSameSet = storedOrder.length === defaultOrder.length && storedOrder.every((vowel) => defaultOrder.includes(vowel));
      const nextOrder = storedSameSet ? storedOrder : defaultOrder;
      const nextLayers = (nextSession.vowel_filter_state_by_file?.[sessionKey] as Record<string, LayerVisibility> | undefined) ?? cached?.state ?? Object.fromEntries(nextVowels.map((vowel) => [vowel, "ON" as LayerVisibility]));
      const nextOverrides = (nextSession.layer_design_overrides_by_file?.[sessionKey] as LayerOverrides | undefined) ?? cached?.overrides ?? {};
      const nextExpanded = cached?.expanded ? new Set(cached.expanded) : new Set<string>();
      // Ranges and global design are intentionally shared across files in PlotSessionState.
      const nextRanges = Object.keys(nextSession.ranges ?? {}).length === 4 ? nextSession.ranges as Ranges : defaultRanges;
      const nextDesign = ({ ...canonicalDesign, ...(nextSession.design_settings ?? {}) }) as DesignSettings;
      const nextSigma = nextSession.sigma ?? "2";
      const nextShowEllipse = nextSession.show_ellipse ?? true;
      layerOrderRef.current = nextOrder;
      setLayerOrder(nextOrder);
      setLayerState(nextLayers);
      setLayerOverrides(nextOverrides);
      setExpandedLayers(nextExpanded);
      const nextLocked = new Set(nextSession.layer_locked_vowels_by_file?.[sessionKey] ?? cached?.locked ?? []);
      setLockedLayers(nextLocked);
      setRanges(nextRanges);
      setDesign(nextDesign);
      setSigma(nextSigma);
      setShowEllipse(nextShowEllipse);
      setState(next);
      setMessage(`${next.sources[target]?.name ?? "파일"}을 불러오는 중입니다.`);
    } catch (err) {
      setMessage(`파일을 이동하지 못했습니다: ${String(err)}`);
    } finally {
      navigatingRef.current = false;
      if (aliveRef.current) setNavigating(false);
    }
  }, [canonicalDesign, currentFileKey, defaultRanges, design, expandedLayers, layerOverrides, layerState, lockedLayers, ranges, showEllipse, sigma, sources.length]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        const target = event.target as HTMLElement | null;
        if (!target?.closest("input, textarea, select, [contenteditable='true']")) {
          event.preventDefault();
          void saveProject();
        }
        return;
      }
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, [contenteditable='true']")) return;
      if (event.key.toLowerCase() === "a") {
        event.preventDefault();
        setLeftPanel("analysis");
        return;
      }
      if (event.key.toLowerCase() === "d") {
        event.preventDefault();
        setLeftPanel("global-design");
        return;
      }
      if (event.key.toLowerCase() === "m") {
        if (sources.length < 2) return;
        event.preventDefault();
        void callSidecar("open_compare", { source_groups: sources.map((source) => [source.index]), normalization: analysis?.normalization ?? null });
        return;
      }
      if (event.key === "Tab") {
        event.preventDefault();
        setLeftOpen((previous) => !previous);
        setRightOpen((previous) => !previous);
        return;
      }
      if (event.key.toLowerCase() === "r") {
        event.preventDefault();
        setTool((previous) => previous === "ruler" ? "select" : "ruler");
        return;
      }
      if (event.key.toLowerCase() === "t") {
        event.preventDefault();
        setTool((previous) => previous === "label" ? "select" : "label");
        setMessage("라벨 이동 모드 · 라벨을 드래그하세요.");
        return;
      }
      if (event.key.toLowerCase() === "p") {
        event.preventDefault();
        setTool((previous) => previous === "draw" ? "select" : "draw");
        setRightPanel("drawing");
        setRightOpen(true);
        setMessage("그리기 모드 · P로 켜고 끌 수 있습니다.");
        return;
      }
      if (event.key === "Escape" && tool === "ruler") {
        event.preventDefault();
        setRulerStart(null);
        setRulerHover(null);
        setRulerPointer(null);
        setRulerSettingsOpen(false);
        return;
      }
      if (event.key === "Escape" && rulerSettingsOpen) {
        event.preventDefault();
        setRulerSettingsOpen(false);
        return;
      }
      if (event.key === "Escape" && tool === "draw") {
        event.preventDefault();
        setTool("select");
        return;
      }
      if (tool === "draw" && ["1", "2", "3", "4", "5"].includes(event.key)) {
        event.preventDefault();
        setDrawTool(event.key === "1" ? "line" : event.key === "2" ? "area" : event.key === "3" ? "text" : "reference");
        return;
      }
      if (event.key === "Home" || event.key === "End") {
        event.preventDefault();
        void navigateTo(event.key === "Home" ? 0 : sources.length - 1);
        return;
      }
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      if (!canNavigate || navigatingRef.current) return;
      event.preventDefault();
      void navigateTo(event.key === "ArrowLeft" ? currentIndexRef.current - 1 : currentIndexRef.current + 1);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [analysis?.normalization, canNavigate, currentIndex, navigateTo, navigating, rulerSettingsOpen, sources, tool]);

  const updateDesign = (patch: Partial<DesignSettings>) => {
    const next = { ...design, ...patch };
    setDesign(next);
    scheduleInteractiveRender({ design: next });
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

  const resetPlot = () => {
    const nextRanges = defaultRanges;
    const nextLayers = Object.fromEntries(currentVowels.map((vowel) => [vowel, "ON" as LayerVisibility]));
    setRanges(nextRanges);
    setSigma("2.0");
    setShowEllipse(true);
    setDesign(canonicalDesign);
    setLayerState(nextLayers);
    setLayerOverrides({});
    void renderInteractive({ design: canonicalDesign, layers: nextLayers, ranges: nextRanges, sigma: "2", showEllipse: true, layerOverrides: {}, layerOrder: sortVowels(currentVowels) });
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

  const removeLayerDragListeners = () => {
    const listeners = dragListenersRef.current;
    if (!listeners) return;
    window.removeEventListener("pointermove", listeners.move);
    window.removeEventListener("pointerup", listeners.up);
    window.removeEventListener("pointercancel", listeners.cancel);
    dragListenersRef.current = null;
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

  // Keep the local handler for browsers that continue dispatching to the
  // handle, while the window listeners cover pointer movement outside it.
  const moveLayerDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (!draggingLayerRef.current) return;
    event.preventDefault();
    dragPointerYRef.current = event.clientY;
    repositionDraggedLayer(event.clientY);
  };

  const stopLayerDragScroll = () => {
    if (dragScrollFrameRef.current !== null) cancelAnimationFrame(dragScrollFrameRef.current);
    dragScrollFrameRef.current = null;
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

  const activateDrawTool = async (next: DrawTool) => {
    setDrawTool(next);
    setTool("select");
    setMessage(`${next === "text" ? "텍스트" : next === "line" ? "선" : next === "area" ? "영역" : "기준선"} 그리기 도구를 선택했습니다.`);
    await openLegacyPlot();
  };

  const openLegacyPlot = async () => {
    setBusy(true);
    try { await callSidecar("open_single_plot"); } finally { setBusy(false); }
  };

  const saveProject = async () => {
    const path = await save({ title: "GichanFormant 프로젝트 저장", defaultPath: "analysis.gfproj", filters: [{ name: "GichanFormant 프로젝트", extensions: ["gfproj"] }] });
    if (!path) return;
    setBusy(true);
    try {
      await callSidecar("update_interactive_session", { options: {
        ranges,
        sigma,
        show_ellipse: showEllipse,
        design,
        filter_state: layerState,
        layer_overrides: layerOverrides,
        layer_order: layerOrder,
        locked_layers: [...lockedLayers],
      } });
      await callSidecar("save_project", { path });
      setMessage("프로젝트를 저장했습니다.");
    } catch (err) {
      setMessage(`프로젝트를 저장하지 못했습니다: ${String(err)}`);
    } finally { setBusy(false); }
  };

  const exportInteractive = async (format: "png" | "jpg" | "svg") => {
    if (!sources.length) return;
    const path = await save({
      title: `${format.toUpperCase()} 내보내기`,
      defaultPath: `${(currentSource?.name ?? "plot").replace(/\.[^.]+$/, "")}.${format}`,
      filters: [{ name: format.toUpperCase(), extensions: [format] }],
    });
    if (!path) return;
    setBusy(true);
    try {
      await callSidecar("export_interactive_preview", {
        path,
        format,
        options: { ranges, sigma, show_ellipse: showEllipse, design, filter_state: layerState, layer_overrides: layerOverrides, layer_order: layerOrder, locked_layers: [...lockedLayers] },
      });
      setMessage(`${format.toUpperCase()} 파일을 저장했습니다.`);
    } catch (err) {
      setMessage(`내보내기 실패: ${String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const chooseBatchDirectory = async () => {
    const selected = await open({ directory: true, multiple: false, title: "일괄 저장 폴더 선택" });
    if (typeof selected === "string") setBatchExportDirectory(selected);
  };

  const runBatchExport = async () => {
    if (!batchExportDirectory || !sources.length) return;
    setBatchExportBusy(true);
    try {
      const result = await callSidecar<{ exported?: string[]; errors?: Array<{ name: string; message: string }> }>("export_interactive_batch", {
        directory: batchExportDirectory,
        format: batchExportFormat,
        options: { ranges, sigma, show_ellipse: showEllipse, design, filter_state: layerState, layer_overrides: layerOverrides, layer_order: layerOrder, locked_layers: [...lockedLayers], batch_options: { apply_global_design: batchApplyGlobalDesign, apply_layer_design: batchApplyLayerDesign, apply_layer_visibility: batchApplyVisibility, apply_label_positions: batchApplyLabelPositions } },
      });
      const count = result.exported?.length ?? 0;
      setMessage(`${count}개 파일을 일괄 저장했습니다${result.errors?.length ? ` · 실패 ${result.errors.length}개` : ""}.`);
      setBatchExportOpen(false);
    } catch (err) {
      setMessage(`일괄 저장 실패: ${String(err)}`);
    } finally {
      setBatchExportBusy(false);
    }
  };

  const rulerImageGeometry = () => {
    const image = plotImageRef.current;
    if (!image || !image.naturalWidth || !image.naturalHeight) return null;
    const box = image.getBoundingClientRect();
    const scale = Math.min(box.width / image.naturalWidth, box.height / image.naturalHeight);
    const width = image.naturalWidth * scale;
    const height = image.naturalHeight * scale;
    return { left: box.left + (box.width - width) / 2, top: box.top + (box.height - height) / 2, scale };
  };

  const rulerPointClient = (point: RulerPoint) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return { x: geometry.left + point.px * geometry.scale, y: geometry.top + (rulerContext.image_height - point.py) * geometry.scale };
  };

  const plotLabelClient = (label: PlotLabel) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return { x: geometry.left + label.lpx * geometry.scale, y: geometry.top + (rulerContext.image_height - label.lpy) * geometry.scale };
  };

  const plotDataFromClient = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    const px = (clientX - geometry.left) / geometry.scale;
    const py = rulerContext.image_height - (clientY - geometry.top) / geometry.scale;
    const x = rulerContext.xlim[0] + ((px - rulerContext.axes_bbox.left) / rulerContext.axes_bbox.width) * (rulerContext.xlim[1] - rulerContext.xlim[0]);
    const y = rulerContext.ylim[0] + ((py - rulerContext.axes_bbox.bottom) / rulerContext.axes_bbox.height) * (rulerContext.ylim[1] - rulerContext.ylim[0]);
    return { x, y };
  };

  const nearestPlotLabel = (clientX: number, clientY: number) => {
    if (!rulerContext) return null;
    let nearest: PlotLabel | null = null;
    let best = 28 * 28;
    for (const label of rulerContext.labels) {
      const screen = plotLabelClient(label);
      if (!screen) continue;
      const distance = (screen.x - clientX) ** 2 + (screen.y - clientY) ** 2;
      if (distance <= best) { best = distance; nearest = label; }
    }
    return nearest;
  };

  const nearestRulerPoint = (clientX: number, clientY: number) => {
    if (!rulerContext) return null;
    let nearest: RulerPoint | null = null;
    let best = 20 * 20;
    for (const point of rulerContext.points) {
      const screen = rulerPointClient(point);
      if (!screen) continue;
      const distance = (screen.x - clientX) ** 2 + (screen.y - clientY) ** 2;
      if (distance <= best) { best = distance; nearest = point; }
    }
    return nearest;
  };

  const rulerLocalPoint = (clientX: number, clientY: number) => {
    const box = plotPaperRef.current?.getBoundingClientRect();
    return box ? { x: clientX - box.left, y: clientY - box.top } : null;
  };

  const handleRulerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (tool === "label" && draggingPlotLabel) {
      setPlotLabelPointer(rulerLocalPoint(event.clientX, event.clientY));
      return;
    }
    if (tool !== "ruler") return;
    const local = rulerLocalPoint(event.clientX, event.clientY);
    if (draggingRulerLabel !== null && local) {
      setRulerMeasurements((previous) => previous.map((measurement, index) => index === draggingRulerLabel ? { ...measurement, labelX: local.x, labelY: local.y } : measurement));
      return;
    }
    setRulerPointer(local);
    setRulerHover(nearestRulerPoint(event.clientX, event.clientY));
  };

  const handleRulerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (tool === "label" && event.button === 0) {
      const label = nearestPlotLabel(event.clientX, event.clientY);
      if (label) {
        setDraggingPlotLabel(label.vowel);
        setPlotLabelPointer(rulerLocalPoint(event.clientX, event.clientY));
        event.currentTarget.setPointerCapture(event.pointerId);
      }
      return;
    }
    if (tool !== "ruler" || event.button !== 0) return;
    const local = rulerLocalPoint(event.clientX, event.clientY);
    if (!local) return;
    const labelIndex = rulerMeasurements.findIndex((measurement) => Math.hypot(local.x - measurement.labelX, local.y - measurement.labelY) < 24);
    if (labelIndex >= 0) { setDraggingRulerLabel(labelIndex); event.currentTarget.setPointerCapture(event.pointerId); return; }
    const point = nearestRulerPoint(event.clientX, event.clientY);
    if (!point) return;
    if (!rulerStart) { setRulerStart(point); return; }
    if (rulerStart === point || (rulerStart.type === point.type && rulerStart.x === point.x && rulerStart.y === point.y)) return;
    const first = rulerStart;
    const measurement: RulerMeasurement = { p1: first, p2: point, labelX: local.x, labelY: local.y - 18, distance: rulerDistanceLabelWithSettings(first, point) };
    setRulerMeasurements((previous) => [...previous, measurement]);
    setRulerStart(null);
  };

  const handleRulerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (tool === "label" && draggingPlotLabel && rulerContext) {
      const label = rulerContext.labels.find((item) => item.vowel === draggingPlotLabel);
      const data = plotDataFromClient(event.clientX, event.clientY);
      if (label && data) {
        const offsets = { [label.vowel]: [data.x - label.cx, data.y - label.cy] as [number, number] };
        void renderInteractive({ labelOffsets: offsets });
        setMessage(`${label.vowel} 라벨 위치를 저장했습니다.`);
      }
      setDraggingPlotLabel(null);
      setPlotLabelPointer(null);
    }
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    setDraggingRulerLabel(null);
  };

  const handleRulerContextMenu = (event: React.MouseEvent<HTMLDivElement>) => {
    if (tool !== "ruler") return;
    event.preventDefault();
    const local = rulerLocalPoint(event.clientX, event.clientY);
    const hit = local ? rulerMeasurements.findIndex((measurement) => {
      const a = rulerPointClient(measurement.p1); const b = rulerPointClient(measurement.p2);
      if (!a || !b) return false;
      const abx = b.x - a.x; const aby = b.y - a.y;
      const t = Math.max(0, Math.min(1, ((event.clientX - a.x) * abx + (event.clientY - a.y) * aby) / Math.max(1, abx * abx + aby * aby)));
      return Math.hypot(local.x - measurement.labelX, local.y - measurement.labelY) < 24 || Math.hypot(event.clientX - (a.x + t * abx), event.clientY - (a.y + t * aby)) < 12;
    }) : -1;
    if (hit >= 0) setRulerMeasurements((previous) => previous.filter((_, index) => index !== hit));
  };

  const rulerTooltip = (point: RulerPoint) => {
    const values = point.raw_f1 !== undefined && point.raw_f2 !== undefined
      ? `F1 ${point.raw_f1.toFixed(0)} Hz · F2 ${point.raw_f2.toFixed(0)} Hz`
      : `x ${point.x.toPrecision(4)} · y ${point.y.toPrecision(4)}`;
    return `${point.label || (point.type === "mean" ? "mean" : "raw")} · ${values}`;
  };

  const rulerDistanceLabelWithSettings = (first: RulerPoint, second: RulerPoint) => {
    const dx = second.x - first.x;
    const dy = second.y - first.y;
    if (first.raw_f1 !== undefined && first.raw_f2 !== undefined && second.raw_f1 !== undefined && second.raw_f2 !== undefined) {
      const bark = (value: number) => 26.81 / (1 + 1960 / value) - 0.53;
      const xHz = second.raw_f2 - first.raw_f2;
      const yHz = second.raw_f1 - first.raw_f1;
      const xBark = bark(second.raw_f2) - bark(first.raw_f2);
      const yBark = bark(second.raw_f1) - bark(first.raw_f1);
      if (rulerGeometryMode === "right-triangle") {
        return rulerDisplayMode === "hz"
          ? `${Math.hypot(xHz, yHz).toFixed(0)} Hz`
          : `${Math.hypot(xBark, yBark).toFixed(2)} Bk`;
      }
      const hz = Math.hypot(xHz, yHz);
      const barkDistance = Math.hypot(xBark, yBark);
      if (rulerDisplayMode === "hz") return `${hz.toFixed(0)} Hz`;
      return `${barkDistance.toFixed(2)} Bk`;
    }
    if (rulerGeometryMode === "right-triangle") return Math.hypot(dx, dy).toPrecision(4);
    return Math.hypot(dx, dy).toPrecision(4);
  };

  const rulerTriangleLabels = (first: RulerPoint, second: RulerPoint) => {
    const dx = second.x - first.x;
    const dy = second.y - first.y;
    if (first.raw_f1 !== undefined && first.raw_f2 !== undefined && second.raw_f1 !== undefined && second.raw_f2 !== undefined) {
      const bark = (value: number) => 26.81 / (1 + 1960 / value) - 0.53;
      const x = rulerDisplayMode === "hz" ? second.raw_f2 - first.raw_f2 : bark(second.raw_f2) - bark(first.raw_f2);
      const y = rulerDisplayMode === "hz" ? second.raw_f1 - first.raw_f1 : bark(second.raw_f1) - bark(first.raw_f1);
      const unit = rulerDisplayMode === "hz" ? "Hz" : "Bk";
      const digits = rulerDisplayMode === "hz" ? 0 : 2;
      const format = (value: number) => `${Math.abs(value).toFixed(digits)} ${unit}`;
      return { horizontal: format(x), vertical: format(y), hypotenuse: format(Math.hypot(x, y)) };
    }
    const format = (value: number) => Math.abs(value).toPrecision(4);
    return { horizontal: format(dx), vertical: format(dy), hypotenuse: format(Math.hypot(dx, dy)) };
  };

  useEffect(() => {
    if (tool !== "ruler") {
      setRulerStart(null);
      setRulerHover(null);
      setRulerPointer(null);
      setRulerMeasurements([]);
    }
    if (tool !== "label") {
      setDraggingPlotLabel(null);
      setPlotLabelPointer(null);
    }
  }, [tool]);

  useEffect(() => {
    setRulerMeasurements((previous) => previous.map((measurement) => ({
      ...measurement,
      distance: rulerDistanceLabelWithSettings(measurement.p1, measurement.p2),
    })));
  }, [rulerDisplayMode, rulerGeometryMode]);

  const fileCounter = useMemo(() => `${sources.length ? currentIndex + 1 : 0} / ${sources.length}`, [currentIndex, sources.length]);
  const effective = <K extends keyof DesignSettings,>(key: K): DesignSettings[K] => (selectedOverride[key] ?? design[key]) as DesignSettings[K];

  return (
    <main className={`interactive-plot-workspace ${leftOpen ? "" : "left-is-collapsed"} ${rightOpen ? "" : "right-is-collapsed"}`}>
      <header className="interactive-plot-header">
        <div className="plot-title-block"><span>단일 분석 · 대화형 플롯</span><h1 title={currentSource?.name}>{currentSource?.name ?? "데이터를 불러와 주세요"}</h1></div>
        <div className="plot-header-meta"><span className={`engine-state ${engineConnected ? "" : "is-offline"}`}><i /> 분석 엔진 {engineConnected ? "연결됨" : "연결 확인 중"}</span><span className="plot-notation">{xAxis} × F1 · {fileCounter}</span><button className="legacy-launch" onClick={() => void openLegacyPlot()} disabled={busy || !sources.length}>PySide 고급 편집 <ArrowUpRight size={14} /></button></div>
      </header>

      <aside className="plot-control-rail">
        <section className="file-navigator">
          <div className="navigator-topline"><div><span className="section-eyebrow">파일 탐색</span><strong>{fileCounter}</strong></div><button className="rail-collapse" aria-label="왼쪽 패널 접기" onClick={() => setLeftOpen(false)}><PanelLeftClose size={16} /></button></div>
          <div className="file-select-row"><button aria-label="이전 파일" onClick={() => void navigateTo(currentIndex - 1)} disabled={!canNavigate || currentIndex === 0}><ChevronLeft size={17} /></button><FileSelectMenu sources={sources} currentIndex={currentIndex} onNavigate={(index) => void navigateTo(index)} disabled={!sources.length} /><button aria-label="다음 파일" onClick={() => void navigateTo(currentIndex + 1)} disabled={!canNavigate || currentIndex >= sources.length - 1}><ChevronRight size={17} /></button></div>
        </section>

        <div className="control-tabs"><button className={leftPanel === "analysis" ? "is-active" : ""} onClick={() => setLeftPanel("analysis")}><SlidersHorizontal size={15} /> 분석 도구</button><button className={leftPanel === "global-design" ? "is-active" : ""} onClick={() => setLeftPanel("global-design")}><Palette size={15} /> 광역 디자인</button></div>

        <div className="control-scroll">
          {leftPanel === "analysis" ? (
            <>
              <section className="control-section range-section">
                <div className="section-heading"><div><span>01</span><strong>좌표축 범위</strong></div><small>{analysis?.use_bark_units ? "Bark" : "Hz"}</small></div>
                <div className="range-matrix">
                  <div className="range-matrix-head"><span>축</span><span>최솟값</span><span /><span>최댓값</span></div>
                  <div className="range-matrix-row"><strong>F1 <small>세로</small></strong><input value={ranges.y_min} onChange={(event) => setRanges({ ...ranges, y_min: event.target.value })} /><i>–</i><input value={ranges.y_max} onChange={(event) => setRanges({ ...ranges, y_max: event.target.value })} /></div>
                  <div className="range-matrix-row"><strong>{xAxis} <small>가로</small></strong><input value={ranges.x_min} onChange={(event) => setRanges({ ...ranges, x_min: event.target.value })} /><i>–</i><input value={ranges.x_max} onChange={(event) => setRanges({ ...ranges, x_max: event.target.value })} /></div>
                </div>
                <div className="ellipse-quick-row"><label><span>신뢰 타원 범위</span><span className="sigma-control"><select value={sigma} onChange={(event) => setSigma(event.target.value)}><option value="1.0">1.0</option><option value="1.5">1.5</option><option value="2.0">2.0</option><option value="2.5">2.5</option><option value="3.0">3.0</option></select><b>σ</b></span></label><ToggleSwitch label="타원 표시" checked={showEllipse} onChange={() => { const next = !showEllipse; setShowEllipse(next); void renderInteractive({ showEllipse: next }); }} /></div>
                <div className="paired-actions"><button onClick={resetPlot}><RefreshCcw size={14} /> 초기화</button><button className="primary" onClick={() => void renderInteractive()} disabled={busy}><Sparkles size={14} /> 범위 적용</button></div>
              </section>

              <section className="control-section"><div className="section-heading"><div><span>02</span><strong>분석 도구</strong></div></div><div className="tool-grid"><button onClick={() => setVowelAnalysisOpen(true)} disabled={!sources.length}><ScanSearch size={17} /><span><strong>모음 상세 분석</strong><small>통계와 분포 보기</small></span></button><button onClick={() => void openLegacyPlot()} disabled={!sources.length}><Layers3 size={17} /><span><strong>다중 플롯 모드</strong><small>파일 비교 구성</small></span></button><button className={tool === "ruler" ? "is-active" : ""} onClick={() => setTool(tool === "ruler" ? "select" : "ruler")}><Ruler size={17} /><span><strong>눈금자</strong><small>R · 거리 측정</small></span></button><button className={tool === "draw" ? "is-active" : ""} onClick={() => { setTool("draw"); setRightPanel("drawing"); setRightOpen(true); }}><PenLine size={17} /><span><strong>그리기</strong><small>P · 주석 도구</small></span></button></div></section>

              <section className="control-section export-section"><div className="section-heading"><div><span>03</span><strong>내보내기</strong></div></div><div className="format-buttons"><button onClick={() => void exportInteractive("jpg")} disabled={!previewUrl}>JPG</button><button onClick={() => void exportInteractive("png")} disabled={!previewUrl}>PNG</button><button onClick={() => void exportInteractive("svg")} disabled={!sources.length}>SVG</button></div><button className="wide-action" onClick={() => void saveProject()} disabled={busy || !sources.length}><Save size={15} /> 프로젝트 저장</button><button className="wide-action primary" onClick={() => setBatchExportOpen(true)} disabled={busy || !sources.length}><Download size={15} /> 일괄 저장</button></section>
            </>
          ) : (
            <>
              <section className="control-section">
                <div className="section-heading"><div><span>01</span><strong>텍스트와 라벨</strong></div><small>전체 레이어</small></div>
                <div className="palette-picker-row">
                  <PalettePicker label="라벨 색상" value={design.lbl_color} onChange={(lbl_color) => lbl_color && updateDesign({ lbl_color })} />
                </div>
                <div className="text-style-block">
                  <span className="control-label">텍스트 설정</span>
                  <div className="text-style-row">
                    <label className="select-field compact"><span>글꼴</span><select value={design.font_style} onChange={(event) => updateDesign({ font_style: event.target.value })}><option value="serif">명조체</option><option value="sans">고딕체</option></select></label>
                    <div className="font-controls">
                      <select value={design.lbl_size} onChange={(event) => updateDesign({ lbl_size: Number(event.target.value) })}><option>14</option><option>16</option><option>18</option><option>20</option><option>24</option><option>28</option></select>
                      <span>pt</span>
                      <button type="button" className={design.lbl_bold ? "is-active" : ""} onClick={() => updateDesign({ lbl_bold: !design.lbl_bold })}><Bold size={15} /></button>
                      <button type="button" className={design.lbl_italic ? "is-active" : ""} onClick={() => updateDesign({ lbl_italic: !design.lbl_italic })}><Italic size={15} /></button>
                    </div>
                  </div>
                </div>
              </section>

              <section className="control-section">
                <div className="section-heading"><div><span>02</span><strong>중심점과 원자료</strong></div></div>
                <div className="switch-stack">
                  <ToggleSwitch label="모음 중심점 표시" checked={design.show_centroid} onChange={() => updateDesign({ show_centroid: !design.show_centroid })} />
                  <ToggleSwitch label="원자료 점 표시" checked={design.show_raw} onChange={() => updateDesign({ show_raw: !design.show_raw })} />
                </div>
                <label className="control-label">모음 중심점 모양</label>
                <MarkerPicker value={design.centroid_marker} onChange={(centroid_marker) => updateDesign({ centroid_marker })} />
                <label className="control-label">원자료 점 모양</label>
                <div className="segmented-row">
                  <button type="button" className={design.raw_marker === "o" ? "is-active" : ""} onClick={() => updateDesign({ raw_marker: "o" })}>빈 원</button>
                  <button type="button" className={design.raw_marker === "x" ? "is-active" : ""} onClick={() => updateDesign({ raw_marker: "x" })}>가위표</button>
                  <button type="button" className={design.raw_marker === "a" ? "is-active" : ""} onClick={() => updateDesign({ raw_marker: "a" })}>라벨</button>
                </div>
                <div className="palette-picker-row"><PalettePicker label="원자료 색상" value={design.raw_color} onChange={(raw_color) => raw_color && updateDesign({ raw_color })} /></div>
              </section>

              <section className="control-section"><div className="section-heading"><div><span>03</span><strong>신뢰 타원</strong></div></div><div className="segmented-row"><button type="button" className={design.ell_thick === 0.5 ? "is-active" : ""} onClick={() => updateDesign({ ell_thick: 0.5 })}>얇게</button><button type="button" className={design.ell_thick === 1 ? "is-active" : ""} onClick={() => updateDesign({ ell_thick: 1 })}>보통</button><button type="button" className={design.ell_thick === 2 ? "is-active" : ""} onClick={() => updateDesign({ ell_thick: 2 })}>굵게</button></div><div className="segmented-row"><button type="button" className={design.ell_style === "-" ? "is-active" : ""} onClick={() => updateDesign({ ell_style: "-" })}>실선</button><button type="button" className={design.ell_style === "--" ? "is-active" : ""} onClick={() => updateDesign({ ell_style: "--" })}>파선</button><button type="button" className={design.ell_style === ":" ? "is-active" : ""} onClick={() => updateDesign({ ell_style: ":" })}>점선</button></div><div className="palette-picker-row"><PalettePicker label="선 색상" value={design.ell_color} onChange={(ell_color) => updateDesign({ ell_color })} allowTransparent /><PalettePicker label="채우기" value={design.ell_fill_color} onChange={(ell_fill_color) => updateDesign({ ell_fill_color })} allowTransparent /></div><label className="opacity-control"><span>채우기 투명도 <b>{Math.round(design.ell_fill_opacity * 100)}%</b></span><input type="range" min="0" max="60" value={design.ell_fill_opacity * 100} onChange={(event) => updateDesign({ ell_fill_opacity: Number(event.target.value) / 100 })} /></label></section>

              <section className="control-section"><div className="section-heading"><div><span>04</span><strong>플롯 배경과 축</strong></div></div><div className="switch-stack"><ToggleSwitch label="격자 표시" checked={design.show_grid} onChange={() => updateDesign({ show_grid: !design.show_grid })} /><ToggleSwitch label="테두리 축" checked={design.box_spines} onChange={() => updateDesign({ box_spines: !design.box_spines })} /><ToggleSwitch label="축 단위 표시" checked={design.show_axis_units} onChange={() => updateDesign({ show_axis_units: !design.show_axis_units })} /></div>{design.show_grid ? <label className="opacity-control"><span>격자 투명도 <b>{Math.round(design.grid_opacity * 100)}%</b></span><input type="range" min="5" max="80" value={design.grid_opacity * 100} onChange={(event) => updateDesign({ grid_opacity: Number(event.target.value) / 100 })} /></label> : null}</section>

              <details className="advanced-options"><summary>고급 옵션 <ChevronDown size={14} /></summary><div className="advanced-body"><div className="switch-stack"><ToggleSwitch label="라벨 슬래시 감싸기" checked={design.label_slash_wrap} onChange={() => updateDesign({ label_slash_wrap: !design.label_slash_wrap })} /><ToggleSwitch label="보조 눈금" checked={design.show_minor_ticks} onChange={() => updateDesign({ show_minor_ticks: !design.show_minor_ticks })} /><ToggleSwitch label="축 위치 반전" checked={design.axis_position_swap} onChange={() => updateDesign({ axis_position_swap: !design.axis_position_swap })} /><ToggleSwitch label="세로축 라벨 회전" checked={design.y_label_rotation} onChange={() => updateDesign({ y_label_rotation: !design.y_label_rotation })} /></div></div></details>
              <button className="wide-action global-design-reset" onClick={resetPlot}><RefreshCcw size={14} /> 광역 디자인 초기화</button>
            </>
          )}
        </div>
      </aside>

      <section className={`interactive-plot-stage tool-${tool}`}>
        <div className="plot-toolbar"><div className="toolbar-leading">{!leftOpen ? <button className="sidebar-reopen" onClick={() => setLeftOpen(true)}><PanelLeftOpen size={16} /> 도구</button> : null}<div className="toolbar-group"><button className={tool === "select" ? "is-active" : ""} onClick={() => setTool("select")}><MousePointer2 size={16} /> 선택</button><div className="ruler-tool-cluster"><button className={tool === "ruler" ? "is-active" : ""} onClick={() => setTool("ruler")}><Ruler size={16} /> 눈금자</button><button type="button" className={`tool-settings-button ${rulerSettingsOpen ? "is-active" : ""}`} onClick={() => setRulerSettingsOpen((previous) => !previous)} aria-label="눈금자 설정" title="눈금자 설정"><SlidersHorizontal size={14} /></button>{rulerSettingsOpen ? <div className="ruler-settings-popover"><div className="ruler-settings-header"><strong>눈금자 설정</strong><span>측정 방식</span></div><div className="ruler-mode-choices"><button type="button" className={`ruler-mode-choice ${rulerGeometryMode === "direct" ? "is-active" : ""}`} onClick={() => setRulerGeometryMode("direct")}><svg viewBox="0 0 44 22" aria-hidden><line x1="5" y1="17" x2="39" y2="5" /><circle cx="5" cy="17" r="2" /><circle cx="39" cy="5" r="2" /></svg><span>직선</span></button><button type="button" className={`ruler-mode-choice ${rulerGeometryMode === "right-triangle" ? "is-active" : ""}`} onClick={() => setRulerGeometryMode("right-triangle")}><svg viewBox="0 0 44 22" aria-hidden><path d="M5 17H39V5" /><line className="hypotenuse" x1="5" y1="17" x2="39" y2="5" /><path className="right-angle" d="M34 17v-5h5" /></svg><span>Δx · Δy</span></button></div><div className="ruler-unit-row"><span>표시 단위</span><div className="ruler-unit-toggles"><button type="button" className={`ruler-unit-toggle ${rulerDisplayMode === "hz" ? "is-on" : ""}`} aria-pressed={rulerDisplayMode === "hz"} onClick={() => setRulerDisplayMode("hz")}>Hz</button><button type="button" className={`ruler-unit-toggle ${rulerDisplayMode === "bark" ? "is-on" : ""}`} aria-pressed={rulerDisplayMode === "bark"} onClick={() => setRulerDisplayMode("bark")}>Bark</button></div></div></div> : null}</div><button className={tool === "label" ? "is-active" : ""} onClick={() => { setTool("label"); setMessage("라벨 이동 모드 · 라벨을 드래그하세요."); }}><MousePointer2 size={16} /> 라벨 이동</button><button className={tool === "draw" ? "is-active" : ""} onClick={() => { setTool("draw"); setRightPanel("drawing"); setRightOpen(true); }}><PenLine size={16} /> 그리기</button></div></div><div className="toolbar-context"><span>{analysis?.normalization ?? "정규화 없음"}</span><span>{analysis?.origin === "top_right" ? "Praat 좌표" : "수학 좌표"}</span>{!rightOpen ? <button className="sidebar-reopen" onClick={() => setRightOpen(true)}>레이어 <PanelRightOpen size={16} /></button> : null}</div></div>
        <div className="plot-canvas-shell"><div className="plot-paper" ref={plotPaperRef}>{previewUrl ? <><img ref={plotImageRef} src={previewUrl} alt={`${currentSource?.name ?? "현재 파일"} 포먼트 플롯`} /><div className="ruler-overlay" onPointerMove={handleRulerMove} onPointerDown={handleRulerDown} onPointerUp={handleRulerUp} onContextMenu={handleRulerContextMenu}>
          {tool === "label" && rulerContext ? rulerContext.labels.map((label) => { const screen = plotLabelClient(label); const paper = plotPaperRef.current?.getBoundingClientRect(); if (!screen || !paper) return null; const isDragging = draggingPlotLabel === label.vowel && plotLabelPointer; const left = isDragging ? plotLabelPointer.x : screen.x - paper.left; const top = isDragging ? plotLabelPointer.y : screen.y - paper.top; return <span className="plot-label-hit-target" key={`label-${label.vowel}`} style={{ left, top }} title={`${label.vowel} 라벨 이동`} />; }) : null}
         {tool === "ruler" ? rulerMeasurements.map((measurement, index) => { const a = rulerPointClient(measurement.p1); const b = rulerPointClient(measurement.p2); const paper = plotPaperRef.current?.getBoundingClientRect(); if (!a || !b || !paper) return null; const x1 = a.x - paper.left; const y1 = a.y - paper.top; const x2 = b.x - paper.left; const y2 = b.y - paper.top; const triangleLabels = rulerGeometryMode === "right-triangle" ? rulerTriangleLabels(measurement.p1, measurement.p2) : null; return <div className="ruler-measurement" key={`${measurement.p1.x}-${measurement.p2.x}-${index}`}><svg className="ruler-line-layer" aria-hidden>{rulerGeometryMode === "right-triangle" ? <><polyline points={`${x1},${y1} ${x2},${y1} ${x2},${y2}`} /><line x1={x1} y1={y1} x2={x2} y2={y2} /></> : <line x1={x1} y1={y1} x2={x2} y2={y2} />}</svg><span className="ruler-point ruler-point-start" style={{ left: x1, top: y1, borderColor: measurement.p1.color }} /><span className="ruler-point ruler-point-end" style={{ left: x2, top: y2, borderColor: measurement.p2.color }} />{triangleLabels ? <><span className="ruler-side-label ruler-side-label-horizontal" style={{ left: (x1 + x2) / 2, top: y1 }}>{triangleLabels.horizontal}</span><span className="ruler-side-label ruler-side-label-vertical" style={{ left: x2, top: (y1 + y2) / 2 }}>{triangleLabels.vertical}</span><span className="ruler-side-label ruler-side-label-hypotenuse" style={{ left: (x1 + x2) / 2, top: (y1 + y2) / 2 }}>{triangleLabels.hypotenuse}</span></> : <button type="button" tabIndex={-1} aria-label={`거리 ${measurement.distance}`} className="ruler-label" style={{ left: measurement.labelX, top: measurement.labelY }} onPointerDown={(event) => { event.stopPropagation(); setDraggingRulerLabel(index); event.currentTarget.setPointerCapture(event.pointerId); }}>{measurement.distance}</button>}</div>; }) : null}
          {tool === "ruler" && rulerStart ? (() => { const screen = rulerPointClient(rulerStart); const paper = plotPaperRef.current?.getBoundingClientRect(); return screen && paper ? <span className={`ruler-snap-marker ${rulerStart.type === "mean" ? "is-mean" : "is-raw"}`} style={{ left: screen.x - paper.left, top: screen.y - paper.top, borderColor: rulerStart.color }} /> : null; })() : null}
          {tool === "ruler" && rulerStart && rulerPointer ? <svg className="ruler-guide-layer" aria-hidden><line x1={rulerPointClient(rulerStart) ? (rulerPointClient(rulerStart)!.x - (plotPaperRef.current?.getBoundingClientRect().left ?? 0)) : 0} y1={rulerPointClient(rulerStart) ? (rulerPointClient(rulerStart)!.y - (plotPaperRef.current?.getBoundingClientRect().top ?? 0)) : 0} x2={rulerPointer.x} y2={rulerPointer.y} /></svg> : null}
          {tool === "ruler" && rulerHover ? (() => { const screen = rulerPointClient(rulerHover); const paper = plotPaperRef.current?.getBoundingClientRect(); return screen && paper ? <><span className={`ruler-snap-marker ${rulerHover.type === "mean" ? "is-mean" : "is-raw"}`} style={{ left: screen.x - paper.left, top: screen.y - paper.top, borderColor: rulerHover.color }} /><span className="ruler-tooltip" style={{ left: screen.x - paper.left + 12, top: screen.y - paper.top - 30 }}>{rulerTooltip(rulerHover)}</span></> : null; })() : null}
        </div></> : <div className="plot-placeholder"><Layers3 size={30} /><strong>표시할 플롯이 없습니다</strong><span>메인 창에서 데이터 파일을 불러와 주세요.</span></div>}</div></div>
        <footer className="plot-stage-footer"><span>{message}</span><span title={previewInfo}>{previewInfo || currentSource?.name || "대기 중"}</span></footer>
      </section>

      <aside className="layer-inspector">
        <header className="layer-inspector-header"><div><span className="section-eyebrow">{rightPanel === "layers" ? "레이어 디자인" : "그리기 디자인"}</span><strong>{rightPanel === "layers" ? `${currentVowels.length}개 모음` : "주석 도구"}</strong></div><button className="rail-collapse" aria-label="오른쪽 패널 접기" onClick={() => setRightOpen(false)}><PanelRightClose size={16} /></button></header>
        <div className="layer-panel-tabs"><button type="button" className={rightPanel === "layers" ? "is-active" : ""} onClick={() => setRightPanel("layers")}><Layers3 size={15} /> 레이어</button><button type="button" className={rightPanel === "drawing" ? "is-active" : ""} onClick={() => { setRightPanel("drawing"); setTool("draw"); }}><PenLine size={15} /> 그리기</button></div>
        {rightPanel === "layers" ? (
        <div className="layer-split-layout" style={{ "--layer-list-height": `${layerListHeight}px` } as CSSProperties}>
        <div className="layer-inspector-scroll">
          {selectedLayer ? (
            <div className={`selected-layer-design ${selectedLocked ? "is-locked" : ""}`}>
              <div className="selected-layer-heading">
                <div><span>선택 레이어</span><strong>{selectedLayer}</strong></div>
                {selectedLocked ? <span><Lock size={12} /> 잠김</span> : <button type="button" onClick={resetSelectedLayer}><RefreshCcw size={13} /> 초기화</button>}
              </div>
              <fieldset className="layer-design-form" disabled={selectedLocked}>
                <div className="palette-picker-row">
                  <PalettePicker label="라벨 색상" value={String(effective("lbl_color"))} onChange={(lbl_color) => lbl_color && updateLayerDesign({ lbl_color })} disabled={selectedLocked} />
                </div>
                <div className="text-style-block">
                  <span className="control-label">텍스트 설정</span>
                  <div className="font-controls">
                    <select value={Number(effective("lbl_size"))} onChange={(event) => updateLayerDesign({ lbl_size: Number(event.target.value) })}><option>14</option><option>16</option><option>18</option><option>20</option><option>24</option><option>28</option></select>
                    <span>pt</span>
                    <button type="button" className={effective("lbl_bold") ? "is-active" : ""} onClick={() => updateLayerDesign({ lbl_bold: !effective("lbl_bold") })}><Bold size={15} /></button>
                    <button type="button" className={effective("lbl_italic") ? "is-active" : ""} onClick={() => updateLayerDesign({ lbl_italic: !effective("lbl_italic") })}><Italic size={15} /></button>
                  </div>
                </div>
                <label className="control-label">중심점 모양</label>
                <MarkerPicker value={String(effective("centroid_marker"))} onChange={(centroid_marker) => updateLayerDesign({ centroid_marker })} disabled={selectedLocked} />
                <label className="control-label">신뢰 타원</label>
                <div className="segmented-row"><button type="button" className={Number(effective("ell_thick")) === 0.5 ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_thick: 0.5 })}>얇게</button><button type="button" className={Number(effective("ell_thick")) === 1 ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_thick: 1 })}>보통</button><button type="button" className={Number(effective("ell_thick")) === 2 ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_thick: 2 })}>굵게</button></div>
                <div className="segmented-row"><button type="button" className={effective("ell_style") === "-" ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_style: "-" })}>실선</button><button type="button" className={effective("ell_style") === "--" ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_style: "--" })}>파선</button><button type="button" className={effective("ell_style") === ":" ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_style: ":" })}>점선</button></div>
                <div className="palette-picker-row"><PalettePicker label="타원 선" value={effective("ell_color")} onChange={(ell_color) => updateLayerDesign({ ell_color })} allowTransparent disabled={selectedLocked} /><PalettePicker label="타원 채우기" value={effective("ell_fill_color")} onChange={(ell_fill_color) => updateLayerDesign({ ell_fill_color })} allowTransparent disabled={selectedLocked} /></div>
                <label className="opacity-control"><span>레이어 타원 투명도 <b>{Math.round(Number(effective("ell_fill_opacity")) * 100)}%</b></span><input type="range" min="0" max="60" value={Number(effective("ell_fill_opacity")) * 100} onChange={(event) => updateLayerDesign({ ell_fill_opacity: Number(event.target.value) / 100 })} /></label>
                <label className="control-label">원자료 점</label>
                <div className="palette-picker-row"><PalettePicker label="원자료 색상" value={effective("raw_color")} onChange={(raw_color) => raw_color && updateLayerDesign({ raw_color })} disabled={selectedLocked} /></div>
                <div className="segmented-row"><button type="button" className={effective("raw_marker") === "o" ? "is-active" : ""} onClick={() => updateLayerDesign({ raw_marker: "o" })}>빈 원</button><button type="button" className={effective("raw_marker") === "x" ? "is-active" : ""} onClick={() => updateLayerDesign({ raw_marker: "x" })}>가위표</button><button type="button" className={effective("raw_marker") === "a" ? "is-active" : ""} onClick={() => updateLayerDesign({ raw_marker: "a" })}>라벨</button></div>
                <details className="layer-advanced layer-text-options" open>
                  <summary>고급 옵션 <ChevronDown size={14} /></summary>
                  <div className="switch-stack">
                    <ToggleSwitch label="라벨 슬래시 감싸기" checked={Boolean(effective("label_slash_wrap"))} onChange={() => updateLayerDesign({ label_slash_wrap: !effective("label_slash_wrap") })} disabled={selectedLocked} />
                  </div>
                </details>
              </fieldset>
            </div>
          ) : <p className="empty-layers">레이어를 선택하면 디자인을 편집할 수 있습니다.</p>}
        </div>
        <div className="layer-splitter" role="separator" aria-orientation="horizontal" aria-label="레이어 디자인과 목록 높이 조절" onPointerDown={beginLayerPanelResize} onPointerMove={resizeLayerPanels} onPointerUp={endLayerPanelResize} onPointerCancel={endLayerPanelResize} onLostPointerCapture={cancelLayerPanelResize}><i /></div>
        <div className="layer-list-dock">
          <div className="layer-batch-row"><span>일괄 적용</span><button type="button" onClick={toggleAllLayerEyes}><Eye size={14} /> 전체 표시</button><button type="button" onClick={toggleAllLayerSemi}>반투명</button></div>
          <div className="layer-list-toolbar"><span><GripVertical size={12} /> 끌어서 순서 변경</span><button type="button" onClick={resetLayerOrder}><RefreshCcw size={11} /> 순서 초기화</button></div>
          <div className="layer-list" ref={layerListRef}>
            {layerOrder.length ? layerOrder.map((vowel) => {
              const visibility = layerState[vowel] ?? "ON";
              const locked = lockedLayers.has(vowel);
              const effects = layerOverrides[vowel] ?? {};
              const effectKeys = DESIGN_EFFECT_ORDER.filter((key) => key in effects);
              const expanded = effectKeys.length > 0 && expandedLayers.has(vowel);
              return (
                <div
                  className={`layer-row visibility-${visibility.toLowerCase()} ${selectedLayers.has(vowel) ? "is-selected" : ""} ${draggingLayer === vowel ? "is-dragging" : ""} ${dropTarget?.vowel === vowel ? dropTarget.after ? "drop-after" : "drop-before" : ""}`}
                  key={vowel}
                  data-layer-vowel={vowel}
                  ref={(element) => { if (element) layerRowRefs.current.set(vowel, element); else layerRowRefs.current.delete(vowel); }}
                >
                  <div className="layer-row-main" onLostPointerCapture={() => { if (draggingLayerRef.current === vowel) cancelLayerDrag(); }}>
                    <button type="button" className="layer-drag-handle" onPointerDown={(event) => beginLayerDrag(event, vowel)} onPointerMove={moveLayerDrag} onPointerUp={commitLayerDrag} onPointerCancel={cancelLayerDrag} onKeyDown={(event) => { if (event.key === "ArrowUp" || event.key === "ArrowDown") { event.preventDefault(); moveLayerByStep(vowel, event.key === "ArrowUp" ? -1 : 1); } }} aria-label={`${vowel} 레이어 순서 이동`} title="끌어서 이동 · 방향키로 한 칸 이동"><GripVertical size={15} /></button>
                    <button type="button" className="layer-visibility" onClick={() => toggleLayerEye(vowel)} title={visibility === "OFF" ? "레이어 표시" : "레이어 숨기기"}>{visibility === "OFF" ? <EyeOff size={15} /> : <Eye size={15} />}</button>
                    <button type="button" className={`layer-semi ${visibility === "SEMI" ? "is-active" : ""}`} onClick={() => toggleLayerSemi(vowel)}>반투명</button>
                    <button type="button" className="layer-name" onMouseDown={(event) => { if (event.button === 0) event.preventDefault(); }} onClick={(event) => selectLayer(vowel, event)}><strong>{vowel}</strong></button>
                    {effectKeys.length ? <button type="button" className={`layer-expand ${expanded ? "is-expanded" : ""}`} onClick={() => setExpandedLayers((previous) => { const next = new Set(previous); if (next.has(vowel)) next.delete(vowel); else next.add(vowel); return next; })} aria-label={`${vowel} 디자인 변경 내역 ${expanded ? "접기" : "펼치기"}`}><ChevronDown size={14} /><span>{effectKeys.length}</span></button> : null}
                    <button type="button" className="layer-lock" onClick={() => void toggleLock(vowel)} aria-label={locked ? `${vowel} 레이어 잠금 해제` : `${vowel} 레이어 잠금`}>{locked ? <Lock size={14} /> : <Unlock size={14} />}</button>
                  </div>
                  {expanded ? (
                    <div className="layer-effects" aria-label={`${vowel} 레이어 디자인 변경 내역`}>
                      {effectKeys.map((key) => {
                        const value = effects[key] as DesignSettings[keyof DesignSettings];
                        const isColor = key === "lbl_color" || key === "ell_color" || key === "ell_fill_color" || key === "raw_color";
                        return (
                          <div className="layer-effect-row" key={key}>
                            <span>{DESIGN_EFFECT_LABELS[key] ?? key}</span>
                            <strong>{isColor ? <><i className={`effect-color ${value === null ? "is-transparent" : ""}`} style={typeof value === "string" ? { background: value } : undefined} /><em>{value === null ? "투명" : String(value).toUpperCase()}</em></> : effectDisplayValue(key, value)}</strong>
                            <button type="button" disabled={locked} onClick={() => removeLayerEffect(vowel, key)} aria-label={`${DESIGN_EFFECT_LABELS[key] ?? key} 설정 제거`}><X size={13} /></button>
                          </div>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              );
            }) : <p className="empty-layers">현재 파일에서 모음 라벨을 찾지 못했습니다.</p>}
          </div>
        </div>
        </div>
        ) : (
        <div className="layer-split-layout drawing-split-layout" style={{ "--layer-list-height": `${layerListHeight}px` } as CSSProperties}>
          <div className="drawing-panel">
            <section>
              <div className="drawing-panel-heading"><span>그리기 도구</span><small>캔버스에 추가할 주석 유형</small></div>
              <div className="drawing-tool-grid">
                <button type="button" className={drawTool === "text" ? "is-active" : ""} onClick={() => activateDrawTool("text")}><span className="draw-tool-icon">T</span><span><strong>텍스트</strong><small>설명과 라벨</small></span></button>
                <button type="button" className={drawTool === "line" ? "is-active" : ""} onClick={() => activateDrawTool("line")}><PenLine size={16} /><span><strong>선</strong><small>직선과 화살표</small></span></button>
                <button type="button" className={drawTool === "area" ? "is-active" : ""} onClick={() => activateDrawTool("area")}><ScanSearch size={16} /><span><strong>영역</strong><small>강조 범위</small></span></button>
                <button type="button" className={drawTool === "reference" ? "is-active" : ""} onClick={() => activateDrawTool("reference")}><Ruler size={16} /><span><strong>기준선</strong><small>축 기준 표시</small></span></button>
              </div>
            </section>
            <section className="drawing-style-card">
              <div className="drawing-panel-heading"><span>현재 도구</span><strong>{drawTool === "text" ? "텍스트" : drawTool === "line" ? "선" : drawTool === "area" ? "영역" : "기준선"}</strong></div>
              <div className="palette-picker-row"><PalettePicker label="그리기 색상" value={drawColor} onChange={setDrawColor} /></div>
              <label className="opacity-control"><span>선 두께 <b>{drawWidth}px</b></span><input type="range" min="1" max="8" value={drawWidth} onChange={(event) => setDrawWidth(Number(event.target.value))} /></label>
              <button type="button" className="wide-action primary" onClick={() => activateDrawTool(drawTool)}><PenLine size={14} /> 캔버스에서 그리기</button>
            </section>
          </div>
          <div className="layer-splitter" role="separator" aria-orientation="horizontal" aria-label="그리기 디자인과 목록 높이 조절" onPointerDown={beginLayerPanelResize} onPointerMove={resizeLayerPanels} onPointerUp={endLayerPanelResize} onPointerCancel={endLayerPanelResize} onLostPointerCapture={cancelLayerPanelResize}><i /></div>
          <div className="drawing-layer-dock">
            <div className="drawing-list-toolbar"><span>그리기 레이어</span><button type="button" disabled>일괄 삭제</button></div>
            <div className="drawing-empty"><PenLine size={20} /><strong>아직 그리기 레이어가 없습니다</strong><span>도구를 선택한 뒤 플롯 위에서 그려 주세요.</span><button type="button" onClick={() => void openLegacyPlot()}>PySide 고급 그리기 <ArrowUpRight size={12} /></button></div>
          </div>
        </div>
        )}
      </aside>
      {batchExportOpen ? <div className="batch-export-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !batchExportBusy) setBatchExportOpen(false); }}>
        <section className="batch-export-dialog" role="dialog" aria-modal="true" aria-labelledby="batch-export-title">
          <header><div><span className="section-eyebrow">EXPORT WORKSPACE</span><h2 id="batch-export-title">일괄 저장</h2><p>현재 React/Tauri 플롯 설정을 모든 파일에 적용해 저장합니다.</p></div><button type="button" onClick={() => setBatchExportOpen(false)} disabled={batchExportBusy} aria-label="닫기"><X size={18} /></button></header>
          <div className="batch-export-body">
            <div className="batch-export-summary"><strong>{sources.length}개 파일</strong><span>범위 · 디자인 · 레이어 상태 · 라벨 위치 포함</span></div>
            <label className="batch-export-field"><span>파일 형식</span><div className="batch-format-picker">{(["png", "jpg", "svg"] as const).map((format) => <button type="button" key={format} className={batchExportFormat === format ? "is-active" : ""} onClick={() => setBatchExportFormat(format)}>{format.toUpperCase()}</button>)}</div></label>
            <label className="batch-export-field"><span>저장 폴더</span><div className="batch-directory-row"><input value={batchExportDirectory} readOnly placeholder="폴더를 선택하세요" /><button type="button" onClick={() => void chooseBatchDirectory()} disabled={batchExportBusy}>찾아보기</button></div></label>
            <div className="batch-export-options"><span>반영할 항목</span><label><input type="checkbox" checked={batchApplyGlobalDesign} onChange={(event) => setBatchApplyGlobalDesign(event.target.checked)} /> 광역 디자인</label><label><input type="checkbox" checked={batchApplyLayerDesign} onChange={(event) => setBatchApplyLayerDesign(event.target.checked)} /> 레이어 디자인</label><label><input type="checkbox" checked={batchApplyVisibility} onChange={(event) => setBatchApplyVisibility(event.target.checked)} /> 레이어 표시 상태</label><label><input type="checkbox" checked={batchApplyLabelPositions} onChange={(event) => setBatchApplyLabelPositions(event.target.checked)} /> 라벨 위치</label></div>
            <p className="batch-export-note">동일한 파일명이 있으면 자동으로 `_2`, `_3` suffix를 붙입니다.</p>
          </div>
          <footer><button type="button" className="wide-action" onClick={() => setBatchExportOpen(false)} disabled={batchExportBusy}>취소</button><button type="button" className="wide-action primary" onClick={() => void runBatchExport()} disabled={!batchExportDirectory || batchExportBusy}>{batchExportBusy ? "저장 중…" : "일괄 저장 시작"}</button></footer>
        </section>
      </div> : null}
      {vowelAnalysisOpen ? <VowelAnalysisShell currentSource={currentSource} sources={sources} currentIndex={currentIndex} onNavigate={(index) => void navigateTo(index)} onClose={() => setVowelAnalysisOpen(false)} /> : null}
    </main>
  );
}
