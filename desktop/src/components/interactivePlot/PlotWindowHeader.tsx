import { ArrowUpRight, CircleHelp } from "lucide-react";

type PlotWindowHeaderProps = {
  sourceName?: string;
  engineConnected: boolean;
  xAxis: string;
  yAxis: string;
  fileCounter: string;
  legacyDisabled: boolean;
  onOpenShortcutHelp: () => void;
  onOpenLegacyPlot: () => void;
};

export function PlotWindowHeader({
  sourceName,
  engineConnected,
  xAxis,
  yAxis,
  fileCounter,
  legacyDisabled,
  onOpenShortcutHelp,
  onOpenLegacyPlot,
}: PlotWindowHeaderProps) {
  return (
    <header className="interactive-plot-header">
      <div className="plot-title-block">
        <span>단일 분석 · 대화형 플롯</span>
        <h1 title={sourceName}>{sourceName ?? "데이터를 불러와 주세요"}</h1>
      </div>
      <div className="plot-header-meta">
        <span className={`engine-state ${engineConnected ? "" : "is-offline"}`}>
          <i /> 분석 엔진 {engineConnected ? "연결됨" : "연결 확인 중"}
        </span>
        <span className="plot-notation">{xAxis} × {yAxis} · {fileCounter}</span>
        <button
          type="button"
          className="shortcut-help-launch"
          onClick={onOpenShortcutHelp}
          aria-label="단축키 도움말"
          title="단축키 (?)"
        >
          <CircleHelp size={15} />
        </button>
        <button
          className="legacy-launch"
          onClick={onOpenLegacyPlot}
          disabled={legacyDisabled}
        >
          PySide 고급 편집 <ArrowUpRight size={14} />
        </button>
      </div>
    </header>
  );
}
