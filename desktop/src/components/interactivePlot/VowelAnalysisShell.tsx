import { useEffect, useRef, useState } from "react";
import {
  BarChart3,
  ChevronDown,
  ChevronLeft,
  ChevronUp,
  Download,
  X,
} from "lucide-react";
import type { SourceInfo } from "../../../ipc/protocol";
import { formatPValue } from "../../formatStats";
import { resolvePlotUnits } from "../../plotUnits";
import { useFocusTrap } from "../../useFocusTrap";
import { FormantStatsTable } from "../FormantStatsTable";
import { AnalysisFigure } from "./AnalysisFigure";
import type { VowelAnalysisPage, VowelAnalysisResult, VowelAnalysisSection } from "./types";
import {
  fetchVowelAnalysisSections,
  getCachedVowelAnalysis,
  hasVowelAnalysisSection,
  vowelAnalysisCacheKey,
} from "./vowelAnalysisCache";

export function VowelAnalysisShell({
  currentSource,
  sources,
  currentIndex,
  displayIndex,
  normalization,
  plotType,
  onNavigate,
  onClose,
}: {
  currentSource: SourceInfo | undefined;
  sources: SourceInfo[];
  currentIndex: number;
  displayIndex: number;
  normalization: string | null | undefined;
  plotType: string | undefined;
  onNavigate: (index: number) => void;
  onClose: () => void;
}) {
  const [page, setPage] = useState<VowelAnalysisPage>("home");
  const [lobbyAnimationEnabled, setLobbyAnimationEnabled] = useState(true);
  const lobbyShownRef = useRef(false);
  // Resets to expanded whenever this shell mounts (entering the analysis lab).
  const [heroCollapsed, setHeroCollapsed] = useState(false);
  const cacheKey = vowelAnalysisCacheKey(currentIndex, normalization, plotType);
  const [analysisData, setAnalysisData] = useState<VowelAnalysisResult | null>(
    () => getCachedVowelAnalysis(cacheKey),
  );
  const [analysisLoading, setAnalysisLoading] = useState(
    () => !hasVowelAnalysisSection(getCachedVowelAnalysis(cacheKey), "core"),
  );
  const [sectionLoading, setSectionLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const analysisBodyRef = useRef<HTMLDivElement | null>(null);
  const shellRef = useRef<HTMLElement | null>(null);
  useFocusTrap(true, shellRef);
  const analysisScrollByFileRef = useRef(new Map<number, number>());
  const previousAnalysisIndexRef = useRef(currentIndex);

  useEffect(() => {
    const cached = getCachedVowelAnalysis(cacheKey);
    setAnalysisData(cached);
    setAnalysisError(null);
    if (hasVowelAnalysisSection(cached, "core")) {
      setAnalysisLoading(false);
      return;
    }
    setAnalysisLoading(true);
    let active = true;
    void fetchVowelAnalysisSections(currentIndex, ["core"], cacheKey)
      .then((result) => {
        if (active) {
          setAnalysisData(result);
          setAnalysisLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setAnalysisData(null);
          setAnalysisLoading(false);
          setAnalysisError(String(err));
        }
      });
    return () => {
      active = false;
    };
  }, [cacheKey, currentIndex]);

  useEffect(() => {
    const needed: VowelAnalysisSection[] = [];
    if (page === "distance" && !hasVowelAnalysisSection(analysisData, "mahalanobis")) needed.push("mahalanobis");
    if (page === "pillai" && !hasVowelAnalysisSection(analysisData, "pillai")) needed.push("pillai");
    if (!needed.length || analysisLoading) {
      setSectionLoading(false);
      return;
    }
    let active = true;
    setSectionLoading(true);
    void fetchVowelAnalysisSections(currentIndex, needed, cacheKey)
      .then((result) => {
        if (active) {
          setAnalysisData(result);
          setSectionLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setSectionLoading(false);
          setAnalysisError(String(err));
        }
      });
    return () => {
      active = false;
    };
  }, [analysisData, analysisLoading, cacheKey, currentIndex, page]);

  useEffect(() => {
    const body = analysisBodyRef.current;
    const previousIndex = previousAnalysisIndexRef.current;
    if (body && previousIndex !== currentIndex) {
      analysisScrollByFileRef.current.set(previousIndex, body.scrollTop);
    }
    previousAnalysisIndexRef.current = currentIndex;
    const frame = window.requestAnimationFrame(() => {
      if (analysisBodyRef.current) {
        analysisBodyRef.current.scrollTop = analysisScrollByFileRef.current.get(currentIndex) ?? 0;
      }
    });
    return () => window.cancelAnimationFrame(frame);
  }, [currentIndex]);

  const analysisPairs = analysisData
    ? Object.keys(analysisData.statistics).flatMap((left, index, vowels) =>
        vowels.slice(index + 1).map((right) => ({ left, right, key: `${left}::${right}` })),
      )
    : [];
  const pages: Array<{ id: VowelAnalysisPage; label: string; detail: string }> = [
    { id: "formant", label: "모음별 통계", detail: "중심점과 분포" },
    { id: "distance", label: "중심점 거리", detail: "Euclidean / Mahalanobis" },
    { id: "pillai", label: "Pillai Score", detail: "모음 조합 비교" },
  ];
  const hero =
    page === "formant"
      ? {
          kicker: "01 · FORMANT PROFILE",
          title: "모음 공간의 모양을 읽습니다",
          copy: "각 모음의 평균 위치와 개별 토큰의 퍼짐을 한 화면에서 확인하는 분석 공간입니다.",
        }
      : page === "distance"
        ? {
            kicker: "02 · VOWEL DISTANCE",
            title: "모음 사이의 간격을 비교합니다",
            copy: "중심점 간 거리와 모음 내부 분산을 함께 살펴볼 수 있도록 준비 중입니다.",
          }
        : {
            kicker: "03 · GROUP SEPARATION",
            title: "모음 조합의 분리도를 확인합니다",
            copy: "선택한 모음 조합이 통계적으로 얼마나 분리되는지 보여주는 분석 페이지입니다.",
          };
  const analysisFileName = currentSource?.name ?? "-";
  const analysisFileMatch = analysisFileName.match(/^(.*?)(\.[^.]+)?$/);
  const analysisFileStem = analysisFileMatch?.[1] || analysisFileName;
  const analysisFileExt = analysisFileMatch?.[2] ?? "";
  const goToAnalysisPage = (next: VowelAnalysisPage) => {
    if (next === "home") setLobbyAnimationEnabled(!lobbyShownRef.current);
    else lobbyShownRef.current = true;
    setPage(next);
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      if (page !== "home") goToAnalysisPage("home");
      else onClose();
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [onClose, page]);

  const formantUnitSuffix = resolvePlotUnits({
    normalization: analysisData?.normalization,
    use_bark_units: false,
    type: "f1_f2",
  }).formantStatSuffix;
  const resultsBusy = analysisLoading || sectionLoading;

  return (
    <div className="vowel-analysis-backdrop" data-modal-root role="presentation">
      <section
        ref={shellRef}
        className={`vowel-analysis-shell ${page === "home" ? "is-lobby" : ""} ${page === "home" && lobbyAnimationEnabled ? "is-lobby-first" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="vowel-analysis-title"
      >
        <header className="vowel-analysis-header">
          <div className="vowel-analysis-title">
            <div className="vowel-analysis-mark">
              <BarChart3 size={18} />
            </div>
            <div>
              <span className="section-eyebrow">모음 공간 분석실</span>
              <h2 id="vowel-analysis-title">모음 상세 분석</h2>
            </div>
          </div>
          <button type="button" className="vowel-analysis-close" onClick={onClose} aria-label="분석 창 닫기">
            <X size={18} />
          </button>
        </header>
        {page !== "home" ? (
          <div className="analysis-file-switcher">
            <button
              type="button"
              onClick={() => onNavigate(sources[Math.max(0, displayIndex - 1)]?.index ?? currentIndex)}
              disabled={displayIndex <= 0}
              aria-label="이전 파일"
            >
              ‹
            </button>
            <div>
              <span className="analysis-file-meta">
                <span>분석 파일</span>
                <strong>
                  {displayIndex + 1} / {sources.length}
                </strong>
              </span>
              <b className="analysis-file-name" title={analysisFileName}>
                <span>{analysisFileStem}</span>
                {analysisFileExt ? <em>{analysisFileExt}</em> : null}
              </b>
            </div>
            <button
              type="button"
              onClick={() =>
                onNavigate(sources[Math.min(sources.length - 1, displayIndex + 1)]?.index ?? currentIndex)
              }
              disabled={displayIndex >= sources.length - 1}
              aria-label="다음 파일"
            >
              ›
            </button>
          </div>
        ) : null}
        {page !== "home" ? (
          <nav className="vowel-analysis-tabs" aria-label="모음 분석 페이지">
            <button type="button" className="analysis-home-tab" onClick={() => goToAnalysisPage("home")}>
              <ChevronLeft size={14} />
              <span>
                <strong>전체 보기</strong>
                <small>분석 항목</small>
              </span>
            </button>
            {pages.map((item) => (
              <button
                key={item.id}
                type="button"
                className={page === item.id ? "is-active" : ""}
                onClick={() => goToAnalysisPage(item.id)}
              >
                <strong>{item.label}</strong>
                <small>{item.detail}</small>
              </button>
            ))}
          </nav>
        ) : null}
        <div className={`vowel-analysis-body ${page === "home" ? "is-lobby" : ""}`} ref={analysisBodyRef}>
          {page === "home" ? (
            <div className="analysis-lobby">
              <section className="analysis-lobby-intro">
                <span>ANALYSIS SUITE</span>
                <strong>모음 공간을 더 자세한 수치들로 분석할 수 있습니다.</strong>
                <p>모음별 분포 통계, 중심점 간 거리, 겹침 정도 등 다양한 통계를 확인하고 내보낼 수 있습니다.</p>
              </section>
              <section className="analysis-lobby-grid">
                <button
                  type="button"
                  className="analysis-bento analysis-bento-formant is-primary"
                  onClick={() => goToAnalysisPage("formant")}
                >
                  <span>01</span>
                  <strong>모음별 통계</strong>
                  <p>평균 · 표준편차 · 범위 · 중심 거리 · n</p>
                </button>
                <button
                  type="button"
                  className="analysis-bento analysis-bento-distance"
                  onClick={() => goToAnalysisPage("distance")}
                >
                  <span>02</span>
                  <strong>중심점 거리</strong>
                  <p>Euclidean · Mahalanobis</p>
                </button>
                <button
                  type="button"
                  className="analysis-bento analysis-bento-pillai"
                  onClick={() => goToAnalysisPage("pillai")}
                >
                  <span>03</span>
                  <strong>Pillai Score</strong>
                  <p>score · p-value</p>
                </button>
                <button type="button" className="analysis-bento analysis-bento-export export-bento" disabled title="곧 지원 예정입니다">
                  <Download size={18} />
                  <strong>분석표 내보내기</strong>
                  <p>곧 표 형식 저장을 지원할 예정입니다</p>
                </button>
              </section>
            </div>
          ) : null}
          <div className={`vowel-analysis-hero ${heroCollapsed ? "is-collapsed" : ""}`}>
            <div className="analysis-hero-copy">
              <span className="analysis-kicker">{hero.kicker}</span>
              <h3>{hero.title}</h3>
              <p>{hero.copy}</p>
            </div>
            <AnalysisFigure page={page} />
            <button
              type="button"
              className="analysis-hero-fold"
              onClick={() => setHeroCollapsed((previous) => !previous)}
              aria-expanded={!heroCollapsed}
              aria-label={heroCollapsed ? "소개 패널 펼치기" : "소개 패널 접기"}
              title={heroCollapsed ? "펼치기" : "접기"}
            >
              {heroCollapsed ? <ChevronDown size={16} strokeWidth={2.2} /> : <ChevronUp size={16} strokeWidth={2.2} />}
            </button>
          </div>
          <section className="analysis-detail-panel">
            <div className="analysis-detail-heading">
              <div>
                <span className="analysis-kicker">RESULTS</span>
                <h4>
                  {page === "formant"
                    ? "모음별 통계"
                    : page === "distance"
                      ? "선택 모음 간 거리"
                      : "모음 조합별 Pillai Score"}
                </h4>
              </div>
              <span>
                {resultsBusy
                  ? "계산 중"
                  : analysisData
                    ? String(analysisData.metadata.total_points ?? 0) + " tokens"
                    : "데이터 없음"}
              </span>
            </div>
            {analysisData ? (
              page === "formant" ? (
                <FormantStatsTable
                  statistics={analysisData.statistics}
                  centroidDistances={analysisData.centroid_distances}
                  xLabel={analysisData.x_label ?? "F2"}
                  yLabel={analysisData.y_label ?? "F1"}
                  unitSuffix={formantUnitSuffix}
                />
              ) : analysisPairs.length ? (
                <div className="analysis-result-table">
                  <div className="analysis-result-row analysis-result-head">
                    <span>모음 조합</span>
                    <span>{page === "distance" ? "Euclidean" : "Pillai Score"}</span>
                    <span>{page === "distance" ? "Mahalanobis" : "p-value"}</span>
                  </div>
                  {analysisPairs.map((pair) => {
                    const euclidean = analysisData.pairwise_euclidean[pair.key];
                    const mahalanobis = analysisData.pairwise_mahalanobis[pair.key];
                    const pillai = analysisData.pillai_scores[pair.key];
                    const pDisplay = page === "pillai" ? formatPValue(pillai?.p_value) : null;
                    const heavyPending =
                      sectionLoading &&
                      ((page === "distance" && mahalanobis == null) || (page === "pillai" && pillai == null));
                    return (
                      <div className="analysis-result-row" key={pair.key}>
                        <strong>
                          {pair.left} - {pair.right}
                        </strong>
                        <span>
                          {page === "distance"
                            ? (euclidean ?? 0).toFixed(3)
                            : heavyPending
                              ? "…"
                              : pillai?.score == null
                                ? "N/A"
                                : pillai.score.toFixed(4)}
                        </span>
                        <span
                          className={pDisplay && !pDisplay.significant ? "analysis-p-ns" : undefined}
                          title={pDisplay && pDisplay.text !== "N/A" ? `p = ${pDisplay.exact}` : undefined}
                        >
                          {page === "distance"
                            ? heavyPending
                              ? "…"
                              : (mahalanobis ?? 0).toFixed(3)
                            : heavyPending
                              ? "…"
                              : (pDisplay?.text ?? "N/A")}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="analysis-result-empty">모음 두 개 이상을 선택하면 조합별 결과가 표시됩니다.</div>
              )
            ) : (
              <div className="analysis-result-empty">
                {analysisError
                  ? `분석 데이터를 불러오지 못했습니다: ${analysisError}`
                  : "분석 데이터를 불러오는 중입니다."}
              </div>
            )}
          </section>
        </div>
      </section>
    </div>
  );
}
