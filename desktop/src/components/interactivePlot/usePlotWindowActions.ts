import { useCallback, useMemo, useRef, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { save } from "@tauri-apps/plugin-dialog";
import type { ApplicationState } from "../../../ipc/protocol";
import { callSidecar } from "../../sidecarClient";
import type {
  DesignSettings,
  DrawObject,
  LayerOverrides,
  LayerVisibility,
  Ranges,
} from "./types";

export type InteractiveExportFormat = "png" | "jpg" | "svg";

type PlotWindowActionsParams = {
  aliveRef: MutableRefObject<boolean>;
  sources: ApplicationState["sources"];
  normalization: string | null;
  currentSourceName?: string;
  hasCombined: boolean;
  ranges: Ranges;
  sigma: string;
  showEllipse: boolean;
  design: DesignSettings;
  layerState: Record<string, LayerVisibility>;
  layerOverrides: LayerOverrides;
  layerOrder: string[];
  lockedLayers: ReadonlySet<string>;
  drawObjects: DrawObject[];
  setMessage: Dispatch<SetStateAction<string>>;
};

export function usePlotWindowActions({
  aliveRef,
  sources,
  normalization,
  currentSourceName,
  hasCombined,
  ranges,
  sigma,
  showEllipse,
  design,
  layerState,
  layerOverrides,
  layerOrder,
  lockedLayers,
  drawObjects,
  setMessage,
}: PlotWindowActionsParams) {
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);

  const sessionOptions = useMemo(() => ({
    ranges,
    sigma,
    show_ellipse: showEllipse,
    design,
    filter_state: layerState,
    layer_overrides: layerOverrides,
    layer_order: layerOrder,
    locked_layers: [...lockedLayers],
    draw_objects: drawObjects,
  }), [
    design,
    drawObjects,
    layerOrder,
    layerOverrides,
    layerState,
    lockedLayers,
    ranges,
    showEllipse,
    sigma,
  ]);

  const runBusyAction = useCallback(async (
    action: () => Promise<void>,
    failureMessage: string,
  ): Promise<boolean> => {
    if (!aliveRef.current || busyRef.current) return false;
    busyRef.current = true;
    setBusy(true);
    try {
      await action();
      return aliveRef.current;
    } catch (err) {
      if (aliveRef.current) setMessage(`${failureMessage}: ${String(err)}`);
      return false;
    } finally {
      busyRef.current = false;
      if (aliveRef.current) setBusy(false);
    }
  }, [aliveRef, setMessage]);

  const openLegacyPlot = useCallback(async () => {
    await runBusyAction(
      () => callSidecar("open_single_plot"),
      "PySide 고급 편집 창을 열지 못했습니다",
    );
  }, [runBusyAction]);

  const openComparePlot = useCallback(async () => {
    const realSources = sources.filter((source) => !source.is_combined);
    if (realSources.length < 2) {
      setMessage("다중 플롯은 파일이 2개 이상일 때 사용할 수 있습니다.");
      return;
    }
    const succeeded = await runBusyAction(
      () => callSidecar("open_compare", {
        source_groups: realSources.map((source) => [source.index]),
        normalization,
      }),
      "다중 플롯을 열지 못했습니다",
    );
    if (succeeded) setMessage("다중 플롯 창을 요청했습니다.");
  }, [normalization, runBusyAction, setMessage, sources]);

  const saveProject = useCallback(async () => {
    let path: string | null;
    try {
      path = await save({
        title: "GichanFormant 프로젝트 저장",
        defaultPath: "analysis.gfproj",
        filters: [{ name: "GichanFormant 프로젝트", extensions: ["gfproj"] }],
      });
    } catch (err) {
      if (aliveRef.current) setMessage(`프로젝트 저장 경로를 선택하지 못했습니다: ${String(err)}`);
      return;
    }
    if (!path || !aliveRef.current) return;
    const succeeded = await runBusyAction(async () => {
      await callSidecar("update_interactive_session", { options: sessionOptions });
      if (!aliveRef.current) return;
      await callSidecar("save_project", { path });
    }, "프로젝트를 저장하지 못했습니다");
    if (succeeded) setMessage("프로젝트를 저장했습니다.");
  }, [aliveRef, runBusyAction, sessionOptions, setMessage]);

  const exportInteractive = useCallback(async (format: InteractiveExportFormat) => {
    if (!sources.length) return;
    let path: string | null;
    try {
      path = await save({
        title: `${format.toUpperCase()} 내보내기`,
        defaultPath: `${(currentSourceName ?? "plot").replace(/\.[^.]+$/, "")}.${format}`,
        filters: [{ name: format.toUpperCase(), extensions: [format] }],
      });
    } catch (err) {
      if (aliveRef.current) setMessage(`내보내기 경로를 선택하지 못했습니다: ${String(err)}`);
      return;
    }
    if (!path || !aliveRef.current) return;
    const succeeded = await runBusyAction(
      () => callSidecar("export_interactive_preview", { path, format, options: sessionOptions }),
      "내보내기 실패",
    );
    if (succeeded) setMessage(`${format.toUpperCase()} 파일을 저장했습니다.`);
  }, [aliveRef, currentSourceName, runBusyAction, sessionOptions, setMessage, sources.length]);

  const exportCombinedTxt = useCallback(async () => {
    if (!hasCombined) return;
    let path: string | null;
    try {
      path = await save({
        title: "결합 데이터 TXT 저장",
        defaultPath: "Combined.txt",
        filters: [{ name: "GichanFormant TXT", extensions: ["txt"] }],
      });
    } catch (err) {
      if (aliveRef.current) setMessage(`TXT 저장 경로를 선택하지 못했습니다: ${String(err)}`);
      return;
    }
    if (!path || !aliveRef.current) return;
    const succeeded = await runBusyAction(
      () => callSidecar("export_combined_txt", { path }),
      "TXT 저장 실패",
    );
    if (succeeded) setMessage("결합 데이터를 TXT로 저장했습니다.");
  }, [aliveRef, hasCombined, runBusyAction, setMessage]);

  return {
    busy,
    openLegacyPlot,
    openComparePlot,
    saveProject,
    exportInteractive,
    exportCombinedTxt,
  };
}
