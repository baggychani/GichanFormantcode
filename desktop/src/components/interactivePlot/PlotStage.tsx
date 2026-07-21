import { useEffect, useRef, useState } from "react";
import type { Dispatch, MutableRefObject, PointerEvent as ReactPointerEvent, SetStateAction } from "react";
import {
  Layers3,
  Loader2,
  MousePointer2,
  PanelLeftOpen,
  PanelRightOpen,
  PenLine,
  Ruler,
  SlidersHorizontal,
} from "lucide-react";
import { barkToHz, hzToBark, type PlotUnitContext } from "../../plotUnits";
import {
  axisPreviewFontFamily,
  fontFamilyStyle,
} from "./designDefaults";
import {
  clampDrawLineWidth,
  clampDrawTextFontSize,
  clampDrawTextLineSpacing,
  DRAW_LINE_DEFAULT_COLOR,
  DRAW_TEXT_DEFAULT_COLOR,
  DRAW_TEXT_DEFAULT_FAMILY,
  DRAW_TEXT_DEFAULT_LINE_SPACING,
  formatRefLabel,
  roundRefValue,
} from "./drawDefaults";
import * as plotGeometry from "./plotGeometry";
import type { InteractiveRenderOverrides } from "./usePlotRender";
import type {
  DesignSettings,
  DrawHoverState,
  DrawLegendObject,
  DrawObject,
  DrawPoint,
  DrawReferenceObject,
  DrawTextObject,
  DrawTool,
  LayerOverrides,
  PlotLabel,
  ReferencePreview,
  RulerContext,
  RulerDisplayMode,
  RulerGeometryMode,
  RulerMeasurement,
  RulerPoint,
  Tool,
} from "./types";

export type PlotStageProps = {
  previewUrl: string | null;
  previewLoading: boolean;
  previewInfo: string;
  message: string;
  currentSourceName: string | undefined;
  currentIndex: number;
  tool: Tool;
  setTool: Dispatch<SetStateAction<Tool>>;
  setMessage: (message: string) => void;
  leftOpen: boolean;
  setLeftOpen: Dispatch<SetStateAction<boolean>>;
  rightOpen: boolean;
  setRightOpen: Dispatch<SetStateAction<boolean>>;
  enterDrawMode: (tool: DrawTool | null) => void;
  design: DesignSettings;
  layerOverrides: LayerOverrides;
  analysisNormalization: string | null | undefined;
  analysisF1Scale: string | null | undefined;
  analysisF2Scale: string | null | undefined;
  analysisOrigin: string | null | undefined;
  plotUnits: PlotUnitContext;
  drawIdRef: MutableRefObject<number>;
  resetCanvasDrawPreviewRef: MutableRefObject<() => void>;
  clearLegendDragPreviewRef: MutableRefObject<() => void>;
  renderInteractive: (overrides?: InteractiveRenderOverrides) => void | Promise<void>;
  drawTool: DrawTool | null;
  drawingPoints: DrawPoint[];
  setDrawingPoints: Dispatch<SetStateAction<DrawPoint[]>>;
  drawHover: DrawHoverState | null;
  setDrawHover: Dispatch<SetStateAction<DrawHoverState | null>>;
  currentDrawObjects: DrawObject[];
  currentLegend: DrawLegendObject | null;
  persistDrawObjects: (objects: DrawObject[]) => void;
  focusDrawObject: (id: string) => void;
  finishDrawLine: (points: DrawPoint[]) => void;
  finishDrawPolygon: (points: DrawPoint[]) => void;
  beginTextInput: (seed: { x: number; y: number; axis_units: string }) => void;
  referenceMode: "horizontal" | "vertical";
  drawRefStyle: string;
  drawRefColor: string | null;
  drawColor: string | null;
  drawWidth: number;
  drawPolyBorderColor: string;
  drawPolyFillColor: string | null;
  drawPolyFillOpacity: number;
  rulerSettingsOpen: boolean;
  setRulerSettingsOpen: Dispatch<SetStateAction<boolean>>;
  rulerGeometryMode: RulerGeometryMode;
  setRulerGeometryMode: Dispatch<SetStateAction<RulerGeometryMode>>;
  rulerDisplayMode: RulerDisplayMode;
  setRulerDisplayMode: Dispatch<SetStateAction<RulerDisplayMode>>;
  rulerContext: RulerContext | null;
  rulerStart: RulerPoint | null;
  setRulerStart: Dispatch<SetStateAction<RulerPoint | null>>;
  rulerHover: RulerPoint | null;
  setRulerHover: Dispatch<SetStateAction<RulerPoint | null>>;
  rulerPointer: { x: number; y: number } | null;
  setRulerPointer: Dispatch<SetStateAction<{ x: number; y: number } | null>>;
  rulerMeasurements: RulerMeasurement[];
  setRulerMeasurements: Dispatch<SetStateAction<RulerMeasurement[]>>;
  draggingRulerLabel: number | null;
  setDraggingRulerLabel: Dispatch<SetStateAction<number | null>>;
  draggingPlotLabel: string | null;
  setDraggingPlotLabel: Dispatch<SetStateAction<string | null>>;
  hoveredPlotLabel: string | null;
  setHoveredPlotLabel: Dispatch<SetStateAction<string | null>>;
  plotLabelPointer: { x: number; y: number } | null;
  setPlotLabelPointer: Dispatch<SetStateAction<{ x: number; y: number } | null>>;
  plotLabelPreviewVowel: string | null;
  setPlotLabelPreviewVowel: Dispatch<SetStateAction<string | null>>;
  plotLabelFrameRef: MutableRefObject<number | null>;
  plotLabelDragStartRef: MutableRefObject<{ x: number; y: number } | null>;
  plotLabelHasMovedRef: MutableRefObject<boolean>;
  rulerTooltip: (point: RulerPoint) => string;
  rulerDistanceLabelWithSettings: (p1: RulerPoint, p2: RulerPoint) => string;
  rulerTriangleLabels: (p1: RulerPoint, p2: RulerPoint) => { horizontal: string; vertical: string; hypotenuse: string };
};

