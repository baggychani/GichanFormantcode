import type { ComponentProps } from "react";
import { Layers3, PanelRightClose, PenLine } from "lucide-react";
import { DrawingPanel } from "./DrawingPanel";
import { LayersPanel } from "./LayersPanel";
import type { RightPanel } from "./types";

type PlotInspectorProps = {
  rightPanel: RightPanel;
  currentVowelCount: number;
  onRightPanelChange: (panel: RightPanel) => void;
  onEnterDrawing: () => void;
  onCollapse: () => void;
  layersProps: ComponentProps<typeof LayersPanel>;
  drawingProps: ComponentProps<typeof DrawingPanel>;
};

export function PlotInspector({
  rightPanel,
  currentVowelCount,
  onRightPanelChange,
  onEnterDrawing,
  onCollapse,
  layersProps,
  drawingProps,
}: PlotInspectorProps) {
  return (
    <aside className="layer-inspector">
      <header className="layer-inspector-header">
        <div>
          <span className="section-eyebrow">
            {rightPanel === "layers" ? "레이어 디자인" : "그리기 디자인"}
          </span>
          <strong>{rightPanel === "layers" ? `${currentVowelCount}개 모음` : "주석 도구"}</strong>
        </div>
        <button className="rail-collapse" aria-label="오른쪽 패널 접기" onClick={onCollapse}>
          <PanelRightClose size={16} />
        </button>
      </header>

      <div className="layer-panel-tabs">
        <button
          type="button"
          className={rightPanel === "layers" ? "is-active" : ""}
          onClick={() => onRightPanelChange("layers")}
        >
          <Layers3 size={15} /> 레이어
        </button>
        <button
          type="button"
          className={rightPanel === "drawing" ? "is-active" : ""}
          onClick={onEnterDrawing}
        >
          <PenLine size={15} /> 그리기
        </button>
      </div>

      {rightPanel === "layers"
        ? <LayersPanel {...layersProps} />
        : <DrawingPanel {...drawingProps} />}
    </aside>
  );
}
