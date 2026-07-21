import {
  PanelRightClose,
  PanelRightOpen,
  SlidersHorizontal,
} from "lucide-react";
import type { AnalysisSettings } from "../../../ipc/protocol";
import { PLOT_TYPES, X_AXIS_LABEL, type PlotType } from "./plotTypes";
import { SettingsSwitch } from "./SettingsSwitch";

type AnalysisSettingsPanelProps = {
  inspectorOpen: boolean;
  onToggleInspector: () => void;
  onOpenInspector: () => void;
  settingsAttention: boolean;
  busy: boolean;
  hasFiles: boolean;
  hasF3: boolean;
  plotType: PlotType;
  analysis: AnalysisSettings | undefined;
  scaleButtonsLocked: boolean;
  axisControlsLocked: boolean;
  barkDisplayLocked: boolean;
  derivedPlotUnsupportedNorm: boolean;
  preLobanovLocked: boolean;
  onPatchSettings: (patch: Record<string, unknown>) => void;
  onToggleBarkDisplayUnits: () => void;
};

export function AnalysisSettingsPanel({
  inspectorOpen,
  onToggleInspector,
  onOpenInspector,
  settingsAttention,
  busy,
  hasFiles,
  hasF3,
  plotType,
  analysis,
  scaleButtonsLocked,
  axisControlsLocked,
  barkDisplayLocked,
  derivedPlotUnsupportedNorm,
  preLobanovLocked,
  onPatchSettings,
  onToggleBarkDisplayUnits,
}: AnalysisSettingsPanelProps) {
  return (
    <aside className={`settings-panel ${settingsAttention ? "is-attention" : ""}`}>
      <div className="settings-header">
        <div className="settings-title">
          <SlidersHorizontal size={16} />
          <div>
            <span className="section-kicker">설정</span>
            <h2>분석 설정</h2>
          </div>
        </div>
        <button
          type="button"
          className="icon-button"
          onClick={onToggleInspector}
          aria-label={inspectorOpen ? "설정 패널 닫기" : "설정 패널 열기"}
        >
          {inspectorOpen ? (
            <PanelRightClose size={16} />
          ) : (
            <PanelRightOpen size={16} />
          )}
        </button>
      </div>

      {inspectorOpen ? (
        <div className="settings-scroll">
          <section className="settings-section">
            <div className="settings-section-title">
              <span>01</span>
              <div>
                <strong>공간 구성</strong>
                <small>살펴볼 포먼트 관계를 선택합니다</small>
              </div>
            </div>
            <div className="plot-mode-list">
              {PLOT_TYPES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`plot-mode ${plotType === item.id ? "active" : ""}`}
                  disabled={busy || !hasFiles || (item.needsF3 && !hasF3)}
                  onClick={() => onPatchSettings({ type: item.id })}
                  aria-pressed={plotType === item.id}
                >
                  <span className="mode-radio" />
                  <span className="mode-copy">
                    <strong>{item.short}</strong>
                    <small>{item.label}</small>
                  </span>
                  {item.needsF3 ? <span className="requirement">F3</span> : null}
                </button>
              ))}
            </div>
          </section>

          <section className="settings-section">
            <div className="settings-section-title">
              <span>02</span>
              <div>
                <strong>축과 방향</strong>
                <small>눈금과 좌표 방향을 정합니다</small>
              </div>
            </div>
            <div className="field-grid">
              <div className="scale-field">
                <span className="field-caption">F1 눈금</span>
                <div className="segmented-control three">
                  <button
                    type="button"
                    className={(analysis?.f1_scale ?? "linear") === "linear" ? "active" : ""}
                    disabled={busy || !hasFiles || scaleButtonsLocked}
                    onClick={() => onPatchSettings({ f1_scale: "linear" })}
                    aria-pressed={(analysis?.f1_scale ?? "linear") === "linear"}
                  >
                    선형
                  </button>
                  <button
                    type="button"
                    className={analysis?.f1_scale === "log" ? "active" : ""}
                    disabled={busy || !hasFiles || scaleButtonsLocked}
                    onClick={() => onPatchSettings({ f1_scale: "log" })}
                    aria-pressed={analysis?.f1_scale === "log"}
                  >
                    로그
                  </button>
                  <button
                    type="button"
                    className={analysis?.f1_scale === "bark" ? "active" : ""}
                    disabled={busy || !hasFiles || scaleButtonsLocked}
                    onClick={() => onPatchSettings({ f1_scale: "bark" })}
                    aria-pressed={analysis?.f1_scale === "bark"}
                  >
                    Bark
                  </button>
                </div>
              </div>
              <div className="scale-field">
                <span className="field-caption">{X_AXIS_LABEL[plotType]} 눈금</span>
                <div className="segmented-control three">
                  <button
                    type="button"
                    className={(analysis?.f2_scale ?? "bark") === "linear" ? "active" : ""}
                    disabled={busy || !hasFiles || scaleButtonsLocked}
                    onClick={() => onPatchSettings({ f2_scale: "linear" })}
                    aria-pressed={(analysis?.f2_scale ?? "bark") === "linear"}
                  >
                    선형
                  </button>
                  <button
                    type="button"
                    className={analysis?.f2_scale === "log" ? "active" : ""}
                    disabled={busy || !hasFiles || scaleButtonsLocked}
                    onClick={() => onPatchSettings({ f2_scale: "log" })}
                    aria-pressed={analysis?.f2_scale === "log"}
                  >
                    로그
                  </button>
                  <button
                    type="button"
                    className={(analysis?.f2_scale ?? "bark") === "bark" ? "active" : ""}
                    disabled={busy || !hasFiles || scaleButtonsLocked}
                    onClick={() => onPatchSettings({ f2_scale: "bark" })}
                    aria-pressed={(analysis?.f2_scale ?? "bark") === "bark"}
                  >
                    Bark
                  </button>
                </div>
              </div>
            </div>
            <label className="select-field wide">
              <span>좌표 원점</span>
              <select
                value={analysis?.origin ?? "top_right"}
                disabled={busy || !hasFiles || axisControlsLocked}
                onChange={(event) =>
                  onPatchSettings({ origin: event.target.value })
                }
              >
                <option value="top_right">Praat 방식 · 오른쪽 위</option>
                <option value="bottom_left">수학적 좌표 · 왼쪽 아래</option>
              </select>
            </label>
            <label className="switch-row">
              <span>
                <strong>Bark 단위로 표시</strong>
                <small>
                  {axisControlsLocked
                    ? "정규화 중에는 축·Bark 설정이 잠깁니다"
                    : barkDisplayLocked
                      ? "양쪽 축 Bark 고정 · 눈금 버튼 잠금"
                      : "주파수 눈금을 지각 척도로 바꿉니다"}
                </small>
              </span>
              <SettingsSwitch
                checked={analysis?.use_bark_units ?? false}
                disabled={busy || !hasFiles || axisControlsLocked}
                onChange={onToggleBarkDisplayUnits}
              />
            </label>
          </section>

          <section className="settings-section">
            <div className="settings-section-title">
              <span>03</span>
              <div>
                <strong>데이터 처리</strong>
                <small>이상치와 화자 차이를 보정합니다</small>
              </div>
            </div>
            <span className="field-caption">이상치 처리</span>
            <div className="segmented-control three">
              <button
                type="button"
                className={!analysis?.outlier_mode ? "active" : ""}
                disabled={busy || !hasFiles}
                onClick={() =>
                  onPatchSettings({ outlier_mode: null, outlier_scope: null })
                }
                aria-pressed={!analysis?.outlier_mode}
              >
                사용 안 함
              </button>
              <button
                type="button"
                className={analysis?.outlier_mode === "tukey_iqr" ? "active" : ""}
                disabled={busy || !hasFiles}
                onClick={() =>
                  onPatchSettings({
                    outlier_mode: "tukey_iqr",
                    outlier_scope: analysis?.outlier_scope ?? "combined",
                  })
                }
                aria-pressed={analysis?.outlier_mode === "tukey_iqr"}
              >
                Tukey
              </button>
              <button
                type="button"
                className={
                  analysis?.outlier_mode === "mahalanobis_2sigma" ? "active" : ""
                }
                disabled={busy || !hasFiles}
                onClick={() =>
                  onPatchSettings({
                    outlier_mode: "mahalanobis_2sigma",
                    outlier_scope: analysis?.outlier_scope ?? "combined",
                  })
                }
                aria-pressed={analysis?.outlier_mode === "mahalanobis_2sigma"}
              >
                2σ
              </button>
            </div>
            {analysis?.outlier_mode ? (
              <label className="select-field wide compact-field">
                <span>적용 범위</span>
                <select
                  value={analysis.outlier_scope ?? "combined"}
                  disabled={busy || !hasFiles}
                  onChange={(event) =>
                    onPatchSettings({ outlier_scope: event.target.value })
                  }
                >
                  <option value="individual">파일별로 계산</option>
                  <option value="combined">전체 데이터를 함께 계산</option>
                </select>
              </label>
            ) : null}
            <label className="select-field wide compact-field">
              <span>화자 정규화</span>
              <select
                value={analysis?.normalization ?? ""}
                disabled={busy || !hasFiles || derivedPlotUnsupportedNorm || preLobanovLocked}
                onChange={(event) =>
                  onPatchSettings({ normalization: event.target.value || null })
                }
                title={
                  preLobanovLocked
                    ? "사전 Lobanov 데이터 · Lobanov 고정"
                    : derivedPlotUnsupportedNorm
                      ? "이 플롯 유형에서는 정규화를 쓸 수 없습니다"
                      : undefined
                }
              >
                <option value="">사용 안 함</option>
                <option value="Lobanov">Lobanov</option>
              </select>
            </label>
          </section>
        </div>
      ) : (
        <button
          type="button"
          className="collapsed-settings-trigger"
          onClick={onOpenInspector}
          aria-label="설정 패널 열기"
        >
          <SlidersHorizontal size={17} />
          <span>분석 설정</span>
        </button>
      )}
    </aside>
  );
}
