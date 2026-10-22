"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ReportView } from "@/components/report-view";
import { Alert } from "@/components/ui/primitives";
import type { Report } from "@/lib/types";

export default function TranscriptReport() {
  const [report, setReport] = useState<Report | null | undefined>(undefined);
  useEffect(() => {
    const raw = sessionStorage.getItem("transcript-report");
    setReport(raw ? (JSON.parse(raw) as Report) : null);
  }, []);
  return (
    <div className="space-y-6">
      <Link href="/" className="text-sm text-slate-600 hover:text-slate-900">← Assess another class</Link>
      {report === undefined && <div className="space-y-4"><div className="skeleton h-40" /><div className="grid gap-4 lg:grid-cols-5"><div className="skeleton h-72 lg:col-span-3" /><div className="skeleton h-72 lg:col-span-2" /></div></div>}
      {report === null && <Alert tone="info">No transcript assessment in this tab yet. <Link className="underline" href="/">Start one</Link>.</Alert>}
      {report && <ReportView report={report} />}
    </div>
  );
}
