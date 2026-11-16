import { describe, expect, it } from "vitest";
import { remapByIdentity, sourceIdentity } from "./sourceIdentity";
import { vowelAnalysisCacheKey } from "./vowelAnalysisCache";

const real = (path: string) => ({ path, name: path.split("/").pop() ?? path, is_combined: false });
const combined = (count: number) => ({ path: null, name: `Combined (${count}명)`, is_combined: true });

describe("sourceIdentity", () => {
  it("keeps Combined stable while its display name changes", () => {
    expect(sourceIdentity(combined(2))).toBe(sourceIdentity(combined(3)));
    expect(sourceIdentity(real("a/s1.txt"))).not.toBe(sourceIdentity(real("b/s1.txt")));
  });
});

describe("remapByIdentity", () => {
  it("moves Combined state with Combined when a file is loaded", () => {
    const previous = [real("s1.txt"), real("s2.txt"), combined(2)].map(sourceIdentity);
    const next = [real("s1.txt"), real("s2.txt"), real("s3.txt"), combined(3)].map(sourceIdentity);

    expect(remapByIdentity({ 0: "first", 2: "combined note" }, previous, next)).toEqual({
      0: "first",
      3: "combined note",
    });
  });

  it("shifts later files down and drops the removed file and vanished Combined", () => {
    const previous = [real("s1.txt"), real("s2.txt"), combined(2)].map(sourceIdentity);
    const next = [real("s2.txt")].map(sourceIdentity);

    expect(remapByIdentity({ 0: "removed", 1: "kept", 2: "combined note" }, previous, next)).toEqual({
      0: "kept",
    });
  });
});

describe("vowelAnalysisCacheKey", () => {
  it("separates results computed under different outlier settings", () => {
    const off = vowelAnalysisCacheKey(0, null, "f1_f2", null, "combined");
    const tukey = vowelAnalysisCacheKey(0, null, "f1_f2", "tukey_iqr", "combined");
    const individual = vowelAnalysisCacheKey(0, null, "f1_f2", "tukey_iqr", "individual");

    expect(new Set([off, tukey, individual]).size).toBe(3);
  });
});
