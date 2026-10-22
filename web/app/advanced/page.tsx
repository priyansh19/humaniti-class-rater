"use client";
import { useState } from "react";
import { AssessForm } from "@/components/assess-form";
import { CapabilityBanner, useCapabilities } from "@/components/capability-banner";
import { ConfigPanel } from "@/components/config-panel";
import { ReportView } from "@/components/report-view";
import { Alert } from "@/components/ui/primitives";
import { ADV_LIMIT_PER_10_MIN, type AdvancedConfig, DEFAULT_CONFIG, addHistory, validateConfig } from "@/lib/advanced";
import { LABEL_STYLE } from "@/lib/format";
import type { Report } from "@/lib/types";

export default function AdvancedPage() {
  const caps = useCapabilities();
  const [cfg, setCfg] = useState<AdvancedConfig>(DEFAULT_CONFIG);
  const [report, setReport] = useState<Report | null>(null);
  const bad = validateConfig(cfg);
  return (
    <div className="space-y-6 pt-4">
      <div>
        <span className="rounded-full bg-pink-600 px-3 py-1 text-xs font-semibold text-white">Advanced mode</span>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight"><span className="rainbow-text">Tune the rater</span></h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">Change the model, cut-points, criterion weights and input cap. The <b>brief</b> answer is always computed with the defaults and shown next to your custom result, so tuning never changes the default rating. Runs are saved to History in this browser only. Limit: {ADV_LIMIT_PER_10_MIN} runs per 10 minutes.</p>
      </div>
      <CapabilityBanner compact />
      <div className="grid gap-6 lg:grid-cols-[22rem_1fr]">
        <ConfigPanel value={cfg} onChange={setCfg} judgeAvailable={!!caps && caps.judge !== "local"} />
        <div className="space-y-4">
          {bad ? <Alert tone="error">Fix the config first: {bad}</Alert> :
            <AssessForm advanced={cfg} onResult={(r, name) => { setReport(r); addHistory({ name, mode: "advanced", report: r }); }} />}
          {report?.custom && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Cmp title="Brief (default config)" label={report.label} sub={`judge: ${report.judge}`} />
              <Cmp title="Your config" label={report.custom.label} sub={`weighted score ${report.custom.score.toFixed(2)}`} />
            </div>
          )}
        </div>
      </div>
      {report && <ReportView report={report} />}
    </div>
  );
}
function Cmp({ title, label, sub }: { title: string; label: Report["label"]; sub: string }) {
  return <div className="rounded-2xl border bg-white p-4 shadow-sm"><div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</div>
    <div className={`mt-2 inline-block rounded-xl px-3 py-1 text-lg font-bold ${LABEL_STYLE[label]}`}>{label}</div><div className="mt-1 text-xs text-slate-500">{sub}</div></div>;
}
