import type { Report } from "./types";

export interface AdvancedConfig {
  provider: "local" | "auto" | "openrouter" | "openai" | "gemini" | "anthropic";
  thresholds: [number, number, number];
  weights: Record<string, number>;
  embeddings: boolean;
  max_chars: number;
}
export const DEFAULT_CONFIG: AdvancedConfig = {
  provider: "local", thresholds: [2.4, 3.1, 3.8], embeddings: false, max_chars: 1_000_000,
  weights: { rapport: 1, individual_attention: 1, energy: 1, homework_closure: 1, av_quality: 1, teaching_aids: 1, content_coverage: 1 },
};
export const ADV_LIMIT_PER_10_MIN = 10;

export function validateConfig(c: AdvancedConfig): string | null {
  const [a, b, d] = c.thresholds;
  if (![a, b, d].every((x) => x >= 1 && x <= 5)) return "Cut-points must be between 1 and 5.";
  if (!(a < b && b < d)) return "Cut-points must increase: Poor < Average < Good < Excellent.";
  if (Object.values(c.weights).some((w) => w < 0 || w > 5)) return "Weights must be between 0 and 5.";
  if (Object.values(c.weights).every((w) => w === 0)) return "At least one criterion needs a non-zero weight.";
  if (c.max_chars < 1000 || c.max_chars > 1_000_000) return "Input cap must be between 1,000 and 1,000,000 characters.";
  return null;
}

/** Same formula as rater/hosted.py custom_label, so the panel can preview instantly. */
export function previewLabel(criteria: Record<string, number>, c: AdvancedConfig) {
  const ks = Object.keys(criteria);
  const tot = ks.reduce((s, k) => s + (c.weights[k] ?? 1), 0);
  const score = tot ? ks.reduce((s, k) => s + criteria[k] * (c.weights[k] ?? 1), 0) / tot : 3;
  const idx = c.thresholds.filter((t) => score >= t).length;
  return { label: (["Poor", "Average", "Good", "Excellent"] as const)[idx], score };
}

// ---- History (Advanced mode only; stays in this browser) ----
export interface HistoryItem { id: string; at: string; name: string; mode: "brief" | "advanced"; report: Report }
const KEY = "rater-history-v1";
export const HISTORY_CAP = 20;

export function loadHistory(store: Pick<Storage, "getItem"> = localStorage): HistoryItem[] {
  try { const v = JSON.parse(store.getItem(KEY) || "[]"); return Array.isArray(v) ? v : []; } catch { return []; }
}
export function addHistory(item: Omit<HistoryItem, "id" | "at">, store: Pick<Storage, "getItem" | "setItem"> = localStorage, now = new Date()): HistoryItem[] {
  const h = [{ ...item, id: now.getTime().toString(36) + Math.random().toString(36).slice(2, 6), at: now.toISOString() }, ...loadHistory(store)].slice(0, HISTORY_CAP);
  try { store.setItem(KEY, JSON.stringify(h)); } catch { /* quota: keep in memory */ }
  return h;
}
export function clearHistory(store: Pick<Storage, "removeItem"> = localStorage) { store.removeItem(KEY); }

// ---- Export ----
export function toMarkdown(r: Report & { custom?: { label: string; score: number } }): string {
  const lines = [`# Class assessment: ${r.label}`, "", `Confidence: ${Math.round(r.confidence * 100)}% · Judge: ${r.judge}`, "", r.summary, ""];
  if (r.custom) lines.push(`Custom-config label: **${r.custom.label}** (weighted score ${r.custom.score.toFixed(2)})`, "");
  lines.push("## Scorecard", "", "| Criterion | Score | Rationale |", "|---|---|---|");
  for (const [k, c] of Object.entries(r.criteria)) lines.push(`| ${k} | ${c.score}/5 | ${c.rationale.replace(/\|/g, "/")} |`);
  lines.push("", "## What to improve", ...r.improvements.map((s, i) => `${i + 1}. ${s}`), "", "## What went well", ...r.strengths.map((s) => `- ${s}`));
  if (r.warnings.length) lines.push("", "## Warnings", ...r.warnings.map((w) => `- ${w}`));
  return lines.join("\n") + "\n";
}
export function downloadText(name: string, text: string, type: string) {
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([text], { type })), download: name });
  a.click(); URL.revokeObjectURL(a.href);
}
