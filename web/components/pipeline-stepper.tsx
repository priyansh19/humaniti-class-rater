"use client";
import { Ear, FileInput, Gauge, Scale } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/cn";

export const PIPELINE = [
  { key: "ingest", title: "Ingest", icon: FileInput, color: "bg-violet-600", ring: "ring-violet-300",
    body: "The browser sends the recording in resumable 8 MB chunks straight to the analysis worker, or the worker fetches a public link (Drive and Dropbox links are supported). On the hosted demo, a Zoom transcript is pasted, uploaded or linked instead.",
    facts: ["8 MB resumable chunks", "Drive / Dropbox links", "Transcript: .vtt / .txt ≤ 5 MB"] },
  { key: "listen", title: "Listen", icon: Ear, color: "bg-pink-600", ring: "ring-pink-300",
    body: "faster-whisper transcribes locally, or the Zoom VTT is used, which gives speaker labels. Names are replaced with Tutor / Student N before anything else happens.",
    facts: ["Local ASR (faster-whisper)", "Speaker labels from VTT", "Names anonymised first"] },
  { key: "measure", title: "Measure", icon: Gauge, color: "bg-amber-500", ring: "ring-amber-300",
    body: "Transcript features (student turns per minute, questions, greetings, new-joiner introductions, praise, homework, silences, AV complaints), audio features (silence, loudness, clipping) and frame features (screen layout, tutor camera off while speaking, face, lighting, 8x8 background).",
    facts: ["Talk & engagement", "Audio quality", "Camera, lighting, background"] },
  { key: "judge", title: "Judge", icon: Scale, color: "bg-emerald-600", ring: "ring-emerald-300",
    body: "A structured-JSON rubric judgement by Gemini, OpenAI or Anthropic (the organiser-approved APIs) or a fully local LLM. Cited timestamps are checked against the real evidence. A local heuristic scorer is the fallback, and it is what the hosted demo uses.",
    facts: ["Rubric JSON", "Timestamps verified", "Local scorer fallback"] },
] as const;

export function PipelineStepper() {
  const [i, setI] = useState(0);
  const s = PIPELINE[i];
  return (
    <div className="space-y-4">
      <ol className="relative grid grid-cols-4 gap-1" role="tablist" aria-label="Pipeline steps">
        <div className="absolute left-[12.5%] right-[12.5%] top-5 h-1 rounded-full bg-slate-200" aria-hidden />
        <div className="absolute left-[12.5%] top-5 h-1 rounded-full bg-gradient-to-r from-violet-600 via-pink-600 to-emerald-600 transition-[width] duration-500 ease-out" style={{ width: `${(i / 3) * 75}%` }} aria-hidden />
        {PIPELINE.map((p, j) => {
          const Icon = p.icon; const on = j === i; const done = j < i;
          return (
            <li key={p.key} className="relative flex flex-col items-center">
              <button role="tab" aria-label={`Step ${j + 1}: ${p.title}`} aria-selected={on} aria-controls="pipeline-panel" onClick={() => setI(j)}
                className={cn("tap relative grid h-11 w-11 place-items-center rounded-full text-white shadow-md ring-4 transition-all duration-300", on || done ? p.color : "bg-slate-300", on ? `${p.ring} scale-110` : "ring-transparent hover:scale-105")}>
                <Icon className="h-5 w-5" />
              </button>
              <span className={cn("mt-2 text-center text-[11px] font-semibold sm:text-sm", on ? "text-slate-900" : "text-slate-500")}>{j + 1}. {p.title}</span>
            </li>
          );
        })}
      </ol>
      <div id="pipeline-panel" role="tabpanel" key={s.key} className="page-enter rounded-2xl bg-slate-50 p-4">
        <p className="text-sm leading-relaxed text-slate-700">{s.body}</p>
        <div className="mt-3 flex flex-wrap gap-1.5">{s.facts.map((f) => <span key={f} className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200">{f}</span>)}</div>
        <div className="mt-3 flex justify-between">
          <button className="tap rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-white disabled:opacity-30" disabled={i === 0} onClick={() => setI(i - 1)}>← Back</button>
          <button className="tap rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-30" disabled={i === 3} onClick={() => setI(i + 1)}>Next →</button>
        </div>
      </div>
    </div>
  );
}
