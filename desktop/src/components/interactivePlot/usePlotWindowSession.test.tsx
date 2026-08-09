import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ApplicationState } from "../../../ipc/protocol";
import { createApplicationState, createDeferred } from "../../test/fixtures";
import type { SidecarEvent } from "./types";
import { usePlotWindowSession } from "./usePlotWindowSession";

type EventHandler = (event: { payload: SidecarEvent }) => void;

const mocks = vi.hoisted(() => ({
  order: [] as string[],
  listen: vi.fn(),
  callSidecar: vi.fn(),
  dispose: vi.fn(),
  eventHandler: undefined as EventHandler | undefined,
}));

vi.mock("@tauri-apps/api/event", () => ({ listen: mocks.listen }));
vi.mock("../../sidecarClient", () => ({ callSidecar: mocks.callSidecar }));

describe("usePlotWindowSession", () => {
  const state = createApplicationState({ capabilities: { can_plot: true } });

  beforeEach(() => {
    mocks.order.length = 0;
    mocks.eventHandler = undefined;
    mocks.listen.mockImplementation(async (_name: string, handler: EventHandler) => {
      mocks.order.push("listen");
      mocks.eventHandler = handler;
      return mocks.dispose;
    });
    mocks.callSidecar.mockImplementation(async (method: string) => {
      mocks.order.push(method);
      return method === "get_state" ? state : undefined;
    });
  });

  function setup() {
    const callbacks = {
      setState: vi.fn(),
      setEngineConnected: vi.fn(),
      setMessage: vi.fn(),
      setPreviewLoading: vi.fn(),
      setRanges: vi.fn(),
      nextRenderRequestId: vi.fn(() => 101),
      isStalePreviewRequest: vi.fn(() => false),
      applyPreviewReady: vi.fn(),
      applyPreviewFailed: vi.fn(),
      applyPreviewCleared: vi.fn(),
      consumePreviewSuccessMessage: vi.fn(() => "렌더링 완료"),
    };
    const refs = {
      aliveRef: { current: true },
      navigatingRef: { current: false },
      setRulerContextRef: { current: vi.fn() },
      applyLegendBoundsRef: { current: vi.fn() },
      clearLegendDragPreviewRef: { current: vi.fn() },
      clearRulerOnPreviewReadyRef: { current: vi.fn() },
      clearRulerOnPreviewClearedRef: { current: vi.fn() },
    };
    const view = renderHook(() => usePlotWindowSession({ ...callbacks, ...refs }));
    return { callbacks, refs, ...view };
  }

  it("subscribes before the initial render and applies interactive preview events", async () => {
    const { callbacks, refs, unmount } = setup();

    await waitFor(() => expect(mocks.callSidecar).toHaveBeenCalledWith("get_state"));
    await waitFor(() => expect(mocks.callSidecar).toHaveBeenCalledWith(
      "render_interactive_preview",
      expect.objectContaining({ options: expect.objectContaining({ request_id: 101 }) }),
    ));
    expect(mocks.order.indexOf("listen")).toBeLessThan(mocks.order.indexOf("get_state"));

    act(() => {
      mocks.eventHandler?.({
        payload: {
          event: "preview_ready",
          payload: {
            target: "interactive",
            request_id: 101,
            png_path: "C:/미리보기.png",
            info: "ready",
            ruler_context: { legend_bounds: { legend: { width_frac: 0.2, height_frac: 0.1 } } },
          },
        },
      });
    });

    expect(callbacks.applyPreviewReady).toHaveBeenCalledWith({
      imagePath: "C:/미리보기.png",
      imageBase64: "",
      info: "ready",
    });
    expect(refs.applyLegendBoundsRef.current).toHaveBeenCalled();
    expect(callbacks.setMessage).toHaveBeenCalledWith("렌더링 완료");

    unmount();
    expect(mocks.dispose).toHaveBeenCalledOnce();
  });

  it("does not continue bootstrap after unmounting during get_state", async () => {
    const pendingState = createDeferred<ApplicationState>();
    mocks.callSidecar.mockImplementation((method: string) => {
      mocks.order.push(method);
      return method === "get_state" ? pendingState.promise : Promise.resolve(undefined);
    });
    const { unmount } = setup();
    await waitFor(() => expect(mocks.callSidecar).toHaveBeenCalledWith("get_state"));
    unmount();

    await act(async () => {
      pendingState.resolve(state);
      await pendingState.promise;
    });

    expect(mocks.callSidecar).not.toHaveBeenCalledWith(
      "render_interactive_preview",
      expect.anything(),
    );
  });
});
