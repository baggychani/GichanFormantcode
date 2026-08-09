import { useCallback, useMemo, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { callSidecar } from "../../sidecarClient";
import type { BatchExportFormat } from "./BatchExportDialog";
import type {
  DesignSettings,
  DrawObject,
  LayerOverrides,
  LayerVisibility,
  Ranges,
} from "./types";

type BatchExportResult = {
  exported?: string[];
  errors?: Array<{ name: string; message: string }>;
};

type BatchExportSessionParams = {
  aliveRef: MutableRefObject<boolean>;
  sourceCount: number;
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

export function useBatchExportSession({
  aliveRef,
  sourceCount,
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
}: BatchExportSessionParams) {
  const [isOpen, setIsOpen] = useState(false);
  const [format, setFormat] = useState<BatchExportFormat>("png");
  const [directory, setDirectory] = useState("");
  const [busy, setBusy] = useState(false);
  const [applyGlobalDesign, setApplyGlobalDesign] = useState(true);
  const [applyLayerDesign, setApplyLayerDesign] = useState(true);
  const [applyVisibility, setApplyVisibility] = useState(true);
  const [applyLabelPositions, setApplyLabelPositions] = useState(true);
  const [applyLegend, setApplyLegend] = useState(true);
  const [applyDrawAnnotations, setApplyDrawAnnotations] = useState(true);

  const openDialog = useCallback(() => setIsOpen(true), []);
  const closeDialog = useCallback(() => {
    if (!busy) setIsOpen(false);
  }, [busy]);

  const chooseDirectory = useCallback(async () => {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: "일괄 저장 폴더 선택",
      });
      if (aliveRef.current && typeof selected === "string") setDirectory(selected);
    } catch (err) {
      if (aliveRef.current) setMessage(`저장 폴더를 선택하지 못했습니다: ${String(err)}`);
    }
  }, [aliveRef, setMessage]);

  const runExport = useCallback(async () => {
    if (!directory || !sourceCount || !aliveRef.current) return;
    setBusy(true);
    try {
      const result = await callSidecar<BatchExportResult>("export_interactive_batch", {
        directory,
        format,
        options: {
          ranges,
          sigma,
          show_ellipse: showEllipse,
          design,
          filter_state: layerState,
          layer_overrides: layerOverrides,
          layer_order: layerOrder,
          locked_layers: [...lockedLayers],
          draw_objects: drawObjects,
          batch_options: {
            apply_global_design: applyGlobalDesign,
            apply_layer_design: applyLayerDesign,
            apply_layer_visibility: applyVisibility,
            apply_label_positions: applyLabelPositions,
            apply_legend: applyLegend,
            apply_draw_annotations: applyDrawAnnotations,
          },
        },
      });
      if (!aliveRef.current) return;
      const count = result.exported?.length ?? 0;
      setMessage(`${count}개 파일을 일괄 저장했습니다${result.errors?.length ? ` · 실패 ${result.errors.length}개` : ""}.`);
      setIsOpen(false);
    } catch (err) {
      if (aliveRef.current) setMessage(`일괄 저장 실패: ${String(err)}`);
    } finally {
      if (aliveRef.current) setBusy(false);
    }
  }, [
    aliveRef,
    applyDrawAnnotations,
    applyGlobalDesign,
    applyLabelPositions,
    applyLayerDesign,
    applyLegend,
    applyVisibility,
    design,
    directory,
    drawObjects,
    format,
    layerOrder,
    layerOverrides,
    layerState,
    lockedLayers,
    ranges,
    setMessage,
    showEllipse,
    sigma,
    sourceCount,
  ]);

  const dialogProps = useMemo(() => ({
    sourceCount,
    format,
    onFormatChange: setFormat,
    directory,
    onChooseDirectory: () => void chooseDirectory(),
    busy,
    applyGlobalDesign,
    onApplyGlobalDesignChange: () => setApplyGlobalDesign((value) => !value),
    applyLayerDesign,
    onApplyLayerDesignChange: () => setApplyLayerDesign((value) => !value),
    applyVisibility,
    onApplyVisibilityChange: () => setApplyVisibility((value) => !value),
    applyLabelPositions,
    onApplyLabelPositionsChange: () => setApplyLabelPositions((value) => !value),
    applyLegend,
    onApplyLegendChange: () => setApplyLegend((value) => !value),
    applyDrawAnnotations,
    onApplyDrawAnnotationsChange: () => setApplyDrawAnnotations((value) => !value),
    onClose: closeDialog,
    onExport: () => void runExport(),
  }), [
    applyDrawAnnotations,
    applyGlobalDesign,
    applyLabelPositions,
    applyLayerDesign,
    applyLegend,
    applyVisibility,
    busy,
    chooseDirectory,
    closeDialog,
    directory,
    format,
    runExport,
    sourceCount,
  ]);

  return { isOpen, openDialog, dialogProps };
}
