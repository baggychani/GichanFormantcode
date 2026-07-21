import type {
  CSSProperties,
  MouseEvent as ReactMouseEvent,
  PointerEvent as ReactPointerEvent,
} from "react";
import {
  Eye,
  EyeOff,
  GripVertical,
  Layers3,
  List,
  Palette,
  PenLine,
  Ruler,
  ScanSearch,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { formatRefLabel } from "./drawDefaults";
import type {
  DrawEditorKind,
  DrawLineObject,
  DrawObject,
  DrawTool,
} from "./types";

export function DrawingPanel({
  layerListHeight,
  drawTool,
  activateDrawTool,
  openDrawDefaultsEditor,
  referenceMode,
  setReferenceMode,
  setMessage,
  beginLayerPanelResize,
  resizeLayerPanels,
  endLayerPanelResize,
  cancelLayerPanelResize,
  toggleAllDrawVisibility,
  toggleAllDrawSemi,
  persistDrawObjects,
  currentDrawObjects,
  drawObjectsTopFirst,
  currentDrawLines,
  normalization,
  selectedDrawObjectIds,
  draggingDrawObject,
  drawDropTarget,
  beginDrawObjectDrag,
  moveDrawObjectDrag,
  commitDrawObjectDrag,
  cancelDrawObjectDrag,
  toggleDrawObjectVisibility,
  toggleDrawObjectSemi,
  selectDrawObject,
  openDrawLayerEditor,
  deleteDrawObjects,
}: {
  layerListHeight: number;
  drawTool: DrawTool | null;
  activateDrawTool: (next: DrawTool) => void;
  openDrawDefaultsEditor: (kind?: DrawEditorKind) => void;
  referenceMode: "horizontal" | "vertical";
  setReferenceMode: (mode: "horizontal" | "vertical") => void;
  setMessage: (message: string) => void;
  beginLayerPanelResize: (event: ReactPointerEvent<HTMLDivElement>) => void;
  resizeLayerPanels: (event: ReactPointerEvent<HTMLDivElement>) => void;
  endLayerPanelResize: (event: ReactPointerEvent<HTMLDivElement>) => void;
  cancelLayerPanelResize: () => void;
  toggleAllDrawVisibility: () => void;
  toggleAllDrawSemi: () => void;
  persistDrawObjects: (objects: DrawObject[]) => void;
  currentDrawObjects: DrawObject[];
  drawObjectsTopFirst: DrawObject[];
  currentDrawLines: DrawLineObject[];
  normalization: string | null;
  selectedDrawObjectIds: Set<string>;
  draggingDrawObject: string | null;
  drawDropTarget: { id: string; after: boolean } | null;
  beginDrawObjectDrag: (event: ReactPointerEvent<HTMLButtonElement>, id: string) => void;
  moveDrawObjectDrag: (event: ReactPointerEvent<HTMLButtonElement>) => void;
  commitDrawObjectDrag: (event: ReactPointerEvent<HTMLButtonElement>) => void;
  cancelDrawObjectDrag: () => void;
  toggleDrawObjectVisibility: (id: string) => void;
  toggleDrawObjectSemi: (id: string) => void;
  selectDrawObject: (id: string, event: ReactMouseEvent<HTMLButtonElement>) => void;
  openDrawLayerEditor: (object: DrawObject) => void;
  deleteDrawObjects: (id: string) => void;
}) {
  return (
    <div
      className="layer-split-layout drawing-split-layout"
      style={{ "--layer-list-height": `${layerListHeight}px` } as CSSProperties}
    >
      <div className="drawing-panel">
        <section>
          <div className="drawing-panel-heading">
            <span>그리기 도구</span>
          </div>
          <div className="drawing-tool-grid">
            <button
              type="button"
              className={drawTool === "text" ? "is-active" : ""}
              onClick={() => activateDrawTool("text")}
            >
              <span className="draw-tool-icon">T</span>
              <span>
                <strong>텍스트</strong>
                <small>설명과 라벨</small>
              </span>
            </button>
            <button
              type="button"
              className={drawTool === "line" ? "is-active" : ""}
              onClick={() => activateDrawTool("line")}
            >
              <PenLine size={16} />
              <span>
                <strong>선</strong>
                <small>직선과 화살표</small>
              </span>
            </button>
            <button
              type="button"
              className={drawTool === "area" ? "is-active" : ""}
              onClick={() => activateDrawTool("area")}
            >
              <ScanSearch size={16} />
              <span>
                <strong>영역</strong>
                <small>강조 범위</small>
              </span>
            </button>
            <button
              type="button"
              className={drawTool === "reference" ? "is-active" : ""}
              onClick={() => activateDrawTool("reference")}
            >
              <Ruler size={16} />
              <span>
                <strong>기준선</strong>
                <small>축 기준 표시</small>
              </span>
            </button>
            <button
              type="button"
              className={drawTool === "legend" ? "is-active" : ""}
              onClick={() => activateDrawTool("legend")}
            >
              <List size={16} />
              <span>
                <strong>범례</strong>
                <small>선과 모음 설명</small>
              </span>
            </button>
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
                <button
                  type="button"
                  className={referenceMode === "horizontal" ? "is-active" : ""}
                  onClick={() => {
                    setReferenceMode("horizontal");
                    setMessage("수평 기준선 · 마우스를 올리면 미리보기가 보입니다.");
                  }}
                >
                  수평
                </button>
                <button
                  type="button"
                  className={referenceMode === "vertical" ? "is-active" : ""}
                  onClick={() => {
                    setReferenceMode("vertical");
                    setMessage("수직 기준선 · 마우스를 올리면 미리보기가 보입니다.");
                  }}
                >
                  수직
                </button>
              </div>
            </div>
          ) : null}
        </section>
      </div>
      <div
        className="layer-splitter"
        role="separator"
        aria-orientation="horizontal"
        aria-label="그리기 디자인과 목록 높이 조절"
        onPointerDown={beginLayerPanelResize}
        onPointerMove={resizeLayerPanels}
        onPointerUp={endLayerPanelResize}
        onPointerCancel={endLayerPanelResize}
        onLostPointerCapture={cancelLayerPanelResize}
      >
        <i />
      </div>
      <div className="drawing-layer-dock">
        <div className="layer-batch-row">
          <span>일괄 적용</span>
          <button
            type="button"
            onClick={toggleAllDrawVisibility}
            disabled={!currentDrawObjects.length}
          >
            <Eye size={14} /> 전체 표시
          </button>
          <button
            type="button"
            onClick={toggleAllDrawSemi}
            disabled={!currentDrawObjects.length}
          >
            반투명
          </button>
        </div>
        <div className="layer-list-toolbar">
          <span>
            <GripVertical size={12} /> 끌어서 순서 변경
          </span>
          <button
            type="button"
            className="layer-toolbar-danger"
            disabled={!currentDrawObjects.length}
            onClick={() => persistDrawObjects([])}
          >
            모두 삭제
          </button>
        </div>
        {currentDrawObjects.length ? (
          <div className="layer-list drawing-object-list">
            {drawObjectsTopFirst.map((object) => {
              const lineIndex =
                object.type === "line"
                  ? currentDrawLines.findIndex((line) => line.id === object.id) + 1
                  : 0;
              const polyIndex =
                object.type === "polygon"
                  ? currentDrawObjects
                      .filter((item) => item.type === "polygon")
                      .findIndex((item) => item.id === object.id) + 1
                  : 0;
              const textIndex =
                object.type === "text"
                  ? currentDrawObjects
                      .filter((item) => item.type === "text")
                      .findIndex((item) => item.id === object.id) + 1
                  : 0;
              const label =
                object.type === "legend"
                  ? object.name || "범례"
                  : object.type === "reference"
                    ? `${object.mode === "horizontal" ? "수평" : "수직"} ${formatRefLabel(object.value, object.axis_units, true, normalization).trim()}`
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
                    <button
                      type="button"
                      className="layer-drag-handle"
                      onPointerDown={(event) => beginDrawObjectDrag(event, object.id)}
                      onPointerMove={moveDrawObjectDrag}
                      onPointerUp={commitDrawObjectDrag}
                      onPointerCancel={cancelDrawObjectDrag}
                      aria-label={`${label} 순서 이동`}
                      title="끌어서 이동"
                    >
                      <GripVertical size={15} />
                    </button>
                    <button
                      type="button"
                      className="layer-visibility"
                      onClick={() => toggleDrawObjectVisibility(object.id)}
                      title={object.visible ? "레이어 숨기기" : "레이어 표시"}
                    >
                      {object.visible ? <Eye size={15} /> : <EyeOff size={15} />}
                    </button>
                    <button
                      type="button"
                      className={`layer-semi ${object.semi ? "is-active" : ""}`}
                      onClick={() => toggleDrawObjectSemi(object.id)}
                    >
                      반투명
                    </button>
                    <button
                      type="button"
                      className="layer-name drawing-layer-name"
                      onMouseDown={(event) => {
                        if (event.button === 0) event.preventDefault();
                      }}
                      onClick={(event) => selectDrawObject(object.id, event)}
                    >
                      <strong>{label}</strong>
                    </button>
                    <button
                      type="button"
                      className="layer-lock drawing-object-edit"
                      onClick={() => openDrawLayerEditor(object)}
                      aria-label={`${label} 편집`}
                      title="스타일 수정"
                    >
                      <Palette size={14} />
                    </button>
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
        ) : (
          <div className="drawing-empty">
            <Layers3 size={20} />
            <strong>그리기 레이어가 없습니다</strong>
            <span>범례·선·기준선을 추가하면 이곳에 표시됩니다.</span>
          </div>
        )}
      </div>
    </div>
  );
}
