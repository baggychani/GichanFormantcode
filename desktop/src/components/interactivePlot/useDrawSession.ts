import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent } from "react";
import { normalizedFontWeight } from "./designDefaults";
import {
  clampDrawLineWidth,
  clampDrawTextFontSize,
  clampDrawTextLineSpacing,
  DRAW_LINE_DEFAULT_COLOR,
  DRAW_LINE_DEFAULT_WIDTH,
  DRAW_POLYGON_DEFAULT_BORDER,
  DRAW_POLYGON_DEFAULT_FILL,
  DRAW_TEXT_DEFAULT_COLOR,
  DRAW_TEXT_DEFAULT_FAMILY,
  DRAW_TEXT_DEFAULT_LINE_SPACING,
  DRAW_TEXT_DEFAULT_SIZE,
  formatRefLabel,
} from "./drawDefaults";
import type {
  DesignSettings,
  DrawArrowHead,
  DrawArrowMode,
  DrawEditorKind,
  DrawEditorMode,
  DrawHoverState,
  DrawLegendObject,
  DrawLineObject,
  DrawObject,
  DrawPoint,
  DrawPolygonObject,
  DrawTextObject,
  DrawTool,
  LegendDraft,
  LegendStyleDefaults,
  LineStyleDraft,
  PolygonStyleDraft,
  ReferenceStyleDraft,
  RightPanel,
  TextInputState,
  TextStyleDraft,
  Tool,
} from "./types";
import type { InteractiveRenderOverrides } from "./usePlotRender";

type UseDrawSessionParams = {
  currentIndex: number;
  currentSourceName: string | undefined;
  normalization: string | null;
  tool: Tool;
  setMessage: (message: string) => void;
  showToast: (message: string) => void;
  setTool: (tool: Tool | ((previous: Tool) => Tool)) => void;
  setRightPanel: (panel: RightPanel) => void;
  setRightOpen: (open: boolean) => void;
  renderInteractive: (overrides?: InteractiveRenderOverrides) => void | Promise<void>;
  /** Parent clears canvas referencePreview / referencePointerRef. */
  onResetCanvasDrawPreview?: () => void;
};

