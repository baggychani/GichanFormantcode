import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createApplicationState, createDeferred } from "../test/fixtures";
import { InteractivePlotWindow } from "./InteractivePlotWindow";

type EventHandler = (event: {
  payload: { event: string; payload: Record<string, unknown> } | string;
}) => void;

const mocks = vi.hoisted(() => ({
  order: [] as string[],
  listen: vi.fn(),
  callSidecar: vi.fn(),
  disposers: new Map<string, ReturnType<typeof vi.fn>>(),
}));

vi.mock("@tauri-apps/api/core", () => ({ convertFileSrc: (path: string) => `asset://${path}` }));
vi.mock("@tauri-apps/api/event", () => ({ listen: mocks.listen }));
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: vi.fn(), save: vi.fn() }));
vi.mock("../sidecarClient", () => ({ callSidecar: mocks.callSidecar }));

const emptyState = createApplicationState();

describe("InteractivePlotWindow bootstrap", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mocks.order.length = 0;
    mocks.disposers.clear();
    mocks.listen.mockImplementation(async (event: string, _handler: EventHandler) => {
      mocks.order.push(`listen:${event}`);
      const dispose = vi.fn();
      mocks.disposers.set(event, dispose);
      return dispose;
    });
    mocks.callSidecar.mockImplementation(async (method: string) => {
      mocks.order.push(`sidecar:${method}`);
      return emptyState;
    });
  });

  it("registers the preview listener before requesting initial state", async () => {
    const view = render(<InteractivePlotWindow />);

    await waitFor(() => expect(mocks.callSidecar).toHaveBeenCalledWith("get_state"));
    expect(mocks.order.indexOf("listen:sidecar-event")).toBeLessThan(
      mocks.order.indexOf("sidecar:get_state"),
    );

    view.unmount();

    expect(mocks.disposers.get("sidecar-event")).toHaveBeenCalledOnce();
    expect(mocks.disposers.get("gichan-theme")).toHaveBeenCalledOnce();
  });

  it("surfaces an initial state failure without issuing a render", async () => {
    mocks.callSidecar.mockImplementation(async (method: string) => {
      mocks.order.push(`sidecar:${method}`);
      if (method === "get_state") throw new Error("render engine offline");
      return emptyState;
    });

    render(<InteractivePlotWindow />);

    expect(await screen.findByText(
      "플롯을 불러오지 못했습니다: Error: render engine offline",
    )).toBeInTheDocument();
    expect(mocks.callSidecar).not.toHaveBeenCalledWith(
      "render_interactive_preview",
      expect.anything(),
    );
  });

  it("does not bootstrap when the sidecar event listener fails", async () => {
    mocks.listen.mockImplementation(async (event: string) => {
      mocks.order.push(`listen:${event}`);
      if (event === "sidecar-event") throw new Error("preview listener unavailable");
      const dispose = vi.fn();
      mocks.disposers.set(event, dispose);
      return dispose;
    });

    render(<InteractivePlotWindow />);

    expect(await screen.findByText("Error: preview listener unavailable")).toBeInTheDocument();
    expect(mocks.callSidecar).not.toHaveBeenCalledWith("get_state");
  });

  it("disposes a sidecar listener that resolves after unmount", async () => {
    const pendingListener = createDeferred<() => void>();
    const delayedDispose = vi.fn();
    mocks.listen.mockImplementation(async (event: string) => {
      mocks.order.push(`listen:${event}`);
      if (event === "sidecar-event") return pendingListener.promise;
      const dispose = vi.fn();
      mocks.disposers.set(event, dispose);
      return dispose;
    });

    const view = render(<InteractivePlotWindow />);
    await waitFor(() => expect(mocks.listen).toHaveBeenCalledWith(
      "sidecar-event",
      expect.any(Function),
    ));
    view.unmount();
    await act(async () => {
      pendingListener.resolve(delayedDispose);
      await pendingListener.promise;
    });

    expect(delayedDispose).toHaveBeenCalledOnce();
    expect(mocks.callSidecar).not.toHaveBeenCalledWith("get_state");
  });
});
