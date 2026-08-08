import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createDeferred } from "../../test/fixtures";
import { useWorkspaceActions } from "./useWorkspaceActions";

const mocks = vi.hoisted(() => ({
  invoke: vi.fn(),
  open: vi.fn(),
  save: vi.fn(),
  callSidecar: vi.fn(),
  dragSubscribe: vi.fn(),
  disposeDrag: vi.fn(),
}));

vi.mock("@tauri-apps/api/core", () => ({ invoke: mocks.invoke }));
vi.mock("@tauri-apps/api/webview", () => ({
  getCurrentWebview: () => ({ onDragDropEvent: mocks.dragSubscribe }),
}));
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: mocks.open, save: mocks.save }));
vi.mock("../../sidecarClient", () => ({ callSidecar: mocks.callSidecar }));

describe("useWorkspaceActions lifetime", () => {
  beforeEach(() => {
    mocks.dragSubscribe.mockResolvedValue(mocks.disposeDrag);
    vi.spyOn(console, "info").mockImplementation(() => undefined);
  });

  function setup() {
    const aliveRef = { current: true };
    const callbacks = {
      setState: vi.fn(),
      setError: vi.fn(),
      beginBusy: vi.fn(),
      endBusySafe: vi.fn(),
      pushStatus: vi.fn(),
      requestMainPreview: vi.fn(),
      clearPreview: vi.fn(),
      signalSettingsAttention: vi.fn(),
      signalGuideAttention: vi.fn(),
    };
    const view = renderHook(() => useWorkspaceActions({ aliveRef, ...callbacks }));
    return { aliveRef, callbacks, ...view };
  }

  it("balances a reset but ignores its result after the workspace closes", async () => {
    const pendingReset = createDeferred<unknown>();
    mocks.callSidecar.mockImplementation((method: string) =>
      method === "reset" ? pendingReset.promise : Promise.resolve(undefined),
    );
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const { aliveRef, callbacks, result, unmount } = setup();

    let resetPromise!: Promise<void>;
    act(() => {
      resetPromise = result.current.resetWorkspace();
    });
    expect(callbacks.beginBusy).toHaveBeenCalledOnce();
    callbacks.setError.mockClear();
    aliveRef.current = false;
    unmount();

    await act(async () => {
      pendingReset.reject(new Error("late reset failure"));
      await resetPromise;
    });

    expect(callbacks.setError).not.toHaveBeenCalled();
    expect(callbacks.clearPreview).not.toHaveBeenCalled();
    expect(callbacks.pushStatus).not.toHaveBeenCalled();
    expect(callbacks.endBusySafe).toHaveBeenCalledOnce();
  });

  it("does not load a file selected after the workspace closes", async () => {
    const pendingDialog = createDeferred<string | null>();
    mocks.open.mockReturnValue(pendingDialog.promise);
    const { aliveRef, result, unmount } = setup();

    let openPromise!: Promise<void>;
    act(() => {
      openPromise = result.current.openFiles();
    });
    aliveRef.current = false;
    unmount();

    await act(async () => {
      pendingDialog.resolve("C:/자료/늦은파일.tsv");
      await openPromise;
    });

    expect(mocks.callSidecar).not.toHaveBeenCalledWith("load_files", expect.anything());
  });
});
