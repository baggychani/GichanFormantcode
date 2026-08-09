import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ApplicationState } from "../../../ipc/protocol";
import { createDeferred } from "../../test/fixtures";
import { EMPTY_DESIGN, RANGE_DEFAULTS } from "./designDefaults";
import { usePlotWindowActions } from "./usePlotWindowActions";

const mocks = vi.hoisted(() => ({
  save: vi.fn(),
  callSidecar: vi.fn(),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({ save: mocks.save }));
vi.mock("../../sidecarClient", () => ({ callSidecar: mocks.callSidecar }));

describe("usePlotWindowActions", () => {
  const sources: ApplicationState["sources"] = [
    { index: 0, name: "첫째.tsv", path: "C:/자료/첫째.tsv", has_f3: false, is_combined: false, is_pre_lobanov: false },
    { index: 1, name: "둘째.tsv", path: "C:/자료/둘째.tsv", has_f3: false, is_combined: false, is_pre_lobanov: false },
  ];

  beforeEach(() => {
    mocks.save.mockResolvedValue("C:/내보내기/result.gfproj");
    mocks.callSidecar.mockResolvedValue(undefined);
  });

  function setup() {
    const aliveRef = { current: true };
    const setMessage = vi.fn();
    const view = renderHook(() => usePlotWindowActions({
      aliveRef,
      sources,
      normalization: "Lobanov",
      currentSourceName: "첫째.tsv",
      hasCombined: false,
      ranges: RANGE_DEFAULTS.f1_f2,
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

  it("persists the interactive session before saving a project", async () => {
    const { result, setMessage } = setup();

    await act(async () => result.current.saveProject());

    expect(mocks.callSidecar).toHaveBeenNthCalledWith(
      1,
      "update_interactive_session",
      expect.objectContaining({
        options: expect.objectContaining({
          ranges: RANGE_DEFAULTS.f1_f2,
          locked_layers: ["a"],
          draw_objects: [],
        }),
      }),
    );
    expect(mocks.callSidecar).toHaveBeenNthCalledWith(
      2,
      "save_project",
      { path: "C:/내보내기/result.gfproj" },
    );
    expect(setMessage).toHaveBeenCalledWith("프로젝트를 저장했습니다.");
    expect(result.current.busy).toBe(false);
  });

  it("uses the current source name and format for image export", async () => {
    mocks.save.mockResolvedValue("C:/내보내기/첫째.svg");
    const { result, setMessage } = setup();

    await act(async () => result.current.exportInteractive("svg"));

    expect(mocks.save).toHaveBeenCalledWith(expect.objectContaining({
      defaultPath: "첫째.svg",
      filters: [{ name: "SVG", extensions: ["svg"] }],
    }));
    expect(mocks.callSidecar).toHaveBeenCalledWith(
      "export_interactive_preview",
      expect.objectContaining({
        path: "C:/내보내기/첫째.svg",
        format: "svg",
        options: expect.objectContaining({ layer_order: ["a"] }),
      }),
    );
    expect(setMessage).toHaveBeenCalledWith("SVG 파일을 저장했습니다.");
  });

  it("surfaces a sidecar save failure and releases the busy state", async () => {
    mocks.callSidecar.mockRejectedValueOnce(new Error("disk full"));
    const { result, setMessage } = setup();

    await act(async () => result.current.saveProject());

    expect(setMessage).toHaveBeenCalledWith(
      "프로젝트를 저장하지 못했습니다: Error: disk full",
    );
    expect(mocks.callSidecar).not.toHaveBeenCalledWith("save_project", expect.anything());
    expect(result.current.busy).toBe(false);
  });

  it("does not start saving when the path dialog resolves after unmount", async () => {
    const pendingPath = createDeferred<string | null>();
    mocks.save.mockReturnValue(pendingPath.promise);
    const { aliveRef, result, setMessage, unmount } = setup();

    let savePromise!: Promise<void>;
    act(() => {
      savePromise = result.current.saveProject();
    });
    aliveRef.current = false;
    unmount();
    await act(async () => {
      pendingPath.resolve("C:/내보내기/late.gfproj");
      await savePromise;
    });

    expect(mocks.callSidecar).not.toHaveBeenCalled();
    expect(setMessage).not.toHaveBeenCalled();
  });
});
