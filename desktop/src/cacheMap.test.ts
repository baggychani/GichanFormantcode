import { describe, expect, it } from "vitest";
import { cacheMapSet } from "./cacheMap";

describe("cacheMapSet", () => {
  it("evicts the least recently inserted entry", () => {
    const cache = new Map<string, number>();

    cacheMapSet(cache, "a", 1, 2);
    cacheMapSet(cache, "b", 2, 2);
    cacheMapSet(cache, "c", 3, 2);

    expect([...cache.entries()]).toEqual([
      ["b", 2],
      ["c", 3],
    ]);
  });

  it("refreshes an existing key's recency", () => {
    const cache = new Map([
      ["a", 1],
      ["b", 2],
    ]);

    cacheMapSet(cache, "a", 10, 2);
    cacheMapSet(cache, "c", 3, 2);

    expect([...cache.entries()]).toEqual([
      ["a", 10],
      ["c", 3],
    ]);
  });

  it("ignores nullish keys and keeps at least one entry", () => {
    const cache = new Map<string, number>();

    cacheMapSet(cache, null as unknown as string, 1, 0);
    cacheMapSet(cache, "kept", 2, 0);

    expect([...cache.entries()]).toEqual([["kept", 2]]);
  });
});