export function useDrawSession({
  currentIndex,
  currentSourceName,
  normalization,
  tool,
  setMessage,
  showToast,
  setTool,
  setRightPanel,
  setRightOpen,
  renderInteractive,
  onResetCanvasDrawPreview,
}: UseDrawSessionParams) {
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
  const [referenceMode, setReferenceMode] = useState<"horizontal" | "vertical">("horizontal");
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
  const drawIdRef = useRef(0);
  const drawObjectDragRef = useRef<{ id: string; ids: string[]; startY: number; moved: boolean } | null>(null);

  const currentDrawObjects = drawObjectsByFile[currentIndex] ?? [];
  const currentDrawLines = currentDrawObjects.filter((object): object is DrawLineObject => object.type === "line");
  const currentLegend = currentDrawObjects.find((object): object is DrawLegendObject => object.type === "legend") ?? null;
  const drawObjectsTopFirst = useMemo(
    () => [...currentDrawObjects].reverse(),
    [currentDrawObjects],
  );

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
    setSelectedDrawObjectId(null);
    setSelectedDrawObjectIds(new Set());
    drawSelectionAnchorRef.current = "";
  }, [currentIndex]);

  const resetTransientDraw = useCallback(() => {
    setDrawingPoints([]);
    setDrawHover(null);
  }, []);

  const clearDrawSelection = useCallback(() => {
    setSelectedDrawObjectId(null);
    setSelectedDrawObjectIds(new Set());
    drawSelectionAnchorRef.current = "";
  }, []);

  const hydrateDrawObjectsForFile = useCallback(({
    index,
    sessionDrawObjects,
  }: {
    index: number;
    sessionDrawObjects: DrawObject[] | undefined;
  }) => {
    if (sessionDrawObjects) {
      setDrawObjectsByFile((previous) => ({ ...previous, [index]: sessionDrawObjects }));
    }
    setDrawingPoints([]);
    setDrawHover(null);
  }, []);

  const applyLegendBounds = useCallback((legendBounds: Record<string, { width_frac: number; height_frac: number }>) => {
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
  }, []);

  const beginTextInput = useCallback(({
    x,
    y,
    axis_units,
  }: {
    x: number;
    y: number;
    axis_units: string;
  }) => {
    setTextInput({ x, y, axis_units, draft: "" });
  }, []);

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
          : [{ series_id: 0, text: (currentSourceName ?? "데이터").replace(/\.[^.]+$/, "") }],
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
        valueLabel: formatRefLabel(object.value, object.axis_units, true, normalization).trim(),
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

  const createDefaultLegend = (): DrawLegendObject => ({
    type: "legend",
    id: `react-legend-${currentIndex}-${Date.now()}-${drawIdRef.current++}`,
    name: legendDefaults.name || "범례",
    entries: [{ series_id: 0, text: (currentSourceName ?? "데이터").replace(/\.[^.]+$/, "") }],
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

  const enterDrawMode = (nextTool: DrawTool | null = null) => {
    if (tool === "ruler" || tool === "label") {
      showToast(`먼저 ${tool === "ruler" ? "눈금자" : "라벨 이동"} 모드를 해제해 주세요.`);
      return;
    }
    setTool("draw");
    setRightPanel("drawing");
    setRightOpen(true);
    setDrawTool(nextTool);
    resetTransientDraw();
    onResetCanvasDrawPreview?.();
    if (!nextTool) setMessage("그리기 도구를 선택하세요.");
  };

  const exitDrawMode = () => {
    setDrawTool(null);
    resetTransientDraw();
    onResetCanvasDrawPreview?.();
    setTool("select");
  };

  const toggleDrawMode = () => {
    if (tool === "draw") {
      exitDrawMode();
      setMessage("그리기 모드를 종료했습니다.");
      return;
    }
    if (tool === "ruler" || tool === "label") {
      showToast(`먼저 ${tool === "ruler" ? "눈금자" : "라벨 이동"} 모드를 해제해 주세요.`);
      return;
    }
    enterDrawMode(null);
  };

  const activateDrawTool = (next: DrawTool) => {
    if (tool === "ruler" || tool === "label") {
      showToast(`먼저 ${tool === "ruler" ? "눈금자" : "라벨 이동"} 모드를 해제해 주세요.`);
      return;
    }
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

  return {
    drawTool,
    setDrawTool,
    drawColor,
    drawWidth,
    drawLineStyle,
    drawArrowMode,
    drawArrowHead,
    drawRefColor,
    drawRefStyle,
    drawPolyBorderStyle,
    drawPolyBorderColor,
    drawPolyFillColor,
    drawPolyFillOpacity,
    drawTextFontSize,
    drawTextFontFamily,
    drawTextFontWeight,
    drawTextItalic,
    drawTextLineSpacing,
    drawTextColor,
    legendDefaults,
    drawingPoints,
    setDrawingPoints,
    drawHover,
    setDrawHover,
    draggingDrawObject,
    drawDropTarget,
    selectedDrawObjectId,
    selectedDrawObjectIds,
    referenceMode,
    setReferenceMode,
    drawEditorOpen,
    drawEditorMode,
    drawEditorKind,
    lineDraft,
    setLineDraft,
    polygonDraft,
    setPolygonDraft,
    referenceDraft,
    setReferenceDraft,
    legendDraft,
    setLegendDraft,
    textDraft,
    setTextDraft,
    textInput,
    setTextInput,
    drawIdRef,
    currentDrawObjects,
    currentDrawLines,
    currentLegend,
    drawObjectsTopFirst,
    persistDrawObjects,
    selectDrawObject,
    focusDrawObject,
    deleteDrawObjects,
    toggleDrawObjectVisibility,
    toggleDrawObjectSemi,
    toggleAllDrawVisibility,
    toggleAllDrawSemi,
    beginDrawObjectDrag,
    moveDrawObjectDrag,
    commitDrawObjectDrag,
    cancelDrawObjectDrag,
    closeDrawEditor,
    openDrawDefaultsEditor,
    openDrawLayerEditor,
    saveDrawEditor,
    createDefaultLegend,
    finishDrawLine,
    finishDrawPolygon,
    confirmTextInput,
    enterDrawMode,
    exitDrawMode,
    toggleDrawMode,
    activateDrawTool,
    hydrateDrawObjectsForFile,
    clearDrawSelection,
    applyLegendBounds,
    beginTextInput,
    resetTransientDraw,
  };
}
