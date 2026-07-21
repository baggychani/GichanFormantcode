import { useCallback, useEffect, useRef, useState } from "react";
import {
  formatRulerDistance,
  formatRulerPointTooltip,
  formatRulerTriangleLegs,
  type PlotUnitContext,
} from "../../plotUnits";
import type {
  RulerContext,
  RulerDisplayMode,
  RulerGeometryMode,
  RulerMeasurement,
  RulerPoint,
  Tool,
} from "./types";

type UseRulerSessionParams = {
  plotUnits: PlotUnitContext;
  tool: Tool;
};

export function useRulerSession({ plotUnits, tool }: UseRulerSessionParams) {
  const [rulerSettingsOpen, setRulerSettingsOpen] = useState(false);
  const [rulerGeometryMode, setRulerGeometryMode] = useState<RulerGeometryMode>("direct");
  const [rulerDisplayMode, setRulerDisplayMode] = useState<RulerDisplayMode>("hz");
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
  const plotLabelFrameRef = useRef<number | null>(null);
  const plotLabelDragStartRef = useRef<{ x: number; y: number } | null>(null);
  const plotLabelHasMovedRef = useRef(false);

  const rulerTooltip = (point: RulerPoint) => formatRulerPointTooltip(point, plotUnits);

  const rulerDistanceLabelWithSettings = (first: RulerPoint, second: RulerPoint) =>
    formatRulerDistance(first, second, plotUnits, {
      preference: rulerDisplayMode,
      geometry: rulerGeometryMode,
    });

  const rulerTriangleLabels = (first: RulerPoint, second: RulerPoint) =>
    formatRulerTriangleLegs(first, second, plotUnits, rulerDisplayMode);

  const resetTransientRuler = useCallback(() => {
    setRulerStart(null);
    setRulerHover(null);
    setRulerPointer(null);
  }, []);

  const clearRulerOnPreviewReady = useCallback(() => {
    setPlotLabelPreviewVowel(null);
    setPlotLabelPointer(null);
    setRulerStart(null);
    setRulerHover(null);
    setRulerMeasurements([]);
  }, []);

  const clearRulerOnPreviewCleared = useCallback(() => {
    setRulerContext(null);
    setRulerStart(null);
    setRulerMeasurements([]);
  }, []);

  useEffect(() => () => {
    if (plotLabelFrameRef.current !== null) cancelAnimationFrame(plotLabelFrameRef.current);
    plotLabelFrameRef.current = null;
  }, []);

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

  return {
    rulerSettingsOpen,
    setRulerSettingsOpen,
    rulerGeometryMode,
    setRulerGeometryMode,
    rulerDisplayMode,
    setRulerDisplayMode,
    rulerContext,
    setRulerContext,
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
    resetTransientRuler,
    clearRulerOnPreviewReady,
    clearRulerOnPreviewCleared,
  };
}
