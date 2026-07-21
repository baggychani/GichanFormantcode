import { barkToHz } from "../../plotUnits";

export const DRAW_LINE_DEFAULT_COLOR = "#000000";
export const DRAW_LINE_WIDTH_MIN = 0.25;
export const DRAW_LINE_WIDTH_MAX = 3;
export const DRAW_LINE_WIDTH_STEP = 0.25;
export const DRAW_LINE_DEFAULT_WIDTH = 0.5;
export const DRAW_POLYGON_DEFAULT_FILL = "#3366CC";
export const DRAW_POLYGON_DEFAULT_BORDER = "#000000";
export const DRAW_TEXT_DEFAULT_COLOR = "#303133";
export const DRAW_TEXT_DEFAULT_SIZE = 13;
export const DRAW_TEXT_DEFAULT_FAMILY = "Noto Sans KR";
export const DRAW_TEXT_DEFAULT_LINE_SPACING = 1.15;
export const DRAW_TEXT_SIZE_MIN = 4;
export const DRAW_TEXT_SIZE_MAX = 32;
export const DRAW_TEXT_LINE_SPACING_MIN = 0.8;
export const DRAW_TEXT_LINE_SPACING_MAX = 2.5;

export const clampDrawLineWidth = (value: number) => {
  const stepped = Math.round(value / DRAW_LINE_WIDTH_STEP) * DRAW_LINE_WIDTH_STEP;
  return Math.min(DRAW_LINE_WIDTH_MAX, Math.max(DRAW_LINE_WIDTH_MIN, Number(stepped.toFixed(2))));
};

export const clampDrawTextFontSize = (value: number) =>
  Math.min(
    DRAW_TEXT_SIZE_MAX,
    Math.max(DRAW_TEXT_SIZE_MIN, Math.round(Number.isFinite(value) ? value : DRAW_TEXT_DEFAULT_SIZE)),
  );

export const clampDrawTextLineSpacing = (value: number) => {
  const n = Number.isFinite(value) ? value : DRAW_TEXT_DEFAULT_LINE_SPACING;
  return Math.min(DRAW_TEXT_LINE_SPACING_MAX, Math.max(DRAW_TEXT_LINE_SPACING_MIN, Number(n.toFixed(2))));
};

/** PySide draw_reference.round_ref_value 이식 — magnet/눈금 스냅. */
export function roundRefValue(
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
    if (norm.includes("lobanov")) {
      stepped = Math.round(raw * 10) / 10;
      tol = 0.05;
    } else if (norm.includes("gerstman")) {
      stepped = Math.round(raw / 10) * 10;
      tol = 5;
    } else if (norm.includes("2mw") || norm.includes("bigham") || norm.includes("nearey")) {
      stepped = Math.round(raw * 20) / 20;
      tol = 0.02;
    } else {
      stepped = Math.round(raw * 100) / 100;
      tol = 0.01;
    }
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
      if (dist < best) {
        nearest = candidate;
        best = dist;
      }
    }
    if (best <= tol) {
      if (u === "norm" && norm.includes("gerstman")) return { value: Math.round(nearest), snapped: true };
      return { value: nearest, snapped: true };
    }
  }
  if (u === "norm" && norm.includes("gerstman")) return { value: Math.round(stepped), snapped: true };
  return { value: stepped, snapped: true };
}

export function formatRefLabel(value: number, unit: string, snapped: boolean, normalization: string | null) {
  const u = (unit || "Hz").trim().toLowerCase();
  if (u === "norm" || u.includes("norm")) {
    if (String(normalization || "").toLowerCase().includes("gerstman")) return `  ${Math.round(value)}`;
    return `  ${value.toFixed(2)}`;
  }
  if (u === "bk" || u === "bark") return snapped ? `  ${value.toFixed(2)}` : `  ${value.toFixed(1)}`;
  return `  ${Math.round(value)}`;
}
