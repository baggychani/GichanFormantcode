import { beforeEach, describe, expect, it, vi } from "vitest";
import { callSidecar } from "./sidecarClient";

const mocks = vi.hoisted(() => ({ invoke: vi.fn() }));

vi.mock("@tauri-apps/api/core", () => ({ invoke: mocks.invoke }));

describe("callSidecar", () => {
  beforeEach(() => {
    mocks.invoke.mockResolvedValue({ ok: true });
  });

  it("uses the single Tauri command boundary", async () => {
    await callSidecar("load_files", { paths: ["C:/자료/a.tsv"] });

    expect(mocks.invoke).toHaveBeenCalledWith("sidecar_call", {
      method: "load_files",
      params: { paths: ["C:/자료/a.tsv"] },
    });
  });

  it("normalizes an omitted parameter object", async () => {
    await callSidecar("get_state");

    expect(mocks.invoke).toHaveBeenCalledWith("sidecar_call", {
      method: "get_state",
      params: {},
    });
  });
});
