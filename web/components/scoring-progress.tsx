"use client";
import { Check, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";

export const SCORING_STAGES = ["Checking the input", "Anonymising names", "Measuring talk & engagement", "Scoring the rubric", "Writing the explanation"];

/** Stage index for a request that has been running `ms`. Paces through stages and holds on the last until the response arrives. */
export function stageAt(ms: number, stepMs = 450): number {
  return Math.min(SCORING_STAGES.length - 1, Math.floor(Math.max(0, ms) / stepMs));
}

export function ScoringProgress() {
  const [ms, setMs] = useState(0);
  useEffect(() => { const t0 = Date.now(); const id = setInterval(() => setMs(Date.now() - t0), 100); return () => clearInterval(id); }, []);
  const cur = stageAt(ms);
  const pct = Math.min(95, ((cur + Math.min(1, (ms % 450) / 450)) / SCORING_STAGES.length) * 100);
  return (
    <div className="page-enter space-y-3 rounded-2xl border border-violet-200 bg-violet-50 p-4" role="status" aria-live="polite">
      <div className="h-1.5 overflow-hidden rounded-full bg-white">
        <div className="h-full rounded-full bg-gradient-to-r from-violet-600 via-pink-600 to-amber-500 transition-[width] duration-300" style={{ width: `${pct}%` }} />
      </div>
      <ol className="grid gap-1.5 sm:grid-cols-5">
        {SCORING_STAGES.map((s, i) => (
          <li key={s} className={cn("flex items-center gap-1.5 text-xs transition-opacity", i > cur ? "opacity-40" : "opacity-100")}>
            {i < cur ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : i === cur ? <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-600" /> : <span className="h-3.5 w-3.5 rounded-full border border-slate-300" />}
            <span className={cn(i === cur && "font-semibold text-violet-800")}>{s}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
