import type { ComponentProps } from "react";
import { X } from "lucide-react";
import { BatchExportDialog } from "./BatchExportDialog";
import { DrawStyleEditor } from "./DrawStyleEditor";
import { ShortcutHelpDialog } from "./ShortcutHelpDialog";
import { VowelAnalysisShell } from "./VowelAnalysisShell";

type PlotWindowOverlaysProps = {
  batchExportProps: ComponentProps<typeof BatchExportDialog> | null;
  textInput: { draft: string } | null;
  onTextInputChange: (draft: string) => void;
  onTextInputClose: () => void;
  onTextInputConfirm: () => void;
  drawEditorProps: ComponentProps<typeof DrawStyleEditor> | null;
  vowelAnalysisProps: ComponentProps<typeof VowelAnalysisShell> | null;
  shortcutHelpOpen: boolean;
  onShortcutHelpClose: () => void;
  toast: string | null;
};

export function PlotWindowOverlays({
  batchExportProps,
  textInput,
  onTextInputChange,
  onTextInputClose,
  onTextInputConfirm,
  drawEditorProps,
  vowelAnalysisProps,
  shortcutHelpOpen,
  onShortcutHelpClose,
  toast,
}: PlotWindowOverlaysProps) {
  return (
    <>
      {batchExportProps ? <BatchExportDialog {...batchExportProps} /> : null}

      {textInput ? (
        <div className="legend-editor-backdrop" role="presentation">
          <section
            className="legend-editor-dialog draw-text-input-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="draw-text-input-title"
          >
            <header>
              <div>
                <span className="section-eyebrow">TEXT</span>
                <h2 id="draw-text-input-title">텍스트 입력</h2>
                <p>여러 줄 가능 · Enter로 줄바꿈</p>
              </div>
              <button type="button" onClick={onTextInputClose} aria-label="닫기">
                <X size={18} />
              </button>
            </header>
            <div className="legend-editor-body">
              <label className="draw-text-content-field">
                <span>표시할 텍스트</span>
                <textarea
                  autoFocus
                  value={textInput.draft}
                  onChange={(event) => onTextInputChange(event.target.value)}
                  rows={6}
                />
              </label>
            </div>
            <footer>
              <button type="button" className="wide-action" onClick={onTextInputClose}>취소</button>
              <button type="button" className="wide-action primary" onClick={onTextInputConfirm}>확인</button>
            </footer>
          </section>
        </div>
      ) : null}

      {drawEditorProps ? <DrawStyleEditor {...drawEditorProps} /> : null}
      {vowelAnalysisProps ? <VowelAnalysisShell {...vowelAnalysisProps} /> : null}
      {shortcutHelpOpen ? <ShortcutHelpDialog onClose={onShortcutHelpClose} /> : null}
      {toast ? (
        <div className="plot-toast" role="status" aria-live="polite">
          <strong>안내</strong>
          <p>{toast}</p>
        </div>
      ) : null}
    </>
  );
}
