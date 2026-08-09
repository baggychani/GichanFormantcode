import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PlotWindowHeader } from "./PlotWindowHeader";
import { PlotWindowOverlays } from "./PlotWindowOverlays";

describe("interactive plot window chrome", () => {
  it("renders engine state and forwards header actions", () => {
    const openHelp = vi.fn();
    const openLegacy = vi.fn();
    render(
      <PlotWindowHeader
        sourceName="모음.tsv"
        engineConnected={false}
        xAxis="F2"
        yAxis="F1"
        fileCounter="1 / 2"
        legacyDisabled={false}
        onOpenShortcutHelp={openHelp}
        onOpenLegacyPlot={openLegacy}
      />,
    );

    expect(screen.getByText("분석 엔진 연결 확인 중")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "단축키 도움말" }));
    fireEvent.click(screen.getByRole("button", { name: /PySide 고급 편집/ }));
    expect(openHelp).toHaveBeenCalledOnce();
    expect(openLegacy).toHaveBeenCalledOnce();
  });

  it("keeps text input and toast interactions in the overlay boundary", () => {
    const changeText = vi.fn();
    const confirmText = vi.fn();
    render(
      <PlotWindowOverlays
        batchExportProps={null}
        textInput={{ draft: "초안" }}
        onTextInputChange={changeText}
        onTextInputClose={vi.fn()}
        onTextInputConfirm={confirmText}
        drawEditorProps={null}
        vowelAnalysisProps={null}
        shortcutHelpOpen={false}
        onShortcutHelpClose={vi.fn()}
        toast="저장 완료"
      />,
    );

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "수정" } });
    fireEvent.click(screen.getByRole("button", { name: "확인" }));
    expect(changeText).toHaveBeenCalledWith("수정");
    expect(confirmText).toHaveBeenCalledOnce();
    expect(screen.getByRole("status")).toHaveTextContent("저장 완료");
  });
});
