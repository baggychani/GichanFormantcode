import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Check,
  CircleDot,
  Database,
  Gauge,
  Sparkles,
} from "lucide-react";
import type { AnalysisSettings, HealthStatus } from "../../../ipc/protocol";
import { EmptyVisualization } from "./EmptyVisualization";
import { InteractiveHeadline } from "./InteractiveHeadline";
import { PLOT_TYPES, scaleLabel } from "./plotTypes";

type ActivePlot = (typeof PLOT_TYPES)[number];

type PreviewStageProps = {
  hasFiles: boolean;
  sourcesCount: number;
  activePlot: ActivePlot;
  health: HealthStatus | null;
  previewUrl: string | null;
  previewLines: string[];
  settingsSummary: string;
  analysis: AnalysisSettings | undefined;
  canPlot: boolean;
  busy: boolean;
  onOpenFiles: () => void;
  onCreatePlot: () => void;
};

export function PreviewStage({
  hasFiles,
  sourcesCount,
  activePlot,
  health,
  previewUrl,
  previewLines,
  settingsSummary,
  analysis,
  canPlot,
  busy,
  onOpenFiles,
  onCreatePlot,
}: PreviewStageProps) {
  return (
    <main className="workspace-main">
      <div className="workspace-stage">
        <div className="intro-copy">
          <span className="section-kicker accent-text">분석 작업 공간</span>
          <InteractiveHeadline
            text={hasFiles ? "모음 공간을 살펴볼 준비가 됐습니다." : "모음 공간을 더 선명하게 살펴보세요."}
          />
          <p>
            {hasFiles
              ? "현재 분석 조건을 확인하고 필요한 설정만 다듬은 뒤 대화형 플롯을 열어 보세요."
              : "음향 측정값을 불러오면 정확하고 보기 좋은 모음 공간으로 정리해 드립니다."}
          </p>
        </div>

        <div className="overview-metrics">
          <div className="metric">
            <span className="metric-icon cyan">
              <Database size={15} />
            </span>
            <div>
              <strong>{String(sourcesCount).padStart(2, "0")}</strong>
              <span>데이터 파일</span>
            </div>
          </div>
          <div className="metric">
            <span className="metric-icon violet">
              <BarChart3 size={15} />
            </span>
            <div>
              <strong>{activePlot.short}</strong>
              <span>분석 유형</span>
            </div>
          </div>
          <div className="metric">
            <span className={`metric-icon ${health?.ok ? "green" : "amber"}`}>
              <Activity size={15} />
            </span>
            <div>
              <strong>{health?.ok ? "연결됨" : "연결 중"}</strong>
              <span>분석 엔진</span>
            </div>
          </div>
        </div>

        <article className="preview-card">
          <div className="panel-heading">
            <div>
              <div className="panel-title-row">
                <CircleDot size={15} />
                <h2>포먼트 공간</h2>
              </div>
              <p>{previewLines[0] ?? "현재 설정으로 만든 간단한 미리보기"}</p>
            </div>
            <span className="preview-badge">미리보기</span>
          </div>

          <div className="preview-body">
            <div
              className={`preview-surface ${hasFiles ? "has-data" : "is-empty"}`}
              onClick={!hasFiles ? onOpenFiles : undefined}
              onKeyDown={(event) => {
                if (!hasFiles && (event.key === "Enter" || event.key === " ")) {
                  onOpenFiles();
                }
              }}
              role={!hasFiles ? "button" : undefined}
              tabIndex={!hasFiles ? 0 : undefined}
            >
              {previewUrl ? (
                <div className="preview-plot-frame">
                  <img src={previewUrl} alt="현재 포먼트 분석 미리보기" />
                </div>
              ) : (
                <>
                  <EmptyVisualization />
                  <div className="empty-callout">
                    <span className="callout-icon">
                      <Sparkles size={16} />
                    </span>
                    <div>
                      <strong>측정 파일을 여기에 놓으세요</strong>
                      <span>포먼트 열을 확인해 자동으로 불러옵니다.</span>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="preview-footer">
            <span>{previewLines[1] ?? settingsSummary}</span>
            <span className="preview-scale">
              {analysis?.origin === "bottom_left" ? "수학적 좌표" : "Praat 좌표"}
            </span>
          </div>
        </article>

        <aside className="launch-card">
          <div className="launch-glow" aria-hidden />
          <div className="launch-icon">
            <Gauge size={20} />
          </div>
          <span className="section-kicker">현재 분석</span>
          <h2>{activePlot.label}</h2>
          <p>{activePlot.description}</p>

          <div className="recipe-stack">
            <div>
              <span>눈금</span>
              <strong>
                {scaleLabel(analysis?.f1_scale)} / {scaleLabel(analysis?.f2_scale)}
              </strong>
            </div>
            <div>
              <span>이상치</span>
              <strong>
                {analysis?.outlier_mode === "tukey_iqr"
                  ? "Tukey IQR"
                  : analysis?.outlier_mode === "mahalanobis_2sigma"
                    ? "2σ Mahalanobis"
                    : "모두 포함"}
              </strong>
            </div>
            <div>
              <span>정규화</span>
              <strong>{analysis?.normalization ?? "사용 안 함"}</strong>
            </div>
          </div>

          <div className={`readiness ${canPlot ? "is-ready" : ""}`}>
            <span>{canPlot ? <Check size={13} /> : <CircleDot size={13} />}</span>
            {canPlot ? "대화형 플롯을 열 수 있습니다" : "데이터 파일을 먼저 추가하세요"}
          </div>

          <button
            type="button"
            className="primary-button launch"
            disabled={busy || !canPlot}
            onClick={onCreatePlot}
          >
            대화형 플롯 열기
            <ArrowUpRight size={16} />
          </button>
        </aside>
      </div>
    </main>
  );
}