export function PlotStage({
  previewUrl,
  previewLoading,
  previewInfo,
  message,
  currentSourceName,
  currentIndex,
  tool,
  setTool,
  setMessage,
  leftOpen,
  setLeftOpen,
  rightOpen,
  setRightOpen,
  enterDrawMode,
  design,
  layerOverrides,
  analysisNormalization,
  analysisF1Scale,
  analysisF2Scale,
  analysisOrigin,
  plotUnits,
  drawIdRef,
  resetCanvasDrawPreviewRef,
  clearLegendDragPreviewRef,
  renderInteractive,
  drawTool,
  drawingPoints,
  setDrawingPoints,
  drawHover,
  setDrawHover,
  currentDrawObjects,
  currentLegend,
  persistDrawObjects,
  focusDrawObject,
  finishDrawLine,
  finishDrawPolygon,
  beginTextInput,
  referenceMode,
  drawRefStyle,
  drawRefColor,
  drawColor,
  drawWidth,
  drawPolyBorderColor,
  drawPolyFillColor,
  drawPolyFillOpacity,
  rulerSettingsOpen,
  setRulerSettingsOpen,
  rulerGeometryMode,
  setRulerGeometryMode,
  rulerDisplayMode,
  setRulerDisplayMode,
  rulerContext,
  rulerStart,
  setRulerStart,
  rulerHover,
  setRulerHover,
  rulerPointer,
  setRulerPointer,
  rulerMeasurements,
  setRulerMeasurements,
  draggingRulerLabel,
  setDraggingRulerLabel,
  draggingPlotLabel,
  setDraggingPlotLabel,
  hoveredPlotLabel,
  setHoveredPlotLabel,
  plotLabelPointer,
  setPlotLabelPointer,
  plotLabelPreviewVowel,
  setPlotLabelPreviewVowel,
  plotLabelFrameRef,
  plotLabelDragStartRef,
  plotLabelHasMovedRef,
  rulerTooltip,
  rulerDistanceLabelWithSettings,
  rulerTriangleLabels,
}: PlotStageProps) {
  const [draggingTextId, setDraggingTextId] = useState<string | null>(null);
  const [hoveredDrawTextId, setHoveredDrawTextId] = useState<string | null>(null);
  const [textDragPointer, setTextDragPointer] = useState<{ x: number; y: number } | null>(null);
  const textDragRef = useRef<{ id: string; offsetX: number; offsetY: number } | null>(null);
  const textDragFrameRef = useRef<number | null>(null);
  const textHasMovedRef = useRef(false);
  const [draggingLegend, setDraggingLegend] = useState(false);
  const [legendDragPreview, setLegendDragPreview] = useState<Pick<DrawLegendObject, "fx" | "fy" | "width_frac" | "height_frac"> | null>(null);
  const [referencePreview, setReferencePreview] = useState<ReferencePreview | null>(null);
  const plotPaperRef = useRef<HTMLDivElement | null>(null);
  const plotImageRef = useRef<HTMLImageElement | null>(null);
  const legendDragRef = useRef<{ startX: number; startY: number; fx: number; fy: number } | null>(null);
  const legendFrameRef = useRef<number | null>(null);
  const referencePointerRef = useRef<ReferencePreview | null>(null);
  const referenceMoveRef = useRef<(clientX: number, clientY: number) => void>(() => {});
  const lineMoveRef = useRef<(clientX: number, clientY: number) => void>(() => {});
  const areaMoveRef = useRef<(clientX: number, clientY: number) => void>(() => {});
  const legendPointerRef = useRef<Pick<DrawLegendObject, "fx" | "fy" | "width_frac" | "height_frac"> | null>(null);

  useEffect(() => () => {
    if (textDragFrameRef.current !== null) cancelAnimationFrame(textDragFrameRef.current);
    if (legendFrameRef.current !== null) cancelAnimationFrame(legendFrameRef.current);
    textDragFrameRef.current = null;
    legendFrameRef.current = null;
  }, []);

  resetCanvasDrawPreviewRef.current = () => {
    referencePointerRef.current = null;
    setReferencePreview(null);
  };
  clearLegendDragPreviewRef.current = () => {
    setLegendDragPreview(null);
  };

  const rulerImageGeometry = () => {
    const image = plotImageRef.current;
    if (!image) return null;
    // PNG 픽셀 공간과 ruler_context(axes_bbox)를 반드시 같은 기준으로 맞춤
    const srcW = rulerContext?.image_width || image.naturalWidth;
    const srcH = rulerContext?.image_height || image.naturalHeight;
    return plotGeometry.computeImageGeometry(image.getBoundingClientRect(), srcW, srcH);
  };

  const legendClientRect = (legend: DrawLegendObject, useMeasured = true) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.legendClientRect(geometry, rulerContext, legend, useMeasured);
  };

  const defaultLegendClientRect = (legend: DrawLegendObject) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.defaultLegendClientRect(geometry, rulerContext, legend);
  };

  const legendFromPointer = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext || !legendDragRef.current) return null;
    const legend = currentLegend;
    if (!legend) return null;
    return plotGeometry.legendFromPointer(geometry, rulerContext, legend, legendDragRef.current, clientX, clientY);
  };

  const rulerPointClient = (point: RulerPoint) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.rulerPointClient(geometry, rulerContext, point);
  };

  const plotLabelClient = (label: PlotLabel) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.plotLabelClient(geometry, rulerContext, label);
  };

  const plotLabelBoxClient = (label: PlotLabel) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !label.bbox) return null;
    return plotGeometry.plotLabelBoxClient(geometry, label);
  };

  const plotDataFromClient = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.plotDataFromClient(geometry, rulerContext, clientX, clientY);
  };

  /** PySide event.inaxes — 축 안 더블클릭만 텍스트 배치 */
  const plotDataInAxesFromClient = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.plotDataInAxesFromClient(geometry, rulerContext, clientX, clientY);
  };

  /** 라벨 plotLabelClient / plotLabelBoxClient 와 동일 좌표계 */
  const drawTextAnchorClient = (object: DrawTextObject) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.drawTextAnchorClient(geometry, rulerContext, object);
  };

  const drawTextBoxClient = (object: DrawTextObject) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.drawTextBoxClient(geometry, rulerContext, object);
  };

  const hitDrawTextAt = (clientX: number, clientY: number): DrawTextObject | null => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.hitDrawTextAt(geometry, rulerContext, currentDrawObjects, clientX, clientY);
  };

  const openTextInputAt = (clientX: number, clientY: number) => {
    if (hitDrawTextAt(clientX, clientY)) return;
    const data = plotDataInAxesFromClient(clientX, clientY);
    if (!data) {
      setMessage("축 영역 안에서 더블클릭하세요.");
      return;
    }
    beginTextInput({
      x: data.x,
      y: data.y,
      axis_units: plotUnits.drawAxisUnits,
    });
  };

  const nearestPlotLabel = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.nearestPlotLabel(geometry, rulerContext, clientX, clientY);
  };

  const nearestRulerPoint = (clientX: number, clientY: number) => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.nearestRulerPoint(geometry, rulerContext, clientX, clientY);
  };

  /** 호버용: 스냅 우선(transData px/py 포함), 없으면 커서 data(가이드만). 클릭은 스냅만. */
  const drawHoverAtClient = (clientX: number, clientY: number): DrawHoverState | null => {
    const geometry = rulerImageGeometry();
    if (!geometry || !rulerContext) return null;
    return plotGeometry.drawHoverAtClient(geometry, rulerContext, clientX, clientY);
  };

  const rulerLocalPoint = (clientX: number, clientY: number) => {
    const box = plotPaperRef.current?.getBoundingClientRect();
    return box ? plotGeometry.clientToLocal(clientX, clientY, box) : null;
  };

  /** 축 bbox를 paper-local 픽셀로 — 프리뷰 선 끝점은 항상 여기서 잡음 (PySide ax.get_xlim/ylim 대응) */
  const axesRectLocal = () => {
    const geometry = rulerImageGeometry();
    const paper = plotPaperRef.current?.getBoundingClientRect();
    if (!geometry || !paper || !rulerContext) return null;
    return plotGeometry.axesRectLocal(geometry, paper, rulerContext);
  };

  const referenceAxesSpan = (paperWidth: number, paperHeight: number) => {
    const axes = axesRectLocal();
    return plotGeometry.referenceAxesSpan(axes, paperWidth, paperHeight);
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
    if (!rulerContext || !axes) return null;
    return plotGeometry.referenceLineFromPlotValue(rulerContext, axes, span, plotValue, horizontal);
  };

  const resolveReferencePlacement = (clientX: number, clientY: number): { object: DrawReferenceObject; preview: ReferencePreview } | null => {
    const data = plotDataFromClient(clientX, clientY);
    if (!data || !rulerContext) return null;
    const normalization = analysisNormalization ?? rulerContext.params.normalization ?? null;
    const horizontal = referenceMode === "horizontal";
    const scale = normalization
      ? "linear"
      : horizontal
        ? (analysisF1Scale ?? rulerContext.params.f1_scale ?? "linear")
        : (analysisF2Scale ?? rulerContext.params.f2_scale ?? "linear");
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

  /** paper-local. 스냅 점은 px/py(transData) 우선 — 선형 drawPointClient는 마커와 어긋남. */
  const drawPointLocal = (point: DrawPoint) => {
    const paper = plotPaperRef.current?.getBoundingClientRect();
    if (!paper) return null;
    const geometry = rulerImageGeometry();
    if (!geometry) return null;
    return plotGeometry.drawPointLocal(geometry, paper, rulerContext, point);
  };

  return (
          <section className={`interactive-plot-stage tool-${tool}${tool === "draw" ? ` draw-tool-${drawTool ?? "none"}` : ""}`}>
        <div className="plot-toolbar"><div className="toolbar-leading">{!leftOpen ? <button className="sidebar-reopen" onClick={() => setLeftOpen(true)}><PanelLeftOpen size={16} /> 도구</button> : null}<div className="toolbar-group"><button className={tool === "select" ? "is-active" : ""} onClick={() => setTool("select")}><MousePointer2 size={16} /> 선택</button><div className="ruler-tool-cluster"><button className={tool === "ruler" ? "is-active" : ""} onClick={() => setTool("ruler")}><Ruler size={16} /> 눈금자</button><button type="button" className={`tool-settings-button ${rulerSettingsOpen ? "is-active" : ""}`} onClick={() => setRulerSettingsOpen((previous) => !previous)} aria-label="눈금자 설정" title="눈금자 설정"><SlidersHorizontal size={14} /></button>{rulerSettingsOpen ? <div className="ruler-settings-popover"><div className="ruler-settings-header"><strong>눈금자 설정</strong><span>측정 방식</span></div><div className="ruler-mode-choices"><button type="button" className={`ruler-mode-choice ${rulerGeometryMode === "direct" ? "is-active" : ""}`} onClick={() => setRulerGeometryMode("direct")}><svg viewBox="0 0 44 22" aria-hidden><line x1="5" y1="17" x2="39" y2="5" /><circle cx="5" cy="17" r="2" /><circle cx="39" cy="5" r="2" /></svg><span>직선</span></button><button type="button" className={`ruler-mode-choice ${rulerGeometryMode === "right-triangle" ? "is-active" : ""}`} onClick={() => setRulerGeometryMode("right-triangle")}><svg viewBox="0 0 44 22" aria-hidden><path d="M5 17H39V5" /><line className="hypotenuse" x1="5" y1="17" x2="39" y2="5" /><path className="right-angle" d="M34 17v-5h5" /></svg><span>Δx · Δy</span></button></div><div className="ruler-unit-row"><span>표시 단위</span>{plotUnits.rulerUnitChoiceEnabled ? <div className="ruler-unit-toggles"><button type="button" className={`ruler-unit-toggle ${rulerDisplayMode === "hz" ? "is-on" : ""}`} aria-pressed={rulerDisplayMode === "hz"} onClick={() => setRulerDisplayMode("hz")}>Hz</button><button type="button" className={`ruler-unit-toggle ${rulerDisplayMode === "bark" ? "is-on" : ""}`} aria-pressed={rulerDisplayMode === "bark"} onClick={() => setRulerDisplayMode("bark")}>Bark</button></div> : <strong className="ruler-unit-locked">{plotUnits.normalization ?? "정규화 좌표"}</strong>}</div></div> : null}</div><button className={tool === "label" ? "is-active" : ""} onClick={() => { setTool("label"); setMessage("라벨 이동 모드 · 라벨을 드래그하세요."); }}><MousePointer2 size={16} /> 라벨 이동</button><button className={tool === "draw" ? "is-active" : ""} onClick={() => enterDrawMode(null)}><PenLine size={16} /> 그리기</button></div></div><div className="toolbar-context"><span>{analysisNormalization ?? "정규화 없음"}</span><span>{analysisOrigin === "top_right" ? "Praat 좌표" : "수학 좌표"}</span>{!rightOpen ? <button className="sidebar-reopen" onClick={() => setRightOpen(true)}>레이어 <PanelRightOpen size={16} /></button> : null}</div></div>
        <div className="plot-canvas-shell"><div className="plot-paper" ref={plotPaperRef}>{previewUrl ? <><img ref={plotImageRef} src={previewUrl} alt={`${currentSourceName ?? "현재 파일"} 포먼트 플롯`} draggable={false} onLoad={() => { if (referencePointerRef.current) setReferencePreview({ ...referencePointerRef.current }); }} /><div className="ruler-overlay" onPointerMove={handleRulerMove} onPointerDown={handleRulerDown} onPointerUp={handleRulerUp} onPointerCancel={handleRulerUp} onDoubleClick={(event) => {
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
        <footer className="plot-stage-footer"><span>{message}</span><span title={previewInfo}>{previewInfo || currentSourceName || "대기 중"}</span></footer>
      </section>
  );
}
