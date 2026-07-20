/**
 * Single source of truth for plot display units in the React interactive window.
 *
 * Mirrors PySide MainUI policy:
 * - Speaker normalization on → plot-space / nF* labels, no Hz|Bark suffix
 * - "Bark 단위로 표시" ON → integer Bark mode: BOTH axes bark (forced in
 *   ApplicationService.set_analysis_settings, same as get_f1_scale/get_f2_scale)
 * - Else Hz display (axis may still use bark *scale* with Hz tick labels)
 *
 * Add new unit kinds here first; call sites should read PlotUnitContext, not invent strings.
 */

export type PlotUnitKind = "hz" | "bark" | "normalized";

export type AnalysisUnitInput = {
  normalization?: string | null;
  use_bark_units?: boolean;
  f1_scale?: string | null;
  f2_scale?: string | null;
  type?: string | null;
};

export type PlotUnitContext = {
  kind: PlotUnitKind;
  normalization: string | null;
  plotType: string;
  /** Axis names shown in UI / tooltips */
  yAxisName: string;
  xAxisName: string;
  /** Badge next to “좌표축 범위” */
  rangeBadge: string;
  /** Suffix for formant stats tables: " (Hz)" | " (Bark)" | "" */
  formantStatSuffix: string;
  /** Draw / reference-line axis_units field */
  drawAxisUnits: "Hz" | "Bark" | "norm";
  /** Whether the ruler may offer an Hz↔Bark preference */
  rulerUnitChoiceEnabled: boolean;
  /** Default preference when choice is enabled */
  defaultRulerPreference: "hz" | "bark";
};

const X_AXIS_LABEL: Record<string, string> = {
  f1_f2: "F2",
  f1_f2_minus_f1: "F2 − F1",
  f1_f3: "F3",
  f1_f2_prime: "F2′",
  f1_f2_prime_minus_f1: "F2′ − F1",
};

const X_AXIS_LABEL_NORMALIZED: Record<string, string> = {
  f1_f2: "nF2",
  f1_f2_minus_f1: "nF2 − nF1",
  f1_f3: "nF3",
  f1_f2_prime: "nF2′",
  f1_f2_prime_minus_f1: "nF2′ − nF1",
};

export function hzToBark(hz: number) {
  return 26.81 / (1 + 1960 / Math.max(hz, 1e-6)) - 0.53;
}

export function barkToHz(bark: number) {
  const clamped = Math.max(-0.529, bark);
  return 1960 / (26.81 / (clamped + 0.53) - 1);
}

/** PySide integer-Bark mode: checkbox ON ⇒ both axes bark regardless of UI buttons. */
export function effectiveAxisScales(analysis: AnalysisUnitInput | null | undefined) {
  if (analysis?.use_bark_units) {
    return { f1_scale: "bark" as const, f2_scale: "bark" as const };
  }
  return {
    f1_scale: (analysis?.f1_scale ?? "linear") as string,
    f2_scale: (analysis?.f2_scale ?? "bark") as string,
  };
}

export type AxisRanges = { y_min: string; y_max: string; x_min: string; x_max: string };

/** Mirrors PlotConfigurationService.smart_ranges with PySide bark-mode coercion. */
export function smartAxisRanges(
  plotType: string,
  analysis: AnalysisUnitInput | null | undefined,
  hzDefaults: Record<string, AxisRanges>,
  barkDefaults: Record<string, AxisRanges>,
): AxisRanges {
  const hz = hzDefaults[plotType] ?? hzDefaults.f1_f2;
  const bark = barkDefaults[plotType] ?? barkDefaults.f1_f2;
  const useBark = Boolean(analysis?.use_bark_units);
  const { f1_scale, f2_scale } = effectiveAxisScales(analysis);
  return {
    y_min: f1_scale === "bark" && useBark ? bark.y_min : hz.y_min,
    y_max: f1_scale === "bark" && useBark ? bark.y_max : hz.y_max,
    x_min: f2_scale === "bark" && useBark ? bark.x_min : hz.x_min,
    x_max: f2_scale === "bark" && useBark ? bark.x_max : hz.x_max,
  };
}

export function resolvePlotUnits(analysis: AnalysisUnitInput | null | undefined): PlotUnitContext {
  const normalization = analysis?.normalization ? String(analysis.normalization) : null;
  const plotType = analysis?.type ?? "f1_f2";
  const useBarkUnits = Boolean(analysis?.use_bark_units);
  const { f2_scale: f2Scale } = effectiveAxisScales(analysis);

  if (normalization) {
    return {
      kind: "normalized",
      normalization,
      plotType,
      yAxisName: "nF1",
      xAxisName: X_AXIS_LABEL_NORMALIZED[plotType] ?? "nF2",
      rangeBadge: normalization === "Gerstman" ? "정규화" : normalization,
      formantStatSuffix: "",
      drawAxisUnits: "norm",
      rulerUnitChoiceEnabled: false,
      defaultRulerPreference: "hz",
    };
  }

  // Integer Bark display (PySide): both axes Bark. Otherwise Hz labels.
  if (useBarkUnits) {
    return {
      kind: "bark",
      normalization: null,
      plotType,
      yAxisName: "F1",
      xAxisName: X_AXIS_LABEL[plotType] ?? "F2",
      rangeBadge: "Bark",
      formantStatSuffix: " (Bark)",
      drawAxisUnits: "Bark",
      rulerUnitChoiceEnabled: true,
      defaultRulerPreference: "bark",
    };
  }

  return {
    kind: "hz",
    normalization: null,
    plotType,
    yAxisName: "F1",
    xAxisName: X_AXIS_LABEL[plotType] ?? "F2",
    rangeBadge: "Hz",
    formantStatSuffix: " (Hz)",
    drawAxisUnits: "Hz",
    rulerUnitChoiceEnabled: true,
    // Prefer Bark distance readout when F2 axis uses bark *scale* (PySide ruler).
    defaultRulerPreference: f2Scale === "bark" ? "bark" : "hz",
  };
}

