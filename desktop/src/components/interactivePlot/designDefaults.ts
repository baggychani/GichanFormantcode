import type { DesignSettings, Ranges } from "./types";

export const RANGE_DEFAULTS: Record<string, Ranges> = {
  f1_f2: { y_min: "200", y_max: "1000", x_min: "500", x_max: "3500" },
  f1_f2_minus_f1: { y_min: "200", y_max: "1000", x_min: "0", x_max: "3000" },
  f1_f3: { y_min: "200", y_max: "1000", x_min: "1500", x_max: "4500" },
  f1_f2_prime: { y_min: "200", y_max: "1000", x_min: "500", x_max: "4000" },
  f1_f2_prime_minus_f1: { y_min: "200", y_max: "1000", x_min: "0", x_max: "3500" },
};

export const BARK_RANGE_DEFAULTS: Record<string, Ranges> = {
  f1_f2: { y_min: "2", y_max: "9", x_min: "4", x_max: "16" },
  f1_f2_minus_f1: { y_min: "2", y_max: "9", x_min: "0", x_max: "12" },
  f1_f3: { y_min: "2", y_max: "9", x_min: "12", x_max: "19" },
  f1_f2_prime: { y_min: "2", y_max: "9", x_min: "4", x_max: "18" },
  f1_f2_prime_minus_f1: { y_min: "2", y_max: "9", x_min: "0", x_max: "14" },
};

/** Mirrors PlotEngine.NORM_RANGES — fixed presets, not data-driven. */
export const NORM_RANGE_DEFAULTS: Record<string, Ranges> = {
  Lobanov: { y_min: "-2", y_max: "2", x_min: "-2", x_max: "2" },
  Gerstman: { y_min: "0", y_max: "1000", x_min: "0", x_max: "1000" },
  "2mW/F": { y_min: "0.4", y_max: "1.8", x_min: "0.4", x_max: "1.8" },
  Bigham: { y_min: "0.4", y_max: "1.8", x_min: "0.4", x_max: "1.8" },
  Nearey1: { y_min: "-1", y_max: "1", x_min: "-1", x_max: "1" },
};

export function rangesLookCompatible(
  ranges: Ranges,
  normalization: string | null | undefined,
  useBark: boolean,
): boolean {
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
export const EMPTY_DESIGN: DesignSettings = {
  show_raw: true,
  show_centroid: true,
  raw_marker: "o",
  raw_color: "#606060",
  centroid_marker: "o",
  lbl_color: "#FF0000",
  lbl_size: 18,
  lbl_bold: true,
  lbl_italic: false,
  ell_thick: 0.5,
  ell_style: "-",
  ell_color: "#606060",
  ell_fill_color: null,
  ell_fill_opacity: 0.15,
  box_spines: false,
  show_grid: false,
  grid_opacity: 0.3,
  y_label_rotation: false,
  axis_position_swap: false,
  show_axis_units: false,
  show_minor_ticks: true,
  font_style: "serif",
  font_family: "Noto Serif KR",
  font_weight: "bold",
  label_slash_wrap: false,
  tick_label_size: 12,
};

export const FONT_FAMILIES = ["Noto Sans KR", "Noto Serif KR", "Charis SIL", "Andika"] as const;
export const FONT_WEIGHTS: Record<string, Array<DesignSettings["font_weight"]>> = {
  "Noto Sans KR": ["regular", "bold"],
  "Noto Serif KR": ["regular", "medium", "bold"],
  "Charis SIL": ["regular", "bold"],
  Andika: ["regular", "medium", "semibold", "bold"],
};
export const FONT_WEIGHT_LABELS: Record<DesignSettings["font_weight"], string> = {
  regular: "Regular",
  medium: "Medium",
  semibold: "Semibold",
  bold: "Bold",
};

export function fontFamilyStyle(family: string) {
  return family === "Noto Serif KR" || family === "Charis SIL" ? "serif" : "sans";
}

export function normalizedFontWeight(family: string, value: unknown): DesignSettings["font_weight"] {
  const choices = FONT_WEIGHTS[family] ?? ["regular"];
  return choices.includes(value as DesignSettings["font_weight"])
    ? (value as DesignSettings["font_weight"])
    : choices[0];
}

export const MARKERS = [
  ["o", "●"],
  ["s", "■"],
  ["^", "▲"],
  ["D", "◆"],
  ["wo", "○"],
  ["ws", "□"],
] as const;

export const MARKER_DISPLAY_LABELS: Record<string, string> = {
  o: "원",
  s: "사각형",
  "^": "삼각형",
  D: "마름모",
  wo: "빈 원",
  ws: "빈 사각형",
  x: "가위표",
  a: "라벨",
};

export const DESIGN_EFFECT_ORDER: (keyof DesignSettings)[] = [
  "lbl_color",
  "lbl_size",
  "lbl_bold",
  "lbl_italic",
  "centroid_marker",
  "ell_thick",
  "ell_style",
  "ell_color",
  "ell_fill_color",
  "ell_fill_opacity",
  "raw_color",
  "raw_marker",
  "label_slash_wrap",
];

export const DESIGN_EFFECT_LABELS: Partial<Record<keyof DesignSettings, string>> = {
  lbl_color: "라벨 색",
  lbl_size: "라벨 크기",
  lbl_bold: "라벨 굵기",
  lbl_italic: "라벨 기울임",
  centroid_marker: "중심점 모양",
  ell_thick: "타원 선 두께",
  ell_style: "타원 선 모양",
  ell_color: "타원 선 색",
  ell_fill_color: "타원 내부 색",
  ell_fill_opacity: "타원 불투명도",
  raw_color: "원자료 색",
  raw_marker: "원자료 모양",
  label_slash_wrap: "슬래시 감싸기",
};

export function effectDisplayValue(key: keyof DesignSettings, value: DesignSettings[keyof DesignSettings]) {
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

/** 축·눈금과 같은 계열 (utils.font_stacks.axis_font_list 대응). 웹뷰에 없는 Noto는 Charis로 폴백. */
export function axisPreviewFontFamily(design: Pick<DesignSettings, "font_style" | "font_family">): string {
  const family = String(design.font_family || "");
  const style = design.font_style || fontFamilyStyle(family);
  if (family === "Charis SIL") return '"Charis SIL", "Times New Roman", serif';
  if (family === "Andika") return '"Andika", "Noto Sans KR", sans-serif';
  if (style === "serif" || family === "Noto Serif KR") {
    return '"Noto Serif KR", "Charis SIL", "Times New Roman", serif';
  }
  return '"Noto Sans KR", "Andika", "Malgun Gothic", sans-serif';
}
