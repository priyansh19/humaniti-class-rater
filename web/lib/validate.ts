/** Client-side guardrails (mirrors rater/guardrails.py; server stays authoritative). */
export const MAX_TRANSCRIPT_CHARS = 3_000_000;
export const MAX_TRANSCRIPT_FILE = 5 * 1024 * 1024;
export const MAX_VIDEO_FILE = 2 * 1024 ** 3;
const TRANSCRIPT_EXT = /\.(vtt|txt|srt)$/i;
const VIDEO_EXT = /\.(mp4|mov|mkv|webm|m4v)$/i;

export type FileCheck = { ok: true; kind: "transcript" | "video" } | { ok: false; error: string };

export function checkFile(f: { name: string; size: number }, workerOnline: boolean): FileCheck {
  if (f.size === 0) return { ok: false, error: `"${f.name}" is empty.` };
  if (TRANSCRIPT_EXT.test(f.name)) {
    if (f.size > MAX_TRANSCRIPT_FILE) return { ok: false, error: "Transcript files must be 5 MB or smaller." };
    return { ok: true, kind: "transcript" };
  }
  if (VIDEO_EXT.test(f.name)) {
    if (!workerOnline) return { ok: false, error: "Video analysis needs the analysis worker, which is offline on this hosted demo. Upload the class's Zoom transcript (.vtt) instead." };
    if (f.size > MAX_VIDEO_FILE) return { ok: false, error: "Recordings up to 2 GB are supported." };
    return { ok: true, kind: "video" };
  }
  return { ok: false, error: "Unsupported file type. Use a .vtt/.txt transcript (or MP4/MOV/MKV/WEBM when the video worker is online)." };
}

export function checkText(t: string, max = MAX_TRANSCRIPT_CHARS): string | null {
  if (!t.trim()) return "Paste a transcript, choose a .vtt/.txt file, or give a link to one.";
  if (t.length > max) return `The transcript is ${t.length.toLocaleString("en")} characters; the limit is ${max.toLocaleString("en")}.`;
  return null;
}

export function checkUrl(u: string): string | null {
  const s = u.trim();
  if (!s) return "Enter a link.";
  if (s.length > 2048) return "That link is too long.";
  let p: URL;
  try { p = new URL(s); } catch { return "That is not a valid link."; }
  if (p.protocol !== "https:" && p.protocol !== "http:") return "Only http(s) links are supported.";
  if (/^(localhost|127\.|10\.|192\.168\.|169\.254\.|0\.0\.0\.0|\[::1\])/i.test(p.hostname)) return "Links to private or internal addresses are not allowed.";
  return null;
}
