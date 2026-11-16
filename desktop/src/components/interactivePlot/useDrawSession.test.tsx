import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { DrawObject } from "./types";
import { useDrawSession } from "./useDrawSession";

vi.mock("../../sidecarClient", () => ({ callSidecar: vi.fn() }));

const note = { type: "text", id: "note", text: "on combined", x: 1500, y: 500 } as unknown as DrawObject;

function setup(initial: { currentIndex: number; sourceIdentities: string[] }) {
  return renderHook(
    (props: { currentIndex: number; sourceIdentities: string[] }) => useDrawSession({
      ...props,
      currentSourceName: "source",
      normalization: null,
      tool: "select",
      setMessage: vi.fn(),
      showToast: vi.fn(),
      setTool: vi.fn(),
      setRightPanel: vi.fn(),
      setRightOpen: vi.fn(),
      renderInteractive: vi.fn(),
    }),
    { initialProps: initial },
  );
}

describe("useDrawSession source remapping", () => {
  it("keeps Combined annotations on Combined when a file is loaded", () => {
    const view = setup({ currentIndex: 2, sourceIdentities: ["s1", "s2", "combined"] });
    act(() => view.result.current.hydrateDrawObjectsForFile({ index: 2, sessionDrawObjects: [note] }));
    expect(view.result.current.currentDrawObjects).toEqual([note]);

    // s3 takes index 2; Combined moves to index 3.
    view.rerender({ currentIndex: 2, sourceIdentities: ["s1", "s2", "s3", "combined"] });
    expect(view.result.current.currentDrawObjects).toEqual([]);

    view.rerender({ currentIndex: 3, sourceIdentities: ["s1", "s2", "s3", "combined"] });
    expect(view.result.current.currentDrawObjects).toEqual([note]);
  });

  it("does not leave a removed file's annotations on the file that replaces it", () => {
    const view = setup({ currentIndex: 0, sourceIdentities: ["s1", "s2"] });
    act(() => view.result.current.hydrateDrawObjectsForFile({ index: 0, sessionDrawObjects: [note] }));

    view.rerender({ currentIndex: 0, sourceIdentities: ["s2"] });

    expect(view.result.current.currentDrawObjects).toEqual([]);
  });
});
