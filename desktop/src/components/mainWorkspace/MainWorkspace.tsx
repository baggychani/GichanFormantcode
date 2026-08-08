import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  ChevronRight,
  Layers3,
  Loader2,
  Moon,
  Sun,
  X,
} from "lucide-react";
import type { ApplicationState } from "../../../ipc/protocol";
import { callSidecar } from "../../sidecarClient";
import appIconUrl from "../../../../assets/icon.ico";
import { DataGuide } from "../DataGuide";
import { SupportPanel } from "../../SupportPanel";
import { SUPPORT_LABEL, SUPPORT_TITLE } from "../../support";
import { AnalysisSettingsPanel } from "./AnalysisSettingsPanel";
import { PreviewStage } from "./PreviewStage";
import { PLOT_TYPES, type PlotType } from "./plotTypes";
import { SourceSidebar } from "./SourceSidebar";
import { useMainWorkspaceSession } from "./useMainWorkspaceSession";
import { useThemePreference } from "./useThemePreference";
import { useWorkspaceActions } from "./useWorkspaceActions";

export function MainWorkspace() {
  const [settingsAttention, setSettingsAttention] = useState(false);
  const settingsAttentionTimersRef = useRef<number[]>([]);
  const [guideAttention, setGuideAttention] = useState(false);
  const guideAttentionTimersRef = useRef<number[]>([]);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [guideOpen, setGuideOpen] = useState(false);
  const [supportOpen, setSupportOpen] = useState(false);
  const {
    aliveRef,
    health,
    state,
    setState,
    previewUrl,
    previewInfo,
    clearPreview,
    status,
    pushStatus,
    error,
    setError,
    busy,
    beginBusy,
    endBusySafe,
    requestMainPreview,
  } = useMainWorkspaceSession();
  const { theme, toggleThemePreference } = useThemePreference();

  const analysis = state?.analysis;
  const sources = state?.sources ?? [];
  const realSources = sources.filter((source) => !source.is_combined);
  const hasFiles = realSources.length > 0;
  /** PySide workspace_service._has_f3_all: every real file must expose F3. */
  const hasF3 = hasFiles && realSources.every((source) => source.has_f3);
  /** PySide all_real_items_pre_lobanov → Lobanov combo locked. */
  const preLobanovLocked = hasFiles && realSources.every((source) => source.is_pre_lobanov);
  const canPlot = state?.capabilities.can_plot ?? false;
  const plotType = (analysis?.type as PlotType) || "f1_f2";
  const derivedPlotUnsupportedNorm =
    plotType === "f1_f2_minus_f1" || plotType === "f1_f2_prime_minus_f1";
  const activePlot =
    PLOT_TYPES.find((plot) => plot.id === plotType) ?? PLOT_TYPES[0];

  const settingsSummary = useMemo(() => {
    if (!analysis) return "분석 설정 대기";
    const outlier = analysis.outlier_mode
      ? analysis.outlier_mode === "tukey_iqr"
        ? "Tukey"
        : "2σ"
      : "원본 데이터";
    const norm = analysis.normalization ?? "정규화 없음";
    return `${activePlot.short} · ${outlier} · ${norm}`;
  }, [activePlot.short, analysis]);

  const signalSettingsAttention = useCallback(() => {
    settingsAttentionTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    setSettingsAttention(false);
    const startTimer = window.setTimeout(() => setSettingsAttention(true), 280);
    const endTimer = window.setTimeout(() => setSettingsAttention(false), 1980);
    settingsAttentionTimersRef.current = [startTimer, endTimer];
  }, []);

  const signalGuideAttention = useCallback(() => {
    guideAttentionTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    setGuideAttention(false);
    // Let the error toast settle first, then pulse the guide button.
    const startTimer = window.setTimeout(() => setGuideAttention(true), 720);
    const endTimer = window.setTimeout(() => setGuideAttention(false), 4200);
    guideAttentionTimersRef.current = [startTimer, endTimer];
  }, []);

  useEffect(() => () => {
    settingsAttentionTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    guideAttentionTimersRef.current.forEach((timer) => window.clearTimeout(timer));
  }, []);

  const {
    dragOver,
    combinedVisible,
    openFiles,
    openProject,
    resetWorkspace,
    removeFile,
    toggleCombinedVisibility,
    saveProject,
    createPlot,
  } = useWorkspaceActions({
    aliveRef,
    setState,
    setError,
    beginBusy,
    endBusySafe,
    pushStatus,
    requestMainPreview,
    clearPreview,
    signalSettingsAttention,
    signalGuideAttention,
  });

  const settingsPatchRef = useRef<Record<string, unknown>>({});
  const settingsTimerRef = useRef<number | null>(null);
  /** PySide `_integer_bark_scale_backup` — restore when Bark display turns off. */
  const barkScaleBackupRef = useRef<{ f1_scale: string; f2_scale: string } | null>(null);
  useEffect(() => () => {
    if (settingsTimerRef.current !== null) window.clearTimeout(settingsTimerRef.current);
  }, []);
  const patchSettings = (patch: Record<string, unknown>) => {
    setError(null);
    settingsPatchRef.current = { ...settingsPatchRef.current, ...patch };
    if (settingsTimerRef.current !== null) window.clearTimeout(settingsTimerRef.current);
    settingsTimerRef.current = window.setTimeout(() => {
      const settings = settingsPatchRef.current;
      settingsPatchRef.current = {};
      settingsTimerRef.current = null;
      if (!aliveRef.current) return;
      void callSidecar<ApplicationState>("set_analysis_settings", { settings })
        .then((next) => { if (aliveRef.current) setState(next); })
        .catch((err) => { if (aliveRef.current) setError(String(err)); });
    }, 90);
  };

  const barkDisplayLocked = Boolean(analysis?.use_bark_units) && !analysis?.normalization;
  const axisControlsLocked = Boolean(analysis?.normalization) || preLobanovLocked;
  const scaleButtonsLocked = axisControlsLocked || barkDisplayLocked;
  const toggleBarkDisplayUnits = () => {
    if (axisControlsLocked) return;
    const turningOn = !(analysis?.use_bark_units ?? false);
    if (turningOn) {
      barkScaleBackupRef.current = {
        f1_scale: analysis?.f1_scale ?? "linear",
        f2_scale: analysis?.f2_scale ?? "bark",
      };
      // Same as PySide get_f*_scale while checkbox is on.
      void patchSettings({ use_bark_units: true, f1_scale: "bark", f2_scale: "bark" });
      return;
    }
    const backup = barkScaleBackupRef.current;
    barkScaleBackupRef.current = null;
    void patchSettings({
      use_bark_units: false,
      f1_scale: backup?.f1_scale ?? "linear",
      f2_scale: backup?.f2_scale ?? "bark",
    });
  };

  // PySide toggle_f3_options: drop F3-only plot types when F3 is unavailable.
  useEffect(() => {
    if (!analysis) return;
    const needsF3 = plotType === "f1_f3" || plotType === "f1_f2_prime" || plotType === "f1_f2_prime_minus_f1";
    if (needsF3 && !hasF3) void patchSettings({ type: "f1_f2" });
  }, [analysis, hasF3, plotType]);

  // PySide: derived plots clear normalization; pre-Lobanov forces Lobanov.
  useEffect(() => {
    if (!analysis || !hasFiles) return;
    if (preLobanovLocked && analysis.normalization !== "Lobanov") {
      void patchSettings({ normalization: "Lobanov" });
      return;
    }
    if (derivedPlotUnsupportedNorm && analysis.normalization) {
      void patchSettings({ normalization: null });
    }
  }, [analysis, derivedPlotUnsupportedNorm, hasFiles, preLobanovLocked]);

  const previewLines = previewInfo.split("\n").filter(Boolean);

  return (
    <div
      className={`workbench ${inspectorOpen ? "" : "settings-hidden"} ${dragOver ? "is-dragging" : ""}`}
    >
      <header className="app-header">
        <div className="app-identity">
          <img className="brand-icon" src={appIconUrl} alt="" aria-hidden />
          <div>
            <div className="app-name">GichanFormant</div>
            <div className="app-edition">모음 음향 분석</div>
          </div>
        </div>

        <div className="workspace-crumb">
          <span>작업 공간</span>
          <ChevronRight size={13} />
          <strong>{hasFiles ? "이름 없는 분석" : "새 분석"}</strong>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="icon-button theme-toggle"
            onClick={toggleThemePreference}
            aria-label={theme === "dark" ? "밝은 테마로 전환" : "어두운 테마로 전환"}
            title={theme === "dark" ? "밝은 테마" : "어두운 테마"}
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <button
            type="button"
            className={`quiet-button guide-button${guideAttention ? " is-attention" : ""}`}
            onClick={() => {
              guideAttentionTimersRef.current.forEach((timer) => window.clearTimeout(timer));
              setGuideAttention(false);
              setGuideOpen(true);
            }}
            disabled={busy}
          >
            <BookOpen size={15} />
            데이터 가이드
          </button>
        </div>
      </header>

      <SourceSidebar
        sources={sources}
        inputFileCount={realSources.length}
        hasF3={hasF3}
        hasFiles={hasFiles}
        busy={busy}
        combinedVisible={combinedVisible}
        onOpenFiles={() => void openFiles()}
        onRemoveFile={(index, name) => void removeFile(index, name)}
        onToggleCombinedVisibility={toggleCombinedVisibility}
        onSaveProject={() => void saveProject()}
        onOpenProject={() => void openProject()}
        onResetWorkspace={() => void resetWorkspace()}
      />

      <PreviewStage
        hasFiles={hasFiles}
        sourcesCount={sources.length}
        activePlot={activePlot}
        health={health}
        previewUrl={previewUrl}
        previewLines={previewLines}
        settingsSummary={settingsSummary}
        analysis={analysis}
        canPlot={canPlot}
        busy={busy}
        onOpenFiles={() => void openFiles()}
        onCreatePlot={() => void createPlot()}
      />

      <AnalysisSettingsPanel
        inspectorOpen={inspectorOpen}
        onToggleInspector={() => setInspectorOpen((open) => !open)}
        onOpenInspector={() => setInspectorOpen(true)}
        settingsAttention={settingsAttention}
        busy={busy}
        hasFiles={hasFiles}
        hasF3={hasF3}
        plotType={plotType}
        analysis={analysis}
        scaleButtonsLocked={scaleButtonsLocked}
        axisControlsLocked={axisControlsLocked}
        barkDisplayLocked={barkDisplayLocked}
        derivedPlotUnsupportedNorm={derivedPlotUnsupportedNorm}
        preLobanovLocked={preLobanovLocked}
        onPatchSettings={patchSettings}
        onToggleBarkDisplayUnits={toggleBarkDisplayUnits}
      />

      <footer className="status-line">
        <span className={`connection-dot ${health?.ok ? "online" : ""}`} />
        <span>{status}</span>
        <span className="status-spacer" />
        <span className="status-copyright">© 2025-2026 Bae Gichan</span>
        <span className="status-divider" />
        <button
          type="button"
          className="status-support"
          title={SUPPORT_TITLE}
          aria-label={SUPPORT_TITLE}
          aria-expanded={supportOpen}
          onClick={() => setSupportOpen(true)}
        >
          {SUPPORT_LABEL}
        </button>
        {busy ? (
          <>
            <span className="status-divider" />
            <span className="status-busy">
              <Loader2 size={12} className="is-spinning" aria-hidden /> 처리 중…
            </span>
          </>
        ) : null}
        <span className="status-divider" />
        <span className="status-mono">v3.0.0</span>
      </footer>

      {busy ? <div className="progress-line" aria-label="작업 진행 중" /> : null}

      {error ? (
        <div className="toast" role="alert" aria-live="assertive">
          <span className="toast-icon">
            <X size={15} />
          </span>
          <div>
            <strong>작업을 완료하지 못했습니다</strong>
            <p>{error}</p>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={() => setError(null)}
            aria-label="알림 닫기"
          >
            <X size={14} />
          </button>
        </div>
      ) : null}

      {dragOver ? (
        <div className="drag-overlay" aria-hidden>
          <span>
            <Layers3 size={23} />
          </span>
          <strong>놓아서 데이터 추가</strong>
          <p>파일 형식을 확인한 뒤 작업 공간에 불러옵니다.</p>
        </div>
      ) : null}

      <DataGuide open={guideOpen} onClose={() => setGuideOpen(false)} />
      <SupportPanel
        open={supportOpen}
        onClose={() => setSupportOpen(false)}
        onCopied={() => pushStatus("후원 계좌번호를 복사했습니다")}
      />
    </div>
  );
}
