import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ApplicationState } from "../../../ipc/protocol";
import {
  createApplicationState,
  createDeferred,
  createHealthStatus,
} from "../../test/fixtures";
import { MainWorkspace } from "./MainWorkspace";

type SidecarEventHandler = (event: {
  payload: { event: string; payload: Record<string, unknown> };
}) => void;
type DragEventHandler = (event: {
  payload: { type: string; paths?: string[] };
}) => void;

const mocks = vi.hoisted(() => ({
  order: [] as string[],
  invoke: vi.fn(),
  listen: vi.fn(),
  emit: vi.fn(),
  callSidecar: vi.fn(),
  dragSubscribe: vi.fn(),
  disposeEvent: vi.fn(),
  disposeDrag: vi.fn(),
  sidecarHandler: undefined as SidecarEventHandler | undefined,
  dragHandler: undefined as DragEventHandler | undefined,
}));

vi.mock("@tauri-apps/api/core", () => ({
  convertFileSrc: (path: string) => `asset://${path}`,
  invoke: mocks.invoke,
}));
vi.mock("@tauri-apps/api/event", () => ({ listen: mocks.listen, emit: mocks.emit }));
vi.mock("@tauri-apps/api/webview", () => ({
  getCurrentWebview: () => ({ onDragDropEvent: mocks.dragSubscribe }),
}));
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: vi.fn(), save: vi.fn() }));
vi.mock("../../sidecarClient", () => ({ callSidecar: mocks.callSidecar }));
vi.mock("../DataGuide", () => ({ DataGuide: () => null }));
vi.mock("../../SupportPanel", () => ({ SupportPanel: () => null }));
vi.mock("./SourceSidebar", () => ({ SourceSidebar: () => <aside data-testid="sources" /> }));
vi.mock("./AnalysisSettingsPanel", () => ({ AnalysisSettingsPanel: () => <aside data-testid="settings" /> }));
vi.mock("./PreviewStage", () => ({
  PreviewStage: ({ previewUrl }: { previewUrl: string | null }) => (
    <main data-testid="preview-url">{previewUrl ?? ""}</main>
  ),
}));

const state = createApplicationState({
  current_vowels: ["a"],
  sources: [{
    index: 0,
    name: "sample.tsv",
    path: "C:/자료/sample.tsv",
    has_f3: false,
    is_combined: false,
    is_pre_lobanov: false,
  }],
  capabilities: { can_plot: true, can_save_project: true },
});

const health = createHealthStatus();

