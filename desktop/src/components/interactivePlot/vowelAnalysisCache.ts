import { callSidecar } from "../../sidecarClient";
import type { VowelAnalysisResult, VowelAnalysisSection } from "./types";

const vowelAnalysisCache = new Map<string, VowelAnalysisResult>();

export function vowelAnalysisCacheKey(
  index: number,
  normalization: string | null | undefined,
  plotType: string | undefined,
): string {
  return `${index}|${normalization ?? ""}|${plotType ?? "f1_f2"}`;
}

export function mergeVowelAnalysis(
  base: VowelAnalysisResult | null,
  next: VowelAnalysisResult,
): VowelAnalysisResult {
  if (!base || base.index !== next.index) return next;
  const sections = new Set([...(base.sections ?? []), ...(next.sections ?? [])]);
  return {
    ...base,
    ...next,
    statistics: Object.keys(next.statistics).length ? next.statistics : base.statistics,
    centroid_distances: Object.keys(next.centroid_distances).length
      ? next.centroid_distances
      : base.centroid_distances,
    pairwise_euclidean: Object.keys(next.pairwise_euclidean).length
      ? next.pairwise_euclidean
      : base.pairwise_euclidean,
    pairwise_mahalanobis: Object.keys(next.pairwise_mahalanobis).length
      ? next.pairwise_mahalanobis
      : base.pairwise_mahalanobis,
    pillai_scores: Object.keys(next.pillai_scores).length ? next.pillai_scores : base.pillai_scores,
    metadata: Object.keys(next.metadata).length ? next.metadata : base.metadata,
    sections: [...sections],
  };
}

export function hasVowelAnalysisSection(
  data: VowelAnalysisResult | null | undefined,
  section: VowelAnalysisSection,
): boolean {
  if (!data) return false;
  if (section === "core") return Object.keys(data.statistics).length > 0 || (data.metadata.total_points ?? 0) === 0;
  if (section === "mahalanobis") {
    return (data.sections?.includes("mahalanobis") ?? false) || Object.keys(data.pairwise_mahalanobis).length > 0;
  }
  return (data.sections?.includes("pillai") ?? false) || Object.keys(data.pillai_scores).length > 0;
}

export function getCachedVowelAnalysis(cacheKey: string): VowelAnalysisResult | null {
  return vowelAnalysisCache.get(cacheKey) ?? null;
}

export function clearVowelAnalysisCache() {
  vowelAnalysisCache.clear();
}

export async function fetchVowelAnalysisSections(
  index: number,
  sections: VowelAnalysisSection[],
  cacheKey: string,
): Promise<VowelAnalysisResult> {
  const result = await callSidecar<VowelAnalysisResult>("get_vowel_analysis", { index, sections });
  const merged = mergeVowelAnalysis(vowelAnalysisCache.get(cacheKey) ?? null, result);
  vowelAnalysisCache.set(cacheKey, merged);
  return merged;
}