export type RulerPointLike = {
  x: number;
  y: number;
  raw_f1?: number;
  raw_f2?: number;
};

/** Format a point tooltip like PySide RulerTool._draw_tooltip. */
export function formatRulerPointTooltip(point: RulerPointLike & { label?: string; type?: string }, units: PlotUnitContext) {
  const tag = point.label || (point.type === "mean" ? "mean" : "raw");
  if (units.kind === "normalized") {
    return `${tag} · ${units.yAxisName} ${point.y.toPrecision(4)} · ${units.xAxisName} ${point.x.toPrecision(4)}`;
  }
  if (point.raw_f1 === undefined || point.raw_f2 === undefined) {
    return `${tag} · x ${point.x.toPrecision(4)} · y ${point.y.toPrecision(4)}`;
  }
  if (units.kind === "bark") {
    const y = hzToBark(point.raw_f1);
    const x = hzToBark(point.raw_f2);
    return `${tag} · ${units.yAxisName} ${y.toFixed(2)} Bk · ${units.xAxisName} ${x.toFixed(2)} Bk`;
  }
  return `${tag} · ${units.yAxisName} ${point.raw_f1.toFixed(0)} Hz · ${units.xAxisName} ${point.raw_f2.toFixed(0)} Hz`;
}

/**
 * Distance label for the ruler overlay.
 * Normalized: Euclidean in plot space, no unit (PySide).
 * Otherwise: preferred unit; dual “Bk ≒ Hz” / “Hz ≒ Bk” for direct mode like PySide.
 */
export function formatRulerDistance(
  first: RulerPointLike,
  second: RulerPointLike,
  units: PlotUnitContext,
  options?: { preference?: "hz" | "bark"; geometry?: "direct" | "right-triangle" },
) {
  const geometry = options?.geometry ?? "direct";
  const preference = options?.preference ?? units.defaultRulerPreference;

  if (units.kind === "normalized") {
    const d = Math.hypot(second.x - first.x, second.y - first.y);
    return Number.isFinite(d) ? d.toPrecision(4) : "—";
  }

  const hasRaw =
    first.raw_f1 !== undefined
    && first.raw_f2 !== undefined
    && second.raw_f1 !== undefined
    && second.raw_f2 !== undefined;

  if (!hasRaw) {
    return Math.hypot(second.x - first.x, second.y - first.y).toPrecision(4);
  }

  const xHz = second.raw_f2! - first.raw_f2!;
  const yHz = second.raw_f1! - first.raw_f1!;
  const xBark = hzToBark(second.raw_f2!) - hzToBark(first.raw_f2!);
  const yBark = hzToBark(second.raw_f1!) - hzToBark(first.raw_f1!);
  const distHz = Math.hypot(xHz, yHz);
  const distBark = Math.hypot(xBark, yBark);

  if (geometry === "right-triangle") {
    return preference === "bark" ? `${distBark.toFixed(2)} Bk` : `${distHz.toFixed(0)} Hz`;
  }

  // PySide: f2_scale bark → Bark primary; else Hz primary — both shown.
  if (preference === "bark") return `${distBark.toFixed(2)} Bk ≒ ${distHz.toFixed(0)} Hz`;
  return `${distHz.toFixed(0)} Hz ≒ ${distBark.toFixed(2)} Bk`;
}

export function formatRulerTriangleLegs(
  first: RulerPointLike,
  second: RulerPointLike,
  units: PlotUnitContext,
  preference: "hz" | "bark" = units.defaultRulerPreference,
) {
  if (units.kind === "normalized") {
    const dx = second.x - first.x;
    const dy = second.y - first.y;
    const format = (value: number) => Math.abs(value).toPrecision(4);
    return { horizontal: format(dx), vertical: format(dy), hypotenuse: format(Math.hypot(dx, dy)) };
  }

  const hasRaw =
    first.raw_f1 !== undefined
    && first.raw_f2 !== undefined
    && second.raw_f1 !== undefined
    && second.raw_f2 !== undefined;

  if (!hasRaw) {
    const dx = second.x - first.x;
    const dy = second.y - first.y;
    const format = (value: number) => Math.abs(value).toPrecision(4);
    return { horizontal: format(dx), vertical: format(dy), hypotenuse: format(Math.hypot(dx, dy)) };
  }

  const useBark = preference === "bark";
  const x = useBark
    ? hzToBark(second.raw_f2!) - hzToBark(first.raw_f2!)
    : second.raw_f2! - first.raw_f2!;
  const y = useBark
    ? hzToBark(second.raw_f1!) - hzToBark(first.raw_f1!)
    : second.raw_f1! - first.raw_f1!;
  const unit = useBark ? "Bk" : "Hz";
  const digits = useBark ? 2 : 0;
  const format = (value: number) => `${Math.abs(value).toFixed(digits)} ${unit}`;
  return { horizontal: format(x), vertical: format(y), hypotenuse: format(Math.hypot(x, y)) };
}
