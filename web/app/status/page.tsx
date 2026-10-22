"use client";
import { CheckCircle2, XCircle } from "lucide-react";
import { useCapabilities } from "@/components/capability-banner";

export default function StatusPage() {
  const c = useCapabilities();
  const rows: Array<[string, boolean, string]> = c ? [
    ["Transcript assessment (local scorer)", true, "Always available."],
    ["LLM judge", c.judge !== "local", c.missing.llm_judge ?? `Active: ${c.judge}`],
    ["Video upload / link", c.video, c.missing.video_processing],
    ["Embeddings (semantic coverage)", c.embeddings, c.missing.embeddings],
  ] : [];
  return (
    <div className="space-y-6 pt-4">
      <h1 className="text-3xl font-extrabold"><span className="rainbow-text">Service status</span></h1>
      {c === undefined ? <div className="space-y-2"><div className="skeleton h-16" /><div className="skeleton h-16" /><div className="skeleton h-16" /><div className="skeleton h-16" /></div> : c === null ?
        <div className="rounded-2xl bg-rose-50 p-6 text-rose-800">The assessment API is unreachable right now.</div> : (
        <div className="overflow-hidden rounded-2xl border bg-white shadow-sm">
          {rows.map(([name, ok, note]) => (
            <div key={name} className="flex items-start gap-3 border-b px-5 py-4 last:border-0">
              {ok ? <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-500" /> : <XCircle className="mt-0.5 h-5 w-5 text-rose-500" />}
              <div><div className="font-semibold">{name}</div><div className="text-sm text-slate-600">{ok ? note : `Needs: ${note}`}</div></div>
            </div>
          ))}
          <div className="bg-slate-50 px-5 py-3 text-xs text-slate-500">mode: {c.mode} · judge: {c.judge}</div>
        </div>)}
    </div>
  );
}
