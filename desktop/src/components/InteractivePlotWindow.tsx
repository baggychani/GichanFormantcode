import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open, save } from "@tauri-apps/plugin-dialog";
import {
  ArrowUpRight,
  ArrowDown,
  ArrowUp,
  BarChart3,
  Bold,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  CircleHelp,
  Download,
  Eye,
  EyeOff,
  GripVertical,
  Italic,
  Layers3,
  List,
  Loader2,
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
import { cacheMapSet } from "../cacheMap";
import { formatPValue } from "../formatStats";
import { useFocusTrap } from "../useFocusTrap";
import { sortVowels } from "../vowelSort";
import {
  barkToHz,
  formatRulerDistance,
  formatRulerPointTooltip,
  formatRulerTriangleLegs,
  hzToBark,
  resolvePlotUnits,
  smartAxisRanges,
} from "../plotUnits";
import { FormantStatsTable } from "./FormantStatsTable";
import "./InteractivePlotWindow.css";

type SidecarEvent = { event: string; payload: Record<string, unknown> };
type Tool = "select" | "ruler" | "label" | "draw";
type RulerPoint = { x: number; y: number; px: number; py: number; type: "raw" | "mean"; label: string; color: string; raw_f1?: number; raw_f2?: number };
type PlotLabel = { vowel: string; display_vowel?: string; cx: number; cy: number; lx: number; ly: number; px: number; py: number; lpx: number; lpy: number; bbox?: { left: number; top: number; width: number; height: number } | null; fontsize?: number; ha?: "left" | "center" | "right"; va?: "bottom" | "center" | "top"; lbl_color?: string; lbl_bold?: boolean | string; lbl_italic?: boolean };
/** 라벨 bbox와 동일 — PNG 상단 원점 픽셀 */
type TextBounds = { x: number; y: number; left: number; top: number; width: number; height: number; apx: number; apy: number };
type RulerContext = { image_width: number; image_height: number; axes_bbox: { left: number; bottom: number; width: number; height: number }; points: RulerPoint[]; labels: PlotLabel[]; xlim: [number, number]; ylim: [number, number]; legend_bounds?: Record<string, { fx: number; fy: number; width_frac: number; height_frac: number }>; text_bounds?: Record<string, TextBounds>; params: { normalization?: string | null; use_bark_units?: boolean; f1_scale?: string; f2_scale?: string } };
type RulerMeasurement = { p1: RulerPoint; p2: RulerPoint; labelX: number; labelY: number; distance: string };
type RulerGeometryMode = "direct" | "right-triangle";
type RulerDisplayMode = "hz" | "bark";
type LeftPanel = "analysis" | "global-design";
type RightPanel = "layers" | "drawing";
type DrawTool = "text" | "line" | "area" | "reference" | "legend";
type DrawArrowMode = "none" | "end" | "all";
type DrawArrowHead = "stealth" | "open" | "latex";
type DrawPoint = { x: number; y: number; label?: string; px?: number; py?: number };
type DrawLineObject = {
  type: "line";
  id: string;
  points: Array<[number, number]>;
  line_color: string;
  line_style: string;
  line_width: number;
  arrow_mode: DrawArrowMode;
  arrow_head: DrawArrowHead;
  visible: boolean;
  semi: boolean;
};
type DrawLegendEntry = { series_id: number; text: string };
type DrawLegendObject = {
  type: "legend";
  id: string;
  name: string;
  entries: DrawLegendEntry[];
  fx: number;
  fy: number;
  width_frac: number;
  height_frac: number;
  font_size: number;
  font_family: string;
  font_weight: "regular" | "medium" | "semibold" | "bold";
  font_italic: boolean;
  show_border: boolean;
  border_style: string;
  border_color: string;
  show_fill: boolean;
  fill_color: string;
  fill_opacity: number;
  visible: boolean;
  semi: boolean;
};
type DrawReferenceObject = {
  type: "reference";
  id: string;
  mode: "horizontal" | "vertical";
  value: number;
  axis_units: string;
  axis_name: string;
  axis_scale: string;
  line_style: string;
  line_color: string | null;
  visible: boolean;
  semi: boolean;
};
type DrawPolygonObject = {
  type: "polygon";
  id: string;
  points: Array<[number, number]>;
  border_style: string;
  border_color: string;
  fill_color: string | null;
  fill_opacity: number;
  show_area_label: boolean;
  visible: boolean;
  semi: boolean;
};
type DrawTextObject = {
  type: "text";
  id: string;
  text: string;
  x: number;
  y: number;
  font_size: number;
  font_family: string;
  font_weight: DesignSettings["font_weight"];
  font_bold: boolean;
  font_italic: boolean;
  line_spacing: number;
  text_color: string;
  axis_units: string;
  visible: boolean;
  semi: boolean;
};
type DrawObject = DrawLineObject | DrawLegendObject | DrawReferenceObject | DrawPolygonObject | DrawTextObject;
type ReferencePreview = {
  mode: "horizontal" | "vertical";
  plotValue: number;
  label: string;
  snapped: boolean;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};
type LegendDraft = Omit<DrawLegendObject, "type" | "id"> & { id: string };
type DrawEditorMode = "defaults" | "layer";
type DrawEditorKind = "line" | "legend" | "reference" | "polygon" | "text";
type LineStyleDraft = {
  line_color: string;
  line_style: string;
  line_width: number;
  arrow_mode: DrawArrowMode;
  arrow_head: DrawArrowHead;
};
type PolygonStyleDraft = {
  border_style: string;
  border_color: string;
  fill_color: string | null;
  fill_opacity: number;
};
type ReferenceStyleDraft = {
  mode: "horizontal" | "vertical";
  line_style: string;
  line_color: string | null;
  valueLabel?: string;
};
type TextStyleDraft = {
  text: string;
  font_size: number;
  font_family: string;
  font_weight: DesignSettings["font_weight"];
  font_italic: boolean;
  line_spacing: number;
  text_color: string;
};
type TextInputState = {
  x: number;
  y: number;
  axis_units: string;
  draft: string;
};
type LegendStyleDefaults = Pick<
  DrawLegendObject,
  "name" | "font_size" | "font_family" | "font_weight" | "font_italic" | "show_border" | "border_style" | "border_color" | "show_fill" | "fill_color" | "fill_opacity"
>;
type DrawHoverState = {
  point: DrawPoint;
  clientX: number;
  clientY: number;
  snapped: boolean;
  rulerPoint: RulerPoint | null;
};
type VowelAnalysisPage = "home" | "formant" | "distance" | "pillai";
type VowelAnalysisResult = {
  index: number;
  name: string;
  x_label?: string;
  y_label?: string;
  normalization?: string | null;
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
  font_family: string;
  font_weight: "regular" | "medium" | "semibold" | "bold";
  label_slash_wrap: boolean;
  tick_label_size: number;
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
const MAX_CACHED_FILE_DESIGNS = 32;

function cacheLayerSession(cache: Map<string, LayerSession>, key: string, session: LayerSession) {
  cacheMapSet(cache, key, session, MAX_CACHED_LAYER_SESSIONS);
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

/** Mirrors PlotEngine.NORM_RANGES — fixed presets, not data-driven. */
const NORM_RANGE_DEFAULTS: Record<string, Ranges> = {
  Lobanov: { y_min: "-2", y_max: "2", x_min: "-2", x_max: "2" },
  Gerstman: { y_min: "0", y_max: "1000", x_min: "0", x_max: "1000" },
  "2mW/F": { y_min: "0.4", y_max: "1.8", x_min: "0.4", x_max: "1.8" },
  Bigham: { y_min: "0.4", y_max: "1.8", x_min: "0.4", x_max: "1.8" },
  Nearey1: { y_min: "-1", y_max: "1", x_min: "-1", x_max: "1" },
};

function rangesLookCompatible(ranges: Ranges, normalization: string | null | undefined, useBark: boolean): boolean {
  const vals = [ranges.x_min, ranges.x_max, ranges.y_min, ranges.y_max].map(Number);
  if (vals.some((value) => !Number.isFinite(value))) return false;
  const [xMin, xMax, yMin, yMax] = vals;
  if (xMin >= xMax || yMin >= yMax) return false;
  const maxAbs = Math.max(...vals.map(Math.abs));
  if (normalization) {
    const preset = NORM_RANGE_DEFAULTS[normalization] ?? NORM_RANGE_DEFAULTS.Lobanov;
    const p = [preset.x_min, preset.x_max, preset.y_min, preset.y_max].map(Number);
    const spanX = Math.abs(p[1] - p[0]);
    const spanY = Math.abs(p[3] - p[2]);
    const padX = Math.max(spanX * 3, 5);
    const padY = Math.max(spanY * 3, 5);
    if (xMin < p[0] - padX || xMax > p[1] + padX) return false;
    if (yMin < p[2] - padY || yMax > p[3] + padY) return false;
    if (Math.abs(xMax - xMin) > Math.max(spanX * 4, 20)) return false;
    if (Math.abs(yMax - yMin) > Math.max(spanY * 4, 20)) return false;
    return true;
  }
  if (useBark) return maxAbs <= 40;
  return maxAbs >= 50;
}

// Safe first paint before the sidecar snapshot arrives.  Avoids undefined
// select values and NaN percentages in controls during window startup.
const EMPTY_DESIGN: DesignSettings = {
  show_raw: true, show_centroid: true, raw_marker: "o", raw_color: "#606060",
  centroid_marker: "o", lbl_color: "#FF0000", lbl_size: 18, lbl_bold: true,
  lbl_italic: false, ell_thick: 0.5, ell_style: "-", ell_color: "#606060",
  ell_fill_color: null, ell_fill_opacity: 0.15, box_spines: false,
  show_grid: false, grid_opacity: 0.3, y_label_rotation: false,
  axis_position_swap: false, show_axis_units: false, show_minor_ticks: true,
  font_style: "serif", font_family: "Noto Serif KR", font_weight: "bold", label_slash_wrap: false, tick_label_size: 13,
};

const FONT_FAMILIES = ["Noto Sans KR", "Noto Serif KR", "Charis SIL", "Andika"] as const;
const FONT_WEIGHTS: Record<string, Array<DesignSettings["font_weight"]>> = {
  "Noto Sans KR": ["regular", "bold"],
  "Noto Serif KR": ["regular", "medium", "bold"],
  "Charis SIL": ["regular", "bold"],
  Andika: ["regular", "medium", "semibold", "bold"],
};
const FONT_WEIGHT_LABELS: Record<DesignSettings["font_weight"], string> = {
  regular: "Regular", medium: "Medium", semibold: "Semibold", bold: "Bold",
};

function fontFamilyStyle(family: string) {
  return family === "Noto Serif KR" || family === "Charis SIL" ? "serif" : "sans";
}

function normalizedFontWeight(family: string, value: unknown): DesignSettings["font_weight"] {
  const choices = FONT_WEIGHTS[family] ?? ["regular"];
  return choices.includes(value as DesignSettings["font_weight"]) ? value as DesignSettings["font_weight"] : choices[0];
}

const MARKERS = [["o", "●"], ["s", "■"], ["^", "▲"], ["D", "◆"], ["wo", "○"], ["ws", "□"]] as const;
const MARKER_DISPLAY_LABELS: Record<string, string> = { o: "원", s: "사각형", "^": "삼각형", D: "마름모", wo: "빈 원", ws: "빈 사각형", x: "가위표", a: "라벨" };
const DESIGN_EFFECT_ORDER: (keyof DesignSettings)[] = ["lbl_color", "lbl_size", "lbl_bold", "lbl_italic", "centroid_marker", "ell_thick", "ell_style", "ell_color", "ell_fill_color", "ell_fill_opacity", "raw_color", "raw_marker", "label_slash_wrap"];
const DESIGN_EFFECT_LABELS: Partial<Record<keyof DesignSettings, string>> = {
  lbl_color: "라벨 색", lbl_size: "라벨 크기", lbl_bold: "라벨 굵기", lbl_italic: "라벨 기울임",
  centroid_marker: "중심점 모양", ell_thick: "타원 선 두께", ell_style: "타원 선 모양",
  ell_color: "타원 선 색", ell_fill_color: "타원 내부 색", ell_fill_opacity: "타원 불투명도",
  raw_color: "원자료 색", raw_marker: "원자료 모양", label_slash_wrap: "슬래시 감싸기",
};

function effectDisplayValue(key: keyof DesignSettings, value: DesignSettings[keyof DesignSettings]) {
  if (value === null) return "투명";
  if (key === "lbl_size") return `${value}pt`;
  if (key === "lbl_bold") return value ? "굵게" : "보통";
  if (key === "lbl_italic") return value ? "기울임" : "보통";
  if (key === "label_slash_wrap") return value ? "사용" : "사용 안 함";
  if (key === "ell_fill_opacity") return `${Math.round(Number(value) * 100)}%`;
  if (key === "ell_style") return value === "-" ? "실선" : value === "---" ? "긴 점선" : "짧은 점선";
  if (key === "ell_thick") return Number(value) <= 0.5 ? "얇게" : Number(value) >= 2 ? "굵게" : "보통";
  if (key === "centroid_marker" || key === "raw_marker") return MARKER_DISPLAY_LABELS[String(value)] ?? String(value);
  return String(value);
}

/** PySide draw_reference.round_ref_value 이식 — magnet/눈금 스냅. */
function roundRefValue(
  plotCoord: number,
  scale: string,
  unit: string,
  extraSnapValues: number[] = [],
  normalization: string | null = null,
): { value: number; snapped: boolean } {
  const u = (unit || "Hz").trim().toLowerCase();
  const s = (scale || "linear").trim().toLowerCase();
  const norm = String(normalization || "").trim().toLowerCase();
  let raw = plotCoord;
  if (s === "bark" && u === "hz") raw = barkToHz(plotCoord);

  let stepped: number;
  let tol: number;
  if (u === "norm") {
    if (norm.includes("lobanov")) { stepped = Math.round(raw * 10) / 10; tol = 0.05; }
    else if (norm.includes("gerstman")) { stepped = Math.round(raw / 10) * 10; tol = 5; }
    else if (norm.includes("2mw") || norm.includes("bigham") || norm.includes("nearey")) { stepped = Math.round(raw * 20) / 20; tol = 0.02; }
    else { stepped = Math.round(raw * 100) / 100; tol = 0.01; }
  } else if (s === "bark" && (u === "bk" || u === "bark")) {
    stepped = Math.round(raw * 10) / 10;
    tol = 0.05;
  } else {
    stepped = Math.round(raw / 10) * 10;
    tol = 5;
  }

  if (extraSnapValues.length) {
    let nearest = extraSnapValues[0];
    let best = Math.abs(nearest - raw);
    for (const candidate of extraSnapValues) {
      const dist = Math.abs(candidate - raw);
      if (dist < best) { nearest = candidate; best = dist; }
    }
    if (best <= tol) {
      if (u === "norm" && norm.includes("gerstman")) return { value: Math.round(nearest), snapped: true };
      return { value: nearest, snapped: true };
    }
  }
  if (u === "norm" && norm.includes("gerstman")) return { value: Math.round(stepped), snapped: true };
  return { value: stepped, snapped: true };
}

function formatRefLabel(value: number, unit: string, snapped: boolean, normalization: string | null) {
  const u = (unit || "Hz").trim().toLowerCase();
  if (u === "norm" || u.includes("norm")) {
    if (String(normalization || "").toLowerCase().includes("gerstman")) return `  ${Math.round(value)}`;
    return `  ${value.toFixed(2)}`;
  }
  if (u === "bk" || u === "bark") return snapped ? `  ${value.toFixed(2)}` : `  ${value.toFixed(1)}`;
  return `  ${Math.round(value)}`;
}

/** 축·눈금과 같은 계열 (utils.font_stacks.axis_font_list 대응). 웹뷰에 없는 Noto는 Charis로 폴백. */
function axisPreviewFontFamily(design: Pick<DesignSettings, "font_style" | "font_family">): string {
  const family = String(design.font_family || "");
  const style = design.font_style || fontFamilyStyle(family);
  if (family === "Charis SIL") return '"Charis SIL", "Times New Roman", serif';
  if (family === "Andika") return '"Andika", "Noto Sans KR", sans-serif';
  if (style === "serif" || family === "Noto Serif KR") {
    return '"Noto Serif KR", "Charis SIL", "Times New Roman", serif';
  }
  return '"Noto Sans KR", "Andika", "Malgun Gothic", sans-serif';
}

const DRAW_LINE_DEFAULT_COLOR = "#000000";
const DRAW_LINE_WIDTH_MIN = 0.25;
const DRAW_LINE_WIDTH_MAX = 3;
const DRAW_LINE_WIDTH_STEP = 0.25;
const DRAW_LINE_DEFAULT_WIDTH = 0.5;
const DRAW_POLYGON_DEFAULT_FILL = "#3366CC";
const DRAW_POLYGON_DEFAULT_BORDER = "#000000";
const DRAW_TEXT_DEFAULT_COLOR = "#303133";
const DRAW_TEXT_DEFAULT_SIZE = 13;
const DRAW_TEXT_DEFAULT_FAMILY = "Noto Sans KR";
const DRAW_TEXT_DEFAULT_LINE_SPACING = 1.15;
const DRAW_TEXT_SIZE_MIN = 4;
const DRAW_TEXT_SIZE_MAX = 32;
const DRAW_TEXT_LINE_SPACING_MIN = 0.8;
const DRAW_TEXT_LINE_SPACING_MAX = 2.5;

const clampDrawLineWidth = (value: number) => {
  const stepped = Math.round(value / DRAW_LINE_WIDTH_STEP) * DRAW_LINE_WIDTH_STEP;
  return Math.min(DRAW_LINE_WIDTH_MAX, Math.max(DRAW_LINE_WIDTH_MIN, Number(stepped.toFixed(2))));
};

const clampDrawTextFontSize = (value: number) => (
  Math.min(DRAW_TEXT_SIZE_MAX, Math.max(DRAW_TEXT_SIZE_MIN, Math.round(Number.isFinite(value) ? value : DRAW_TEXT_DEFAULT_SIZE)))
);

const clampDrawTextLineSpacing = (value: number) => {
  const n = Number.isFinite(value) ? value : DRAW_TEXT_DEFAULT_LINE_SPACING;
  return Math.min(DRAW_TEXT_LINE_SPACING_MAX, Math.max(DRAW_TEXT_LINE_SPACING_MIN, Number(n.toFixed(2))));
};

/** PySide create_trajectory_icon 대응 — 화살표 위치/모양 미리보기. */
function TrajectoryIcon({ mode, head }: { mode: DrawArrowMode; head?: DrawArrowHead }) {
  const headStyle = head ?? "stealth";
  const tips = mode === "end" ? [44] : mode === "all" ? [27, 44] : [];
  const length = 8.5;
  const width = 4.6;
  const cy = 12;
  return (
    <svg className="trajectory-icon" viewBox="0 0 54 24" width="44" height="20" aria-hidden>
      <line x1="10" y1={cy} x2="44" y2={cy} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      {tips.map((ax) => {
        if (headStyle === "open") {
          return (
            <g key={`open-${ax}`}>
              <line x1={ax - length} y1={cy - width} x2={ax} y2={cy} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
              <line x1={ax - length} y1={cy + width} x2={ax} y2={cy} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
            </g>
          );
        }
        if (headStyle === "latex") {
          return <polygon key={`latex-${ax}`} points={`${ax},${cy} ${ax - length},${cy - width} ${ax - length},${cy + width}`} fill="currentColor" />;
        }
        const indent = 3.6;
        return <polygon key={`stealth-${ax}`} points={`${ax},${cy} ${ax - length},${cy - width} ${ax - length + indent},${cy} ${ax - length},${cy + width}`} fill="currentColor" />;
      })}
      {[10, 27, 44].map((x) => <circle key={x} cx={x} cy={cy} r="2" fill="currentColor" />)}
    </svg>
  );
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
  const colors = ["#000000", "#202938", "#606060", "#9ca3af", "#FF0000", "#ef2929", "#f97316", "#eab308", "#16a34a", "#0891b2", "#2563eb", "#7c3aed"];
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
        {sources.map((source) => <button type="button" role="option" aria-selected={source.index === currentIndex} className={source.index === currentIndex ? "is-selected" : ""} key={`${source.index}-${source.name}`} onClick={() => { setOpen(false); onNavigate(source.index); }}>{source.name}</button>)}
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
          <ellipse className="figure-ellipse ellipse-a" cx="88" cy="78" rx="34" ry="42" />
          <ellipse className="figure-ellipse ellipse-b" cx="228" cy="138" rx="40" ry="34" />
          <g className="figure-cloud cloud-a">{[[78, 68], [90, 76], [98, 88], [84, 92], [100, 72]].map(([cx, cy]) => <circle key={`da-${cx}-${cy}`} cx={cx} cy={cy} r="2.5" />)}</g>
          <g className="figure-cloud cloud-b">{[[214, 128], [230, 136], [242, 146], [220, 148], [238, 124]].map(([cx, cy]) => <circle key={`db-${cx}-${cy}`} cx={cx} cy={cy} r="2.5" />)}</g>
          <path className="figure-distance-line" d="M88 78L228 138" />
          <circle className="figure-centroid centroid-a" cx="88" cy="78" r="6" />
          <circle className="figure-centroid centroid-b" cx="228" cy="138" r="6" />
          <text x="74" y="58">a</text><text x="236" y="158">u</text><text x="138" y="100">d(a, u)</text>
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

function VowelAnalysisShell({ currentSource, sources, currentIndex, displayIndex, onNavigate, onClose }: { currentSource: SourceInfo | undefined; sources: SourceInfo[]; currentIndex: number; displayIndex: number; onNavigate: (index: number) => void; onClose: () => void }) {
  const [page, setPage] = useState<VowelAnalysisPage>("home");
  const [lobbyAnimationEnabled, setLobbyAnimationEnabled] = useState(true);
  const lobbyShownRef = useRef(false);
  // Resets to expanded whenever this shell mounts (entering the analysis lab).
  const [heroCollapsed, setHeroCollapsed] = useState(false);
  const [analysisData, setAnalysisData] = useState<VowelAnalysisResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(true);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const analysisBodyRef = useRef<HTMLDivElement | null>(null);
  const shellRef = useRef<HTMLElement | null>(null);
  useFocusTrap(true, shellRef);
  const analysisScrollByFileRef = useRef(new Map<number, number>());
  const previousAnalysisIndexRef = useRef(currentIndex);
  useEffect(() => {
    setAnalysisLoading(true);
    setAnalysisError(null);
    let active = true;
    void callSidecar<VowelAnalysisResult>("get_vowel_analysis", { index: currentIndex }).then((result) => {
      if (active) {
        setAnalysisData(result);
        setAnalysisLoading(false);
      }
    }).catch((err) => {
      if (active) {
        setAnalysisData(null);
        setAnalysisLoading(false);
        setAnalysisError(String(err));
      }
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
  const analysisFileName = currentSource?.name ?? "-";
  const analysisFileMatch = analysisFileName.match(/^(.*?)(\.[^.]+)?$/);
  const analysisFileStem = analysisFileMatch?.[1] || analysisFileName;
  const analysisFileExt = analysisFileMatch?.[2] ?? "";
  const goToAnalysisPage = (next: VowelAnalysisPage) => {
    if (next === "home") setLobbyAnimationEnabled(!lobbyShownRef.current);
    else lobbyShownRef.current = true;
    setPage(next);
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      if (page !== "home") goToAnalysisPage("home");
      else onClose();
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [onClose, page]);

  const formantUnitSuffix = resolvePlotUnits({
    normalization: analysisData?.normalization,
    use_bark_units: false,
    type: "f1_f2",
  }).formantStatSuffix;

  return (
    <div className="vowel-analysis-backdrop" data-modal-root role="presentation">
      <section ref={shellRef} className={`vowel-analysis-shell ${page === "home" ? "is-lobby" : ""} ${page === "home" && lobbyAnimationEnabled ? "is-lobby-first" : ""}`} role="dialog" aria-modal="true" aria-labelledby="vowel-analysis-title">
        <header className="vowel-analysis-header">
          <div className="vowel-analysis-title"><div className="vowel-analysis-mark"><BarChart3 size={18} /></div><div><span className="section-eyebrow">모음 공간 분석실</span><h2 id="vowel-analysis-title">모음 상세 분석</h2></div></div>
          <button type="button" className="vowel-analysis-close" onClick={onClose} aria-label="분석 창 닫기"><X size={18} /></button>
        </header>
        {page !== "home" ? <div className="analysis-file-switcher"><button type="button" onClick={() => onNavigate(sources[Math.max(0, displayIndex - 1)]?.index ?? currentIndex)} disabled={displayIndex <= 0} aria-label="이전 파일">‹</button><div><span className="analysis-file-meta"><span>분석 파일</span><strong>{displayIndex + 1} / {sources.length}</strong></span><b className="analysis-file-name" title={analysisFileName}><span>{analysisFileStem}</span>{analysisFileExt ? <em>{analysisFileExt}</em> : null}</b></div><button type="button" onClick={() => onNavigate(sources[Math.min(sources.length - 1, displayIndex + 1)]?.index ?? currentIndex)} disabled={displayIndex >= sources.length - 1} aria-label="다음 파일">›</button></div> : null}
        {page !== "home" ? <nav className="vowel-analysis-tabs" aria-label="모음 분석 페이지"><button type="button" className="analysis-home-tab" onClick={() => goToAnalysisPage("home")}><ChevronLeft size={14} /><span><strong>전체 보기</strong><small>분석 항목</small></span></button>{pages.map((item) => <button key={item.id} type="button" className={page === item.id ? "is-active" : ""} onClick={() => goToAnalysisPage(item.id)}><strong>{item.label}</strong><small>{item.detail}</small></button>)}</nav> : null}
        <div className={`vowel-analysis-body ${page === "home" ? "is-lobby" : ""}`} ref={analysisBodyRef}>
          {page === "home" ? <div className="analysis-lobby">
            <section className="analysis-lobby-intro">
              <span>ANALYSIS SUITE</span>
              <strong>모음 공간을 더 자세한 수치들로 분석할 수 있습니다.</strong>
              <p>모음별 분포 통계, 중심점 간 거리, 겹침 정도 등 다양한 통계를 확인하고 내보낼 수 있습니다.</p>
            </section>
            <section className="analysis-lobby-grid">
              <button type="button" className="analysis-bento analysis-bento-formant is-primary" onClick={() => goToAnalysisPage("formant")}><span>01</span><strong>모음별 통계</strong><p>평균 · 표준편차 · 범위 · 중심 거리 · n</p></button>
              <button type="button" className="analysis-bento analysis-bento-distance" onClick={() => goToAnalysisPage("distance")}><span>02</span><strong>중심점 거리</strong><p>Euclidean · Mahalanobis</p></button>
              <button type="button" className="analysis-bento analysis-bento-pillai" onClick={() => goToAnalysisPage("pillai")}><span>03</span><strong>Pillai Score</strong><p>score · p-value</p></button>
              <button type="button" className="analysis-bento analysis-bento-export export-bento" disabled title="곧 지원 예정입니다">
                <Download size={18} /><strong>분석표 내보내기</strong><p>곧 표 형식 저장을 지원할 예정입니다</p>
              </button>
            </section>
          </div> : null}
          <div className={`vowel-analysis-hero ${heroCollapsed ? "is-collapsed" : ""}`}>
            <div className="analysis-hero-copy">
              <span className="analysis-kicker">{hero.kicker}</span>
              <h3>{hero.title}</h3>
              <p>{hero.copy}</p>
            </div>
            <AnalysisFigure page={page} />
            <button
              type="button"
              className="analysis-hero-fold"
              onClick={() => setHeroCollapsed((previous) => !previous)}
              aria-expanded={!heroCollapsed}
              aria-label={heroCollapsed ? "소개 패널 펼치기" : "소개 패널 접기"}
              title={heroCollapsed ? "펼치기" : "접기"}
            >
              {heroCollapsed ? <ChevronDown size={16} strokeWidth={2.2} /> : <ChevronUp size={16} strokeWidth={2.2} />}
            </button>
          </div>
          <section className="analysis-detail-panel">
            <div className="analysis-detail-heading">
              <div>
                <span className="analysis-kicker">RESULTS</span>
                <h4>{page === "formant" ? "모음별 통계" : page === "distance" ? "선택 모음 간 거리" : "모음 조합별 Pillai Score"}</h4>
              </div>
              <span>{analysisLoading ? "계산 중" : analysisData ? String(analysisData.metadata.total_points ?? 0) + " tokens" : "데이터 없음"}</span>
            </div>
            {analysisData ? (
              page === "formant" ? (
                <FormantStatsTable
                  statistics={analysisData.statistics}
                  centroidDistances={analysisData.centroid_distances}
                  xLabel={analysisData.x_label ?? "F2"}
                  yLabel={analysisData.y_label ?? "F1"}
                  unitSuffix={formantUnitSuffix}
                />
              ) : analysisPairs.length ? (
                <div className="analysis-result-table">
                  <div className="analysis-result-row analysis-result-head">
                    <span>모음 조합</span>
                    <span>{page === "distance" ? "Euclidean" : "Pillai Score"}</span>
                    <span>{page === "distance" ? "Mahalanobis" : "p-value"}</span>
                  </div>
                  {analysisPairs.map((pair) => {
                    const euclidean = analysisData.pairwise_euclidean[pair.key];
                    const mahalanobis = analysisData.pairwise_mahalanobis[pair.key];
                    const pillai = analysisData.pillai_scores[pair.key];
                    const pDisplay = page === "pillai" ? formatPValue(pillai?.p_value) : null;
                    return (
                      <div className="analysis-result-row" key={pair.key}>
                        <strong>{pair.left} - {pair.right}</strong>
                        <span>{page === "distance" ? (euclidean ?? 0).toFixed(3) : pillai?.score == null ? "N/A" : pillai.score.toFixed(4)}</span>
                        <span
                          className={pDisplay && !pDisplay.significant ? "analysis-p-ns" : undefined}
                          title={pDisplay && pDisplay.text !== "N/A" ? `p = ${pDisplay.exact}` : undefined}
                        >
                          {page === "distance"
                            ? (mahalanobis ?? 0).toFixed(3)
                            : pDisplay?.text ?? "N/A"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="analysis-result-empty">모음 두 개 이상을 선택하면 조합별 결과가 표시됩니다.</div>
              )
            ) : (
              <div className="analysis-result-empty">
                {analysisError ? `분석 데이터를 불러오지 못했습니다: ${analysisError}` : "분석 데이터를 불러오는 중입니다."}
              </div>
            )}
          </section>
        </div>
      </section>
    </div>
  );
}

export function InteractivePlotWindow() {
  const [state, setState] = useState<ApplicationState | null>(null);
  const [combinedVisible, setCombinedVisible] = useState(() => window.localStorage.getItem("gichanformant-show-combined") === "true");
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
  const [hoveredPlotLabel, setHoveredPlotLabel] = useState<string | null>(null);
  const [plotLabelPointer, setPlotLabelPointer] = useState<{ x: number; y: number } | null>(null);
  const [plotLabelPreviewVowel, setPlotLabelPreviewVowel] = useState<string | null>(null);
  const [tool, setTool] = useState<Tool>("select");
  const [leftPanel, setLeftPanel] = useState<LeftPanel>("analysis");
  const [rightPanel, setRightPanel] = useState<RightPanel>("layers");
  const [drawTool, setDrawTool] = useState<DrawTool | null>(null);
  const [drawColor, setDrawColor] = useState<string | null>(DRAW_LINE_DEFAULT_COLOR);
  const [drawWidth, setDrawWidth] = useState(DRAW_LINE_DEFAULT_WIDTH);
  const [drawLineStyle, setDrawLineStyle] = useState("-");
  const [drawArrowMode, setDrawArrowMode] = useState<DrawArrowMode>("none");
  const [drawArrowHead, setDrawArrowHead] = useState<DrawArrowHead>("stealth");
  const [drawRefColor, setDrawRefColor] = useState<string | null>(null);
  const [drawRefStyle, setDrawRefStyle] = useState("-");
  const [drawPolyBorderStyle, setDrawPolyBorderStyle] = useState("-");
  const [drawPolyBorderColor, setDrawPolyBorderColor] = useState(DRAW_POLYGON_DEFAULT_BORDER);
  const [drawPolyFillColor, setDrawPolyFillColor] = useState<string | null>(DRAW_POLYGON_DEFAULT_FILL);
  const [drawPolyFillOpacity, setDrawPolyFillOpacity] = useState(0.15);
  const [drawTextFontSize, setDrawTextFontSize] = useState(DRAW_TEXT_DEFAULT_SIZE);
  const [drawTextFontFamily, setDrawTextFontFamily] = useState(DRAW_TEXT_DEFAULT_FAMILY);
  const [drawTextFontWeight, setDrawTextFontWeight] = useState<DesignSettings["font_weight"]>("regular");
  const [drawTextItalic, setDrawTextItalic] = useState(false);
  const [drawTextLineSpacing, setDrawTextLineSpacing] = useState(DRAW_TEXT_DEFAULT_LINE_SPACING);
  const [drawTextColor, setDrawTextColor] = useState(DRAW_TEXT_DEFAULT_COLOR);
  const [draggingTextId, setDraggingTextId] = useState<string | null>(null);
  const [hoveredDrawTextId, setHoveredDrawTextId] = useState<string | null>(null);
  const [textDragPointer, setTextDragPointer] = useState<{ x: number; y: number } | null>(null);
  const textDragRef = useRef<{ id: string; offsetX: number; offsetY: number } | null>(null);
  const textDragFrameRef = useRef<number | null>(null);
  const textHasMovedRef = useRef(false);
  const [legendDefaults, setLegendDefaults] = useState<LegendStyleDefaults>({
    name: "범례",
    font_size: 9,
    font_family: "Noto Sans KR",
    font_weight: "regular",
    font_italic: false,
    show_border: true,
    border_style: "-",
    border_color: "#3f4650",
    show_fill: true,
    fill_color: "#ffffff",
    fill_opacity: 1,
  });
  const [drawObjectsByFile, setDrawObjectsByFile] = useState<Record<number, DrawObject[]>>({});
  const [drawingPoints, setDrawingPoints] = useState<DrawPoint[]>([]);
  const [drawHover, setDrawHover] = useState<DrawHoverState | null>(null);
  const [draggingDrawObject, setDraggingDrawObject] = useState<string | null>(null);
  const [drawDropTarget, setDrawDropTarget] = useState<{ id: string; after: boolean } | null>(null);
  const [selectedDrawObjectId, setSelectedDrawObjectId] = useState<string | null>(null);
  const [selectedDrawObjectIds, setSelectedDrawObjectIds] = useState<Set<string>>(() => new Set());
  const drawSelectionAnchorRef = useRef("");
  const [draggingLegend, setDraggingLegend] = useState(false);
  const [legendDragPreview, setLegendDragPreview] = useState<Pick<DrawLegendObject, "fx" | "fy" | "width_frac" | "height_frac"> | null>(null);
  const [referenceMode, setReferenceMode] = useState<"horizontal" | "vertical">("horizontal");
  const [referencePreview, setReferencePreview] = useState<ReferencePreview | null>(null);
  const [drawEditorOpen, setDrawEditorOpen] = useState(false);
  const [drawEditorMode, setDrawEditorMode] = useState<DrawEditorMode>("defaults");
  const [drawEditorKind, setDrawEditorKind] = useState<DrawEditorKind>("line");
  const [drawEditorObjectId, setDrawEditorObjectId] = useState<string | null>(null);
  const [lineDraft, setLineDraft] = useState<LineStyleDraft | null>(null);
  const [polygonDraft, setPolygonDraft] = useState<PolygonStyleDraft | null>(null);
  const [referenceDraft, setReferenceDraft] = useState<ReferenceStyleDraft | null>(null);
  const [legendDraft, setLegendDraft] = useState<LegendDraft | null>(null);
  const [textDraft, setTextDraft] = useState<TextStyleDraft | null>(null);
  const [textInput, setTextInput] = useState<TextInputState | null>(null);
  const [globalDesignLocked, setGlobalDesignLocked] = useState(true);
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
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false);
  const batchExportDialogRef = useRef<HTMLElement | null>(null);
  const shortcutHelpRef = useRef<HTMLElement | null>(null);
  useFocusTrap(batchExportOpen, batchExportDialogRef);
  useFocusTrap(shortcutHelpOpen, shortcutHelpRef);
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
  // A reopened Tauri window must not accept an older preview event from the
  // same sidecar just because its local counter started at zero again.
  const renderRequestRef = useRef(Date.now() * 1000);
  const renderTimerRef = useRef<number | null>(null);
  const layerSessionsRef = useRef(new Map<string, LayerSession>());
  const plotPaperRef = useRef<HTMLDivElement | null>(null);
  const plotImageRef = useRef<HTMLImageElement | null>(null);
  const plotLabelFrameRef = useRef<number | null>(null);
  const drawIdRef = useRef(0);
  const plotLabelDragStartRef = useRef<{ x: number; y: number } | null>(null);
  const plotLabelHasMovedRef = useRef(false);
  const legendDragRef = useRef<{ startX: number; startY: number; fx: number; fy: number } | null>(null);
  const legendFrameRef = useRef<number | null>(null);
  const referencePointerRef = useRef<ReferencePreview | null>(null);
  const referenceMoveRef = useRef<(clientX: number, clientY: number) => void>(() => {});
  const lineMoveRef = useRef<(clientX: number, clientY: number) => void>(() => {});
  const areaMoveRef = useRef<(clientX: number, clientY: number) => void>(() => {});
  const legendPointerRef = useRef<Pick<DrawLegendObject, "fx" | "fy" | "width_frac" | "height_frac"> | null>(null);
  const drawObjectDragRef = useRef<{ id: string; ids: string[]; startY: number; moved: boolean } | null>(null);
  const saveDrawEditorRef = useRef<() => void>(() => {});
  const closeDrawEditorRef = useRef<() => void>(() => {});
  const globalDesignByFileRef = useRef(new Map<string, DesignSettings>());
  const designInitializedRef = useRef(false);
  const [previewLoading, setPreviewLoading] = useState(true);

  const refresh = useCallback(async () => {
    setPreviewLoading(true);
    try {
      const next = await callSidecar<ApplicationState>("get_state");
      if (!aliveRef.current) return;
      setState(next);
      setEngineConnected(true);
      if (next.capabilities.can_plot) {
        const requestId = ++renderRequestRef.current;
        const nextNorm = next.analysis?.normalization ?? null;
        const nextPlotType = next.analysis?.type ?? "f1_f2";
        const useBark = next.analysis?.use_bark_units ?? false;
        let bootRanges: Ranges;
        if (nextNorm) {
          bootRanges = NORM_RANGE_DEFAULTS[nextNorm] ?? NORM_RANGE_DEFAULTS.Lobanov;
        } else {
          bootRanges = smartAxisRanges(nextPlotType, next.analysis, RANGE_DEFAULTS, BARK_RANGE_DEFAULTS);
        }
        const sessionRanges = next.plot_session?.ranges as Ranges | undefined;
        const rangesForBoot = sessionRanges
          && Object.keys(sessionRanges).length === 4
          && rangesLookCompatible(sessionRanges, nextNorm, useBark)
          ? sessionRanges
          : bootRanges;
        setRanges(rangesForBoot);
        await callSidecar("render_interactive_preview", {
          options: { request_id: requestId, ranges: rangesForBoot },
        });
      } else {
        setPreviewLoading(false);
      }
    } catch (err) {
      setEngineConnected(false);
      setMessage(`플롯을 불러오지 못했습니다: ${String(err)}`);
      setPreviewLoading(false);
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
        if (Number.isFinite(requestId) && requestId > 0 && requestId < renderRequestRef.current) return;
        const imagePath = String(payload.payload.png_path ?? "");
        const image = String(payload.payload.png_base64 ?? "");
        setPreviewUrl(imagePath ? convertFileSrc(imagePath) : image ? `data:image/png;base64,${image}` : null);
        setPreviewLoading(false);
        const nextRuler = (payload.payload.ruler_context as RulerContext | undefined) ?? null;
        setRulerContext(nextRuler);
        const legendBounds = nextRuler?.legend_bounds;
        if (legendBounds) {
          setDrawObjectsByFile((previous) => {
            let changed = false;
            const next: Record<number, DrawObject[]> = { ...previous };
            for (const [key, list] of Object.entries(previous)) {
              const updated = list.map((obj) => {
                if (obj.type !== "legend") return obj;
                const measured = legendBounds[obj.id];
                if (!measured) return obj;
                if (
                  Math.abs(measured.width_frac - obj.width_frac) < 0.002
                  && Math.abs(measured.height_frac - obj.height_frac) < 0.002
                ) {
                  return obj;
                }
                changed = true;
                return { ...obj, width_frac: measured.width_frac, height_frac: measured.height_frac };
              });
              next[Number(key)] = updated;
            }
            return changed ? next : previous;
          });
        }
        setLegendDragPreview(null);
        setPlotLabelPreviewVowel(null);
        setPlotLabelPointer(null);
        setRulerStart(null);
        setRulerHover(null);
        setRulerMeasurements([]);
        setPreviewInfo(String(payload.payload.info ?? ""));
        setMessage("현재 설정을 플롯에 반영했습니다.");
      } else if (payload.event === "preview_failed" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (requestId && requestId < renderRequestRef.current) return;
        setPreviewLoading(false);
        setMessage(`렌더링 오류: ${String(payload.payload.message ?? "알 수 없는 오류")}`);
      } else if (payload.event === "preview_cleared" && payload.payload.target === "interactive") {
        const requestId = Number(payload.payload.request_id ?? 0);
        if (requestId && requestId < renderRequestRef.current) return;
        setPreviewUrl(null);
        setPreviewLoading(false);
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
      } else if (payload.event === "plot_session_changed") {
        const nextSession = payload.payload.plot_session as ApplicationState["plot_session"] | undefined;
        if (!nextSession || typeof nextSession.revision !== "number") return;
        setState((previous) => {
          if (!previous) return previous;
          if (nextSession.revision <= (previous.plot_session?.revision ?? -1)) return previous;
          return { ...previous, plot_session: nextSession };
        });
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
    if (!shortcutHelpOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      setShortcutHelpOpen(false);
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [shortcutHelpOpen]);

  useEffect(() => {
    if (!batchExportOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || batchExportBusy) return;
      event.preventDefault();
      event.stopPropagation();
      setBatchExportOpen(false);
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [batchExportBusy, batchExportOpen]);

  useEffect(() => {
    if (!drawEditorOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        closeDrawEditorRef.current();
        return;
      }
      if (event.key !== "Enter" && event.key !== "Return") return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("textarea, select, [contenteditable='true']")) return;
      event.preventDefault();
      event.stopPropagation();
      saveDrawEditorRef.current();
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [drawEditorOpen]);

  useEffect(() => {
    if (!textInput) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      setTextInput(null);
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [textInput]);

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
    let themeDisposed = false;
    let unlistenTheme: (() => void) | undefined;
    void listen<string>("gichan-theme", ({ payload }) => {
      if (payload !== "light" && payload !== "dark") return;
      document.documentElement.dataset.theme = payload;
      document.documentElement.style.colorScheme = payload;
    }).then((dispose) => {
      if (themeDisposed) dispose();
      else unlistenTheme = dispose;
    });
    return () => {
      themeDisposed = true;
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
    if (textDragFrameRef.current !== null) cancelAnimationFrame(textDragFrameRef.current);
    if (legendFrameRef.current !== null) cancelAnimationFrame(legendFrameRef.current);
    if (plotLabelFrameRef.current !== null) cancelAnimationFrame(plotLabelFrameRef.current);
    dragScrollFrameRef.current = null;
    flipFrameRef.current = null;
    textDragFrameRef.current = null;
    legendFrameRef.current = null;
    plotLabelFrameRef.current = null;
    draggingLayerRef.current = null;
  }, []);

  const analysis = state?.analysis;
  const allSources = state?.sources ?? [];
  const sources = combinedVisible ? allSources : allSources.filter((source) => !source.is_combined);
  const rawCurrentIndex = state?.current_index ?? 0;
  const currentIndex = sources.some((source) => source.index === rawCurrentIndex)
    ? rawCurrentIndex
    : sources[0]?.index ?? rawCurrentIndex;
  const currentSource = sources.find((source) => source.index === currentIndex);
  const currentSourcePosition = Math.max(0, sources.findIndex((source) => source.index === currentIndex));
  const hasCombined = currentSource?.is_combined === true;
  const currentFileKey = currentSource ? String(currentSource.path ?? `${currentSource.index}:${currentSource.name}`) : "";
  const currentDrawObjects = drawObjectsByFile[currentIndex] ?? [];
  const currentDrawLines = currentDrawObjects.filter((object): object is DrawLineObject => object.type === "line");
  const currentLegend = currentDrawObjects.find((object): object is DrawLegendObject => object.type === "legend") ?? null;
  const currentVowels = state?.current_vowels ?? [];
  const plotType = analysis?.type ?? "f1_f2";
  const plotUnits = useMemo(() => resolvePlotUnits(analysis), [analysis]);
  const normalization = plotUnits.normalization;
  const xAxis = plotUnits.xAxisName;
  const yAxis = plotUnits.yAxisName;
  const rangeUnitLabel = plotUnits.rangeBadge;
  const rangesReadOnly = normalization === "Gerstman";
  const defaultRanges = useMemo(() => {
    if (normalization) {
      return NORM_RANGE_DEFAULTS[normalization] ?? NORM_RANGE_DEFAULTS.Lobanov;
    }
    return smartAxisRanges(plotType, analysis, RANGE_DEFAULTS, BARK_RANGE_DEFAULTS);
  }, [analysis, normalization, plotType]);
  const canonicalDesign = useMemo(
    () => ({ ...(state?.design_defaults ?? {}) }) as DesignSettings,
    [state?.design_defaults],
  );
  const canNavigate = sources.length > 1;

  useEffect(() => {
    const syncCombinedVisibility = () => setCombinedVisible(window.localStorage.getItem("gichanformant-show-combined") === "true");
    window.addEventListener("storage", syncCombinedVisibility);
    return () => window.removeEventListener("storage", syncCombinedVisibility);
  }, []);

  useEffect(() => {
    if (!combinedVisible && rawCurrentIndex !== currentIndex && sources.length) {
      void navigateTo(currentIndex);
    }
  }, [combinedVisible, currentIndex, rawCurrentIndex, sources.length]);
  const selectedOverride = selectedLayer ? layerOverrides[selectedLayer] ?? {} : {};
  const selectedLocked = selectedLayer ? lockedLayers.has(selectedLayer) : false;

  useEffect(() => {
    currentIndexRef.current = currentIndex;
  }, [currentIndex]);

  useEffect(() => {
    setSelectedDrawObjectId(null);
    setSelectedDrawObjectIds(new Set());
    drawSelectionAnchorRef.current = "";
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
    const sessionDrawObjects = session?.draw_objects_by_file?.[sessionKey] as DrawObject[] | undefined;
    setLayerState(sessionState ?? cached?.state ?? Object.fromEntries(currentVowels.map((vowel) => [vowel, "ON"])));
    setLayerOverrides(sessionOverrides ?? cached?.overrides ?? {});
    const sessionRanges = session?.ranges as Ranges | undefined;
    const useBark = analysis?.use_bark_units ?? false;
    const canReuseSessionRanges = sessionRanges
      && Object.keys(sessionRanges).length === 4
      && rangesLookCompatible(sessionRanges, normalization, useBark);
    setRanges(canReuseSessionRanges ? sessionRanges : defaultRanges);
    setSigma(session?.sigma ?? "2");
    setShowEllipse(session?.show_ellipse ?? true);
    const sessionDesign = ({ ...canonicalDesign, ...(session?.design_settings ?? {}) }) as DesignSettings;
    if (currentFileKey && !designInitializedRef.current) {
      cacheMapSet(globalDesignByFileRef.current, currentFileKey, sessionDesign, MAX_CACHED_FILE_DESIGNS);
      setDesign(sessionDesign);
      designInitializedRef.current = true;
    }
    setSelectedLayer(defaultOrder[0] ?? "");
    setSelectedLayers(new Set(defaultOrder[0] ? [defaultOrder[0]] : []));
    selectionAnchorRef.current = defaultOrder[0] ?? "";
    setExpandedLayers(cached?.expanded ? new Set(cached.expanded) : new Set());
    setLockedLayers(sessionLocked ? new Set(sessionLocked) : cached ? new Set(cached.locked) : new Set());
    if (sessionDrawObjects) {
      setDrawObjectsByFile((previous) => ({ ...previous, [currentIndex]: sessionDrawObjects }));
    }
    setDrawingPoints([]);
    setDrawHover(null);
    const storedOrder = sessionOrder ?? cached?.order ?? layerOrderRef.current;
    const sameSet = storedOrder.length === defaultOrder.length && storedOrder.every((vowel) => defaultOrder.includes(vowel));
    const nextOrder = sameSet ? storedOrder : defaultOrder;
    layerOrderRef.current = nextOrder;
    setLayerOrder(nextOrder);
    // Hydrate from durable session when the *file* changes — not on every
    // plot_session revision (those arrive while local controls are mid-edit).
  }, [analysis?.use_bark_units, canonicalDesign, currentFileKey, currentIndex, currentVowels.join("\u0000"), defaultRanges, normalization]);

  const unitModeKey = [
    normalization ?? "",
    analysis?.use_bark_units ? "bark" : "hz",
    analysis?.f1_scale ?? "",
    analysis?.f2_scale ?? "",
    analysis?.origin ?? "",
    analysis?.outlier_mode ?? "",
    analysis?.outlier_scope ?? "",
    plotType,
  ].join("|");
  const unitModeKeyRef = useRef(unitModeKey);
  const previousNormRef = useRef<string | null>(normalization);
  useEffect(() => {
    if (!state?.capabilities.can_plot) return;
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
  }, [currentDrawObjects, defaultRanges, design, layerOrder, layerOverrides, layerState, lockedLayers, normalization, showEllipse, sigma, state?.capabilities.can_plot, unitModeKey]);

  const renderInteractive = async (overrides: {
    design?: DesignSettings;
    layers?: Record<string, LayerVisibility>;
    ranges?: Ranges;
    sigma?: string;
    showEllipse?: boolean;
    layerOverrides?: LayerOverrides;
    layerOrder?: string[];
    labelOffsets?: Record<string, [number, number]>;
    drawObjects?: DrawObject[];
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
          draw_objects: overrides.drawObjects ?? currentDrawObjects,
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
      if (!aliveRef.current) return;
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

  const navigateTo = useCallback(async (sourceIndex: number) => {
    if (!sources.length || navigatingRef.current) return;
    const nextSource = sources.find((source) => source.index === sourceIndex);
    if (!nextSource) return;
    const target = nextSource.index;
    if (target === currentIndexRef.current) return;
    navigatingRef.current = true;
    ++renderRequestRef.current;
    if (renderTimerRef.current !== null) {
      window.clearTimeout(renderTimerRef.current);
      renderTimerRef.current = null;
    }
    setNavigating(true);
    setPreviewLoading(true);
    setRulerStart(null);
    setRulerHover(null);
    setRulerPointer(null);
    setDrawingPoints([]);
    setDrawHover(null);
    try {
       if (currentFileKey) {
         cacheMapSet(globalDesignByFileRef.current, currentFileKey, design, MAX_CACHED_FILE_DESIGNS);
         cacheLayerSession(layerSessionsRef.current, currentFileKey, {
          state: { ...layerState },
          overrides: { ...layerOverrides },
          locked: new Set(lockedLayers),
          order: [...layerOrderRef.current],
          expanded: new Set(expandedLayers),
        });
      }
       const nextFileKey = nextSource ? String(nextSource.path ?? `${nextSource.index}:${nextSource.name}`) : "";
       const nextDesignForFile = globalDesignLocked
         ? design
         : globalDesignByFileRef.current.get(nextFileKey) ?? canonicalDesign;
       const requestId = ++renderRequestRef.current;
      const navRanges = rangesLookCompatible(ranges, normalization, analysis?.use_bark_units ?? false)
        ? ranges
        : defaultRanges;
      const response = await callSidecar<{ state: ApplicationState }>("navigate_interactive_preview", {
        index: target,
        options: {
          ranges: navRanges,
          sigma,
          show_ellipse: showEllipse,
           design: nextDesignForFile,
          request_id: requestId,
        },
      });
      const next = response.state;
      if (!aliveRef.current) return;
      currentIndexRef.current = target;
      const nextVowels = next.current_vowels ?? [];
       const nextStateSource = next.sources.find((source) => source.index === target);
       const resolvedNextFileKey = nextStateSource ? String(nextStateSource.path ?? `${nextStateSource.index}:${nextStateSource.name}`) : nextFileKey;
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
      const sessionNextRanges = nextSession.ranges as Ranges | undefined;
      const nextRanges = sessionNextRanges
        && Object.keys(sessionNextRanges).length === 4
        && rangesLookCompatible(sessionNextRanges, next.analysis?.normalization ?? null, next.analysis?.use_bark_units ?? false)
        ? sessionNextRanges
        : defaultRanges;
       const nextDesign = globalDesignLocked
         ? design
         : globalDesignByFileRef.current.get(resolvedNextFileKey) ?? ({ ...canonicalDesign, ...(nextSession.design_settings ?? {}) } as DesignSettings);
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
       cacheMapSet(globalDesignByFileRef.current, resolvedNextFileKey, nextDesign, MAX_CACHED_FILE_DESIGNS);
      setSigma(nextSigma);
      setShowEllipse(nextShowEllipse);
      setState(next);
      setMessage(`${nextStateSource?.name ?? nextSource.name ?? "파일"}을 불러오는 중입니다.`);
    } catch (err) {
      setMessage(`파일을 이동하지 못했습니다: ${String(err)}`);
      setPreviewLoading(false);
    } finally {
      navigatingRef.current = false;
      if (aliveRef.current) setNavigating(false);
    }
  }, [analysis?.use_bark_units, canonicalDesign, currentFileKey, defaultRanges, design, expandedLayers, globalDesignLocked, layerOverrides, layerState, lockedLayers, normalization, ranges, showEllipse, sigma, sources]);

  const navigateByPosition = useCallback((position: number) => {
    const target = sources[Math.max(0, Math.min(position, sources.length - 1))];
    if (target) void navigateTo(target.index);
  }, [navigateTo, sources]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (shortcutHelpOpen) {
        if (event.key === "?" || (event.shiftKey && event.key === "/")) {
          event.preventDefault();
          setShortcutHelpOpen(false);
        }
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        const target = event.target as HTMLElement | null;
        if (!target?.closest("input, textarea, select, [contenteditable='true']")) {
          event.preventDefault();
          void saveProject();
        }
        return;
        }
      if (tool === "draw" && (drawTool === "line" || drawTool === "area") && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        setDrawingPoints((previous) => previous.slice(0, -1));
        setMessage(drawTool === "area" ? "현재 영역의 마지막 점을 되돌렸습니다." : "현재 선의 마지막 점을 되돌렸습니다.");
        return;
      }
      if (tool === "draw" && (drawTool === "line" || drawTool === "area") && event.key === "Escape") {
        event.preventDefault();
        if (drawingPoints.length > 0) {
          setDrawingPoints([]);
          setDrawHover(null);
          setMessage(drawTool === "area" ? "영역 그리기를 취소했습니다." : "선 그리기를 취소했습니다.");
        } else {
          setDrawTool(null);
          setDrawHover(null);
          setReferencePreview(null);
          setTool("select");
          setMessage("그리기 모드를 종료했습니다.");
        }
        return;
      }
      if (tool === "draw" && (event.key === "Enter" || event.key === "Return")) {
        if (drawEditorOpen) return;
        const keyTarget = event.target as HTMLElement | null;
        if (keyTarget?.closest("textarea, select, [contenteditable='true']")) return;
        event.preventDefault();
        if (drawTool === "area") finishDrawPolygon(drawingPoints);
        else if (drawTool === "line") finishDrawLine(drawingPoints);
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
        if (sources.filter((source) => !source.is_combined).length < 2) return;
        event.preventDefault();
        void callSidecar("open_compare", { source_groups: sources.filter((source) => !source.is_combined).map((source) => [source.index]), normalization: analysis?.normalization ?? null });
        return;
      }
      if (event.key === "?" || (event.shiftKey && event.key === "/")) {
        const helpTarget = event.target as HTMLElement | null;
        if (helpTarget?.closest("input, textarea, select, [contenteditable='true']")) return;
        event.preventDefault();
        setShortcutHelpOpen((previous) => !previous);
        return;
      }
      if (event.key === "`" || event.code === "Backquote") {
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
        setTool((previous) => {
          if (previous === "draw") {
            setDrawTool(null);
            setReferencePreview(null);
            return "select";
          }
          setDrawTool(null);
          setRightPanel("drawing");
          setRightOpen(true);
          setMessage("그리기 도구를 선택하세요.");
          return "draw";
        });
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
        setDrawTool(null);
        setReferencePreview(null);
        setTool("select");
        return;
      }
      if (tool === "draw" && ["1", "2", "3", "4", "5"].includes(event.key)) {
        event.preventDefault();
        const next = (event.key === "1" ? "line" : event.key === "2" ? "area" : event.key === "3" ? "text" : event.key === "4" ? "reference" : "legend") as DrawTool;
        void activateDrawTool(next);
        return;
      }
      if (event.key === "Home" || event.key === "End") {
        event.preventDefault();
        navigateByPosition(event.key === "Home" ? 0 : sources.length - 1);
        return;
      }
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      if (!canNavigate || navigatingRef.current) return;
      event.preventDefault();
      navigateByPosition(currentSourcePosition + (event.key === "ArrowLeft" ? -1 : 1));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [analysis?.normalization, canNavigate, currentSourcePosition, drawArrowHead, drawArrowMode, drawColor, drawEditorOpen, drawLineStyle, drawTool, drawWidth, drawingPoints, navigateByPosition, navigating, rulerSettingsOpen, shortcutHelpOpen, sources, tool]);

  const updateDesign = (patch: Partial<DesignSettings>) => {
    const next = { ...design, ...patch };
    setDesign(next);
    if (currentFileKey) cacheMapSet(globalDesignByFileRef.current, currentFileKey, next, MAX_CACHED_FILE_DESIGNS);
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
    setGlobalDesignLocked(false);
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

  const enterDrawMode = (nextTool: DrawTool | null = null) => {
    setTool("draw");
    setRightPanel("drawing");
    setRightOpen(true);
    setDrawTool(nextTool);
    setDrawingPoints([]);
    setDrawHover(null);
    referencePointerRef.current = null;
    setReferencePreview(null);
    if (!nextTool) setMessage("그리기 도구를 선택하세요.");
  };

  const activateDrawTool = (next: DrawTool) => {
    enterDrawMode(next);
    if (next === "legend" && !currentLegend) {
      const legend = createDefaultLegend();
      persistDrawObjects([...currentDrawObjects, legend]);
      focusDrawObject(legend.id);
      setMessage("범례를 추가했습니다. 플롯에서 드래그해 위치를 옮기거나 팔레트로 편집하세요.");
    } else if (next === "reference") {
      setMessage(referenceMode === "horizontal" ? "수평 기준선 · 마우스를 올리면 미리보기가 보입니다." : "수직 기준선 · 마우스를 올리면 미리보기가 보입니다.");
    } else if (next === "area") {
      setMessage("영역을 그립니다. 점을 스냅하고 Enter 또는 시작점 재클릭으로 닫으세요.");
    } else if (next === "text") {
      setMessage("캔버스를 더블클릭하여 텍스트를 배치하세요.");
    } else if (next === "line") {
      setMessage("선을 그립니다. 점을 클릭하고 Enter 또는 더블클릭으로 확정하세요.");
    } else {
      setMessage("범례를 선택했습니다. 플롯에서 드래그해 위치를 옮길 수 있습니다.");
    }
  };

  const openLegacyPlot = async () => {
    setBusy(true);
    try { await callSidecar("open_single_plot"); } finally { setBusy(false); }
  };

  const openComparePlot = async () => {
    const real = sources.filter((source) => !source.is_combined);
    if (real.length < 2) {
      setMessage("다중 플롯은 파일이 2개 이상일 때 사용할 수 있습니다.");
      return;
    }
    setBusy(true);
    try {
      await callSidecar("open_compare", {
        source_groups: real.map((source) => [source.index]),
        normalization: analysis?.normalization ?? null,
      });
      setMessage("다중 플롯 창을 요청했습니다.");
    } catch (err) {
      setMessage(`다중 플롯을 열지 못했습니다: ${String(err)}`);
    } finally {
      setBusy(false);
    }
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
        draw_objects: currentDrawObjects,
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
        options: { ranges, sigma, show_ellipse: showEllipse, design, filter_state: layerState, layer_overrides: layerOverrides, layer_order: layerOrder, locked_layers: [...lockedLayers], draw_objects: currentDrawObjects },
      });
      setMessage(`${format.toUpperCase()} 파일을 저장했습니다.`);
    } catch (err) {
      setMessage(`내보내기 실패: ${String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const exportCombinedTxt = async () => {
    if (!hasCombined) return;
    const path = await save({
      title: "결합 데이터 TXT 저장",
      defaultPath: "Combined.txt",
      filters: [{ name: "GichanFormant TXT", extensions: ["txt"] }],
    });
    if (!path) return;
    setBusy(true);
    try {
      await callSidecar("export_combined_txt", { path });
      setMessage("결합 데이터를 TXT로 저장했습니다.");
    } catch (err) {
      setMessage(`TXT 저장 실패: ${String(err)}`);
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
        options: { ranges, sigma, show_ellipse: showEllipse, design, filter_state: layerState, layer_overrides: layerOverrides, layer_order: layerOrder, locked_layers: [...lockedLayers], draw_objects: currentDrawObjects, batch_options: { apply_global_design: batchApplyGlobalDesign, apply_layer_design: batchApplyLayerDesign, apply_layer_visibility: batchApplyVisibility, apply_label_positions: batchApplyLabelPositions } },
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
    if (!image) return null;
    // PNG 픽셀 공간과 ruler_context(axes_bbox)를 반드시 같은 기준으로 맞춤
    const srcW = rulerContext?.image_width || image.naturalWidth;
    const srcH = rulerContext?.image_height || image.naturalHeight;
    if (!srcW || !srcH) return null;
    const box = image.getBoundingClientRect();
    const scale = Math.min(box.width / srcW, box.height / srcH);
    const width = srcW * scale;
    const height = srcH * scale;
    return { left: box.left + (box.width - width) / 2, top: box.top + (box.height - height) / 2, scale, srcW, srcH };
  };

  const legendClientRect = (legend: DrawLegendObject, useMeasured = true) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    const measured = useMeasured ? rulerContext.legend_bounds?.[legend.id] : undefined;
    const bounds = measured ? { ...legend, ...measured } : legend;
    return {
      left: geometry.left + bounds.fx * rulerContext.image_width * geometry.scale,
      top: geometry.top + (1 - bounds.fy) * rulerContext.image_height * geometry.scale,
      width: bounds.width_frac * rulerContext.image_width * geometry.scale,
      height: bounds.height_frac * rulerContext.image_height * geometry.scale,
    };
  };

  const defaultLegendClientRect = (legend: DrawLegendObject) => legendClientRect({ ...legend, fx: 0.035, fy: Math.min(0.205, 1 - legend.height_frac - 0.016) }, false);

  const legendFromPointer = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext || !legendDragRef.current) return null;
    const dx = (clientX - legendDragRef.current.startX) / Math.max(1, rulerContext.image_width * geometry.scale);
    const dy = (clientY - legendDragRef.current.startY) / Math.max(1, rulerContext.image_height * geometry.scale);
    const legend = currentLegend;
    if (!legend) return null;
    const measured = rulerContext.legend_bounds?.[legend.id];
    const base = measured ? { ...legend, ...measured } : legend;
    const margin = 0.016;
    return {
      ...base,
      fx: Math.max(margin, Math.min(1 - base.width_frac - margin, legendDragRef.current.fx + dx)),
      fy: Math.max(base.height_frac + margin, Math.min(1 - margin, legendDragRef.current.fy - dy)),
    };
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

  const plotLabelBoxClient = (label: PlotLabel) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext || !label.bbox) return null;
    return {
      left: geometry.left + label.bbox.left * geometry.scale,
      top: geometry.top + label.bbox.top * geometry.scale,
      width: label.bbox.width * geometry.scale,
      height: label.bbox.height * geometry.scale,
    };
  };

  const plotDataFromClient = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    const imgH = rulerContext.image_height || geometry.srcH;
    const px = (clientX - geometry.left) / geometry.scale;
    const py = imgH - (clientY - geometry.top) / geometry.scale;
    const box = rulerContext.axes_bbox;
    if (box.width <= 0 || box.height <= 0) return null;
    const x = rulerContext.xlim[0] + ((px - box.left) / box.width) * (rulerContext.xlim[1] - rulerContext.xlim[0]);
    const y = rulerContext.ylim[0] + ((py - box.bottom) / box.height) * (rulerContext.ylim[1] - rulerContext.ylim[0]);
    return { x, y, px, py };
  };

  /** PySide event.inaxes — 축 안 더블클릭만 텍스트 배치 */
  const plotDataInAxesFromClient = (clientX: number, clientY: number) => {
    const data = plotDataFromClient(clientX, clientY);
    if (!data || !rulerContext) return null;
    const box = rulerContext.axes_bbox;
    if (
      data.px < box.left
      || data.px > box.left + box.width
      || data.py < box.bottom
      || data.py > box.bottom + box.height
    ) {
      return null;
    }
    return data;
  };

  /** 라벨 plotLabelClient / plotLabelBoxClient 와 동일 좌표계 */
  const drawTextAnchorClient = (object: DrawTextObject) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    const bounds = rulerContext.text_bounds?.[object.id];
    const imgH = rulerContext.image_height || geometry.srcH;
    if (bounds && Number.isFinite(bounds.apx) && Number.isFinite(bounds.apy)) {
      return {
        x: geometry.left + bounds.apx * geometry.scale,
        y: geometry.top + (imgH - bounds.apy) * geometry.scale,
      };
    }
    const box = rulerContext.axes_bbox;
    if (box.width <= 0 || box.height <= 0) return null;
    const xRatio = (object.x - rulerContext.xlim[0]) / Math.max(1e-9, rulerContext.xlim[1] - rulerContext.xlim[0]);
    const yRatio = (object.y - rulerContext.ylim[0]) / Math.max(1e-9, rulerContext.ylim[1] - rulerContext.ylim[0]);
    const px = box.left + xRatio * box.width;
    const py = box.bottom + yRatio * box.height;
    return {
      x: geometry.left + px * geometry.scale,
      y: geometry.top + (imgH - py) * geometry.scale,
    };
  };

  const drawTextBoxClient = (object: DrawTextObject) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    const bounds = rulerContext.text_bounds?.[object.id];
    if (!bounds) return null;
    return {
      left: geometry.left + bounds.left * geometry.scale,
      top: geometry.top + bounds.top * geometry.scale,
      width: Math.max(8, bounds.width * geometry.scale),
      height: Math.max(8, bounds.height * geometry.scale),
    };
  };

  const hitDrawTextAt = (clientX: number, clientY: number): DrawTextObject | null => {
    for (const object of currentDrawObjects) {
      if (object.type !== "text" || !object.visible) continue;
      const box = drawTextBoxClient(object);
      if (!box) continue;
      const pad = 6;
      if (
        clientX >= box.left - pad
        && clientX <= box.left + box.width + pad
        && clientY >= box.top - pad
        && clientY <= box.top + box.height + pad
      ) {
        return object;
      }
    }
    return null;
  };

  const openTextInputAt = (clientX: number, clientY: number) => {
    if (hitDrawTextAt(clientX, clientY)) return;
    const data = plotDataInAxesFromClient(clientX, clientY);
    if (!data) {
      setMessage("축 영역 안에서 더블클릭하세요.");
      return;
    }
    setTextInput({
      x: data.x,
      y: data.y,
      axis_units: plotUnits.drawAxisUnits,
      draft: "",
    });
  };

  const confirmTextInput = () => {
    if (!textInput) return;
    const content = textInput.draft;
    if (!content.trim()) {
      setMessage("텍스트가 비어 있으면 배치할 수 없습니다.");
      return;
    }
    const textObj: DrawTextObject = {
      type: "text",
      id: `react-text-${currentIndex}-${Date.now()}-${drawIdRef.current++}`,
      text: content,
      x: textInput.x,
      y: textInput.y,
      font_size: clampDrawTextFontSize(drawTextFontSize),
      font_family: drawTextFontFamily || DRAW_TEXT_DEFAULT_FAMILY,
      font_weight: normalizedFontWeight(drawTextFontFamily || DRAW_TEXT_DEFAULT_FAMILY, drawTextFontWeight),
      font_bold: ["bold", "semibold"].includes(normalizedFontWeight(drawTextFontFamily || DRAW_TEXT_DEFAULT_FAMILY, drawTextFontWeight)),
      font_italic: drawTextItalic,
      line_spacing: clampDrawTextLineSpacing(drawTextLineSpacing),
      text_color: drawTextColor || DRAW_TEXT_DEFAULT_COLOR,
      axis_units: textInput.axis_units,
      visible: true,
      semi: false,
    };
    const count = currentDrawObjects.filter((object) => object.type === "text").length;
    persistDrawObjects([...currentDrawObjects, textObj]);
    focusDrawObject(textObj.id);
    setTextInput(null);
    setMessage(`텍스트 ${count + 1}개를 추가했습니다. 팔레트로 스타일을 수정할 수 있습니다.`);
  };

  const nearestPlotLabel = (clientX: number, clientY: number) => {
    if (!rulerContext) return null;
    let nearest: PlotLabel | null = null;
    let best = 28 * 28;
    for (const label of rulerContext.labels) {
      const box = plotLabelBoxClient(label);
      if (box && clientX >= box.left - 8 && clientX <= box.left + box.width + 8 && clientY >= box.top - 8 && clientY <= box.top + box.height + 8) return label;
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

  /** data → client (선 그리기·스냅용). 축 안 값은 axesRectLocal 비율로도 동일하게 나와야 함. */
  const drawPointClient = (point: DrawPoint) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    const box = rulerContext.axes_bbox;
    if (box.width <= 0 || box.height <= 0) return null;
    const xRatio = (point.x - rulerContext.xlim[0]) / Math.max(1e-9, rulerContext.xlim[1] - rulerContext.xlim[0]);
    const yRatio = (point.y - rulerContext.ylim[0]) / Math.max(1e-9, rulerContext.ylim[1] - rulerContext.ylim[0]);
    const px = box.left + xRatio * box.width;
    const py = box.bottom + yRatio * box.height;
    const imgH = rulerContext.image_height || geometry.srcH;
    return { x: geometry.left + px * geometry.scale, y: geometry.top + (imgH - py) * geometry.scale };
  };

  /** 호버용: 스냅 우선(transData px/py 포함), 없으면 커서 data(가이드만). 클릭은 스냅만. */
  const drawHoverAtClient = (clientX: number, clientY: number): DrawHoverState | null => {
    if (!rulerContext) return null;
    const snapped = nearestRulerPoint(clientX, clientY);
    if (snapped) {
      return {
        point: { x: snapped.x, y: snapped.y, label: snapped.label, px: snapped.px, py: snapped.py },
        clientX,
        clientY,
        snapped: true,
        rulerPoint: snapped,
      };
    }
    const data = plotDataFromClient(clientX, clientY);
    if (!data) return null;
    return { point: { x: data.x, y: data.y }, clientX, clientY, snapped: false, rulerPoint: null };
  };

  const createDefaultLegend = (): DrawLegendObject => ({
    type: "legend",
    id: `react-legend-${currentIndex}-${Date.now()}-${drawIdRef.current++}`,
    name: legendDefaults.name || "범례",
    entries: [{ series_id: 0, text: (currentSource?.name ?? "데이터").replace(/\.[^.]+$/, "") }],
    fx: 0.035,
    fy: 0.205,
    width_frac: 0.30,
    height_frac: 0.14,
    font_size: legendDefaults.font_size,
    font_family: legendDefaults.font_family,
    font_weight: legendDefaults.font_weight,
    font_italic: legendDefaults.font_italic,
    show_border: legendDefaults.show_border,
    border_style: legendDefaults.border_style,
    border_color: legendDefaults.border_color,
    show_fill: legendDefaults.show_fill,
    fill_color: legendDefaults.fill_color,
    fill_opacity: legendDefaults.fill_opacity,
    visible: true,
    semi: false,
  });

  const persistDrawObjects = (objects: DrawObject[]) => {
    setDrawObjectsByFile((previous) => ({ ...previous, [currentIndex]: objects }));
    const alive = new Set(objects.map((object) => object.id));
    setSelectedDrawObjectIds((previous) => {
      const next = new Set([...previous].filter((id) => alive.has(id)));
      if (next.size !== previous.size) {
        const primary = selectedDrawObjectId && next.has(selectedDrawObjectId)
          ? selectedDrawObjectId
          : [...next][0] ?? null;
        setSelectedDrawObjectId(primary);
        drawSelectionAnchorRef.current = primary ?? "";
      } else if (selectedDrawObjectId && !alive.has(selectedDrawObjectId)) {
        setSelectedDrawObjectId(null);
        drawSelectionAnchorRef.current = "";
      }
      return next.size === previous.size ? previous : next;
    });
    void renderInteractive({ drawObjects: objects });
  };

  /** 목록은 위=앞(최신). 저장 배열은 아래→위(렌더 마지막이 위). */
  const drawObjectsTopFirst = useMemo(
    () => [...currentDrawObjects].reverse(),
    [currentDrawObjects],
  );

  const selectDrawObject = (id: string, event: ReactMouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    const order = drawObjectsTopFirst.map((object) => object.id);
    const anchor = drawSelectionAnchorRef.current;
    const withRange = event.shiftKey && anchor && order.includes(anchor);
    if (withRange) {
      const start = order.indexOf(anchor);
      const end = order.indexOf(id);
      const range = order.slice(Math.min(start, end), Math.max(start, end) + 1);
      setSelectedDrawObjectIds((previous) => {
        if (event.ctrlKey || event.metaKey) return new Set([...previous, ...range]);
        return new Set(range);
      });
      setSelectedDrawObjectId(id);
      return;
    }
    if (event.ctrlKey || event.metaKey) {
      setSelectedDrawObjectIds((previous) => {
        const next = new Set(previous);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        const nextPrimary = next.has(id) ? id : [...next][0] ?? null;
        setSelectedDrawObjectId(nextPrimary);
        if (next.size) drawSelectionAnchorRef.current = nextPrimary ?? "";
        return next;
      });
      return;
    }
    if (selectedDrawObjectId === id) {
      setSelectedDrawObjectId(null);
      setSelectedDrawObjectIds(new Set());
      drawSelectionAnchorRef.current = "";
      return;
    }
    setSelectedDrawObjectIds(new Set([id]));
    setSelectedDrawObjectId(id);
    drawSelectionAnchorRef.current = id;
  };

  const focusDrawObject = (id: string) => {
    setSelectedDrawObjectIds(new Set([id]));
    setSelectedDrawObjectId(id);
    drawSelectionAnchorRef.current = id;
  };

  const deleteDrawObjects = (id: string) => {
    const targets = selectedDrawObjectIds.has(id) && selectedDrawObjectIds.size > 1
      ? selectedDrawObjectIds
      : new Set([id]);
    persistDrawObjects(currentDrawObjects.filter((object) => !targets.has(object.id)));
  };

  const toggleDrawObjectVisibility = (id: string) => {
    persistDrawObjects(currentDrawObjects.map((object) => object.id === id ? { ...object, visible: !object.visible } : object));
  };

  const toggleAllDrawVisibility = () => {
    const allHidden = currentDrawObjects.length > 0 && currentDrawObjects.every((object) => !object.visible);
    persistDrawObjects(currentDrawObjects.map((object) => ({ ...object, visible: allHidden })));
  };

  const toggleAllDrawSemi = () => {
    const allSemi = currentDrawObjects.length > 0 && currentDrawObjects.every((object) => object.semi);
    persistDrawObjects(currentDrawObjects.map((object) => ({ ...object, semi: !allSemi })));
  };

  const toggleDrawObjectSemi = (id: string) => {
    persistDrawObjects(currentDrawObjects.map((object) => object.id === id ? { ...object, semi: !object.semi } : object));
  };

  const beginDrawObjectDrag = (event: ReactPointerEvent<HTMLButtonElement>, id: string) => {
    event.preventDefault();
    const visualIds = drawObjectsTopFirst.map((object) => object.id);
    const ids = selectedDrawObjectIds.has(id) && selectedDrawObjectIds.size > 1
      ? visualIds.filter((item) => selectedDrawObjectIds.has(item))
      : [id];
    drawObjectDragRef.current = { id, ids, startY: event.clientY, moved: false };
    setDraggingDrawObject(id);
    if (!selectedDrawObjectIds.has(id)) {
      setSelectedDrawObjectIds(new Set([id]));
      setSelectedDrawObjectId(id);
      drawSelectionAnchorRef.current = id;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const moveDrawObjectDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = drawObjectDragRef.current;
    if (!drag) return;
    if (!drag.moved && Math.abs(event.clientY - drag.startY) < 4) return;
    drag.moved = true;
    const element = document.elementFromPoint(event.clientX, event.clientY)?.closest<HTMLElement>("[data-draw-object-id]");
    if (!element) return;
    const targetId = element.dataset.drawObjectId;
    if (!targetId || drag.ids.includes(targetId)) return;
    const rect = element.getBoundingClientRect();
    setDrawDropTarget({ id: targetId, after: event.clientY > rect.top + rect.height / 2 });
  };

  const commitDrawObjectDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = drawObjectDragRef.current;
    if (!drag) return;
    const target = drawDropTarget;
    if (drag.moved && target) {
      const visual = [...currentDrawObjects].reverse();
      const draggedSet = new Set(drag.ids);
      const without = visual.filter((object) => !draggedSet.has(object.id));
      const insertAt = without.findIndex((object) => object.id === target.id) + (target.after ? 1 : 0);
      const dragged = visual.filter((object) => draggedSet.has(object.id));
      if (dragged.length) {
        const nextVisual = [...without];
        nextVisual.splice(Math.max(0, insertAt), 0, ...dragged);
        persistDrawObjects([...nextVisual].reverse());
      }
    }
    drawObjectDragRef.current = null;
    setDraggingDrawObject(null);
    setDrawDropTarget(null);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  };

  const cancelDrawObjectDrag = () => {
    drawObjectDragRef.current = null;
    setDraggingDrawObject(null);
    setDrawDropTarget(null);
  };

  const closeDrawEditor = () => {
    setDrawEditorOpen(false);
    setDrawEditorObjectId(null);
    setLineDraft(null);
    setPolygonDraft(null);
    setReferenceDraft(null);
    setLegendDraft(null);
    setTextDraft(null);
  };

  const openDrawDefaultsEditor = (kind?: DrawEditorKind) => {
    const nextKind: DrawEditorKind = kind
      ?? (drawTool === "legend" || drawTool === "reference" || drawTool === "line" || drawTool === "text"
        ? drawTool
        : drawTool === "area" ? "polygon" : "line");
    setDrawEditorMode("defaults");
    setDrawEditorKind(nextKind);
    setDrawEditorObjectId(null);
    setLineDraft(null);
    setPolygonDraft(null);
    setReferenceDraft(null);
    setLegendDraft(null);
    setTextDraft(null);
    if (nextKind === "line") {
      setLineDraft({
        line_color: drawColor ?? DRAW_LINE_DEFAULT_COLOR,
        line_style: drawLineStyle,
        line_width: clampDrawLineWidth(drawWidth),
        arrow_mode: drawArrowMode,
        arrow_head: drawArrowHead,
      });
    } else if (nextKind === "polygon") {
      setPolygonDraft({
        border_style: drawPolyBorderStyle,
        border_color: drawPolyBorderColor,
        fill_color: drawPolyFillColor,
        fill_opacity: drawPolyFillOpacity,
      });
    } else if (nextKind === "reference") {
      setReferenceDraft({
        mode: referenceMode,
        line_style: drawRefStyle,
        line_color: drawRefColor,
      });
    } else if (nextKind === "text") {
      setTextDraft({
        text: "",
        font_size: drawTextFontSize,
        font_family: drawTextFontFamily,
        font_weight: normalizedFontWeight(drawTextFontFamily, drawTextFontWeight),
        font_italic: drawTextItalic,
        line_spacing: drawTextLineSpacing,
        text_color: drawTextColor,
      });
    } else {
      const legend = currentLegend;
      setLegendDraft({
        id: legend?.id ?? "legend-defaults",
        name: legendDefaults.name,
        entries: legend
          ? legend.entries.map((entry) => ({ ...entry }))
          : [{ series_id: 0, text: (currentSource?.name ?? "데이터").replace(/\.[^.]+$/, "") }],
        fx: legend?.fx ?? 0.035,
        fy: legend?.fy ?? 0.205,
        width_frac: legend?.width_frac ?? 0.30,
        height_frac: legend?.height_frac ?? 0.14,
        font_size: legendDefaults.font_size,
        font_family: legendDefaults.font_family,
        font_weight: legendDefaults.font_weight,
        font_italic: legendDefaults.font_italic,
        show_border: legendDefaults.show_border,
        border_style: legendDefaults.border_style,
        border_color: legendDefaults.border_color,
        show_fill: legendDefaults.show_fill,
        fill_color: legendDefaults.fill_color,
        fill_opacity: legendDefaults.fill_opacity,
        visible: true,
        semi: false,
      });
    }
    setDrawEditorOpen(true);
  };

  const openDrawLayerEditor = (object: DrawObject) => {
    focusDrawObject(object.id);
    setDrawEditorMode("layer");
    setDrawEditorObjectId(object.id);
    setLineDraft(null);
    setPolygonDraft(null);
    setReferenceDraft(null);
    setLegendDraft(null);
    setTextDraft(null);
    if (object.type === "line") {
      setDrawEditorKind("line");
      setLineDraft({
        line_color: object.line_color,
        line_style: object.line_style,
        line_width: clampDrawLineWidth(object.line_width),
        arrow_mode: object.arrow_mode,
        arrow_head: object.arrow_head,
      });
    } else if (object.type === "polygon") {
      setDrawEditorKind("polygon");
      setPolygonDraft({
        border_style: object.border_style,
        border_color: object.border_color,
        fill_color: object.fill_color,
        fill_opacity: Number.isFinite(object.fill_opacity) ? object.fill_opacity : 0.15,
      });
    } else if (object.type === "reference") {
      setDrawEditorKind("reference");
      setReferenceDraft({
        mode: object.mode,
        line_style: object.line_style,
        line_color: object.line_color,
        valueLabel: formatRefLabel(object.value, object.axis_units, true, analysis?.normalization ?? null).trim(),
      });
    } else if (object.type === "text") {
      setDrawEditorKind("text");
      const family = object.font_family || DRAW_TEXT_DEFAULT_FAMILY;
      setTextDraft({
        text: object.text,
        font_size: clampDrawTextFontSize(object.font_size),
        font_family: family,
        font_weight: normalizedFontWeight(family, object.font_weight ?? (object.font_bold ? "bold" : "regular")),
        font_italic: object.font_italic,
        line_spacing: clampDrawTextLineSpacing(object.line_spacing ?? DRAW_TEXT_DEFAULT_LINE_SPACING),
        text_color: object.text_color || DRAW_TEXT_DEFAULT_COLOR,
      });
    } else {
      setDrawEditorKind("legend");
      setLegendDraft({ ...object, entries: object.entries.map((entry) => ({ ...entry })) });
    }
    setDrawEditorOpen(true);
  };

  const saveDrawEditor = () => {
    if (drawEditorKind === "line" && lineDraft) {
      if (drawEditorMode === "defaults") {
        setDrawColor(lineDraft.line_color);
        setDrawLineStyle(lineDraft.line_style);
        setDrawWidth(clampDrawLineWidth(lineDraft.line_width));
        setDrawArrowMode(lineDraft.arrow_mode);
        setDrawArrowHead(lineDraft.arrow_head);
        setMessage("선 기본 스타일을 저장했습니다.");
      } else if (drawEditorObjectId) {
        const nextLine = { ...lineDraft, line_width: clampDrawLineWidth(lineDraft.line_width) };
        persistDrawObjects(currentDrawObjects.map((object) => (
          object.type === "line" && object.id === drawEditorObjectId
            ? { ...object, ...nextLine }
            : object
        )));
        setMessage("선 레이어를 수정했습니다.");
      }
    } else if (drawEditorKind === "polygon" && polygonDraft) {
      const nextPoly = {
        ...polygonDraft,
        fill_opacity: Math.min(1, Math.max(0, Number(polygonDraft.fill_opacity) || 0)),
      };
      if (drawEditorMode === "defaults") {
        setDrawPolyBorderStyle(nextPoly.border_style);
        setDrawPolyBorderColor(nextPoly.border_color);
        setDrawPolyFillColor(nextPoly.fill_color);
        setDrawPolyFillOpacity(nextPoly.fill_opacity);
        setMessage("영역 기본 스타일을 저장했습니다.");
      } else if (drawEditorObjectId) {
        persistDrawObjects(currentDrawObjects.map((object) => (
          object.type === "polygon" && object.id === drawEditorObjectId
            ? { ...object, ...nextPoly }
            : object
        )));
        setMessage("영역 레이어를 수정했습니다.");
      }
    } else if (drawEditorKind === "reference" && referenceDraft) {
      if (drawEditorMode === "defaults") {
        setReferenceMode(referenceDraft.mode);
        setDrawRefStyle(referenceDraft.line_style);
        setDrawRefColor(referenceDraft.line_color);
        setMessage("기준선 기본 스타일을 저장했습니다.");
      } else if (drawEditorObjectId) {
        persistDrawObjects(currentDrawObjects.map((object) => (
          object.type === "reference" && object.id === drawEditorObjectId
            ? { ...object, mode: referenceDraft.mode, line_style: referenceDraft.line_style, line_color: referenceDraft.line_color }
            : object
        )));
        setMessage("기준선 레이어를 수정했습니다.");
      }
    } else if (drawEditorKind === "legend" && legendDraft) {
      const nextLegend: DrawLegendObject = {
        type: "legend",
        ...legendDraft,
        entries: legendDraft.entries.map((entry, index) => ({
          ...entry,
          series_id: Number.isFinite(entry.series_id) ? entry.series_id : index,
        })),
      };
      if (drawEditorMode === "defaults") {
        setLegendDefaults({
          name: nextLegend.name,
          font_size: nextLegend.font_size,
          font_family: nextLegend.font_family,
          font_weight: nextLegend.font_weight,
          font_italic: nextLegend.font_italic,
          show_border: nextLegend.show_border,
          border_style: nextLegend.border_style,
          border_color: nextLegend.border_color,
          show_fill: nextLegend.show_fill,
          fill_color: nextLegend.fill_color,
          fill_opacity: nextLegend.fill_opacity,
        });
        setMessage("범례 기본 스타일을 저장했습니다.");
      } else {
        persistDrawObjects([...currentDrawObjects.filter((object) => object.type !== "legend"), nextLegend]);
        setMessage("범례 레이어를 수정했습니다.");
      }
    } else if (drawEditorKind === "text" && textDraft) {
      const family = textDraft.font_family || DRAW_TEXT_DEFAULT_FAMILY;
      const weight = normalizedFontWeight(family, textDraft.font_weight);
      const nextText = {
        text: textDraft.text,
        font_size: clampDrawTextFontSize(textDraft.font_size),
        font_family: family,
        font_weight: weight,
        font_bold: weight === "bold" || weight === "semibold",
        font_italic: textDraft.font_italic,
        line_spacing: clampDrawTextLineSpacing(textDraft.line_spacing),
        text_color: textDraft.text_color || DRAW_TEXT_DEFAULT_COLOR,
      };
      if (drawEditorMode === "defaults") {
        setDrawTextFontSize(nextText.font_size);
        setDrawTextFontFamily(nextText.font_family);
        setDrawTextFontWeight(nextText.font_weight);
        setDrawTextItalic(nextText.font_italic);
        setDrawTextLineSpacing(nextText.line_spacing);
        setDrawTextColor(nextText.text_color);
        setMessage("텍스트 기본 스타일을 저장했습니다.");
      } else if (drawEditorObjectId) {
        if (!nextText.text.trim()) {
          setMessage("텍스트가 비어 있으면 적용할 수 없습니다.");
          return;
        }
        persistDrawObjects(currentDrawObjects.map((object) => (
          object.type === "text" && object.id === drawEditorObjectId
            ? { ...object, ...nextText }
            : object
        )));
        setMessage("텍스트 레이어를 수정했습니다.");
      }
    }
    closeDrawEditor();
  };

  saveDrawEditorRef.current = saveDrawEditor;
  closeDrawEditorRef.current = closeDrawEditor;

  const finishDrawLine = (points: DrawPoint[]) => {
    if (points.length < 2) {
      setDrawingPoints([]);
      setDrawHover(null);
      return;
    }
    const line: DrawLineObject = {
      type: "line",
      id: `react-line-${currentIndex}-${Date.now()}-${drawIdRef.current++}`,
      points: points.map(({ x, y }) => [x, y]),
      line_color: drawColor ?? DRAW_LINE_DEFAULT_COLOR,
      line_style: drawLineStyle,
      line_width: clampDrawLineWidth(drawWidth),
      arrow_mode: drawArrowMode,
      arrow_head: drawArrowHead,
      visible: true,
      semi: false,
    };
    persistDrawObjects([...currentDrawObjects, line]);
    focusDrawObject(line.id);
    setDrawingPoints([]);
    setDrawHover(null);
    setMessage(`선 ${currentDrawLines.length + 1}개를 추가했습니다. 팔레트로 스타일을 수정할 수 있습니다.`);
  };

  const finishDrawPolygon = (points: DrawPoint[]) => {
    const unique = points.length >= 2
      && Math.hypot(points[0].x - points[points.length - 1].x, points[0].y - points[points.length - 1].y) < 1e-6
      ? points.slice(0, -1)
      : points;
    if (unique.length < 3) {
      setMessage("영역은 점 3개 이상이 필요합니다.");
      return;
    }
    const closed: Array<[number, number]> = [
      ...unique.map(({ x, y }): [number, number] => [x, y]),
      [unique[0].x, unique[0].y],
    ];
    const polygon: DrawPolygonObject = {
      type: "polygon",
      id: `react-poly-${currentIndex}-${Date.now()}-${drawIdRef.current++}`,
      points: closed,
      border_style: drawPolyBorderStyle,
      border_color: drawPolyBorderColor,
      fill_color: drawPolyFillColor,
      fill_opacity: drawPolyFillOpacity,
      show_area_label: false,
      visible: true,
      semi: false,
    };
    const polyCount = currentDrawObjects.filter((object) => object.type === "polygon").length;
    persistDrawObjects([...currentDrawObjects, polygon]);
    focusDrawObject(polygon.id);
    setDrawingPoints([]);
    setDrawHover(null);
    setMessage(`영역 ${polyCount + 1}개를 추가했습니다. 팔레트로 스타일을 수정할 수 있습니다.`);
  };

  const rulerLocalPoint = (clientX: number, clientY: number) => {
    const box = plotPaperRef.current?.getBoundingClientRect();
    return box ? { x: clientX - box.left, y: clientY - box.top } : null;
  };

  /** 축 bbox를 paper-local 픽셀로 — 프리뷰 선 끝점은 항상 여기서 잡음 (PySide ax.get_xlim/ylim 대응) */
  const axesRectLocal = () => {
    const geometry = rulerImageGeometry();
    const paper = plotPaperRef.current?.getBoundingClientRect();
    if (!geometry || !paper || !rulerContext) return null;
    const box = rulerContext.axes_bbox;
    const imgH = rulerContext.image_height || geometry.srcH;
    const left = geometry.left - paper.left + box.left * geometry.scale;
    const top = geometry.top - paper.top + (imgH - (box.bottom + box.height)) * geometry.scale;
    return { left, top, width: box.width * geometry.scale, height: box.height * geometry.scale };
  };

  const referenceAxesSpan = (paperWidth: number, paperHeight: number) => {
    const axes = axesRectLocal();
    const x1 = axes && axes.width > 8 ? axes.left : 4;
    const x2 = axes && axes.width > 8 ? axes.left + axes.width : paperWidth - 4;
    const y1 = axes && axes.height > 8 ? axes.top : 4;
    const y2 = axes && axes.height > 8 ? axes.top + axes.height : paperHeight - 4;
    return { x1, x2, y1, y2 };
  };

  /**
   * plotValue(축 data) → paper-local 선. axesRectLocal 비율만 사용.
   * ylim/xlim에 가까우면 축 박스 안으로 clamp → 항상 보임 + 눈금과 같은 비율.
   * 단위가 완전히 어긋난 값(축 밖 멀리)은 null → 커서 fallback(라벨 없음).
   * Matplotlib: ylim[0]=축 하단 data, ylim[1]=축 상단 data.
   */
  const referenceLineFromPlotValue = (plotValue: number, horizontal: boolean, paperWidth: number, paperHeight: number) => {
    const axes = axesRectLocal();
    const span = referenceAxesSpan(paperWidth, paperHeight);
    if (!rulerContext || !axes || axes.width <= 8 || axes.height <= 8) return null;
    const { xlim, ylim } = rulerContext;
    if (horizontal) {
      const denom = ylim[1] - ylim[0];
      if (!Number.isFinite(plotValue) || Math.abs(denom) < 1e-12) return null;
      const tRaw = (plotValue - ylim[0]) / denom;
      if (tRaw < -0.5 || tRaw > 1.5) return null;
      const t = Math.min(1, Math.max(0, tRaw));
      const y = axes.top + (1 - t) * axes.height;
      return { x1: span.x1, y1: y, x2: span.x2, y2: y };
    }
    const denom = xlim[1] - xlim[0];
    if (!Number.isFinite(plotValue) || Math.abs(denom) < 1e-12) return null;
    const tRaw = (plotValue - xlim[0]) / denom;
    if (tRaw < -0.5 || tRaw > 1.5) return null;
    const t = Math.min(1, Math.max(0, tRaw));
    const x = axes.left + t * axes.width;
    return { x1: x, y1: span.y1, x2: x, y2: span.y2 };
  };

  const resolveReferencePlacement = (clientX: number, clientY: number): { object: DrawReferenceObject; preview: ReferencePreview } | null => {
    const data = plotDataFromClient(clientX, clientY);
    if (!data || !rulerContext) return null;
    const normalization = analysis?.normalization ?? rulerContext.params.normalization ?? null;
    const horizontal = referenceMode === "horizontal";
    const scale = normalization
      ? "linear"
      : horizontal
        ? (analysis?.f1_scale ?? rulerContext.params.f1_scale ?? "linear")
        : (analysis?.f2_scale ?? rulerContext.params.f2_scale ?? "linear");
    const unit = plotUnits.drawAxisUnits;
    const axisName = horizontal ? plotUnits.yAxisName : plotUnits.xAxisName;
    const plotCoord = horizontal ? data.y : data.x;
    const means = (rulerContext.points || []).filter((point) => point.type === "mean");
    const extra = means.map((point) => {
      const coord = horizontal ? point.y : point.x;
      if (scale === "bark" && unit.toLowerCase() === "hz") return barkToHz(coord);
      return coord;
    });
    const { value, snapped } = roundRefValue(plotCoord, scale, unit, extra, normalization);
    let plotValue = value;
    if (scale === "bark" && unit.toLowerCase() === "hz") plotValue = hzToBark(value);
    const paper = plotPaperRef.current?.getBoundingClientRect();
    if (!paper) return null;
    // 선·라벨 동일 plotValue. 축 비율 투영 → 보이기 + 눈금 정렬 동시.
    const line = referenceLineFromPlotValue(plotValue, horizontal, paper.width, paper.height);
    if (!line) return null;
    return {
      object: {
        type: "reference",
        id: `react-ref-${currentIndex}-${Date.now()}-${drawIdRef.current++}`,
        mode: referenceMode,
        value,
        axis_units: unit,
        axis_name: axisName,
        axis_scale: scale,
        line_style: drawRefStyle,
        line_color: drawRefColor,
        visible: true,
        semi: false,
      },
      preview: {
        mode: referenceMode,
        plotValue,
        label: formatRefLabel(value, unit, snapped, normalization),
        snapped,
        ...line,
      },
    };
  };

  const pushReferencePreview = (preview: ReferencePreview | null) => {
    referencePointerRef.current = preview;
    setReferencePreview(preview);
  };

  /**
   * 둘 다 만족:
   * 1) paper 위면 선은 항상 보임
   * 2) 스냅 라벨이 있으면 선은 그 plotValue 축 위치(커서와 라벨 혼합 금지)
   */
  referenceMoveRef.current = (clientX: number, clientY: number) => {
    if (tool !== "draw" || drawTool !== "reference") return;
    const paper = plotPaperRef.current?.getBoundingClientRect();
    const local = rulerLocalPoint(clientX, clientY);
    if (!paper || !local) {
      pushReferencePreview(null);
      return;
    }
    if (local.x < 0 || local.y < 0 || local.x > paper.width || local.y > paper.height) {
      pushReferencePreview(null);
      return;
    }
    const horizontal = referenceMode === "horizontal";
    const span = referenceAxesSpan(paper.width, paper.height);
    const cursorLine = {
      x1: horizontal ? span.x1 : local.x,
      y1: horizontal ? local.y : span.y1,
      x2: horizontal ? span.x2 : local.x,
      y2: horizontal ? local.y : span.y2,
    };
    const placed = resolveReferencePlacement(clientX, clientY);
    if (placed) {
      pushReferencePreview(placed.preview);
      return;
    }
    // 투영 실패: 커서로 보이게 하되 스냅 라벨은 붙이지 않음
    pushReferencePreview({
      mode: referenceMode,
      plotValue: 0,
      label: "",
      snapped: false,
      ...cursorLine,
    });
  };

  useEffect(() => {
    if (tool !== "draw" || drawTool !== "reference") {
      referencePointerRef.current = null;
      setReferencePreview(null);
      return;
    }
    const onMove = (event: PointerEvent) => referenceMoveRef.current(event.clientX, event.clientY);
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [tool, drawTool]);

  /** PySide DrawLineTool / DrawPolygonTool._on_move: paper 안이면 스냅/커서 hover */
  const assignSnapDrawMove = (clientX: number, clientY: number) => {
    const paper = plotPaperRef.current?.getBoundingClientRect();
    const local = rulerLocalPoint(clientX, clientY);
    if (!paper || !local) {
      setDrawHover(null);
      return;
    }
    if (local.x < 0 || local.y < 0 || local.x > paper.width || local.y > paper.height) {
      setDrawHover(null);
      return;
    }
    setDrawHover(drawHoverAtClient(clientX, clientY));
  };

  lineMoveRef.current = (clientX: number, clientY: number) => {
    if (tool !== "draw" || drawTool !== "line") return;
    assignSnapDrawMove(clientX, clientY);
  };

  areaMoveRef.current = (clientX: number, clientY: number) => {
    if (tool !== "draw" || drawTool !== "area") return;
    assignSnapDrawMove(clientX, clientY);
  };

  useEffect(() => {
    if (tool !== "draw" || (drawTool !== "line" && drawTool !== "area")) {
      if (drawTool !== "line" && drawTool !== "area") setDrawHover(null);
      return;
    }
    const onMove = (event: PointerEvent) => {
      if (drawTool === "area") areaMoveRef.current(event.clientX, event.clientY);
      else lineMoveRef.current(event.clientX, event.clientY);
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [tool, drawTool]);

  const handleRulerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (tool === "draw") {
      if (textDragRef.current) {
        const local = rulerLocalPoint(event.clientX, event.clientY);
        if (local) {
          textHasMovedRef.current = true;
          if (textDragFrameRef.current === null) {
            textDragFrameRef.current = requestAnimationFrame(() => {
              textDragFrameRef.current = null;
              setTextDragPointer(local);
            });
          }
        }
        return;
      }
      setHoveredDrawTextId(hitDrawTextAt(event.clientX, event.clientY)?.id ?? null);
      if (drawTool === "reference") {
        referenceMoveRef.current(event.clientX, event.clientY);
        return;
      }
      if (drawTool === "line") {
        lineMoveRef.current(event.clientX, event.clientY);
        return;
      }
      if (drawTool === "area") {
        areaMoveRef.current(event.clientX, event.clientY);
        return;
      }
      if (drawTool === "legend" && draggingLegend) {
        const nextLegend = legendFromPointer(event.clientX, event.clientY);
        if (nextLegend) {
          legendPointerRef.current = {
            fx: nextLegend.fx,
            fy: nextLegend.fy,
            width_frac: nextLegend.width_frac,
            height_frac: nextLegend.height_frac,
          };
          if (legendFrameRef.current === null) {
            legendFrameRef.current = requestAnimationFrame(() => {
              legendFrameRef.current = null;
              const latest = legendPointerRef.current;
              if (latest) setLegendDragPreview(latest);
            });
          }
        }
        return;
      }
      if (drawTool === "legend" || drawTool === "text") return;
      setDrawHover(drawHoverAtClient(event.clientX, event.clientY));
      return;
    }
    if (tool === "label" && draggingPlotLabel) {
      const local = rulerLocalPoint(event.clientX, event.clientY);
      const start = plotLabelDragStartRef.current;
      if (start && Math.hypot(event.clientX - start.x, event.clientY - start.y) > 4) {
        plotLabelHasMovedRef.current = true;
      }
      if (!plotLabelHasMovedRef.current) return;
      if (local && plotLabelFrameRef.current === null) {
        plotLabelFrameRef.current = requestAnimationFrame(() => {
          plotLabelFrameRef.current = null;
          setPlotLabelPointer(local);
        });
      }
      return;
    }
    if (tool === "label") {
      setHoveredPlotLabel(nearestPlotLabel(event.clientX, event.clientY)?.vowel ?? null);
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
    if (tool === "draw" && event.button === 0) {
      event.preventDefault();
      const hitText = hitDrawTextAt(event.clientX, event.clientY);
      if (hitText) {
        const data = plotDataFromClient(event.clientX, event.clientY);
        if (!data) return;
        focusDrawObject(hitText.id);
        textDragRef.current = {
          id: hitText.id,
          offsetX: hitText.x - data.x,
          offsetY: hitText.y - data.y,
        };
        textHasMovedRef.current = false;
        setDraggingTextId(hitText.id);
        setTextDragPointer(null);
        event.currentTarget.setPointerCapture(event.pointerId);
        return;
      }
      if (drawTool === "reference") {
        const placed = resolveReferencePlacement(event.clientX, event.clientY);
        if (!placed) {
          setMessage("플롯 영역 안에서 클릭해 기준선을 놓으세요.");
          return;
        }
        persistDrawObjects([...currentDrawObjects, placed.object]);
        focusDrawObject(placed.object.id);
        // 클릭 직후 백엔드 렌더 전까지도 프리뷰를 유지 (PySide는 canvas artist로 즉시 보임)
        pushReferencePreview(placed.preview);
        setMessage(`${placed.object.mode === "horizontal" ? "수평" : "수직"} 기준선 ${placed.preview.label.trim()} 을(를) 추가했습니다.`);
        return;
      }
      if (drawTool === "legend") {
        if (!currentLegend) return;
        const rect = legendClientRect(currentLegend);
        if (!rect || event.clientX < rect.left || event.clientX > rect.left + rect.width || event.clientY < rect.top || event.clientY > rect.top + rect.height) {
          setMessage("범례 박스를 드래그하면 위치를 옮길 수 있습니다.");
          return;
        }
        const measured = rulerContext?.legend_bounds?.[currentLegend.id];
        legendDragRef.current = { startX: event.clientX, startY: event.clientY, fx: measured?.fx ?? currentLegend.fx, fy: measured?.fy ?? currentLegend.fy };
        setLegendDragPreview({
          fx: measured?.fx ?? currentLegend.fx,
          fy: measured?.fy ?? currentLegend.fy,
          width_frac: measured?.width_frac ?? currentLegend.width_frac,
          height_frac: measured?.height_frac ?? currentLegend.height_frac,
        });
        setDraggingLegend(true);
        event.currentTarget.setPointerCapture(event.pointerId);
        return;
      }
      if (drawTool === "area") {
        const snapped = nearestRulerPoint(event.clientX, event.clientY);
        if (!snapped) {
          setMessage("데이터 점 가까이에서 클릭하면 영역의 점으로 스냅합니다.");
          return;
        }
        const point: DrawPoint = {
          x: snapped.x,
          y: snapped.y,
          label: snapped.label,
          px: snapped.px,
          py: snapped.py,
        };
        if (drawingPoints.length >= 3) {
          const firstLocal = drawPointLocal(drawingPoints[0]);
          const snapLocal = drawPointLocal(point);
          if (firstLocal && snapLocal && Math.hypot(firstLocal.x - snapLocal.x, firstLocal.y - snapLocal.y) < 20) {
            finishDrawPolygon(drawingPoints);
            return;
          }
        }
        setDrawingPoints([...drawingPoints, point]);
        setMessage(`${snapped.label || "점"}에 스냅했습니다. 다음 점을 선택하세요.`);
        return;
      }
      if (drawTool !== "line") return;
      const snapped = nearestRulerPoint(event.clientX, event.clientY);
      if (!snapped) {
        setMessage("데이터 점 가까이에서 클릭하면 선의 점으로 스냅합니다.");
        return;
      }
      const point: DrawPoint = {
        x: snapped.x,
        y: snapped.y,
        label: snapped.label,
        px: snapped.px,
        py: snapped.py,
      };
      const nextPoints = [...drawingPoints, point];
      setDrawingPoints(nextPoints);
      setMessage(`${snapped.label || "점"}에 스냅했습니다. 다음 점을 선택하세요.`);
      if (event.detail >= 2) finishDrawLine(nextPoints);
      return;
    }
    if (tool === "label" && event.button === 0) {
      event.preventDefault();
      event.stopPropagation();
      const label = nearestPlotLabel(event.clientX, event.clientY);
      if (label) {
        setDraggingPlotLabel(label.vowel);
        setPlotLabelPreviewVowel(label.vowel);
        setHoveredPlotLabel(label.vowel);
        plotLabelDragStartRef.current = { x: event.clientX, y: event.clientY };
        plotLabelHasMovedRef.current = false;
        setPlotLabelPointer(null);
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

  const resetPlotLabel = (event: React.MouseEvent<HTMLDivElement>) => {
    if (tool !== "label") return;
    event.preventDefault();
    const label = nearestPlotLabel(event.clientX, event.clientY);
    if (!label) return;
    void renderInteractive({ labelOffsets: { [label.vowel]: [0, 0] } });
    setDraggingPlotLabel(null);
    plotLabelDragStartRef.current = null;
    plotLabelHasMovedRef.current = false;
    setPlotLabelPreviewVowel(null);
    setPlotLabelPointer(null);
    setMessage(`${label.vowel} 라벨을 기본 위치로 되돌렸습니다.`);
  };

  const handleRulerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (tool === "draw") {
      if (textDragRef.current) {
        const drag = textDragRef.current;
        const data = plotDataFromClient(event.clientX, event.clientY);
        if (data && textHasMovedRef.current) {
          persistDrawObjects(currentDrawObjects.map((object) => (
            object.type === "text" && object.id === drag.id
              ? { ...object, x: data.x + drag.offsetX, y: data.y + drag.offsetY }
              : object
          )));
          setMessage("텍스트 위치를 옮겼습니다.");
        }
        textDragRef.current = null;
        textHasMovedRef.current = false;
        setDraggingTextId(null);
        setTextDragPointer(null);
        if (textDragFrameRef.current !== null) {
          cancelAnimationFrame(textDragFrameRef.current);
          textDragFrameRef.current = null;
        }
        if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
        return;
      }
      if (drawTool === "legend" && draggingLegend) {
        const nextLegend = legendFromPointer(event.clientX, event.clientY);
        if (nextLegend) {
          setLegendDragPreview({
            fx: nextLegend.fx,
            fy: nextLegend.fy,
            width_frac: nextLegend.width_frac,
            height_frac: nextLegend.height_frac,
          });
          persistDrawObjects([...currentDrawObjects.filter((object) => object.type !== "legend"), nextLegend]);
        } else {
          setLegendDragPreview(null);
        }
        legendDragRef.current = null;
        setDraggingLegend(false);
        if (legendFrameRef.current !== null) {
          cancelAnimationFrame(legendFrameRef.current);
          legendFrameRef.current = null;
        }
        if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
      }
      return;
    }
    if (tool === "label" && draggingPlotLabel && rulerContext) {
      const label = rulerContext.labels.find((item) => item.vowel === draggingPlotLabel);
      const data = plotDataFromClient(event.clientX, event.clientY);
      if (label && data && plotLabelHasMovedRef.current) {
        const offsets = { [label.vowel]: [data.x - label.cx, data.y - label.cy] as [number, number] };
        void renderInteractive({ labelOffsets: offsets });
        setMessage(`${label.vowel} 라벨 위치를 저장했습니다.`);
      }
      setDraggingPlotLabel(null);
      // Keep the optimistic preview in place until preview_ready replaces the image.
      setPlotLabelPreviewVowel(plotLabelHasMovedRef.current ? label?.vowel ?? null : null);
      plotLabelDragStartRef.current = null;
      plotLabelHasMovedRef.current = false;
    }
    if (plotLabelFrameRef.current !== null) {
      cancelAnimationFrame(plotLabelFrameRef.current);
      plotLabelFrameRef.current = null;
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

  const rulerTooltip = (point: RulerPoint) => formatRulerPointTooltip(point, plotUnits);

  const rulerDistanceLabelWithSettings = (first: RulerPoint, second: RulerPoint) =>
    formatRulerDistance(first, second, plotUnits, {
      preference: rulerDisplayMode,
      geometry: rulerGeometryMode,
    });

  const rulerTriangleLabels = (first: RulerPoint, second: RulerPoint) =>
    formatRulerTriangleLegs(first, second, plotUnits, rulerDisplayMode);

  useEffect(() => {
    if (!plotUnits.rulerUnitChoiceEnabled) return;
    setRulerDisplayMode(plotUnits.defaultRulerPreference);
  }, [plotUnits.defaultRulerPreference, plotUnits.rulerUnitChoiceEnabled]);

  useEffect(() => {
    if (tool !== "ruler") {
      setRulerStart(null);
      setRulerHover(null);
      setRulerPointer(null);
      setRulerMeasurements([]);
    }
    if (tool !== "label") {
      setDraggingPlotLabel(null);
      setHoveredPlotLabel(null);
      setPlotLabelPointer(null);
      plotLabelDragStartRef.current = null;
      plotLabelHasMovedRef.current = false;
    }
  }, [tool]);

  useEffect(() => {
    setRulerMeasurements((previous) => previous.map((measurement) => ({
      ...measurement,
      distance: rulerDistanceLabelWithSettings(measurement.p1, measurement.p2),
    })));
  }, [plotUnits, rulerDisplayMode, rulerGeometryMode]);

  /** paper-local. 스냅 점은 px/py(transData) 우선 — 선형 drawPointClient는 마커와 어긋남. */
  const drawPointLocal = (point: DrawPoint) => {
    const paper = plotPaperRef.current?.getBoundingClientRect();
    if (!paper) return null;
    if (Number.isFinite(point.px) && Number.isFinite(point.py) && rulerContext) {
      const geometry = rulerImageGeometry();
      if (!geometry) return null;
      const imgH = rulerContext.image_height || geometry.srcH;
      return {
        x: geometry.left - paper.left + (point.px as number) * geometry.scale,
        y: geometry.top - paper.top + (imgH - (point.py as number)) * geometry.scale,
      };
    }
    const screen = drawPointClient(point);
    return screen ? { x: screen.x - paper.left, y: screen.y - paper.top } : null;
  };

  const fileCounter = useMemo(
    () => `${sources.length ? currentSourcePosition + 1 : 0} / ${sources.length}`,
    [currentSourcePosition, sources.length],
  );
  const effective = <K extends keyof DesignSettings,>(key: K): DesignSettings[K] => (selectedOverride[key] ?? design[key]) as DesignSettings[K];

  return (
    <main className={`interactive-plot-workspace ${leftOpen ? "" : "left-is-collapsed"} ${rightOpen ? "" : "right-is-collapsed"}`}>
      <header className="interactive-plot-header">
        <div className="plot-title-block"><span>단일 분석 · 대화형 플롯</span><h1 title={currentSource?.name}>{currentSource?.name ?? "데이터를 불러와 주세요"}</h1></div>
        <div className="plot-header-meta"><span className={`engine-state ${engineConnected ? "" : "is-offline"}`}><i /> 분석 엔진 {engineConnected ? "연결됨" : "연결 확인 중"}</span><span className="plot-notation">{xAxis} × {yAxis} · {fileCounter}</span><button type="button" className="shortcut-help-launch" onClick={() => setShortcutHelpOpen(true)} aria-label="단축키 도움말" title="단축키 (?)"><CircleHelp size={15} /></button><button className="legacy-launch" onClick={() => void openLegacyPlot()} disabled={busy || !sources.length}>PySide 고급 편집 <ArrowUpRight size={14} /></button></div>
      </header>

      <aside className="plot-control-rail">
        <section className="file-navigator">
          <div className="navigator-topline"><div><span className="section-eyebrow">파일 탐색</span><strong>{fileCounter}</strong></div><button className="rail-collapse" aria-label="왼쪽 패널 접기" onClick={() => setLeftOpen(false)}><PanelLeftClose size={16} /></button></div>
          <div className="file-select-row"><button aria-label="이전 파일" onClick={() => navigateByPosition(currentSourcePosition - 1)} disabled={!canNavigate || currentSourcePosition === 0}><ChevronLeft size={17} /></button><FileSelectMenu sources={sources} currentIndex={currentIndex} onNavigate={(index) => void navigateTo(index)} disabled={!sources.length} /><button aria-label="다음 파일" onClick={() => navigateByPosition(currentSourcePosition + 1)} disabled={!canNavigate || currentSourcePosition >= sources.length - 1}><ChevronRight size={17} /></button></div>
        </section>

        <div className="control-tabs"><button className={leftPanel === "analysis" ? "is-active" : ""} onClick={() => setLeftPanel("analysis")}><SlidersHorizontal size={15} /> 분석 도구</button><button className={leftPanel === "global-design" ? "is-active" : ""} onClick={() => setLeftPanel("global-design")}><Palette size={15} /> 광역 디자인</button></div>

        <div className="control-scroll">
          {leftPanel === "analysis" ? (
            <>
              <section className="control-section range-section">
                <div className="section-heading"><div><span>01</span><strong>좌표축 범위</strong></div><small>{rangeUnitLabel || "정규화"}</small></div>
                <div className="range-matrix">
                  <div className="range-matrix-head"><span>축</span><span>최솟값</span><span /><span>최댓값</span></div>
                  <div className="range-matrix-row"><strong>{yAxis} <small>세로</small></strong><input value={ranges.y_min} readOnly={rangesReadOnly} onChange={(event) => setRanges({ ...ranges, y_min: event.target.value })} /><i>–</i><input value={ranges.y_max} readOnly={rangesReadOnly} onChange={(event) => setRanges({ ...ranges, y_max: event.target.value })} /></div>
                  <div className="range-matrix-row"><strong>{xAxis} <small>가로</small></strong><input value={ranges.x_min} readOnly={rangesReadOnly} onChange={(event) => setRanges({ ...ranges, x_min: event.target.value })} /><i>–</i><input value={ranges.x_max} readOnly={rangesReadOnly} onChange={(event) => setRanges({ ...ranges, x_max: event.target.value })} /></div>
                </div>
                <div className="ellipse-quick-row"><label><span>신뢰 타원 범위</span><span className="sigma-control"><select value={sigma} onChange={(event) => { const next = event.target.value; setSigma(next); void renderInteractive({ sigma: next }); }}><option value="1.0">1.0</option><option value="1.5">1.5</option><option value="2.0">2.0</option><option value="2.5">2.5</option><option value="3.0">3.0</option></select><b>σ</b></span></label><ToggleSwitch label="타원 표시" checked={showEllipse} onChange={() => { const next = !showEllipse; setShowEllipse(next); void renderInteractive({ showEllipse: next }); }} /></div>
                <div className="paired-actions"><button onClick={resetPlot}><RefreshCcw size={14} /> 초기화</button><button className="primary" onClick={() => void renderInteractive()} disabled={busy}><Sparkles size={14} /> 범위 적용</button></div>
              </section>

              <section className="control-section"><div className="section-heading"><div><span>02</span><strong>분석 도구</strong></div></div><div className="tool-grid"><button onClick={() => setVowelAnalysisOpen(true)} disabled={!sources.length}><ScanSearch size={17} /><span><strong>모음 상세 분석</strong><small>통계와 분포 보기</small></span></button><button onClick={() => void openComparePlot()} disabled={sources.filter((source) => !source.is_combined).length < 2}><Layers3 size={17} /><span><strong>다중 플롯 모드</strong><small>파일 비교 구성</small></span></button><button className={tool === "ruler" ? "is-active" : ""} onClick={() => setTool(tool === "ruler" ? "select" : "ruler")}><Ruler size={17} /><span><strong>눈금자</strong><small>R · 거리 측정</small></span></button><button className={tool === "draw" ? "is-active" : ""} onClick={() => enterDrawMode(null)}><PenLine size={17} /><span><strong>그리기</strong><small>P · 주석 도구</small></span></button></div></section>

              <section className="control-section export-section"><div className="section-heading"><div><span>03</span><strong>내보내기</strong></div></div><div className={`format-buttons ${hasCombined ? "has-txt" : ""}`}><button onClick={() => void exportInteractive("jpg")} disabled={!previewUrl}>JPG</button><button onClick={() => void exportInteractive("png")} disabled={!previewUrl}>PNG</button><button onClick={() => void exportInteractive("svg")} disabled={!sources.length}>SVG</button>{hasCombined ? <button onClick={() => void exportCombinedTxt()} disabled={busy}>TXT</button> : null}</div><button className="wide-action" onClick={() => void saveProject()} disabled={busy || !sources.length}><Save size={15} /> 프로젝트 저장</button><button className="wide-action primary" onClick={() => setBatchExportOpen(true)} disabled={busy || !sources.length}><Download size={15} /> 일괄 저장</button></section>
            </>
          ) : (
            <>
              <fieldset className="global-design-form">
              <section className="control-section">
                <div className="section-heading"><div><span>01</span><strong>모음 라벨</strong></div><small>전체 레이어</small></div>
                <div className="palette-picker-row">
                  <PalettePicker label="라벨 색상" value={design.lbl_color} onChange={(lbl_color) => lbl_color && updateDesign({ lbl_color })} />
                </div>
                <div className="text-style-block">
                  <span className="control-label">텍스트 설정</span>
                  <div className="text-style-row">
                    <div className="font-controls font-family-row">
                      <select value={design.font_family} onChange={(event) => { const font_family = event.target.value; updateDesign({ font_family, font_style: fontFamilyStyle(font_family), font_weight: normalizedFontWeight(font_family, design.font_weight) }); }} aria-label="글꼴">
                        {FONT_FAMILIES.map((family) => <option key={family}>{family}</option>)}
                      </select>
                      <select value={normalizedFontWeight(design.font_family, design.font_weight)} onChange={(event) => updateDesign({ font_weight: event.target.value as DesignSettings["font_weight"], lbl_bold: event.target.value === "bold" })} disabled={(FONT_WEIGHTS[design.font_family] ?? []).length <= 1} aria-label="Weight">
                        {(FONT_WEIGHTS[design.font_family] ?? ["regular"]).map((weight) => <option key={weight} value={weight}>{FONT_WEIGHT_LABELS[weight]}</option>)}
                      </select>
                    </div>
                    <div className="font-size-row">
                      <label className="font-size-control"><span className="font-control-caption">크기 <b>{design.lbl_size}pt</b></span><input type="range" min="12" max="28" step="1" value={design.lbl_size} onChange={(event) => updateDesign({ lbl_size: Number(event.target.value) })} /></label>
                      <div className="font-style-buttons"><button type="button" className={design.font_weight === "bold" ? "is-active" : ""} onClick={() => updateDesign({ font_weight: design.font_weight === "bold" ? "regular" : "bold", lbl_bold: design.font_weight !== "bold" })} aria-label="볼드"><Bold size={15} /></button><button type="button" className={design.lbl_italic ? "is-active" : ""} onClick={() => updateDesign({ lbl_italic: !design.lbl_italic })} aria-label="기울임"><Italic size={15} /></button></div>
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

              <section className="control-section"><div className="section-heading"><div><span>03</span><strong>신뢰 타원</strong></div></div><div className="segmented-row"><button type="button" className={design.ell_thick === 0.5 ? "is-active" : ""} onClick={() => updateDesign({ ell_thick: 0.5 })}>얇게</button><button type="button" className={design.ell_thick === 1 ? "is-active" : ""} onClick={() => updateDesign({ ell_thick: 1 })}>보통</button><button type="button" className={design.ell_thick === 2 ? "is-active" : ""} onClick={() => updateDesign({ ell_thick: 2 })}>굵게</button></div><div className="segmented-row"><button type="button" className={design.ell_style === "-" ? "is-active" : ""} onClick={() => updateDesign({ ell_style: "-" })}>실선</button><button type="button" className={design.ell_style === "---" ? "is-active" : ""} onClick={() => updateDesign({ ell_style: "---" })}>긴 점선</button><button type="button" className={design.ell_style === "--" || design.ell_style === ":" ? "is-active" : ""} onClick={() => updateDesign({ ell_style: "--" })}>짧은 점선</button></div><div className="palette-picker-row"><PalettePicker label="선 색상" value={design.ell_color} onChange={(ell_color) => updateDesign({ ell_color })} allowTransparent /><PalettePicker label="채우기" value={design.ell_fill_color} onChange={(ell_fill_color) => updateDesign({ ell_fill_color })} allowTransparent /></div><label className="opacity-control"><span>채우기 투명도 <b>{Math.round(design.ell_fill_opacity * 100)}%</b></span><input type="range" min="0" max="60" value={design.ell_fill_opacity * 100} onChange={(event) => updateDesign({ ell_fill_opacity: Number(event.target.value) / 100 })} /></label></section>

              <section className="control-section"><div className="section-heading"><div><span>04</span><strong>플롯 배경과 축</strong></div></div><div className="switch-stack"><ToggleSwitch label="격자 표시" checked={design.show_grid} onChange={() => updateDesign({ show_grid: !design.show_grid })} /><ToggleSwitch label="테두리 축" checked={design.box_spines} onChange={() => updateDesign({ box_spines: !design.box_spines })} /><ToggleSwitch label="축 단위 표시" checked={design.show_axis_units} onChange={() => updateDesign({ show_axis_units: !design.show_axis_units })} /></div><label className="opacity-control"><span>눈금 숫자 크기 <b>{Number(design.tick_label_size ?? 13)}pt</b></span><input type="range" min="10" max="18" step="1" value={Number(design.tick_label_size ?? 13)} onChange={(event) => updateDesign({ tick_label_size: Number(event.target.value) })} /></label>{design.show_grid ? <label className="opacity-control"><span>격자 투명도 <b>{Math.round(design.grid_opacity * 100)}%</b></span><input type="range" min="5" max="80" value={design.grid_opacity * 100} onChange={(event) => updateDesign({ grid_opacity: Number(event.target.value) / 100 })} /></label> : null}</section>

              <details className="advanced-options"><summary>고급 옵션 <ChevronDown size={14} /></summary><div className="advanced-body"><div className="switch-stack"><ToggleSwitch label="라벨 슬래시 감싸기" checked={design.label_slash_wrap} onChange={() => updateDesign({ label_slash_wrap: !design.label_slash_wrap })} /><ToggleSwitch label="보조 눈금" checked={design.show_minor_ticks} onChange={() => updateDesign({ show_minor_ticks: !design.show_minor_ticks })} /><ToggleSwitch label="축 위치 반전" checked={design.axis_position_swap} onChange={() => updateDesign({ axis_position_swap: !design.axis_position_swap })} /><ToggleSwitch label="세로축 라벨 회전" checked={design.y_label_rotation} onChange={() => updateDesign({ y_label_rotation: !design.y_label_rotation })} /></div></div></details>
              </fieldset>
              <div className="global-design-actions"><button className="wide-action" onClick={resetPlot}><RefreshCcw size={14} /> 광역 디자인 초기화</button><button type="button" className={`global-design-lock ${globalDesignLocked ? "is-locked" : ""}`} onClick={() => setGlobalDesignLocked((locked) => !locked)} aria-pressed={globalDesignLocked} title={globalDesignLocked ? "설정 유지 ON" : "설정 유지 OFF"}>{globalDesignLocked ? <Lock size={14} /> : <Unlock size={14} />}<span>설정 유지</span></button></div>
            </>
          )}
        </div>
      </aside>

      <section className={`interactive-plot-stage tool-${tool}${tool === "draw" ? ` draw-tool-${drawTool ?? "none"}` : ""}`}>
        <div className="plot-toolbar"><div className="toolbar-leading">{!leftOpen ? <button className="sidebar-reopen" onClick={() => setLeftOpen(true)}><PanelLeftOpen size={16} /> 도구</button> : null}<div className="toolbar-group"><button className={tool === "select" ? "is-active" : ""} onClick={() => setTool("select")}><MousePointer2 size={16} /> 선택</button><div className="ruler-tool-cluster"><button className={tool === "ruler" ? "is-active" : ""} onClick={() => setTool("ruler")}><Ruler size={16} /> 눈금자</button><button type="button" className={`tool-settings-button ${rulerSettingsOpen ? "is-active" : ""}`} onClick={() => setRulerSettingsOpen((previous) => !previous)} aria-label="눈금자 설정" title="눈금자 설정"><SlidersHorizontal size={14} /></button>{rulerSettingsOpen ? <div className="ruler-settings-popover"><div className="ruler-settings-header"><strong>눈금자 설정</strong><span>측정 방식</span></div><div className="ruler-mode-choices"><button type="button" className={`ruler-mode-choice ${rulerGeometryMode === "direct" ? "is-active" : ""}`} onClick={() => setRulerGeometryMode("direct")}><svg viewBox="0 0 44 22" aria-hidden><line x1="5" y1="17" x2="39" y2="5" /><circle cx="5" cy="17" r="2" /><circle cx="39" cy="5" r="2" /></svg><span>직선</span></button><button type="button" className={`ruler-mode-choice ${rulerGeometryMode === "right-triangle" ? "is-active" : ""}`} onClick={() => setRulerGeometryMode("right-triangle")}><svg viewBox="0 0 44 22" aria-hidden><path d="M5 17H39V5" /><line className="hypotenuse" x1="5" y1="17" x2="39" y2="5" /><path className="right-angle" d="M34 17v-5h5" /></svg><span>Δx · Δy</span></button></div><div className="ruler-unit-row"><span>표시 단위</span>{plotUnits.rulerUnitChoiceEnabled ? <div className="ruler-unit-toggles"><button type="button" className={`ruler-unit-toggle ${rulerDisplayMode === "hz" ? "is-on" : ""}`} aria-pressed={rulerDisplayMode === "hz"} onClick={() => setRulerDisplayMode("hz")}>Hz</button><button type="button" className={`ruler-unit-toggle ${rulerDisplayMode === "bark" ? "is-on" : ""}`} aria-pressed={rulerDisplayMode === "bark"} onClick={() => setRulerDisplayMode("bark")}>Bark</button></div> : <strong className="ruler-unit-locked">{plotUnits.normalization ?? "정규화 좌표"}</strong>}</div></div> : null}</div><button className={tool === "label" ? "is-active" : ""} onClick={() => { setTool("label"); setMessage("라벨 이동 모드 · 라벨을 드래그하세요."); }}><MousePointer2 size={16} /> 라벨 이동</button><button className={tool === "draw" ? "is-active" : ""} onClick={() => enterDrawMode(null)}><PenLine size={16} /> 그리기</button></div></div><div className="toolbar-context"><span>{analysis?.normalization ?? "정규화 없음"}</span><span>{analysis?.origin === "top_right" ? "Praat 좌표" : "수학 좌표"}</span>{!rightOpen ? <button className="sidebar-reopen" onClick={() => setRightOpen(true)}>레이어 <PanelRightOpen size={16} /></button> : null}</div></div>
        <div className="plot-canvas-shell"><div className="plot-paper" ref={plotPaperRef}>{previewUrl ? <><img ref={plotImageRef} src={previewUrl} alt={`${currentSource?.name ?? "현재 파일"} 포먼트 플롯`} draggable={false} onLoad={() => { if (referencePointerRef.current) setReferencePreview({ ...referencePointerRef.current }); }} /><div className="ruler-overlay" onPointerMove={handleRulerMove} onPointerDown={handleRulerDown} onPointerUp={handleRulerUp} onPointerCancel={handleRulerUp} onDoubleClick={(event) => {
                  if (tool === "draw" && drawTool === "line") {
                    event.preventDefault();
                    finishDrawLine(drawingPoints);
                  } else if (tool === "draw" && drawTool === "text") {
                    event.preventDefault();
                    openTextInputAt(event.clientX, event.clientY);
                  } else if (tool !== "draw") {
                    resetPlotLabel(event);
                  }
                }} onContextMenu={tool === "label" ? resetPlotLabel : handleRulerContextMenu}>
          <svg className="draw-line-layer" aria-hidden>
            {tool === "draw" && drawTool === "line" ? (() => {
              const paper = plotPaperRef.current?.getBoundingClientRect();
              const locals = drawingPoints
                .map((point) => drawPointLocal(point))
                .filter((point): point is { x: number; y: number } => Boolean(point));
              // 스냅: transData(px/py). 비스냅: 커서 paper-local (선형 axes_bbox면 가이드가 비뚤어짐)
              const hoverLocal = drawHover
                ? (drawHover.snapped
                  ? drawPointLocal(drawHover.point)
                  : (paper
                    ? { x: drawHover.clientX - paper.left, y: drawHover.clientY - paper.top }
                    : null))
                : null;
              const stroke = drawColor ?? DRAW_LINE_DEFAULT_COLOR;
              const last = locals[locals.length - 1];
              return (
                <>
                  {/* PySide _line_artist: 확정 점 ≥2 → 실선 alpha 0.4 */}
                  {locals.length >= 2 ? (
                    <polyline
                      className="draw-line-live"
                      points={locals.map((point) => `${point.x},${point.y}`).join(" ")}
                      fill="none"
                      stroke={stroke}
                      strokeWidth={Math.max(0.75, clampDrawLineWidth(drawWidth))}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      vectorEffect="non-scaling-stroke"
                    />
                  ) : null}
                  {/* PySide 가이드: 점 ≥1 + hover → 마지막점→호버, gray dotted */}
                  {last && hoverLocal ? (
                    <line
                      className="draw-line-guide"
                      x1={last.x}
                      y1={last.y}
                      x2={hoverLocal.x}
                      y2={hoverLocal.y}
                      stroke="#888888"
                      strokeWidth={1.25}
                      strokeDasharray="4 4"
                      strokeLinecap="round"
                      vectorEffect="non-scaling-stroke"
                    />
                  ) : null}
                  {locals.map((local, index) => (
                    <circle
                      key={`draw-point-${index}`}
                      className="draw-line-point"
                      cx={local.x}
                      cy={local.y}
                      r={index === locals.length - 1 ? 5 : 3.5}
                      fill="white"
                      stroke={stroke}
                      strokeWidth="2"
                    />
                  ))}
                </>
              );
            })() : null}
            {tool === "draw" && drawTool === "area" ? (() => {
              const paper = plotPaperRef.current?.getBoundingClientRect();
              const locals = drawingPoints
                .map((point) => drawPointLocal(point))
                .filter((point): point is { x: number; y: number } => Boolean(point));
              const hoverLocal = drawHover
                ? (drawHover.snapped
                  ? drawPointLocal(drawHover.point)
                  : (paper
                    ? { x: drawHover.clientX - paper.left, y: drawHover.clientY - paper.top }
                    : null))
                : null;
              const last = locals[locals.length - 1];
              const stroke = drawPolyBorderColor;
              const fill = drawPolyFillColor
                ? (() => {
                  const hex = drawPolyFillColor.replace("#", "");
                  if (hex.length !== 6) return "rgba(51, 102, 204, 0.15)";
                  const r = Number.parseInt(hex.slice(0, 2), 16);
                  const g = Number.parseInt(hex.slice(2, 4), 16);
                  const b = Number.parseInt(hex.slice(4, 6), 16);
                  return `rgba(${r}, ${g}, ${b}, ${drawPolyFillOpacity})`;
                })()
                : "transparent";
              return (
                <>
                  {locals.length >= 3 ? (
                    <polygon
                      className="draw-area-fill"
                      points={locals.map((point) => `${point.x},${point.y}`).join(" ")}
                      fill={fill}
                      stroke="none"
                    />
                  ) : null}
                  {locals.length >= 2 ? (
                    <polyline
                      className="draw-line-live"
                      points={locals.map((point) => `${point.x},${point.y}`).join(" ")}
                      fill="none"
                      stroke={stroke}
                      strokeWidth={1.5}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      vectorEffect="non-scaling-stroke"
                    />
                  ) : null}
                  {last && hoverLocal ? (
                    <line
                      className="draw-line-guide"
                      x1={last.x}
                      y1={last.y}
                      x2={hoverLocal.x}
                      y2={hoverLocal.y}
                      stroke="#888888"
                      strokeWidth={1.25}
                      strokeDasharray="4 4"
                      strokeLinecap="round"
                      vectorEffect="non-scaling-stroke"
                    />
                  ) : null}
                  {locals.map((local, index) => (
                    <circle
                      key={`area-point-${index}`}
                      className="draw-line-point"
                      cx={local.x}
                      cy={local.y}
                      r={index === 0 ? 5.5 : index === locals.length - 1 ? 5 : 3.5}
                      fill="white"
                      stroke={stroke}
                      strokeWidth="2"
                    />
                  ))}
                </>
              );
            })() : null}
          </svg>
          {tool === "draw" && (drawTool === "line" || drawTool === "area") && drawHover?.snapped && drawHover.rulerPoint ? (() => {
            const screen = rulerPointClient(drawHover.rulerPoint);
            const paper = plotPaperRef.current?.getBoundingClientRect();
            if (!screen || !paper) return null;
            return (
              <>
                <span
                  className={`ruler-snap-marker ${drawHover.rulerPoint.type === "mean" ? "is-mean" : "is-raw"}`}
                  style={{ left: screen.x - paper.left, top: screen.y - paper.top, borderColor: drawHover.rulerPoint.color }}
                />
                <span className="ruler-tooltip" style={{ left: screen.x - paper.left + 12, top: screen.y - paper.top - 30 }}>
                  {rulerTooltip(drawHover.rulerPoint)}
                </span>
              </>
            );
          })() : null}
          {tool === "draw" && drawTool === "reference" && referencePreview ? (
            <div
              className={`reference-preview ${referencePreview.mode === "horizontal" ? "is-horizontal" : "is-vertical"}${referencePreview.snapped ? " is-snapped" : ""}`}
              aria-hidden
            >
              <div
                className="reference-preview-line"
                style={
                  referencePreview.mode === "horizontal"
                    ? {
                      left: Math.min(referencePreview.x1, referencePreview.x2),
                      top: referencePreview.y1,
                      width: Math.max(1, Math.abs(referencePreview.x2 - referencePreview.x1)),
                      height: 2,
                      transform: "translateY(-50%)",
                    }
                    : {
                      left: referencePreview.x1,
                      top: Math.min(referencePreview.y1, referencePreview.y2),
                      width: 2,
                      height: Math.max(1, Math.abs(referencePreview.y2 - referencePreview.y1)),
                      transform: "translateX(-50%)",
                    }
                }
              />
              {referencePreview.label.trim() ? (
                <div
                  className="reference-preview-label"
                  style={{
                    left: referencePreview.mode === "horizontal" ? Math.min(referencePreview.x1, referencePreview.x2) + 4 : referencePreview.x1,
                    top: referencePreview.mode === "horizontal" ? referencePreview.y1 : Math.min(referencePreview.y1, referencePreview.y2),
                    fontFamily: axisPreviewFontFamily(design),
                    fontSize: Number(design.tick_label_size ?? 12),
                    fontWeight: 400,
                  }}
                >
                  {referencePreview.label.trim()}
                </div>
              ) : null}
            </div>
          ) : null}
          {tool === "draw" && drawTool === "legend" && currentLegend?.visible ? (() => {
            const liveLegend = legendDragPreview ? { ...currentLegend, ...legendDragPreview } : currentLegend;
            const rect = legendClientRect(liveLegend, !legendDragPreview);
            const defaultRect = draggingLegend || legendDragPreview ? defaultLegendClientRect(liveLegend) : null;
            const paper = plotPaperRef.current?.getBoundingClientRect();
            if (!rect || !paper) return null;
            const style = { left: rect.left - paper.left, top: rect.top - paper.top, width: rect.width, height: rect.height };
            return (
              <>
                <div className={`legend-live-hit ${draggingLegend || legendDragPreview ? "is-dragging" : ""}`} style={style} title="드래그하여 범례 이동" />
                {legendDragPreview ? <div className="legend-drag-preview" style={style} aria-hidden /> : null}
                {defaultRect ? <div className="legend-default-guide" style={{ left: defaultRect.left - paper.left, top: defaultRect.top - paper.top, width: defaultRect.width, height: defaultRect.height }} /> : null}
              </>
            );
          })() : null}
          {tool === "draw" ? currentDrawObjects.filter((object): object is DrawTextObject => object.type === "text" && object.visible).map((object) => {
            const paper = plotPaperRef.current?.getBoundingClientRect();
            const screen = drawTextAnchorClient(object);
            const box = drawTextBoxClient(object);
            if (!paper || !screen) return null;
            const isDragging = draggingTextId === object.id && textDragPointer !== null;
            const isHovered = hoveredDrawTextId === object.id;
            const anchorOffsetX = box ? box.left - screen.x : 0;
            const anchorOffsetY = box ? box.top - screen.y : 0;
            const left = isDragging ? textDragPointer.x + anchorOffsetX : box ? box.left - paper.left : screen.x - paper.left;
            const top = isDragging ? textDragPointer.y + anchorOffsetY : box ? box.top - paper.top : screen.y - paper.top;
            const weight = object.font_weight || (object.font_bold ? "bold" : "regular");
            const previewStyle = {
              color: object.text_color || DRAW_TEXT_DEFAULT_COLOR,
              fontSize: `${clampDrawTextFontSize(object.font_size)}pt`,
              fontWeight: weight === "bold" || weight === "semibold" ? 700 : weight === "medium" ? 500 : 400,
              fontStyle: object.font_italic ? "italic" as const : "normal" as const,
              fontFamily: axisPreviewFontFamily({ font_style: fontFamilyStyle(object.font_family || DRAW_TEXT_DEFAULT_FAMILY), font_family: object.font_family || DRAW_TEXT_DEFAULT_FAMILY }),
              lineHeight: clampDrawTextLineSpacing(object.line_spacing ?? DRAW_TEXT_DEFAULT_LINE_SPACING),
            };
            const boxStyle = box ? { width: box.width, height: box.height } : {};
            return (
              <span
                className={`draw-text-hit-target ${isDragging ? "is-dragging" : ""} ${isHovered ? "is-hovered" : ""}`}
                key={object.id}
                style={{ left, top, ...boxStyle }}
                title="드래그하여 텍스트 이동"
              >
                {/* 히트용 투명 텍스트 — opacity는 CSS만 (인라인 opacity 금지: 프리뷰와 겹침) */}
                <span className="draw-text-hit-text" style={previewStyle} aria-hidden>
                  {object.text.split("\n").map((line, index) => (
                    <span key={`${object.id}-hit-${index}`}>{line || "\u00a0"}</span>
                  ))}
                </span>
                {isDragging ? (
                  <span
                    className="draw-text-drag-preview"
                    style={{ ...previewStyle, opacity: object.semi ? 0.35 : 1 }}
                    aria-hidden
                  >
                    {object.text.split("\n").map((line, index) => (
                      <span key={`${object.id}-prev-${index}`}>{line || "\u00a0"}</span>
                    ))}
                  </span>
                ) : null}
              </span>
            );
          }) : null}
          {tool === "label" && rulerContext ? rulerContext.labels.map((label) => { const screen = plotLabelClient(label); const box = plotLabelBoxClient(label); const paper = plotPaperRef.current?.getBoundingClientRect(); if (!screen || !paper) return null; const isDragging = draggingPlotLabel === label.vowel && plotLabelPointer !== null; const isPreviewing = plotLabelPreviewVowel === label.vowel && plotLabelPointer !== null; const isHovered = hoveredPlotLabel === label.vowel; const anchorOffsetX = box ? box.left - screen.x : 0; const anchorOffsetY = box ? box.top - screen.y : 0; const left = isPreviewing ? plotLabelPointer.x + anchorOffsetX : box ? box.left - paper.left : screen.x - paper.left; const top = isPreviewing ? plotLabelPointer.y + anchorOffsetY : box ? box.top - paper.top : screen.y - paper.top; const labelDesign = { ...design, ...(layerOverrides[label.vowel] ?? {}) }; const rawWeight = String(labelDesign.font_weight ?? ""); const rawBold = String(labelDesign.lbl_bold); const isBold = rawWeight === "bold" || (!rawWeight && (rawBold === "true" || rawBold === "bold" || rawBold === "medium")); const previewStyle = { color: String(label.lbl_color ?? labelDesign.lbl_color ?? "#ff0000"), fontSize: `${Number(label.fontsize ?? labelDesign.lbl_size ?? 18)}pt`, fontWeight: isBold ? 700 : 400, fontStyle: label.lbl_italic ?? labelDesign.lbl_italic ? "italic" as const : "normal" as const, fontFamily: labelDesign.font_style === "sans" ? "var(--gf-font-sans)" : "var(--gf-font-serif)" }; const boxStyle = box ? { width: box.width, height: box.height } : {}; return <span className={`plot-label-hit-target ${isDragging ? "is-dragging" : ""} ${isHovered ? "is-hovered" : ""}`} key={`label-${label.vowel}`} style={{ left, top, ...boxStyle }} title={`${label.vowel} 라벨 이동`}><span className="plot-label-hit-text" style={previewStyle}>{label.display_vowel ?? label.vowel}</span>{isPreviewing ? <span className="plot-label-drag-preview" style={previewStyle}>{label.display_vowel ?? label.vowel}</span> : null}</span>; }) : null}
         {tool === "ruler" ? rulerMeasurements.map((measurement, index) => { const a = rulerPointClient(measurement.p1); const b = rulerPointClient(measurement.p2); const paper = plotPaperRef.current?.getBoundingClientRect(); if (!a || !b || !paper) return null; const x1 = a.x - paper.left; const y1 = a.y - paper.top; const x2 = b.x - paper.left; const y2 = b.y - paper.top; const triangleLabels = rulerGeometryMode === "right-triangle" ? rulerTriangleLabels(measurement.p1, measurement.p2) : null; const dx = x2 - x1; const dy = y2 - y1; const length = Math.max(1, Math.hypot(dx, dy)); const hypotenuseAngle = Math.atan2(dy, dx) * 180 / Math.PI; const readableAngle = hypotenuseAngle > 90 || hypotenuseAngle < -90 ? hypotenuseAngle + 180 : hypotenuseAngle; const hypotenuseOffset = 18; const hypotenuseLabelX = (x1 + x2) / 2 - (dy / length) * hypotenuseOffset; const hypotenuseLabelY = (y1 + y2) / 2 + (dx / length) * hypotenuseOffset; return <div className="ruler-measurement" key={`${measurement.p1.x}-${measurement.p2.x}-${index}`}><svg className="ruler-line-layer" aria-hidden>{rulerGeometryMode === "right-triangle" ? <><polyline points={`${x1},${y1} ${x2},${y1} ${x2},${y2}`} /><line x1={x1} y1={y1} x2={x2} y2={y2} /></> : <line x1={x1} y1={y1} x2={x2} y2={y2} />}</svg><span className="ruler-point ruler-point-start" style={{ left: x1, top: y1, borderColor: measurement.p1.color }} /><span className="ruler-point ruler-point-end" style={{ left: x2, top: y2, borderColor: measurement.p2.color }} />{triangleLabels ? <><span className="ruler-side-label ruler-side-label-horizontal" style={{ left: (x1 + x2) / 2, top: y1 + 6 }}>{triangleLabels.horizontal}</span><span className="ruler-side-label ruler-side-label-vertical" style={{ left: x2 + 6, top: (y1 + y2) / 2 }}>{triangleLabels.vertical}</span><span className="ruler-side-label ruler-side-label-hypotenuse" style={{ left: hypotenuseLabelX, top: hypotenuseLabelY, transform: `translate(-50%, -50%) rotate(${readableAngle}deg)` }}>{triangleLabels.hypotenuse}</span></> : <button type="button" tabIndex={-1} aria-label={`거리 ${measurement.distance}`} className="ruler-label" style={{ left: measurement.labelX, top: measurement.labelY }} onPointerDown={(event) => { event.stopPropagation(); setDraggingRulerLabel(index); event.currentTarget.setPointerCapture(event.pointerId); }}>{measurement.distance}</button>}</div>; }) : null}
          {tool === "ruler" && rulerStart ? (() => { const screen = rulerPointClient(rulerStart); const paper = plotPaperRef.current?.getBoundingClientRect(); return screen && paper ? <span className={`ruler-snap-marker ${rulerStart.type === "mean" ? "is-mean" : "is-raw"}`} style={{ left: screen.x - paper.left, top: screen.y - paper.top, borderColor: rulerStart.color }} /> : null; })() : null}
          {tool === "ruler" && rulerStart && rulerPointer ? <svg className="ruler-guide-layer" aria-hidden><line x1={rulerPointClient(rulerStart) ? (rulerPointClient(rulerStart)!.x - (plotPaperRef.current?.getBoundingClientRect().left ?? 0)) : 0} y1={rulerPointClient(rulerStart) ? (rulerPointClient(rulerStart)!.y - (plotPaperRef.current?.getBoundingClientRect().top ?? 0)) : 0} x2={rulerPointer.x} y2={rulerPointer.y} /></svg> : null}
          {tool === "ruler" && rulerHover ? (() => { const screen = rulerPointClient(rulerHover); const paper = plotPaperRef.current?.getBoundingClientRect(); return screen && paper ? <><span className={`ruler-snap-marker ${rulerHover.type === "mean" ? "is-mean" : "is-raw"}`} style={{ left: screen.x - paper.left, top: screen.y - paper.top, borderColor: rulerHover.color }} /><span className="ruler-tooltip" style={{ left: screen.x - paper.left + 12, top: screen.y - paper.top - 30 }}>{rulerTooltip(rulerHover)}</span></> : null; })() : null}
        </div></> : <div className="plot-placeholder">{previewLoading ? <><Loader2 size={30} className="is-spinning" aria-hidden /><strong>플롯을 준비하는 중</strong><span>분석 엔진에서 미리보기를 그리는 동안 잠시만 기다려 주세요.</span></> : <><Layers3 size={30} /><strong>표시할 플롯이 없습니다</strong><span>메인 창에서 데이터 파일을 불러와 주세요.</span></>}</div>}</div></div>
        <footer className="plot-stage-footer"><span>{message}</span><span title={previewInfo}>{previewInfo || currentSource?.name || "대기 중"}</span></footer>
      </section>

      <aside className="layer-inspector">
        <header className="layer-inspector-header"><div><span className="section-eyebrow">{rightPanel === "layers" ? "레이어 디자인" : "그리기 디자인"}</span><strong>{rightPanel === "layers" ? `${currentVowels.length}개 모음` : "주석 도구"}</strong></div><button className="rail-collapse" aria-label="오른쪽 패널 접기" onClick={() => setRightOpen(false)}><PanelRightClose size={16} /></button></header>
        <div className="layer-panel-tabs"><button type="button" className={rightPanel === "layers" ? "is-active" : ""} onClick={() => setRightPanel("layers")}><Layers3 size={15} /> 레이어</button><button type="button" className={rightPanel === "drawing" ? "is-active" : ""} onClick={() => enterDrawMode(drawTool)}><PenLine size={15} /> 그리기</button></div>
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
                  <div className="font-controls font-family-row">
                    <select value={String(effective("font_family"))} onChange={(event) => { const font_family = event.target.value; updateLayerDesign({ font_family, font_style: fontFamilyStyle(font_family), font_weight: normalizedFontWeight(font_family, effective("font_weight")) }); }} aria-label="글꼴">
                      {FONT_FAMILIES.map((family) => <option key={family}>{family}</option>)}
                    </select>
                    <select value={normalizedFontWeight(String(effective("font_family")), effective("font_weight"))} onChange={(event) => updateLayerDesign({ font_weight: event.target.value as DesignSettings["font_weight"], lbl_bold: event.target.value === "bold" })} disabled={(FONT_WEIGHTS[String(effective("font_family"))] ?? []).length <= 1} aria-label="Weight">
                      {(FONT_WEIGHTS[String(effective("font_family"))] ?? ["regular"]).map((weight) => <option key={weight} value={weight}>{FONT_WEIGHT_LABELS[weight]}</option>)}
                    </select>
                  </div>
                  <div className="font-size-row">
                    <label className="font-size-control"><span className="font-control-caption">크기 <b>{Number(effective("lbl_size"))}pt</b></span><input type="range" min="12" max="28" step="1" value={Number(effective("lbl_size"))} onChange={(event) => updateLayerDesign({ lbl_size: Number(event.target.value) })} /></label>
                    <div className="font-style-buttons"><button type="button" className={effective("font_weight") === "bold" ? "is-active" : ""} onClick={() => updateLayerDesign({ font_weight: effective("font_weight") === "bold" ? "regular" : "bold", lbl_bold: effective("font_weight") !== "bold" })} aria-label="볼드"><Bold size={15} /></button><button type="button" className={effective("lbl_italic") ? "is-active" : ""} onClick={() => updateLayerDesign({ lbl_italic: !effective("lbl_italic") })} aria-label="기울임"><Italic size={15} /></button></div>
                  </div>
                </div>
                <label className="control-label">중심점 모양</label>
                <MarkerPicker value={String(effective("centroid_marker"))} onChange={(centroid_marker) => updateLayerDesign({ centroid_marker })} disabled={selectedLocked} />
                <label className="control-label">신뢰 타원</label>
                <div className="segmented-row"><button type="button" className={Number(effective("ell_thick")) === 0.5 ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_thick: 0.5 })}>얇게</button><button type="button" className={Number(effective("ell_thick")) === 1 ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_thick: 1 })}>보통</button><button type="button" className={Number(effective("ell_thick")) === 2 ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_thick: 2 })}>굵게</button></div>
                <div className="segmented-row"><button type="button" className={effective("ell_style") === "-" ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_style: "-" })}>실선</button><button type="button" className={effective("ell_style") === "---" ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_style: "---" })}>긴 점선</button><button type="button" className={effective("ell_style") === "--" || effective("ell_style") === ":" ? "is-active" : ""} onClick={() => updateLayerDesign({ ell_style: "--" })}>짧은 점선</button></div>
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
              <div className="drawing-panel-heading"><span>그리기 도구</span></div>
              <div className="drawing-tool-grid">
                <button type="button" className={drawTool === "text" ? "is-active" : ""} onClick={() => activateDrawTool("text")}><span className="draw-tool-icon">T</span><span><strong>텍스트</strong><small>설명과 라벨</small></span></button>
                <button type="button" className={drawTool === "line" ? "is-active" : ""} onClick={() => activateDrawTool("line")}><PenLine size={16} /><span><strong>선</strong><small>직선과 화살표</small></span></button>
                <button type="button" className={drawTool === "area" ? "is-active" : ""} onClick={() => activateDrawTool("area")}><ScanSearch size={16} /><span><strong>영역</strong><small>강조 범위</small></span></button>
                <button type="button" className={drawTool === "reference" ? "is-active" : ""} onClick={() => activateDrawTool("reference")}><Ruler size={16} /><span><strong>기준선</strong><small>축 기준 표시</small></span></button>
                <button type="button" className={drawTool === "legend" ? "is-active" : ""} onClick={() => activateDrawTool("legend")}><List size={16} /><span><strong>범례</strong><small>선과 모음 설명</small></span></button>
              </div>
              {drawTool !== "legend" ? (
                <div className="drawing-defaults-row">
                  <button
                    type="button"
                    className="wide-action primary drawing-defaults-button"
                    onClick={() => {
                      openDrawDefaultsEditor(drawTool === "text" ? "text" : undefined);
                    }}
                  >
                    <SlidersHorizontal size={14} /> 그리기 수정
                  </button>
                </div>
              ) : null}
              {drawTool === "reference" ? (
                <div className="reference-mode-row drawing-panel-reference-modes">
                  <span>기준선 종류</span>
                  <div className="segmented-row reference-mode-choices">
                    <button type="button" className={referenceMode === "horizontal" ? "is-active" : ""} onClick={() => { setReferenceMode("horizontal"); setMessage("수평 기준선 · 마우스를 올리면 미리보기가 보입니다."); }}>수평</button>
                    <button type="button" className={referenceMode === "vertical" ? "is-active" : ""} onClick={() => { setReferenceMode("vertical"); setMessage("수직 기준선 · 마우스를 올리면 미리보기가 보입니다."); }}>수직</button>
                  </div>
                </div>
              ) : null}
            </section>
          </div>
          <div className="layer-splitter" role="separator" aria-orientation="horizontal" aria-label="그리기 디자인과 목록 높이 조절" onPointerDown={beginLayerPanelResize} onPointerMove={resizeLayerPanels} onPointerUp={endLayerPanelResize} onPointerCancel={endLayerPanelResize} onLostPointerCapture={cancelLayerPanelResize}><i /></div>
          <div className="drawing-layer-dock">
            <div className="layer-batch-row"><span>일괄 적용</span><button type="button" onClick={toggleAllDrawVisibility} disabled={!currentDrawObjects.length}><Eye size={14} /> 전체 표시</button><button type="button" onClick={toggleAllDrawSemi} disabled={!currentDrawObjects.length}>반투명</button></div>
            <div className="layer-list-toolbar"><span><GripVertical size={12} /> 끌어서 순서 변경</span><button type="button" className="layer-toolbar-danger" disabled={!currentDrawObjects.length} onClick={() => persistDrawObjects([])}>모두 삭제</button></div>
            {currentDrawObjects.length ? (
              <div className="layer-list drawing-object-list">
                {drawObjectsTopFirst.map((object) => {
                  const lineIndex = object.type === "line" ? currentDrawLines.findIndex((line) => line.id === object.id) + 1 : 0;
                  const polyIndex = object.type === "polygon"
                    ? currentDrawObjects.filter((item) => item.type === "polygon").findIndex((item) => item.id === object.id) + 1
                    : 0;
                  const textIndex = object.type === "text"
                    ? currentDrawObjects.filter((item) => item.type === "text").findIndex((item) => item.id === object.id) + 1
                    : 0;
                  const label = object.type === "legend"
                    ? (object.name || "범례")
                    : object.type === "reference"
                      ? `${object.mode === "horizontal" ? "수평" : "수직"} ${formatRefLabel(object.value, object.axis_units, true, analysis?.normalization ?? null).trim()}`
                      : object.type === "polygon"
                        ? `영역 ${polyIndex}`
                        : object.type === "text"
                          ? `텍스트 ${textIndex}`
                          : `선 ${lineIndex}`;
                  return (
                    <div
                      className={`layer-row drawing-object-row ${object.visible ? "" : "visibility-off"} ${object.semi ? "visibility-semi" : ""} ${selectedDrawObjectIds.has(object.id) ? "is-selected" : ""} ${draggingDrawObject === object.id ? "is-dragging" : ""} ${drawDropTarget?.id === object.id ? (drawDropTarget.after ? "drop-after" : "drop-before") : ""}`}
                      data-draw-object-id={object.id}
                      key={object.id}
                    >
                      <div className="layer-row-main">
                        <button type="button" className="layer-drag-handle" onPointerDown={(event) => beginDrawObjectDrag(event, object.id)} onPointerMove={moveDrawObjectDrag} onPointerUp={commitDrawObjectDrag} onPointerCancel={cancelDrawObjectDrag} aria-label={`${label} 순서 이동`} title="끌어서 이동"><GripVertical size={15} /></button>
                        <button type="button" className="layer-visibility" onClick={() => toggleDrawObjectVisibility(object.id)} title={object.visible ? "레이어 숨기기" : "레이어 표시"}>{object.visible ? <Eye size={15} /> : <EyeOff size={15} />}</button>
                        <button type="button" className={`layer-semi ${object.semi ? "is-active" : ""}`} onClick={() => toggleDrawObjectSemi(object.id)}>반투명</button>
                        <button
                          type="button"
                          className="layer-name drawing-layer-name"
                          onMouseDown={(event) => { if (event.button === 0) event.preventDefault(); }}
                          onClick={(event) => selectDrawObject(object.id, event)}
                        >
                          <strong>{label}</strong>
                        </button>
                        <button type="button" className="layer-lock drawing-object-edit" onClick={() => openDrawLayerEditor(object)} aria-label={`${label} 편집`} title="스타일 수정"><Palette size={14} /></button>
                        <button
                          type="button"
                          className="layer-lock drawing-object-delete"
                          onClick={() => deleteDrawObjects(object.id)}
                          aria-label={`${label} 삭제`}
                          title="삭제"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : <div className="drawing-empty"><Layers3 size={20} /><strong>그리기 레이어가 없습니다</strong><span>범례·선·기준선을 추가하면 이곳에 표시됩니다.</span></div>}
          </div>
        </div>
        )}
      </aside>
      {batchExportOpen ? <div className="batch-export-backdrop" data-modal-root role="presentation">
        <section ref={batchExportDialogRef} className="batch-export-dialog" role="dialog" aria-modal="true" aria-labelledby="batch-export-title">
          <header><div><span className="section-eyebrow">EXPORT WORKSPACE</span><h2 id="batch-export-title">일괄 저장</h2><p>현재 React/Tauri 플롯 설정을 모든 파일에 적용해 저장합니다.</p></div><button type="button" onClick={() => setBatchExportOpen(false)} disabled={batchExportBusy} aria-label="닫기"><X size={18} /></button></header>
          <div className="batch-export-body">
            <div className="batch-export-summary"><strong>{sources.length}개 파일</strong><span>범위 · 디자인 · 레이어 상태 · 라벨 위치 포함</span></div>
            <label className="batch-export-field"><span>파일 형식</span><div className="batch-format-picker">{(["png", "jpg", "svg"] as const).map((format) => <button type="button" key={format} className={batchExportFormat === format ? "is-active" : ""} onClick={() => setBatchExportFormat(format)}>{format.toUpperCase()}</button>)}</div></label>
            <label className="batch-export-field"><span>저장 폴더</span><div className="batch-directory-row"><input value={batchExportDirectory} readOnly placeholder="폴더를 선택하세요" /><button type="button" onClick={() => void chooseBatchDirectory()} disabled={batchExportBusy}>찾아보기</button></div></label>
            <div className="batch-export-options"><span>반영할 항목</span><ToggleSwitch label="광역 디자인" checked={batchApplyGlobalDesign} onChange={() => setBatchApplyGlobalDesign((value) => !value)} /><ToggleSwitch label="레이어 디자인" checked={batchApplyLayerDesign} onChange={() => setBatchApplyLayerDesign((value) => !value)} /><ToggleSwitch label="레이어 표시 상태" checked={batchApplyVisibility} onChange={() => setBatchApplyVisibility((value) => !value)} /><ToggleSwitch label="라벨 위치" checked={batchApplyLabelPositions} onChange={() => setBatchApplyLabelPositions((value) => !value)} /></div>
            <p className="batch-export-note">동일한 파일명이 있으면 자동으로 `_2`, `_3` suffix를 붙입니다.</p>
          </div>
          <footer><button type="button" className="wide-action" onClick={() => setBatchExportOpen(false)} disabled={batchExportBusy}>취소</button><button type="button" className="wide-action primary" onClick={() => void runBatchExport()} disabled={!batchExportDirectory || batchExportBusy}>{batchExportBusy ? "저장 중…" : "일괄 저장 시작"}</button></footer>
        </section>
      </div> : null}
      {textInput ? (
        <div className="legend-editor-backdrop" role="presentation">
          <section className="legend-editor-dialog draw-text-input-dialog" role="dialog" aria-modal="true" aria-labelledby="draw-text-input-title">
            <header>
              <div>
                <span className="section-eyebrow">TEXT</span>
                <h2 id="draw-text-input-title">텍스트 입력</h2>
                <p>여러 줄 가능 · Enter로 줄바꿈</p>
              </div>
              <button type="button" onClick={() => setTextInput(null)} aria-label="닫기"><X size={18} /></button>
            </header>
            <div className="legend-editor-body">
              <label className="draw-text-content-field">
                <span>표시할 텍스트</span>
                <textarea
                  autoFocus
                  value={textInput.draft}
                  onChange={(event) => setTextInput({ ...textInput, draft: event.target.value })}
                  rows={6}
                />
              </label>
            </div>
            <footer>
              <button type="button" className="wide-action" onClick={() => setTextInput(null)}>취소</button>
              <button type="button" className="wide-action primary" onClick={confirmTextInput}>확인</button>
            </footer>
          </section>
        </div>
      ) : null}
      {drawEditorOpen ? <div className="legend-editor-backdrop" role="presentation">
        <section className="legend-editor-dialog draw-style-editor-dialog" role="dialog" aria-modal="true" aria-labelledby="draw-editor-title">
          <header>
            <div>
              <span className="section-eyebrow">DRAW STYLE</span>
              <h2 id="draw-editor-title">
                {drawEditorKind === "line" ? "선 수정" : drawEditorKind === "polygon" ? "영역 수정" : drawEditorKind === "reference" ? "기준선 수정" : drawEditorKind === "text" ? "텍스트 수정" : "범례 수정"}
              </h2>
              {drawEditorMode === "layer" && drawEditorKind !== "legend" ? <p>선택한 레이어에 적용</p> : null}
            </div>
            <button type="button" onClick={closeDrawEditor} aria-label="닫기"><X size={18} /></button>
          </header>
          <div className="legend-editor-body">
            {drawEditorKind === "line" && lineDraft ? (
              <div className="legend-editor-section is-first">
                <div className="legend-editor-section-heading"><strong>선 스타일</strong></div>
                <div className="palette-picker-row"><PalettePicker label="선 색상" value={lineDraft.line_color} onChange={(line_color) => line_color && setLineDraft({ ...lineDraft, line_color })} /></div>
                <label className="opacity-control"><span>선 두께 <b>{clampDrawLineWidth(lineDraft.line_width)}pt</b></span><input type="range" min={DRAW_LINE_WIDTH_MIN} max={DRAW_LINE_WIDTH_MAX} step={DRAW_LINE_WIDTH_STEP} value={clampDrawLineWidth(lineDraft.line_width)} onChange={(event) => setLineDraft({ ...lineDraft, line_width: clampDrawLineWidth(Number(event.target.value)) })} /></label>
                <div className="drawing-style-group"><span className="drawing-style-caption">선 스타일</span><div className="segmented-row is-cols-4"><button type="button" className={lineDraft.line_style === "-" ? "is-active" : ""} onClick={() => setLineDraft({ ...lineDraft, line_style: "-" })} title="실선"><i className="line-style-swatch" /></button><button type="button" className={lineDraft.line_style === "--" ? "is-active" : ""} onClick={() => setLineDraft({ ...lineDraft, line_style: "--" })} title="파선"><i className="line-style-swatch is-dashed" /></button><button type="button" className={lineDraft.line_style === ":" ? "is-active" : ""} onClick={() => setLineDraft({ ...lineDraft, line_style: ":" })} title="점선"><i className="line-style-swatch is-dotted" /></button><button type="button" className={lineDraft.line_style === "-." ? "is-active" : ""} onClick={() => setLineDraft({ ...lineDraft, line_style: "-." })} title="일점쇄선"><i className="line-style-swatch is-dash-dot" /></button></div></div>
                <div className="drawing-style-group"><span className="drawing-style-caption">화살표 위치</span><div className="segmented-row is-cols-3"><button type="button" className={lineDraft.arrow_mode === "none" ? "is-active" : ""} onClick={() => setLineDraft({ ...lineDraft, arrow_mode: "none" })} title="화살표 없음"><TrajectoryIcon mode="none" /></button><button type="button" className={lineDraft.arrow_mode === "end" ? "is-active" : ""} onClick={() => setLineDraft({ ...lineDraft, arrow_mode: "end" })} title="끝점"><TrajectoryIcon mode="end" head={lineDraft.arrow_head} /></button><button type="button" className={lineDraft.arrow_mode === "all" ? "is-active" : ""} onClick={() => setLineDraft({ ...lineDraft, arrow_mode: "all" })} title="점마다"><TrajectoryIcon mode="all" head={lineDraft.arrow_head} /></button></div></div>
                {lineDraft.arrow_mode !== "none" ? <div className="drawing-style-group"><span className="drawing-style-caption">화살표 모양</span><div className="segmented-row is-cols-3"><button type="button" className={lineDraft.arrow_head === "stealth" ? "is-active" : ""} onClick={() => setLineDraft({ ...lineDraft, arrow_head: "stealth" })} title="stealth"><TrajectoryIcon mode="end" head="stealth" /></button><button type="button" className={lineDraft.arrow_head === "open" ? "is-active" : ""} onClick={() => setLineDraft({ ...lineDraft, arrow_head: "open" })} title="open"><TrajectoryIcon mode="end" head="open" /></button><button type="button" className={lineDraft.arrow_head === "latex" ? "is-active" : ""} onClick={() => setLineDraft({ ...lineDraft, arrow_head: "latex" })} title="latex"><TrajectoryIcon mode="end" head="latex" /></button></div></div> : null}
              </div>
            ) : null}
            {drawEditorKind === "polygon" && polygonDraft ? (
              <div className="legend-editor-section is-first">
                <div className="legend-editor-section-heading"><strong>영역 스타일</strong></div>
                <div className="drawing-style-group"><span className="drawing-style-caption">테두리 스타일</span><div className="segmented-row is-cols-4"><button type="button" className={polygonDraft.border_style === "-" ? "is-active" : ""} onClick={() => setPolygonDraft({ ...polygonDraft, border_style: "-" })} title="실선"><i className="line-style-swatch" /></button><button type="button" className={polygonDraft.border_style === "--" ? "is-active" : ""} onClick={() => setPolygonDraft({ ...polygonDraft, border_style: "--" })} title="파선"><i className="line-style-swatch is-dashed" /></button><button type="button" className={polygonDraft.border_style === ":" ? "is-active" : ""} onClick={() => setPolygonDraft({ ...polygonDraft, border_style: ":" })} title="점선"><i className="line-style-swatch is-dotted" /></button><button type="button" className={polygonDraft.border_style === "-." ? "is-active" : ""} onClick={() => setPolygonDraft({ ...polygonDraft, border_style: "-." })} title="일점쇄선"><i className="line-style-swatch is-dash-dot" /></button></div></div>
                <div className="palette-picker-row"><PalettePicker label="테두리 색상" value={polygonDraft.border_color} onChange={(border_color) => border_color && setPolygonDraft({ ...polygonDraft, border_color })} /><PalettePicker label="채우기 색상" value={polygonDraft.fill_color} onChange={(fill_color) => setPolygonDraft({ ...polygonDraft, fill_color })} allowTransparent /></div>
                <label className="opacity-control"><span>채우기 불투명도 <b>{Math.round(polygonDraft.fill_opacity * 100)}%</b></span><input type="range" min="0" max="100" step="1" value={Math.round(polygonDraft.fill_opacity * 100)} onChange={(event) => setPolygonDraft({ ...polygonDraft, fill_opacity: Number(event.target.value) / 100 })} /></label>
              </div>
            ) : null}
            {drawEditorKind === "reference" && referenceDraft ? (
              <div className="legend-editor-section is-first">
                <div className="legend-editor-section-heading"><strong>기준선</strong></div>
                {referenceDraft.valueLabel ? <div className="drawing-tool-summary"><span>값</span><b>{referenceDraft.valueLabel}</b></div> : null}
                <div className="reference-mode-row"><span>종류</span><div className="segmented-row is-cols-2 reference-mode-choices"><button type="button" className={referenceDraft.mode === "horizontal" ? "is-active" : ""} onClick={() => setReferenceDraft({ ...referenceDraft, mode: "horizontal" })}>수평</button><button type="button" className={referenceDraft.mode === "vertical" ? "is-active" : ""} onClick={() => setReferenceDraft({ ...referenceDraft, mode: "vertical" })}>수직</button></div></div>
                <div className="drawing-style-group"><span className="drawing-style-caption">선 스타일</span><div className="segmented-row is-cols-4"><button type="button" className={referenceDraft.line_style === "-" ? "is-active" : ""} onClick={() => setReferenceDraft({ ...referenceDraft, line_style: "-" })} title="실선"><i className="line-style-swatch" /></button><button type="button" className={referenceDraft.line_style === "--" ? "is-active" : ""} onClick={() => setReferenceDraft({ ...referenceDraft, line_style: "--" })} title="파선"><i className="line-style-swatch is-dashed" /></button><button type="button" className={referenceDraft.line_style === ":" ? "is-active" : ""} onClick={() => setReferenceDraft({ ...referenceDraft, line_style: ":" })} title="점선"><i className="line-style-swatch is-dotted" /></button><button type="button" className={referenceDraft.line_style === "-." ? "is-active" : ""} onClick={() => setReferenceDraft({ ...referenceDraft, line_style: "-." })} title="일점쇄선"><i className="line-style-swatch is-dash-dot" /></button></div></div>
                <div className="palette-picker-row"><PalettePicker label="선 색상" value={referenceDraft.line_color} onChange={(line_color) => setReferenceDraft({ ...referenceDraft, line_color })} allowTransparent /></div>
              </div>
            ) : null}
            {drawEditorKind === "text" && textDraft ? (
              <div className="legend-editor-section is-first">
                <div className="legend-editor-section-heading"><strong>텍스트 스타일</strong></div>
                {drawEditorMode === "layer" ? (
                  <label className="draw-text-content-field">
                    <span>내용 (Enter로 줄바꿈)</span>
                    <textarea
                      value={textDraft.text}
                      onChange={(event) => setTextDraft({ ...textDraft, text: event.target.value })}
                      rows={5}
                    />
                  </label>
                ) : null}
                <div className="legend-editor-grid">
                  <label>
                    <span>글꼴</span>
                    <select
                      value={textDraft.font_family}
                      onChange={(event) => {
                        const font_family = event.target.value;
                        setTextDraft({
                          ...textDraft,
                          font_family,
                          font_weight: normalizedFontWeight(font_family, textDraft.font_weight),
                        });
                      }}
                    >
                      {FONT_FAMILIES.map((family) => <option key={family}>{family}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>굵기</span>
                    <select
                      value={normalizedFontWeight(textDraft.font_family, textDraft.font_weight)}
                      onChange={(event) => setTextDraft({ ...textDraft, font_weight: event.target.value as DesignSettings["font_weight"] })}
                      disabled={(FONT_WEIGHTS[textDraft.font_family] ?? []).length <= 1}
                    >
                      {(FONT_WEIGHTS[textDraft.font_family] ?? ["regular"]).map((weight) => (
                        <option key={weight} value={weight}>{FONT_WEIGHT_LABELS[weight]}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <label className="opacity-control"><span>글자 크기 <b>{clampDrawTextFontSize(textDraft.font_size)}pt</b></span><input type="range" min={DRAW_TEXT_SIZE_MIN} max={DRAW_TEXT_SIZE_MAX} step={1} value={clampDrawTextFontSize(textDraft.font_size)} onChange={(event) => setTextDraft({ ...textDraft, font_size: clampDrawTextFontSize(Number(event.target.value)) })} /></label>
                <label className="opacity-control"><span>줄간격 <b>{clampDrawTextLineSpacing(textDraft.line_spacing).toFixed(2)}</b></span><input type="range" min={DRAW_TEXT_LINE_SPACING_MIN} max={DRAW_TEXT_LINE_SPACING_MAX} step={0.05} value={clampDrawTextLineSpacing(textDraft.line_spacing)} onChange={(event) => setTextDraft({ ...textDraft, line_spacing: clampDrawTextLineSpacing(Number(event.target.value)) })} /></label>
                <ToggleSwitch label="기울임" checked={textDraft.font_italic} onChange={() => setTextDraft({ ...textDraft, font_italic: !textDraft.font_italic })} />
                <div className="palette-picker-row"><PalettePicker label="글자 색상" value={textDraft.text_color} onChange={(text_color) => text_color && setTextDraft({ ...textDraft, text_color })} /></div>
              </div>
            ) : null}
            {drawEditorKind === "legend" && legendDraft ? (
              <>
                <div className="legend-editor-section is-first"><div className="legend-editor-section-heading"><strong>항목 순서와 이름</strong><button type="button" onClick={() => setLegendDraft({ ...legendDraft, entries: [...legendDraft.entries, { series_id: legendDraft.entries.length, text: "새 항목" }] })}>항목 추가</button></div><div className="legend-entry-editor">{legendDraft.entries.map((entry, index) => <div className="legend-entry-row" key={`${entry.series_id}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><input value={entry.text} onChange={(event) => setLegendDraft({ ...legendDraft, entries: legendDraft.entries.map((item, itemIndex) => itemIndex === index ? { ...item, text: event.target.value } : item) })} /><button type="button" onClick={() => setLegendDraft({ ...legendDraft, entries: legendDraft.entries.map((item, itemIndex) => itemIndex === index && itemIndex > 0 ? legendDraft.entries[itemIndex - 1] : itemIndex === index - 1 ? entry : item) })} disabled={index === 0} aria-label="위로 이동" title="위로 이동"><ArrowUp size={13} /></button><button type="button" onClick={() => setLegendDraft({ ...legendDraft, entries: legendDraft.entries.map((item, itemIndex) => itemIndex === index && itemIndex < legendDraft.entries.length - 1 ? legendDraft.entries[itemIndex + 1] : itemIndex === index + 1 ? entry : item) })} disabled={index === legendDraft.entries.length - 1} aria-label="아래로 이동" title="아래로 이동"><ArrowDown size={13} /></button><button type="button" onClick={() => setLegendDraft({ ...legendDraft, entries: legendDraft.entries.filter((_, itemIndex) => itemIndex !== index) })} disabled={legendDraft.entries.length <= 1} aria-label="항목 삭제" title="항목 삭제"><X size={13} /></button></div>)}</div></div>
                <div className="legend-editor-section"><div className="legend-editor-section-heading"><strong>문자 스타일</strong></div><div className="legend-editor-grid"><label><span>글꼴</span><select value={legendDraft.font_family} onChange={(event) => setLegendDraft({ ...legendDraft, font_family: event.target.value })}>{FONT_FAMILIES.map((family) => <option key={family}>{family}</option>)}</select></label><label><span>굵기</span><select value={legendDraft.font_weight} onChange={(event) => setLegendDraft({ ...legendDraft, font_weight: event.target.value as LegendDraft["font_weight"] })}><option value="regular">보통</option><option value="medium">중간</option><option value="semibold">세미볼드</option><option value="bold">굵게</option></select></label></div><label className="opacity-control legend-size-control"><span>글자 크기 <b>{legendDraft.font_size}pt</b></span><input type="range" min="6" max="20" step="1" value={legendDraft.font_size} onChange={(event) => setLegendDraft({ ...legendDraft, font_size: Number(event.target.value) })} /></label><ToggleSwitch label="기울임" checked={legendDraft.font_italic} onChange={() => setLegendDraft({ ...legendDraft, font_italic: !legendDraft.font_italic })} /></div>
                <div className="legend-editor-section"><div className="legend-editor-section-heading"><strong>상자 스타일</strong></div><div className="legend-border-toggle-row"><ToggleSwitch label="테두리 표시" checked={legendDraft.show_border} onChange={() => setLegendDraft({ ...legendDraft, show_border: !legendDraft.show_border })} /></div><div className="drawing-style-group legend-border-style-group"><span className="drawing-style-caption">테두리 스타일</span><div className="segmented-row"><button type="button" className={legendDraft.border_style === "-" ? "is-active" : ""} onClick={() => setLegendDraft({ ...legendDraft, border_style: "-" })} aria-label="실선" title="실선"><i className="line-style-swatch" /></button><button type="button" className={legendDraft.border_style === "--" ? "is-active" : ""} onClick={() => setLegendDraft({ ...legendDraft, border_style: "--" })} aria-label="파선" title="파선"><i className="line-style-swatch is-dashed" /></button><button type="button" className={legendDraft.border_style === ":" ? "is-active" : ""} onClick={() => setLegendDraft({ ...legendDraft, border_style: ":" })} aria-label="점선" title="점선"><i className="line-style-swatch is-dotted" /></button><button type="button" className={legendDraft.border_style === "-." ? "is-active" : ""} onClick={() => setLegendDraft({ ...legendDraft, border_style: "-." })} aria-label="일점쇄선" title="일점쇄선"><i className="line-style-swatch is-dash-dot" /></button></div></div><div className="palette-picker-row"><PalettePicker label="테두리 색상" value={legendDraft.border_color} onChange={(border_color) => border_color && setLegendDraft({ ...legendDraft, border_color })} /><PalettePicker label="채우기 색상" value={legendDraft.fill_color} onChange={(fill_color) => fill_color && setLegendDraft({ ...legendDraft, fill_color })} /></div><ToggleSwitch label="배경 채우기" checked={legendDraft.show_fill} onChange={() => setLegendDraft({ ...legendDraft, show_fill: !legendDraft.show_fill })} /><label className="opacity-control"><span>배경 불투명도 <b>{Math.round(legendDraft.fill_opacity * 100)}%</b></span><input type="range" min="0" max="100" value={Math.round(legendDraft.fill_opacity * 100)} onChange={(event) => setLegendDraft({ ...legendDraft, fill_opacity: Number(event.target.value) / 100 })} /></label></div>
              </>
            ) : null}
          </div>
          <footer><button type="button" className="wide-action" onClick={closeDrawEditor}>취소</button><button type="button" className="wide-action primary" onClick={saveDrawEditor}>적용</button></footer>
        </section>
      </div> : null}
      {vowelAnalysisOpen ? <VowelAnalysisShell currentSource={currentSource} sources={sources} currentIndex={currentIndex} displayIndex={Math.max(0, sources.findIndex((source) => source.index === currentIndex))} onNavigate={(index) => void navigateTo(index)} onClose={() => setVowelAnalysisOpen(false)} /> : null}
      {shortcutHelpOpen ? (
        <div className="shortcut-help-backdrop" data-modal-root role="presentation" onClick={() => setShortcutHelpOpen(false)}>
          <section
            ref={shortcutHelpRef}
            className="shortcut-help-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="shortcut-help-title"
            onClick={(event) => event.stopPropagation()}
          >
            <header>
              <div>
                <span className="section-eyebrow">KEYBOARD</span>
                <h2 id="shortcut-help-title">단축키</h2>
                <p>입력란에 포커스가 있을 때는 일부 키가 무시됩니다.</p>
              </div>
              <button type="button" onClick={() => setShortcutHelpOpen(false)} aria-label="닫기"><X size={18} /></button>
            </header>
            <div className="shortcut-help-body">
              <div className="shortcut-help-group">
                <strong>패널</strong>
                <ul>
                  <li><kbd>`</kbd><span>좌·우 패널 접기/펼치기</span></li>
                  <li><kbd>A</kbd><span>분석 도구 패널</span></li>
                  <li><kbd>D</kbd><span>광역 디자인 패널</span></li>
                  <li><kbd>?</kbd><span>이 도움말</span></li>
                </ul>
              </div>
              <div className="shortcut-help-group">
                <strong>도구</strong>
                <ul>
                  <li><kbd>R</kbd><span>눈금자</span></li>
                  <li><kbd>T</kbd><span>라벨 이동</span></li>
                  <li><kbd>P</kbd><span>그리기 모드</span></li>
                  <li><kbd>1</kbd>–<kbd>5</kbd><span>그리기 도구 (선·영역·텍스트·기준선·범례)</span></li>
                  <li><kbd>Esc</kbd><span>도구 취소 / 모드 종료</span></li>
                </ul>
              </div>
              <div className="shortcut-help-group">
                <strong>파일</strong>
                <ul>
                  <li><kbd>←</kbd> <kbd>→</kbd><span>이전/다음 파일</span></li>
                  <li><kbd>Home</kbd> / <kbd>End</kbd><span>첫/마지막 파일</span></li>
                  <li><kbd>Ctrl</kbd>+<kbd>S</kbd><span>프로젝트 저장</span></li>
                  <li><kbd>M</kbd><span>다중 플롯 (파일 2개 이상)</span></li>
                </ul>
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
