import { describe, expect, it } from "vitest";
import { DEFAULT_CONFIG, HISTORY_CAP, addHistory, loadHistory, previewLabel, toMarkdown, validateConfig } from "../lib/advanced";
import { checkFile, checkText, checkUrl, MAX_TRANSCRIPT_FILE } from "../lib/validate";
import type { Report } from "../lib/types";

const mem = () => { const m = new Map<string, string>(); return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v), removeItem: (k: string) => void m.delete(k) }; };
const R = { label: "Good", confidence: 0.6, judge: "local", summary: "ok", criteria: { rapport: { score: 4, rationale: "a|b", evidence: [] } }, improvements: ["x"], strengths: ["y"], warnings: [] } as unknown as Report;

describe("validate", () => {
  it("accepts vtt/txt", () => expect(checkFile({ name: "a.vtt", size: 10 }, false)).toEqual({ ok: true, kind: "transcript" }));
  it("rejects empty file", () => expect(checkFile({ name: "a.vtt", size: 0 }, false).ok).toBe(false));
  it("rejects oversized transcript", () => expect(checkFile({ name: "a.txt", size: MAX_TRANSCRIPT_FILE + 1 }, false).ok).toBe(false));
  it("rejects unknown type", () => expect(checkFile({ name: "a.exe", size: 5 }, true).ok).toBe(false));
  it("explains video needs worker", () => { const c = checkFile({ name: "c.mp4", size: 5 }, false); expect(c.ok).toBe(false); if (!c.ok) expect(c.error).toMatch(/worker/); });
  it("accepts video when worker online", () => expect(checkFile({ name: "c.mp4", size: 5 }, true).ok).toBe(true));
  it("empty text", () => expect(checkText("  \n")).toMatch(/Paste/));
  it("huge text", () => expect(checkText("x".repeat(11), 10)).toMatch(/limit/));
  it("ok text", () => expect(checkText("hello")).toBeNull());
  it.each(["", "not a url", "ftp://x/y", "http://localhost/a", "http://192.168.1.2/a", "https://" + "a".repeat(2100)])("bad url %s", (u) => expect(checkUrl(u)).not.toBeNull());
  it("good url", () => expect(checkUrl("https://example.com/t.vtt")).toBeNull());
});

describe("advanced config", () => {
  it("defaults valid", () => expect(validateConfig(DEFAULT_CONFIG)).toBeNull());
  it("non-increasing thresholds", () => expect(validateConfig({ ...DEFAULT_CONFIG, thresholds: [3, 2, 4] })).toMatch(/increase/));
  it("out of range thresholds", () => expect(validateConfig({ ...DEFAULT_CONFIG, thresholds: [0, 2, 4] })).toMatch(/between/));
  it("all-zero weights", () => expect(validateConfig({ ...DEFAULT_CONFIG, weights: { a: 0 } })).toMatch(/non-zero/));
  it("bad cap", () => expect(validateConfig({ ...DEFAULT_CONFIG, max_chars: 10 })).toMatch(/cap/));
  it("preview label uses weights", () => {
    const cfg = { ...DEFAULT_CONFIG, weights: { a: 1, b: 0 } };
    expect(previewLabel({ a: 4, b: 1 }, cfg).label).toBe("Excellent");
    expect(previewLabel({ a: 2, b: 5 }, cfg).label).toBe("Poor");
  });
});

describe("history + export", () => {
  it("caps and orders newest first", () => {
    const s = mem();
    for (let i = 0; i < HISTORY_CAP + 5; i++) addHistory({ name: `n${i}`, mode: "advanced", report: R }, s, new Date(2026, 0, 1, 0, i));
    const h = loadHistory(s); expect(h).toHaveLength(HISTORY_CAP); expect(h[0].name).toBe(`n${HISTORY_CAP + 4}`);
  });
  it("survives corrupt storage", () => expect(loadHistory({ getItem: () => "{bad" })).toEqual([]));
  it("markdown export escapes pipes", () => { const md = toMarkdown(R); expect(md).toContain("# Class assessment: Good"); expect(md).toContain("a/b"); });
});