describe("MainWorkspace bootstrap", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mocks.order.length = 0;
    mocks.sidecarHandler = undefined;
    mocks.dragHandler = undefined;
    mocks.invoke.mockImplementation(async (command: string) => {
      mocks.order.push(`invoke:${command}`);
      return health;
    });
    mocks.callSidecar.mockImplementation(async (method: string) => {
      mocks.order.push(`sidecar:${method}`);
      if (method === "load_files") {
        return { load_result: { success_count: 1, failed: [] }, state };
      }
      return state;
    });
    mocks.listen.mockImplementation(async (_event: string, handler: SidecarEventHandler) => {
      mocks.order.push("listen:sidecar-event");
      mocks.sidecarHandler = handler;
      return mocks.disposeEvent;
    });
    mocks.dragSubscribe.mockImplementation(async (handler: DragEventHandler) => {
      mocks.order.push("listen:drag-drop");
      mocks.dragHandler = handler;
      return mocks.disposeDrag;
    });
    vi.spyOn(console, "info").mockImplementation(() => undefined);
  });

  it("subscribes before bootstrapping and disposes both listeners", async () => {
    const view = render(<MainWorkspace />);

    await waitFor(() => expect(mocks.callSidecar).toHaveBeenCalledWith("get_state"));
    expect(mocks.order.indexOf("listen:sidecar-event")).toBeLessThan(
      mocks.order.indexOf("invoke:sidecar_ensure"),
    );
    expect(mocks.order.indexOf("sidecar:get_state")).toBeLessThan(
      mocks.order.indexOf("sidecar:request_preview"),
    );

    view.unmount();

    expect(mocks.disposeEvent).toHaveBeenCalledOnce();
    expect(mocks.disposeDrag).toHaveBeenCalledOnce();
  });

  it("ignores stale previews and applies the latest Tauri asset", async () => {
    render(<MainWorkspace />);
    await waitFor(() => expect(mocks.sidecarHandler).toBeDefined());

    act(() => {
      mocks.sidecarHandler?.({
        payload: {
          event: "preview_ready",
          payload: { target: "main", request_id: 1, png_path: "C:/stale.png" },
        },
      });
    });
    expect(screen.getByTestId("preview-url")).toHaveTextContent("");

    act(() => {
      mocks.sidecarHandler?.({
        payload: {
          event: "preview_ready",
          payload: {
            target: "main",
            request_id: Number.MAX_SAFE_INTEGER,
            png_path: "C:/Temp/GichanFormant/previews/latest.png",
          },
        },
      });
    });
    expect(screen.getByTestId("preview-url")).toHaveTextContent(
      "asset://C:/Temp/GichanFormant/previews/latest.png",
    );
  });

  it("filters dropped files before crossing the sidecar boundary", async () => {
    render(<MainWorkspace />);
    await waitFor(() => expect(mocks.dragHandler).toBeDefined());

    await act(async () => {
      mocks.dragHandler?.({
        payload: {
          type: "drop",
          paths: ["C:/자료/모음.tsv", "C:/자료/readme.exe"],
        },
      });
    });

    await waitFor(() => expect(mocks.callSidecar).toHaveBeenCalledWith("load_files", {
      paths: ["C:/자료/모음.tsv"],
    }));
  });

  it("disposes a listener that resolves after unmount without bootstrapping", async () => {
    let resolveListener: ((dispose: () => void) => void) | undefined;
    mocks.listen.mockImplementation((_event: string, handler: SidecarEventHandler) => {
      mocks.sidecarHandler = handler;
      return new Promise<() => void>((resolve) => {
        resolveListener = resolve;
      });
    });

    const view = render(<MainWorkspace />);
    view.unmount();
    await act(async () => {
      resolveListener?.(mocks.disposeEvent);
      await Promise.resolve();
    });

    expect(mocks.disposeEvent).toHaveBeenCalledOnce();
    expect(mocks.invoke).not.toHaveBeenCalled();
  });

  it("surfaces sidecar startup failure and clears the busy state", async () => {
    mocks.invoke.mockRejectedValueOnce(new Error("engine offline"));

    render(<MainWorkspace />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Error: engine offline");
    await waitFor(() => expect(screen.queryByText("처리 중…")).not.toBeInTheDocument());
    expect(mocks.callSidecar).not.toHaveBeenCalledWith("get_state");
  });

  it("surfaces initial state failure and clears the busy state", async () => {
    mocks.callSidecar.mockImplementation(async (method: string) => {
      mocks.order.push(`sidecar:${method}`);
      if (method === "get_state") throw new Error("state unavailable");
      return state;
    });

    render(<MainWorkspace />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Error: state unavailable");
    await waitFor(() => expect(screen.queryByText("처리 중…")).not.toBeInTheDocument());
    expect(mocks.callSidecar).not.toHaveBeenCalledWith("request_preview", expect.anything());
  });

  it("does not bootstrap when event subscription fails", async () => {
    mocks.listen.mockRejectedValueOnce(new Error("listener unavailable"));

    render(<MainWorkspace />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Error: listener unavailable");
    expect(mocks.invoke).not.toHaveBeenCalled();
  });

  it("does not continue bootstrap after unmounting during get_state", async () => {
    const pendingState = createDeferred<ApplicationState>();
    mocks.callSidecar.mockImplementation((method: string) => {
      mocks.order.push(`sidecar:${method}`);
      if (method === "get_state") return pendingState.promise;
      return Promise.resolve(state);
    });

    const view = render(<MainWorkspace />);
    await waitFor(() => expect(mocks.callSidecar).toHaveBeenCalledWith("get_state"));
    view.unmount();
    await act(async () => {
      pendingState.resolve(state);
      await pendingState.promise;
    });

    expect(mocks.callSidecar).not.toHaveBeenCalledWith("request_preview", expect.anything());
  });
});
