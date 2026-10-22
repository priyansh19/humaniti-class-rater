import type { Label } from "./types";

export const LABELS: Label[] = ["Poor", "Average", "Good", "Excellent"];

export const CRITERIA: Record<string, { title: string; hint: string }> = {
  rapport: { title: "Intro & rapport", hint: "Greeting, warm-up, time for new joiners to introduce themselves" },
  individual_attention: { title: "Individual attention", hint: "Each child called on by name and questioned individually" },
  energy: { title: "Energy & pleasant interaction", hint: "Encouraging, energetic tone; little dead air" },
  homework_closure: { title: "Homework & conclusion", hint: "Homework given and a clear wrap-up" },
  presentation: { title: "Camera, face, background & light", hint: "Camera on, face visible, 8x8 background, good lighting" },
  av_quality: { title: "Audio/video quality", hint: "No repeated 'can't hear / can't see' complaints" },
  teaching_aids: { title: "Teaching aids", hint: "Board, puzzles, topic videos" },
  content_coverage: { title: "Lesson content", hint: "Topics introduced, explained, practised, recapped" },
};

export const STAGES = [
  { key: "uploading", title: "Uploading" },
  { key: "queued", title: "Queued" },
  { key: "downloading", title: "Fetching link" },
  { key: "transcribing", title: "Transcribing" },
  { key: "audio", title: "Audio analysis" },
  { key: "frames", title: "Frame analysis" },
  { key: "judging", title: "Rubric judgement" },
  { key: "done", title: "Report ready" },
] as const;

export function fmtTs(t: number): string {
  const s = Math.max(0, Math.floor(t));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  const mm = String(m).padStart(2, "0"), ss = String(sec).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

export function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const u = ["KB", "MB", "GB"]; let v = n / 1024, i = 0;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(v < 10 ? 1 : 0)} ${u[i]}`;
}

export const LABEL_STYLE: Record<Label, string> = {
  Poor: "bg-rose-50 text-rose-700 ring-rose-200",
  Average: "bg-amber-50 text-amber-800 ring-amber-200",
  Good: "bg-sky-50 text-sky-700 ring-sky-200",
  Excellent: "bg-emerald-50 text-emerald-700 ring-emerald-200",
};

export function scoreColor(score: number): string {
  return score >= 4 ? "bg-emerald-500" : score >= 3 ? "bg-sky-500" : score >= 2 ? "bg-amber-500" : "bg-rose-500";
}

export function judgeLabel(judge: string): string {
  if (judge === "local") return "Local heuristic scorer";
  const [p, m] = judge.split(":");
  const names: Record<string, string> = { gemini: "Gemini", openrouter: "OpenRouter", openai: "OpenAI", anthropic: "Anthropic", local: "Local LLM" };
  return `${names[p] ?? p} LLM judge${m && m !== "local" ? ` (${m})` : ""}`;
}
