/** Interactive plot window domain types (extracted from InteractivePlotWindow). */

export type SidecarEvent = { event: string; payload: Record<string, unknown> };
export type Tool = "select" | "ruler" | "label" | "draw";
export type RulerPoint = {
  x: number;
  y: number;
  px: number;
  py: number;
  type: "raw" | "mean";
  label: string;
  color: string;
  raw_f1?: number;
  raw_f2?: number;
};
export type PlotLabel = {
  vowel: string;
  display_vowel?: string;
  cx: number;
  cy: number;
  lx: number;
  ly: number;
  px: number;
  py: number;
  lpx: number;
  lpy: number;
  bbox?: { left: number; top: number; width: number; height: number } | null;
  fontsize?: number;
  ha?: "left" | "center" | "right";
  va?: "bottom" | "center" | "top";
  lbl_color?: string;
  lbl_bold?: boolean | string;
  lbl_italic?: boolean;
};
/** 라벨 bbox와 동일 — PNG 상단 원점 픽셀 */
export type TextBounds = {
  x: number;
  y: number;
  left: number;
  top: number;
  width: number;
  height: number;
  apx: number;
  apy: number;
};
export type RulerContext = {
  image_width: number;
  image_height: number;
  axes_bbox: { left: number; bottom: number; width: number; height: number };
  points: RulerPoint[];
  labels: PlotLabel[];
  xlim: [number, number];
  ylim: [number, number];
  legend_bounds?: Record<string, { fx: number; fy: number; width_frac: number; height_frac: number }>;
  text_bounds?: Record<string, TextBounds>;
  params: {
    normalization?: string | null;
    use_bark_units?: boolean;
    f1_scale?: string;
    f2_scale?: string;
  };
};
export type RulerMeasurement = {
  p1: RulerPoint;
  p2: RulerPoint;
  labelX: number;
  labelY: number;
  distance: string;
};
export type RulerGeometryMode = "direct" | "right-triangle";
export type RulerDisplayMode = "hz" | "bark";
export type LeftPanel = "analysis" | "global-design";
export type RightPanel = "layers" | "drawing";
export type DrawTool = "text" | "line" | "area" | "reference" | "legend";
export type DrawArrowMode = "none" | "end" | "all";
export type DrawArrowHead = "stealth" | "open" | "latex";

export type LayerVisibility = "ON" | "SEMI" | "OFF";
export type Ranges = { y_min: string; y_max: string; x_min: string; x_max: string };
export type DesignSettings = {
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
export type LayerOverrides = Record<string, Partial<DesignSettings>>;
export type LayerSession = {
  state: Record<string, LayerVisibility>;
  overrides: LayerOverrides;
  locked: Set<string>;
  order: string[];
  expanded: Set<string>;
};

export type DrawPoint = { x: number; y: number; label?: string; px?: number; py?: number };
export type DrawLineObject = {
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
export type DrawLegendEntry = { series_id: number; text: string };
export type DrawLegendObject = {
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
export type DrawReferenceObject = {
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
export type DrawPolygonObject = {
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
export type DrawTextObject = {
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
export type DrawObject =
  | DrawLineObject
  | DrawLegendObject
  | DrawReferenceObject
  | DrawPolygonObject
  | DrawTextObject;
export type ReferencePreview = {
  mode: "horizontal" | "vertical";
  plotValue: number;
  label: string;
  snapped: boolean;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};
export type LegendDraft = Omit<DrawLegendObject, "type" | "id"> & { id: string };
export type DrawEditorMode = "defaults" | "layer";
export type DrawEditorKind = "line" | "legend" | "reference" | "polygon" | "text";
export type LineStyleDraft = {
  line_color: string;
  line_style: string;
  line_width: number;
  arrow_mode: DrawArrowMode;
  arrow_head: DrawArrowHead;
};
export type PolygonStyleDraft = {
  border_style: string;
  border_color: string;
  fill_color: string | null;
  fill_opacity: number;
};
export type ReferenceStyleDraft = {
  mode: "horizontal" | "vertical";
  line_style: string;
  line_color: string | null;
  valueLabel?: string;
};
export type TextStyleDraft = {
  text: string;
  font_size: number;
  font_family: string;
  font_weight: DesignSettings["font_weight"];
  font_italic: boolean;
  line_spacing: number;
  text_color: string;
};
export type TextInputState = {
  x: number;
  y: number;
  axis_units: string;
  draft: string;
};
export type LegendStyleDefaults = Pick<
  DrawLegendObject,
  | "name"
  | "font_size"
  | "font_family"
  | "font_weight"
  | "font_italic"
  | "show_border"
  | "border_style"
  | "border_color"
  | "show_fill"
  | "fill_color"
  | "fill_opacity"
>;
export type DrawHoverState = {
  point: DrawPoint;
  clientX: number;
  clientY: number;
  snapped: boolean;
  rulerPoint: RulerPoint | null;
};
export type VowelAnalysisPage = "home" | "formant" | "distance" | "pillai";
export type VowelAnalysisSection = "core" | "mahalanobis" | "pillai";
export type VowelAnalysisResult = {
  index: number;
  name: string;
  x_label?: string;
  y_label?: string;
  normalization?: string | null;
  statistics: Record<
    string,
    {
      x_mean: number;
      x_std: number;
      x_min: number;
      x_max: number;
      y_mean: number;
      y_std: number;
      y_min: number;
      y_max: number;
      count: number;
    }
  >;
  centroid_distances: Record<string, { distance_to_centroid: number }>;
  pairwise_euclidean: Record<string, number>;
  pairwise_mahalanobis: Record<string, number>;
  pillai_scores: Record<string, { score: number | null; p_value: number | null }>;
  metadata: { total_points?: number; vowel_count?: number };
  sections?: string[];
};
