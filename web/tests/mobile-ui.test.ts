import { describe, expect, it } from "vitest";
import { SCORING_STAGES, stageAt } from "../components/scoring-progress";
import { PIPELINE } from "../components/pipeline-stepper";
import { NAV, isActive } from "../components/site-header";
import { THEME_SCRIPT } from "../components/theme";
import { EVAL_SUMMARY } from "../lib/eval";

describe("mobile UI helpers", () => {
  it("scoring stages advance and hold on the last", () => {
    expect(stageAt(0)).toBe(0); expect(stageAt(-5)).toBe(0);
    expect(stageAt(460)).toBe(1); expect(stageAt(60_000)).toBe(SCORING_STAGES.length - 1);
  });
  it("pipeline has the 4 documented steps", () => expect(PIPELINE.map((p) => p.title)).toEqual(["Ingest", "Listen", "Measure", "Judge"]));
  it("bottom tab bar fits 5 items with short labels", () => { expect(NAV).toHaveLength(5); NAV.forEach((n) => expect(n.short.length).toBeLessThanOrEqual(8)); });
  it("active tab matching", () => {
    expect(isActive("/", "/")).toBe(true); expect(isActive("/report", "/")).toBe(true);
    expect(isActive("/about", "/")).toBe(false); expect(isActive("/advanced", "/advanced")).toBe(true);
  });
  it("theme script is safe in private mode", () => expect(THEME_SCRIPT).toMatch(/^try\{/));
  it("eval chart values are percentages", () => EVAL_SUMMARY.forEach((r) => { expect(r.exact).toBeGreaterThanOrEqual(0); expect(r.within1).toBeLessThanOrEqual(100); expect(r.within1).toBeGreaterThanOrEqual(r.exact); }));
});
