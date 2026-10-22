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
  content?: ContentMap;
  warnings: string[];
  analysis?: { duration_s: number; transcript_source: string; roles_estimated: boolean; features: Record<string, Record<string, number>> };
}
export type JobStatus = "queued" | "running" | "done" | "failed";
export interface Job {
  id: string; status: JobStatus; stage: string; progress: number; message: string; report: Report | null; queue_position?: number;
}
export interface Health { ok: boolean; version: string; judge: string; asr_model: string; max_upload_bytes: number; chunk_size: number }

export interface ContentTopic {
  topic: string; first_t: number; minutes: number; mentions?: number;
  explained: boolean; practised_turns: number; recapped: boolean; depth: number;
  evidence?: { t: number; speaker: string; quote: string }[];
}
export interface ContentMap {
  subject?: string; subject_confidence?: number; topics?: ContentTopic[]; metrics?: Record<string, number>;
  llm_subject?: string; llm_topics?: { topic: string; introduced_at: string; explained: boolean; practised: boolean; recapped: boolean; depth: number }[];
}
