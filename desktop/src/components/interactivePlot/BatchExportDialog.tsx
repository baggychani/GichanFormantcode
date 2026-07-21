import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { useFocusTrap } from "../../useFocusTrap";
import { ToggleSwitch } from "./widgets";

export type BatchExportFormat = "png" | "jpg" | "svg";

export function BatchExportDialog({
  sourceCount,
  format,
  onFormatChange,
  directory,
  onChooseDirectory,
  busy,
  applyGlobalDesign,
  onApplyGlobalDesignChange,
  applyLayerDesign,
  onApplyLayerDesignChange,
  applyVisibility,
  onApplyVisibilityChange,
  applyLabelPositions,
  onApplyLabelPositionsChange,
  applyLegend,
  onApplyLegendChange,
  applyDrawAnnotations,
  onApplyDrawAnnotationsChange,
  onClose,
  onExport,
}: {
  sourceCount: number;
  format: BatchExportFormat;
  onFormatChange: (format: BatchExportFormat) => void;
  directory: string;
  onChooseDirectory: () => void;
  busy: boolean;
  applyGlobalDesign: boolean;
  onApplyGlobalDesignChange: () => void;
  applyLayerDesign: boolean;
  onApplyLayerDesignChange: () => void;
  applyVisibility: boolean;
  onApplyVisibilityChange: () => void;
  applyLabelPositions: boolean;
  onApplyLabelPositionsChange: () => void;
  applyLegend: boolean;
  onApplyLegendChange: () => void;
  applyDrawAnnotations: boolean;
  onApplyDrawAnnotationsChange: () => void;
  onClose: () => void;
  onExport: () => void;
}) {
  const dialogRef = useRef<HTMLElement | null>(null);
  useFocusTrap(true, dialogRef);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || busy) return;
      event.preventDefault();
      event.stopPropagation();
      onClose();
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [busy, onClose]);

  return (
    <div className="batch-export-backdrop" data-modal-root role="presentation">
      <section
        ref={dialogRef}
        className="batch-export-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="batch-export-title"
      >
        <header>
          <div>
            <span className="section-eyebrow">EXPORT WORKSPACE</span>
            <h2 id="batch-export-title">일괄 저장</h2>
            <p>현재 플롯 설정을 모든 파일에 적용해 저장합니다.</p>
          </div>
          <button type="button" onClick={onClose} disabled={busy} aria-label="닫기">
            <X size={18} />
          </button>
        </header>
        <div className="batch-export-body">
          <div className="batch-export-summary">
            <strong>{sourceCount}개 파일</strong>
            <span>범위 · 디자인 · 레이어 · 라벨 · 범례 · 그리기</span>
          </div>
          <label className="batch-export-field">
            <span>파일 형식</span>
            <div className="batch-format-picker">
              {(["png", "jpg", "svg"] as const).map((item) => (
                <button
                  type="button"
                  key={item}
                  className={format === item ? "is-active" : ""}
                  onClick={() => onFormatChange(item)}
                >
                  {item.toUpperCase()}
                </button>
              ))}
            </div>
          </label>
          <label className="batch-export-field">
            <span>저장 폴더</span>
            <div className="batch-directory-row">
              <input value={directory} readOnly placeholder="폴더를 선택하세요" />
              <button type="button" onClick={onChooseDirectory} disabled={busy}>
                찾아보기
              </button>
            </div>
          </label>
          <div className="batch-export-options">
            <span>반영할 항목</span>
            <ToggleSwitch label="광역 디자인" checked={applyGlobalDesign} onChange={onApplyGlobalDesignChange} />
            <ToggleSwitch label="레이어 디자인" checked={applyLayerDesign} onChange={onApplyLayerDesignChange} />
            <ToggleSwitch label="레이어 표시 상태" checked={applyVisibility} onChange={onApplyVisibilityChange} />
            <ToggleSwitch label="라벨 위치" checked={applyLabelPositions} onChange={onApplyLabelPositionsChange} />
            <ToggleSwitch label="범례" checked={applyLegend} onChange={onApplyLegendChange} />
            <ToggleSwitch label="그리기 주석" checked={applyDrawAnnotations} onChange={onApplyDrawAnnotationsChange} />
          </div>
          <p className="batch-export-note">동일한 파일명이 있으면 자동으로 `_2`, `_3` suffix를 붙입니다.</p>
        </div>
        <footer>
          <button type="button" className="wide-action" onClick={onClose} disabled={busy}>
            취소
          </button>
          <button
            type="button"
            className="wide-action primary"
            onClick={onExport}
            disabled={!directory || busy}
          >
            {busy ? "저장 중…" : "일괄 저장 시작"}
          </button>
        </footer>
      </section>
    </div>
  );
}
