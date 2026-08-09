import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ApplicationState } from "../../../ipc/protocol";
import { createApplicationState, createDeferred } from "../../test/fixtures";
import { EMPTY_DESIGN, RANGE_DEFAULTS } from "./designDefaults";
import { usePlotNavigation } from "./usePlotNavigation";

const mocks = vi.hoisted(() => ({ callSidecar: vi.fn() }));

vi.mock("../../sidecarClient", () => ({ callSidecar: mocks.callSidecar }));

describe("usePlotNavigation", () => {
  const sources: ApplicationState["sources"] = [
    { index: 0, name: "첫째.tsv", path: "C:/자료/첫째.tsv", has_f3: false, is_combined: false, is_pre_lobanov: false },
    { index: 1, name: "둘째.tsv", path: "C:/자료/둘째.tsv", has_f3: false, is_combined: false, is_pre_lobanov: false },
  ];
  const nextState = createApplicationState({
    current_index: 1,
    current_vowels: ["a"],
    sources,
    plot_session: {
      ranges: RANGE_DEFAULTS.f1_f2,
      sigma: "2",
      show_ellipse: true,
    },
  });

  beforeEach(() => {
    mocks.callSidecar.mockResolvedValue({ state: nextState });
  });

  function setup() {
    const refs = {
      aliveRef: { current: true },
      navigatingRef: { current: false },
      currentIndexRef: { current: 0 },
      globalDesignByFileRef: { current: new Map() },
    };
    const callbacks = {
      setNavigating: vi.fn(),
      setPreviewLoading: vi.fn(),
      setRanges: vi.fn(),
      setSigma: vi.fn(),
      setShowEllipse: vi.fn(),
      setDesign: vi.fn(),
      setState: vi.fn(),
      setMessage: vi.fn(),
      invalidatePendingRender: vi.fn(),
      nextRenderRequestId: vi.fn(() => 202),
      resetTransientRuler: vi.fn(),
      resetTransientDraw: vi.fn(),
      cacheCurrentLayerSession: vi.fn(),
      applyLayersAfterNavigate: vi.fn(),
    };
    const view = renderHook(() => usePlotNavigation({
      ...refs,
      ...callbacks,
      sources,
      currentFileKey: "C:/자료/첫째.tsv",
      analysisUseBark: false,
      normalization: null,
      ranges: RANGE_DEFAULTS.f1_f2,
      defaultRanges: RANGE_DEFAULTS.f1_f2,
      sigma: "2",
      showEllipse: true,
      design: EMPTY_DESIGN,
      canonicalDesign: EMPTY_DESIGN,
      globalDesignLocked: true,
    }));
    return { callbacks, refs, ...view };
  }

  it("navigates with a fresh render id and applies the authoritative response", async () => {
    const { callbacks, refs, result } = setup();

    await act(async () => result.current.navigateTo(1));

    expect(mocks.callSidecar).toHaveBeenCalledWith(
      "navigate_interactive_preview",
      expect.objectContaining({
        index: 1,
        options: expect.objectContaining({ request_id: 202 }),
      }),
    );
    expect(callbacks.invalidatePendingRender).toHaveBeenCalledOnce();
    expect(callbacks.cacheCurrentLayerSession).toHaveBeenCalledWith("C:/자료/첫째.tsv");
    expect(callbacks.applyLayersAfterNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ fileKey: "C:/자료/둘째.tsv", sessionKey: "1" }),
    );
    expect(callbacks.setState).toHaveBeenCalledWith(nextState);
    expect(callbacks.setMessage).toHaveBeenCalledWith("둘째.tsv을 불러왔습니다.");
    expect(refs.currentIndexRef.current).toBe(1);
    expect(refs.navigatingRef.current).toBe(false);
  });

  it("ignores a navigation response after the plot window closes", async () => {
    const pendingNavigation = createDeferred<{ state: ApplicationState }>();
    mocks.callSidecar.mockReturnValue(pendingNavigation.promise);
    const { callbacks, refs, result } = setup();

    let navigationPromise!: Promise<void>;
    act(() => {
      navigationPromise = result.current.navigateTo(1);
    });
    refs.aliveRef.current = false;
    await act(async () => {
      pendingNavigation.resolve({ state: nextState });
      await navigationPromise;
    });

    expect(callbacks.setState).not.toHaveBeenCalled();
    expect(callbacks.setMessage).not.toHaveBeenCalled();
    expect(refs.currentIndexRef.current).toBe(0);
  });
});
