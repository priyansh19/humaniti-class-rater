"use client";
import { Check, Loader2 } from "lucide-react";
import { Card, CardContent, Progress } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { STAGES } from "@/lib/format";
import type { Job } from "@/lib/types";

const ORDER = ["queued", "downloading", "probing", "transcribing", "audio", "frames", "judging", "done"];

export function JobProgress({ job }: { job: Job }) {
  const steps = STAGES.filter((s) => s.key !== "uploading" && (s.key !== "downloading" || job.stage === "downloading"));
  const cur = ORDER.indexOf(job.stage === "probing" ? "transcribing" : job.stage);
  return (
    <Card>
      <CardContent className="space-y-6 pt-6">
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <h2 className="text-lg font-semibold">Analysing the class…</h2>
            <span className="text-sm tabular-nums text-slate-600">{Math.round(job.progress * 100)}%</span>
          </div>
          <Progress value={job.progress * 100} />
          <p className="text-sm text-slate-500">
            {job.status === "queued" ? `Waiting in queue${job.queue_position ? ` (${job.queue_position} ahead)` : ""}…` :
              "A 60-minute class usually takes 5–10 minutes. You can leave this page open; the link keeps working."}
          </p>
        </div>
        <ol className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {steps.filter((s) => s.key !== "done").map((s) => {
            const idx = ORDER.indexOf(s.key);
            const state = idx < cur ? "done" : idx === cur ? "active" : "todo";
            return (
              <li key={s.key} className={cn("flex items-center gap-2 rounded-xl border px-3 py-2 text-sm", state === "active" ? "border-brand-500 bg-brand-50 text-brand-700" : state === "done" ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 text-slate-400")}>
                {state === "done" ? <Check className="h-4 w-4" /> : state === "active" ? <Loader2 className="h-4 w-4 animate-spin" /> : <span className="h-4 w-4 rounded-full border border-current" />}
                {s.title}
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
