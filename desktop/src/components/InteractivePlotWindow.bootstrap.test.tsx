import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ApplicationState } from "../../ipc/protocol";
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

const emptyState: ApplicationState = {
  analysis: {
    type: "f1_f2",
    f1_scale: "linear",
    f2_scale: "bark",
    origin: "upper_right",
    use_bark_units: false,
    outlier_mode: null,
    outlier_scope: null,
    normalization: null,
  },
  current_index: 0,
  current_vowels: [],
  design_defaults: {},
  plot_session: {
    revision: 0,
    active: false,
    current_idx: 0,
    ranges: {},
    sigma: "2",
    show_ellipse: true,
    design_settings: {},
    vowel_filter_state_by_file: {},
    layer_design_overrides_by_file: {},
    layer_locked_vowels_by_file: {},
    layer_order_by_file: {},
    draw_objects_by_file: {},
  },
  sources: [],
  capabilities: { can_plot: false, can_compare: false, can_save_project: false },
};

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
});
