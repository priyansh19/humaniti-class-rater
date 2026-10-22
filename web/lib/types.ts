export type Label = "Poor" | "Average" | "Good" | "Excellent";
export interface Quote { t: number; speaker: string; quote: string }
export interface Criterion { score: number; rationale: string; evidence: Quote[] }
export interface Report {
  label: Label;
  confidence: number;
  summary: string;
  criteria: Record<string, Criterion>;
  strengths: string[];
  improvements: string[];
  metrics: Record<string, number>;
  judge: string;
  warnings: string[];
  analysis?: { duration_s: number; transcript_source: string; roles_estimated: boolean; features: Record<string, Record<string, number>> };
}
export type JobStatus = "queued" | "running" | "done" | "failed";
export interface Job {
  id: string; status: JobStatus; stage: string; progress: number; message: string; report: Report | null; queue_position?: number;
}
export interface Health { ok: boolean; version: string; judge: string; asr_model: string; max_upload_bytes: number; chunk_size: number }
