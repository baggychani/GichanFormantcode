import type { ComponentProps } from "react";
import { ChevronLeft, ChevronRight, Palette, PanelLeftClose, SlidersHorizontal } from "lucide-react";
import type { ApplicationState } from "../../../ipc/protocol";
import { AnalysisToolsPanel } from "./AnalysisToolsPanel";
import { GlobalDesignPanel } from "./GlobalDesignPanel";
import type { LeftPanel } from "./types";
import { FileSelectMenu } from "./widgets";

type PlotControlRailProps = {
  sources: ApplicationState["sources"];
  currentIndex: number;
  currentSourcePosition: number;
  canNavigate: boolean;
  fileCounter: string;
  leftPanel: LeftPanel;
  onLeftPanelChange: (panel: LeftPanel) => void;
  onCollapse: () => void;
  onNavigate: (index: number) => void;
  onNavigateByPosition: (position: number) => void;
  analysisProps: ComponentProps<typeof AnalysisToolsPanel>;
  globalDesignProps: ComponentProps<typeof GlobalDesignPanel>;
};

export function PlotControlRail({
  sources,
  currentIndex,
  currentSourcePosition,
  canNavigate,
  fileCounter,
  leftPanel,
  onLeftPanelChange,
  onCollapse,
  onNavigate,
  onNavigateByPosition,
  analysisProps,
  globalDesignProps,
}: PlotControlRailProps) {
  return (
    <aside className="plot-control-rail">
      <section className="file-navigator">
        <div className="navigator-topline">
          <div>
            <span className="section-eyebrow">파일 탐색</span>
            <strong>{fileCounter}</strong>
          </div>
          <button className="rail-collapse" aria-label="왼쪽 패널 접기" onClick={onCollapse}>
            <PanelLeftClose size={16} />
          </button>
        </div>
        <div className="file-select-row">
          <button
            aria-label="이전 파일"
            onClick={() => onNavigateByPosition(currentSourcePosition - 1)}
            disabled={!canNavigate || currentSourcePosition === 0}
          >
            <ChevronLeft size={17} />
          </button>
          <FileSelectMenu
            sources={sources}
            currentIndex={currentIndex}
            onNavigate={onNavigate}
            disabled={!sources.length}
          />
          <button
            aria-label="다음 파일"
            onClick={() => onNavigateByPosition(currentSourcePosition + 1)}
            disabled={!canNavigate || currentSourcePosition >= sources.length - 1}
          >
            <ChevronRight size={17} />
          </button>
        </div>
      </section>

      <div className="control-tabs">
        <button
          className={leftPanel === "analysis" ? "is-active" : ""}
          onClick={() => onLeftPanelChange("analysis")}
        >
          <SlidersHorizontal size={15} /> 분석 도구
        </button>
        <button
          className={leftPanel === "global-design" ? "is-active" : ""}
          onClick={() => onLeftPanelChange("global-design")}
        >
          <Palette size={15} /> 광역 디자인
        </button>
      </div>

      <div className="control-scroll">
        {leftPanel === "analysis"
          ? <AnalysisToolsPanel {...analysisProps} />
          : <GlobalDesignPanel {...globalDesignProps} />}
      </div>
    </aside>
  );
}
