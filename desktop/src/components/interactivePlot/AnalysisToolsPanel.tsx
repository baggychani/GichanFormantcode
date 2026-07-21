import {
  Download,
  Layers3,
  PenLine,
  RefreshCcw,
  Ruler,
  Save,
  ScanSearch,
  Sparkles,
} from "lucide-react";
import type { Ranges, Tool } from "./types";
import { UnitConverterPopover } from "./UnitConverterPopover";
import { ToggleSwitch } from "./widgets";

export function AnalysisToolsPanel({
  rangeUnitLabel,
  xAxis,
  yAxis,
  ranges,
  rangesReadOnly,
  onRangesChange,
  sigma,
  onSigmaChange,
  showEllipse,
  onShowEllipseChange,
  onReset,
  onApplyRanges,
  busy,
  sourceCount,
  canCompare,
  tool,
  onOpenVowelAnalysis,
  onOpenCompare,
  onToggleRuler,
  onEnterDraw,
  hasCombined,
  hasPreview,
  onExport,
  onExportCombinedTxt,
  onSaveProject,
  onOpenBatchExport,
}: {
  rangeUnitLabel: string;
  xAxis: string;
  yAxis: string;
  ranges: Ranges;
  rangesReadOnly: boolean;
  onRangesChange: (next: Ranges) => void;
  sigma: string;
  onSigmaChange: (next: string) => void;
  showEllipse: boolean;
  onShowEllipseChange: (next: boolean) => void;
  onReset: () => void;
  onApplyRanges: () => void;
  busy: boolean;
  sourceCount: number;
  canCompare: boolean;
  tool: Tool;
  onOpenVowelAnalysis: () => void;
  onOpenCompare: () => void;
  onToggleRuler: () => void;
  onEnterDraw: () => void;
  hasCombined: boolean;
  hasPreview: boolean;
  onExport: (format: "jpg" | "png" | "svg") => void;
  onExportCombinedTxt: () => void;
  onSaveProject: () => void;
  onOpenBatchExport: () => void;
}) {
  return (
    <>
      <section className="control-section range-section">
        <div className="section-heading">
          <div>
            <span>01</span>
            <strong>좌표축 범위</strong>
          </div>
          <div className="range-heading-meta">
            <small>{rangeUnitLabel || "정규화"}</small>
            <UnitConverterPopover />
          </div>
        </div>
        <div className="range-matrix">
          <div className="range-matrix-head">
            <span>축</span>
            <span>최솟값</span>
            <span />
            <span>최댓값</span>
          </div>
          <div className="range-matrix-row">
            <strong>
              {yAxis} <small>세로</small>
            </strong>
            <input
              value={ranges.y_min}
              readOnly={rangesReadOnly}
              onChange={(event) => onRangesChange({ ...ranges, y_min: event.target.value })}
            />
            <i>–</i>
            <input
              value={ranges.y_max}
              readOnly={rangesReadOnly}
              onChange={(event) => onRangesChange({ ...ranges, y_max: event.target.value })}
            />
          </div>
          <div className="range-matrix-row">
            <strong>
              {xAxis} <small>가로</small>
            </strong>
            <input
              value={ranges.x_min}
              readOnly={rangesReadOnly}
              onChange={(event) => onRangesChange({ ...ranges, x_min: event.target.value })}
            />
            <i>–</i>
            <input
              value={ranges.x_max}
              readOnly={rangesReadOnly}
              onChange={(event) => onRangesChange({ ...ranges, x_max: event.target.value })}
            />
          </div>
        </div>
        <div className="ellipse-quick-row">
          <label>
            <span>신뢰 타원 범위</span>
            <span className="sigma-control">
              <select
                value={sigma}
                onChange={(event) => onSigmaChange(event.target.value)}
              >
                <option value="1.0">1.0</option>
                <option value="1.5">1.5</option>
                <option value="2.0">2.0</option>
                <option value="2.5">2.5</option>
                <option value="3.0">3.0</option>
              </select>
              <b>σ</b>
            </span>
          </label>
          <ToggleSwitch
            label="타원 표시"
            checked={showEllipse}
            onChange={() => onShowEllipseChange(!showEllipse)}
          />
        </div>
        <div className="paired-actions">
          <button type="button" onClick={onReset}>
            <RefreshCcw size={14} /> 초기화
          </button>
          <button type="button" className="primary" onClick={onApplyRanges} disabled={busy}>
            <Sparkles size={14} /> 범위 적용
          </button>
        </div>
      </section>

      <section className="control-section">
        <div className="section-heading">
          <div>
            <span>02</span>
            <strong>분석 도구</strong>
          </div>
        </div>
        <div className="tool-grid">
          <button type="button" onClick={onOpenVowelAnalysis} disabled={!sourceCount}>
            <ScanSearch size={17} />
            <span>
              <strong>모음 상세 분석</strong>
              <small>통계와 분포 보기</small>
            </span>
          </button>
          <button type="button" onClick={onOpenCompare} disabled={!canCompare}>
            <Layers3 size={17} />
            <span>
              <strong>다중 플롯 모드</strong>
              <small>파일 비교 구성</small>
            </span>
          </button>
          <button type="button" className={tool === "ruler" ? "is-active" : ""} onClick={onToggleRuler}>
            <Ruler size={17} />
            <span>
              <strong>눈금자</strong>
              <small>R · 거리 측정</small>
            </span>
          </button>
          <button type="button" className={tool === "draw" ? "is-active" : ""} onClick={onEnterDraw}>
            <PenLine size={17} />
            <span>
              <strong>그리기</strong>
              <small>P · 주석 도구</small>
            </span>
          </button>
        </div>
      </section>

      <section className="control-section export-section">
        <div className="section-heading">
          <div>
            <span>03</span>
            <strong>내보내기</strong>
          </div>
        </div>
        <div className={`format-buttons ${hasCombined ? "has-txt" : ""}`}>
          <button type="button" onClick={() => onExport("jpg")} disabled={!hasPreview}>
            JPG
          </button>
          <button type="button" onClick={() => onExport("png")} disabled={!hasPreview}>
            PNG
          </button>
          <button type="button" onClick={() => onExport("svg")} disabled={!sourceCount}>
            SVG
          </button>
          {hasCombined ? (
            <button type="button" onClick={onExportCombinedTxt} disabled={busy}>
              TXT
            </button>
          ) : null}
        </div>
        <button type="button" className="wide-action" onClick={onSaveProject} disabled={busy || !sourceCount}>
          <Save size={15} /> 프로젝트 저장
        </button>
        <button
          type="button"
          className="wide-action primary"
          onClick={onOpenBatchExport}
          disabled={busy || !sourceCount}
        >
          <Download size={15} /> 일괄 저장
        </button>
      </section>
    </>
  );
}
