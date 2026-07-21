import type {
  DrawHoverState,
  DrawLegendObject,
  DrawObject,
  DrawPoint,
  DrawTextObject,
  PlotLabel,
  RulerContext,
  RulerPoint,
} from "./types";

/** Displayed PNG layout in client (viewport) coordinates. */
export type ImageGeometry = {
  left: number;
  top: number;
  scale: number;
  srcW: number;
  srcH: number;
};

export type ClientRect = { left: number; top: number; width: number; height: number };
export type ClientPoint = { x: number; y: number };
export type LocalRect = { left: number; top: number; width: number; height: number };
export type LocalLine = { x1: number; y1: number; x2: number; y2: number };

/** Map natural/context PNG size into the image element's letterboxed client box. */
export function computeImageGeometry(
  imageRect: ClientRect,
  srcW: number,
  srcH: number,
): ImageGeometry | null {
  if (!srcW || !srcH) return null;
  const scale = Math.min(imageRect.width / srcW, imageRect.height / srcH);
  const width = srcW * scale;
  const height = srcH * scale;
  return {
    left: imageRect.left + (imageRect.width - width) / 2,
    top: imageRect.top + (imageRect.height - height) / 2,
    scale,
    srcW,
    srcH,
  };
}

export function legendClientRect(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  legend: DrawLegendObject,
  useMeasured = true,
): ClientRect | null {
  const measured = useMeasured ? rulerContext.legend_bounds?.[legend.id] : undefined;
  const bounds = measured ? { ...legend, ...measured } : legend;
  return {
    left: geometry.left + bounds.fx * rulerContext.image_width * geometry.scale,
    top: geometry.top + (1 - bounds.fy) * rulerContext.image_height * geometry.scale,
    width: bounds.width_frac * rulerContext.image_width * geometry.scale,
    height: bounds.height_frac * rulerContext.image_height * geometry.scale,
  };
}

export function defaultLegendClientRect(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  legend: DrawLegendObject,
): ClientRect | null {
  return legendClientRect(
    geometry,
    rulerContext,
    { ...legend, fx: 0.035, fy: Math.min(0.205, 1 - legend.height_frac - 0.016) },
    false,
  );
}

export function legendFromPointer(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  legend: DrawLegendObject,
  dragStart: { startX: number; startY: number; fx: number; fy: number },
  clientX: number,
  clientY: number,
): DrawLegendObject | null {
  const dx = (clientX - dragStart.startX) / Math.max(1, rulerContext.image_width * geometry.scale);
  const dy = (clientY - dragStart.startY) / Math.max(1, rulerContext.image_height * geometry.scale);
  const measured = rulerContext.legend_bounds?.[legend.id];
  const base = measured ? { ...legend, ...measured } : legend;
  const margin = 0.016;
  return {
    ...base,
    fx: Math.max(margin, Math.min(1 - base.width_frac - margin, dragStart.fx + dx)),
    fy: Math.max(base.height_frac + margin, Math.min(1 - margin, dragStart.fy - dy)),
  };
}

export function rulerPointClient(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  point: RulerPoint,
): ClientPoint {
  return {
    x: geometry.left + point.px * geometry.scale,
    y: geometry.top + (rulerContext.image_height - point.py) * geometry.scale,
  };
}

export function plotLabelClient(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  label: PlotLabel,
): ClientPoint {
  return {
    x: geometry.left + label.lpx * geometry.scale,
    y: geometry.top + (rulerContext.image_height - label.lpy) * geometry.scale,
  };
}

export function plotLabelBoxClient(
  geometry: ImageGeometry,
  label: PlotLabel,
): ClientRect | null {
  if (!label.bbox) return null;
  return {
    left: geometry.left + label.bbox.left * geometry.scale,
    top: geometry.top + label.bbox.top * geometry.scale,
    width: label.bbox.width * geometry.scale,
    height: label.bbox.height * geometry.scale,
  };
}

export function plotDataFromClient(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  clientX: number,
  clientY: number,
): { x: number; y: number; px: number; py: number } | null {
  const imgH = rulerContext.image_height || geometry.srcH;
  const px = (clientX - geometry.left) / geometry.scale;
  const py = imgH - (clientY - geometry.top) / geometry.scale;
  const box = rulerContext.axes_bbox;
  if (box.width <= 0 || box.height <= 0) return null;
  const x = rulerContext.xlim[0] + ((px - box.left) / box.width) * (rulerContext.xlim[1] - rulerContext.xlim[0]);
  const y = rulerContext.ylim[0] + ((py - box.bottom) / box.height) * (rulerContext.ylim[1] - rulerContext.ylim[0]);
  return { x, y, px, py };
}

/** PySide event.inaxes — 축 안 좌표만. */
export function plotDataInAxesFromClient(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  clientX: number,
  clientY: number,
): { x: number; y: number; px: number; py: number } | null {
  const data = plotDataFromClient(geometry, rulerContext, clientX, clientY);
  if (!data) return null;
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
}

/** 라벨 plotLabelClient / plotLabelBoxClient 와 동일 좌표계. */
export function drawTextAnchorClient(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  object: DrawTextObject,
): ClientPoint | null {
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
}

export function drawTextBoxClient(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  object: DrawTextObject,
): ClientRect | null {
  const bounds = rulerContext.text_bounds?.[object.id];
  if (!bounds) return null;
  return {
    left: geometry.left + bounds.left * geometry.scale,
    top: geometry.top + bounds.top * geometry.scale,
    width: Math.max(8, bounds.width * geometry.scale),
    height: Math.max(8, bounds.height * geometry.scale),
  };
}

