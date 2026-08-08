import { describe, expect, it } from "vitest";
import {
  barkToHz,
  effectiveAxisScales,
  formatRulerDistance,
  hzToBark,
  resolvePlotUnits,
} from "./plotUnits";

describe("plot units", () => {
  it("forces both axes to Bark in integer-Bark mode", () => {
    expect(effectiveAxisScales({
      use_bark_units: true,
      f1_scale: "linear",
      f2_scale: "linear",
    })).toEqual({ f1_scale: "bark", f2_scale: "bark" });
  });

  it("gives normalization precedence over Bark display", () => {
    expect(resolvePlotUnits({
      normalization: "Lobanov",
      use_bark_units: true,
      type: "f1_f3",
    })).toMatchObject({
      kind: "normalized",
      yAxisName: "nF1",
      xAxisName: "nF3",
      drawAxisUnits: "norm",
      rulerUnitChoiceEnabled: false,
    });
  });

  it("round-trips positive Hz values through Bark conversion", () => {
    for (const hz of [200, 500, 1500, 3500]) {
      expect(barkToHz(hzToBark(hz))).toBeCloseTo(hz, 8);
    }
  });

  it("formats direct ruler distance with both units", () => {
    const units = resolvePlotUnits({ f2_scale: "bark" });
    const label = formatRulerDistance(
      { x: 0, y: 0, raw_f1: 400, raw_f2: 1200 },
      { x: 0, y: 0, raw_f1: 500, raw_f2: 1500 },
      units,
    );

    expect(label).toMatch(/^\d+\.\d{2} Bk ≒ \d+ Hz$/);
  });
});
