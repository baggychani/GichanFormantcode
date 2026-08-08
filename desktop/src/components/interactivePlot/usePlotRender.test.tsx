import { act, renderHook } from "@testing-library/react";
import type { MutableRefObject } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EMPTY_DESIGN, RANGE_DEFAULTS } from "./designDefaults";
import { usePlotRender } from "./usePlotRender";

const mocks = vi.hoisted(() => ({
  callSidecar: vi.fn(),
  convertFileSrc: vi.fn((path: string) => `asset://${path}`),
}));

vi.mock("../../sidecarClient", () => ({ callSidecar: mocks.callSidecar }));
vi.mock("@tauri-apps/api/core", () => ({ convertFileSrc: mocks.convertFileSrc }));

function createParams() {
  return {
    aliveRef: { current: true } as MutableRefObject<boolean>,
    canPlot: true,
    setMessage: vi.fn(),
    ranges: RANGE_DEFAULTS.f1_f2,
    sigma: "1.5",
    showEllipse: true,
    design: EMPTY_DESIGN,
    layerState: { raw: "ON" as const },
    layerOverrides: {},
    layerOrder: ["raw"],
    lockedLayers: new Set<string>(),
    currentDrawObjects: [],
    unitModeKey: "hz:f1_f2",
    normalization: null,
    defaultRanges: RANGE_DEFAULTS.f1_f2,
    setDesign: vi.fn(),
    setRanges: vi.fn(),
  };
}

describe("usePlotRender", () => {
  beforeEach(() => {
    mocks.callSidecar.mockResolvedValue({});
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("coalesces scheduled renders and sends only the latest options", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => usePlotRender(createParams()));

    act(() => {
      result.current.scheduleInteractiveRender({ sigma: "2.0" });
      result.current.scheduleInteractiveRender({ sigma: "2.5" });
    });

    expect(mocks.callSidecar).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(70);
    });

    expect(mocks.callSidecar).toHaveBeenCalledOnce();
    expect(mocks.callSidecar).toHaveBeenCalledWith("render_interactive_preview", {
      options: expect.objectContaining({
        sigma: "2.5",
        request_id: expect.any(Number),
      }),
    });
  });

  it("tracks success messages by render request", async () => {
    const { result } = renderHook(() => usePlotRender(createParams()));

    await act(async () => {
      await result.current.renderInteractive({ successMessage: "저장 완료" });
    });

    const request = mocks.callSidecar.mock.calls[0][1] as {
      options: { request_id: number };
    };
    expect(result.current.consumePreviewSuccessMessage(request.options.request_id)).toBe("저장 완료");
    expect(result.current.consumePreviewSuccessMessage(request.options.request_id)).toBeNull();
  });

  it("rejects older preview events after issuing a newer request", () => {
    const { result } = renderHook(() => usePlotRender(createParams()));

    let currentRequest = 0;
    act(() => {
      currentRequest = result.current.nextRenderRequestId();
    });

    expect(result.current.isStalePreviewRequest(currentRequest - 1)).toBe(true);
    expect(result.current.isStalePreviewRequest(currentRequest)).toBe(false);
    expect(result.current.isStalePreviewRequest(currentRequest + 1)).toBe(false);
  });

  it("applies a ready preview through the Tauri asset protocol", () => {
    const { result } = renderHook(() => usePlotRender(createParams()));

    act(() => {
      result.current.applyPreviewReady({
        imagePath: "C:/Temp/GichanFormant/previews/plot.png",
        imageBase64: "",
        info: "3개 모음",
      });
    });

    expect(mocks.convertFileSrc).toHaveBeenCalledWith("C:/Temp/GichanFormant/previews/plot.png");
    expect(result.current.previewUrl).toBe("asset://C:/Temp/GichanFormant/previews/plot.png");
    expect(result.current.previewInfo).toBe("3개 모음");
    expect(result.current.previewLoading).toBe(false);
  });
});