export function hitDrawTextAt(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  objects: DrawObject[],
  clientX: number,
  clientY: number,
): DrawTextObject | null {
  for (const object of objects) {
    if (object.type !== "text" || !object.visible) continue;
    const box = drawTextBoxClient(geometry, rulerContext, object);
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
}

export function nearestPlotLabel(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  clientX: number,
  clientY: number,
): PlotLabel | null {
  let nearest: PlotLabel | null = null;
  let best = 28 * 28;
  for (const label of rulerContext.labels) {
    const box = plotLabelBoxClient(geometry, label);
    if (
      box
      && clientX >= box.left - 8
      && clientX <= box.left + box.width + 8
      && clientY >= box.top - 8
      && clientY <= box.top + box.height + 8
    ) {
      return label;
    }
    const screen = plotLabelClient(geometry, rulerContext, label);
    const distance = (screen.x - clientX) ** 2 + (screen.y - clientY) ** 2;
    if (distance <= best) {
      best = distance;
      nearest = label;
    }
  }
  return nearest;
}

export function nearestRulerPoint(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  clientX: number,
  clientY: number,
): RulerPoint | null {
  let nearest: RulerPoint | null = null;
  let best = 20 * 20;
  for (const point of rulerContext.points) {
    const screen = rulerPointClient(geometry, rulerContext, point);
    const distance = (screen.x - clientX) ** 2 + (screen.y - clientY) ** 2;
    if (distance <= best) {
      best = distance;
      nearest = point;
    }
  }
  return nearest;
}

/** data → client (선 그리기·스냅용). */
export function drawPointClient(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  point: DrawPoint,
): ClientPoint | null {
  const box = rulerContext.axes_bbox;
  if (box.width <= 0 || box.height <= 0) return null;
  const xRatio = (point.x - rulerContext.xlim[0]) / Math.max(1e-9, rulerContext.xlim[1] - rulerContext.xlim[0]);
  const yRatio = (point.y - rulerContext.ylim[0]) / Math.max(1e-9, rulerContext.ylim[1] - rulerContext.ylim[0]);
  const px = box.left + xRatio * box.width;
  const py = box.bottom + yRatio * box.height;
  const imgH = rulerContext.image_height || geometry.srcH;
  return { x: geometry.left + px * geometry.scale, y: geometry.top + (imgH - py) * geometry.scale };
}

/** 호버용: 스냅 우선, 없으면 커서 data. */
export function drawHoverAtClient(
  geometry: ImageGeometry,
  rulerContext: RulerContext,
  clientX: number,
  clientY: number,
): DrawHoverState | null {
  const snapped = nearestRulerPoint(geometry, rulerContext, clientX, clientY);
  if (snapped) {
    return {
      point: { x: snapped.x, y: snapped.y, label: snapped.label, px: snapped.px, py: snapped.py },
      clientX,
      clientY,
      snapped: true,
      rulerPoint: snapped,
    };
  }
  const data = plotDataFromClient(geometry, rulerContext, clientX, clientY);
  if (!data) return null;
  return { point: { x: data.x, y: data.y }, clientX, clientY, snapped: false, rulerPoint: null };
}

export function clientToLocal(
  clientX: number,
  clientY: number,
  paper: ClientRect,
): ClientPoint {
  return { x: clientX - paper.left, y: clientY - paper.top };
}

/** 축 bbox를 paper-local 픽셀로. */
export function axesRectLocal(
  geometry: ImageGeometry,
  paper: ClientRect,
  rulerContext: RulerContext,
): LocalRect {
  const box = rulerContext.axes_bbox;
  const imgH = rulerContext.image_height || geometry.srcH;
  const left = geometry.left - paper.left + box.left * geometry.scale;
  const top = geometry.top - paper.top + (imgH - (box.bottom + box.height)) * geometry.scale;
  return { left, top, width: box.width * geometry.scale, height: box.height * geometry.scale };
}

export function referenceAxesSpan(
  axes: LocalRect | null,
  paperWidth: number,
  paperHeight: number,
): { x1: number; x2: number; y1: number; y2: number } {
  const x1 = axes && axes.width > 8 ? axes.left : 4;
  const x2 = axes && axes.width > 8 ? axes.left + axes.width : paperWidth - 4;
  const y1 = axes && axes.height > 8 ? axes.top : 4;
  const y2 = axes && axes.height > 8 ? axes.top + axes.height : paperHeight - 4;
  return { x1, x2, y1, y2 };
}

/**
 * plotValue(축 data) → paper-local 선.
 * ylim/xlim에 가까우면 축 박스 안으로 clamp. 멀리 벗어나면 null.
 */
export function referenceLineFromPlotValue(
  rulerContext: RulerContext,
  axes: LocalRect,
  span: { x1: number; x2: number; y1: number; y2: number },
  plotValue: number,
  horizontal: boolean,
): LocalLine | null {
  if (axes.width <= 8 || axes.height <= 8) return null;
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
}

/** paper-local. 스냅 점은 px/py(transData) 우선. */
export function drawPointLocal(
  geometry: ImageGeometry,
  paper: ClientRect,
  rulerContext: RulerContext | null,
  point: DrawPoint,
): ClientPoint | null {
  if (Number.isFinite(point.px) && Number.isFinite(point.py) && rulerContext) {
    const imgH = rulerContext.image_height || geometry.srcH;
    return {
      x: geometry.left - paper.left + (point.px as number) * geometry.scale,
      y: geometry.top - paper.top + (imgH - (point.py as number)) * geometry.scale,
    };
  }
  if (!rulerContext) return null;
  const screen = drawPointClient(geometry, rulerContext, point);
  return screen ? { x: screen.x - paper.left, y: screen.y - paper.top } : null;
}
