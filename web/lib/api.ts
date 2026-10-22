import type { Health, Job, Report } from "./types";

export const WORKER_URL = (process.env.NEXT_PUBLIC_WORKER_URL || "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public status = 0) { super(message); }
}

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new ApiError("Could not reach the analysis service. Check your connection and try again.");
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try { const j = await res.json(); msg = j.detail || j.error || msg; } catch { /* non-JSON */ }
    throw new ApiError(msg, res.status);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({ method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });

export function workerConfigured(): boolean { return WORKER_URL.length > 0; }

export async function health(): Promise<Health | null> {
  if (!WORKER_URL) return null;
  try { return await call<Health>(`${WORKER_URL}/health`, { cache: "no-store" }); } catch { return null; }
}

export function planChunks(size: number, chunk: number): Array<[number, number, number]> {
  const out: Array<[number, number, number]> = [];
  for (let i = 0, start = 0; start < size; i++, start += chunk) out.push([i, start, Math.min(start + chunk, size)]);
  return out;
}

export async function withRetry<T>(fn: () => Promise<T>, tries = 4, baseMs = 800, sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))): Promise<T> {
  let last: unknown;
  for (let i = 0; i < tries; i++) {
    try { return await fn(); } catch (e) {
      last = e;
      if (e instanceof ApiError && e.status >= 400 && e.status < 500 && e.status !== 429) throw e;
      if (i < tries - 1) await sleep(baseMs * 2 ** i);
    }
  }
  throw last;
}

/** Resumable chunked upload straight to the worker; returns the job id. */
export async function uploadRecording(file: File, transcriptText: string | null, onProgress: (f: number) => void, signal?: AbortSignal): Promise<string> {
  const init = await call<{ upload_id: string; chunk_size: number; chunks: number }>(`${WORKER_URL}/uploads`, json({ filename: file.name, size: file.size }));
  const plan = planChunks(file.size, init.chunk_size);
  let done = 0;
  const queue = [...plan];
  const worker = async () => {
    while (queue.length) {
      if (signal?.aborted) throw new ApiError("Upload cancelled");
      const [n, a, b] = queue.shift()!;
      await withRetry(() => call(`${WORKER_URL}/uploads/${init.upload_id}/chunks/${n}`, { method: "PUT", body: file.slice(a, b), signal }));
      done += b - a;
      onProgress(done / file.size);
    }
  };
  await Promise.all([worker(), worker(), worker()]);
  const r = await call<{ job_id: string }>(`${WORKER_URL}/uploads/${init.upload_id}/complete`, json({ transcript_text: transcriptText }));
  return r.job_id;
}

export async function createLinkJob(url: string, transcriptUrl?: string, transcriptText?: string | null): Promise<string> {
  const r = await call<{ job_id: string }>(`${WORKER_URL}/jobs`, json({ url, transcript_url: transcriptUrl || null, transcript_text: transcriptText || null }));
  return r.job_id;
}

export async function getJob(id: string): Promise<Job> {
  return call<Job>(`${WORKER_URL}/jobs/${encodeURIComponent(id)}`, { cache: "no-store" });
}

/** Transcript-only assessment: worker if configured, otherwise the Vercel Python fallback. */
export async function assessTranscript(text: string | null, url: string | null): Promise<Report> {
  const body = { transcript_text: text || null, transcript_url: url || null };
  return WORKER_URL ? call<Report>(`${WORKER_URL}/assess/transcript`, json(body)) : call<Report>(`/api/py/assess`, json(body));
}
