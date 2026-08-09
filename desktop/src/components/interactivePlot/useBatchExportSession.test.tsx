import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createDeferred } from "../../test/fixtures";
import { EMPTY_DESIGN } from "./designDefaults";
import { useBatchExportSession } from "./useBatchExportSession";

const mocks = vi.hoisted(() => ({
  open: vi.fn(),
  callSidecar: vi.fn(),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({ open: mocks.open }));
vi.mock("../../sidecarClient", () => ({ callSidecar: mocks.callSidecar }));

describe("useBatchExportSession", () => {
  beforeEach(() => {
    mocks.open.mockResolvedValue("C:/내보내기");
    mocks.callSidecar.mockResolvedValue({ exported: ["a.png", "b.png"], errors: [] });
  });

  function setup() {
    const aliveRef = { current: true };
    const setMessage = vi.fn();
    const view = renderHook(() => useBatchExportSession({
      aliveRef,
      sourceCount: 2,
      ranges: { y_min: "200", y_max: "1200", x_min: "500", x_max: "3500" },
      sigma: "2",
      showEllipse: true,
      design: EMPTY_DESIGN,
      layerState: { a: "ON" },
      layerOverrides: {},
      layerOrder: ["a"],
      lockedLayers: new Set(["a"]),
      drawObjects: [],
      setMessage,
    }));
    return { aliveRef, setMessage, ...view };
  }

  async function chooseDirectory(result: ReturnType<typeof setup>["result"]) {
    act(() => result.current.dialogProps.onChooseDirectory());
    await waitFor(() => expect(result.current.dialogProps.directory).toBe("C:/내보내기"));
  }

  it("exports the current plot session and closes the dialog", async () => {
    const { result, setMessage } = setup();
    act(() => result.current.openDialog());
    await chooseDirectory(result);

    act(() => result.current.dialogProps.onExport());

    await waitFor(() => expect(mocks.callSidecar).toHaveBeenCalledWith(
      "export_interactive_batch",
      expect.objectContaining({
        directory: "C:/내보내기",
        format: "png",
        options: expect.objectContaining({
          locked_layers: ["a"],
          batch_options: {
            apply_global_design: true,
            apply_layer_design: true,
            apply_layer_visibility: true,
            apply_label_positions: true,
            apply_legend: true,
            apply_draw_annotations: true,
          },
        }),
      }),
    ));
    await waitFor(() => expect(setMessage).toHaveBeenCalledWith("2개 파일을 일괄 저장했습니다."));
    expect(result.current.isOpen).toBe(false);
  });

  it("ignores a completed export after the plot window closes", async () => {
    const pendingExport = createDeferred<{ exported: string[]; errors: [] }>();
    mocks.callSidecar.mockReturnValue(pendingExport.promise);
    const { aliveRef, result, setMessage, unmount } = setup();
    await chooseDirectory(result);
    act(() => result.current.dialogProps.onExport());
    await waitFor(() => expect(mocks.callSidecar).toHaveBeenCalled());

    aliveRef.current = false;
    unmount();
    await act(async () => {
      pendingExport.resolve({ exported: ["late.png"], errors: [] });
      await pendingExport.promise;
    });

    expect(setMessage).not.toHaveBeenCalled();
  });

  it("surfaces directory picker failure without starting an export", async () => {
    mocks.open.mockRejectedValueOnce(new Error("dialog unavailable"));
    const { result, setMessage } = setup();

    act(() => result.current.dialogProps.onChooseDirectory());

    await waitFor(() => expect(setMessage).toHaveBeenCalledWith(
      "저장 폴더를 선택하지 못했습니다: Error: dialog unavailable",
    ));
    expect(mocks.callSidecar).not.toHaveBeenCalled();
  });

  it("keeps the dialog open and releases busy state after export failure", async () => {
    mocks.callSidecar.mockRejectedValueOnce(new Error("write denied"));
    const { result, setMessage } = setup();
    act(() => result.current.openDialog());
    await chooseDirectory(result);

    act(() => result.current.dialogProps.onExport());

    await waitFor(() => expect(setMessage).toHaveBeenCalledWith(
      "일괄 저장 실패: Error: write denied",
    ));
    expect(result.current.dialogProps.busy).toBe(false);
    expect(result.current.isOpen).toBe(true);
  });
});
