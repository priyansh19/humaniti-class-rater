"use client";
import Link from "next/link";
import { use, useEffect, useRef, useState } from "react";
import { JobProgress } from "@/components/job-progress";
import { ReportView } from "@/components/report-view";
import { Alert, Button } from "@/components/ui/primitives";
import { getJob } from "@/lib/api";
import type { Job } from "@/lib/types";

export default function JobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const misses = useRef(0);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const j = await getJob(id);
        if (!alive) return;
        misses.current = 0; setJob(j); setError(null);
        if (j.status === "done" || j.status === "failed") return;
      } catch (e) {
        misses.current += 1;
        if (misses.current > 5) setError(e instanceof Error ? e.message : "Lost contact with the analysis worker.");
      }
      timer = setTimeout(tick, 3000);
    };
    tick();
    return () => { alive = false; clearTimeout(timer); };
  }, [id]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-sm text-slate-600 hover:text-slate-900">← Assess another class</Link>
        <span className="font-mono text-xs text-slate-400">job {id}</span>
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      {!job && !error && <div className="h-40 animate-pulse rounded-2xl bg-slate-200/60" />}
      {job && (job.status === "queued" || job.status === "running") && <JobProgress job={job} />}
      {job?.status === "failed" && (
        <Alert tone="error"><div className="space-y-3"><p><b>The assessment failed.</b> {job.message}</p><Link href="/"><Button variant="outline" size="sm">Try again</Button></Link></div></Alert>
      )}
      {job?.status === "done" && job.report && <ReportView report={job.report} />}
    </div>
  );
}
