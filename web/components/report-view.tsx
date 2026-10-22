"use client";
import { downloadText, toMarkdown } from "@/lib/advanced";
import { AlertTriangle, FileDown, CheckCircle2, Clock, Download, Lightbulb, MessageSquareQuote, TrendingUp } from "lucide-react";
import { Alert, Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Progress } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { CRITERIA, LABELS, LABEL_STYLE, fmtTs, judgeLabel, scoreColor } from "@/lib/format";
import type { Report } from "@/lib/types";

const METRIC_NAMES: Record<string, string> = {
  duration_min: "Class length (min)", student_turns_per_min: "Student turns / min", students_speaking: "Students who spoke",
  tutor_questions_per_min: "Tutor questions / min", praise_per_min: "Praise cues / min", long_gaps_30s: "Silences > 30 s", homework_cues: "Homework mentions",
};

export function ReportView({ report }: { report: Report }) {
  const crit = Object.entries(report.criteria);
  const merged = new Map<string, { t: number; speaker: string; quote: string; ks: string[] }>();
  for (const [k, c] of crit) for (const q of c.evidence) {
    const key = `${q.t}|${q.quote}`;
    const cur = merged.get(key);
    if (cur) { if (!cur.ks.includes(k)) cur.ks.push(k); } else merged.set(key, { ...q, ks: [k] });
  }
  const timeline = [...merged.values()].sort((a, b) => a.t - b.t);
  const download = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `class-assessment-${report.label.toLowerCase()}.json` });
    a.click(); URL.revokeObjectURL(a.href);
  };
  const isLocal = report.judge === "local";
  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="flex flex-col gap-6 pt-6 md:flex-row md:items-center">
          <div className="flex flex-col items-start gap-2 md:w-64">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-500">Overall rating</span>
            <span className={cn("rounded-2xl px-5 py-2 text-3xl font-bold ring-1 ring-inset", LABEL_STYLE[report.label])}>{report.label}</span>
            <div className="flex w-full gap-1" aria-hidden>
              {LABELS.map((l) => <div key={l} className={cn("h-1.5 flex-1 rounded-full", LABELS.indexOf(l) <= LABELS.indexOf(report.label) ? "bg-brand-600" : "bg-slate-200")} />)}
            </div>
            <div className="w-full text-xs text-slate-500">Confidence {Math.round(report.confidence * 100)}%<Progress value={report.confidence * 100} className="mt-1 h-1.5" /></div>
          </div>
          <div className="flex-1 space-y-3">
            <p className="text-lg leading-relaxed text-slate-800">{report.summary}</p>
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-slate-50 text-slate-700 ring-slate-200">{judgeLabel(report.judge)}</Badge>
              {report.analysis && <Badge className="bg-slate-50 text-slate-700 ring-slate-200"><Clock className="h-3 w-3" />{Math.round(report.analysis.duration_s / 60)} min · transcript: {report.analysis.transcript_source}{report.analysis.roles_estimated ? " (roles estimated)" : ""}</Badge>}
              <Button variant="outline" size="sm" onClick={download}><Download className="h-3.5 w-3.5" /> JSON</Button>
              <Button variant="outline" size="sm" onClick={() => downloadText(`class-assessment-${report.label.toLowerCase()}.md`, toMarkdown(report), "text/markdown")}><FileDown className="h-3.5 w-3.5" /> Markdown</Button>
            </div>
            {isLocal && <Alert tone="warn">Scored by the local heuristic scorer (no LLM key configured). Its labels are indicative only. See Method &amp; eval.</Alert>}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader><CardTitle>Rubric scorecard</CardTitle><CardDescription>Criteria derived from the organiser&apos;s own tutor feedback. Scored 1–5.</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            {crit.map(([k, c]) => (
              <div key={k} className="space-y-1.5">
                <div className="flex items-baseline justify-between gap-2">
                  <div><div className="text-sm font-medium">{CRITERIA[k]?.title ?? k}</div><div className="text-xs text-slate-500">{CRITERIA[k]?.hint}</div></div>
                  <span className="shrink-0 text-sm font-semibold tabular-nums">{c.score}/5</span>
                </div>
                <div className="flex gap-1" aria-label={`${c.score} out of 5`}>
                  {[1, 2, 3, 4, 5].map((i) => <div key={i} className={cn("h-2 flex-1 rounded-full", i <= c.score ? scoreColor(c.score) : "bg-slate-100")} />)}
                </div>
                <p className="text-sm text-slate-600">{c.rationale}</p>
              </div>
            ))}
            {!report.criteria.presentation && <p className="text-xs text-slate-500">Camera/background/lighting was not assessed (no video was analysed).</p>}
          </CardContent>
        </Card>

        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><Lightbulb className="h-4 w-4 text-amber-500" />What to improve</CardTitle></CardHeader>
            <CardContent><ol className="space-y-3">{report.improvements.map((s, i) => (
              <li key={i} className="flex gap-3 text-sm"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-amber-100 text-xs font-semibold text-amber-800">{i + 1}</span><span className="text-slate-700">{s}</span></li>
            ))}</ol></CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" />What went well</CardTitle></CardHeader>
            <CardContent><ul className="space-y-2">{report.strengths.map((s, i) => <li key={i} className="text-sm text-slate-700">• {s}</li>)}</ul></CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><TrendingUp className="h-4 w-4 text-brand-600" />Key metrics</CardTitle></CardHeader>
            <CardContent><dl className="grid grid-cols-2 gap-3">{Object.entries(report.metrics).map(([k, v]) => (
              <div key={k} className="rounded-xl bg-slate-50 p-3"><dt className="text-xs text-slate-500">{METRIC_NAMES[k] ?? k}</dt><dd className="text-lg font-semibold tabular-nums">{Number.isInteger(v) ? v : v.toFixed(2)}</dd></div>
            ))}</dl></CardContent>
          </Card>
        </div>
      </div>

      {report.content?.topics && report.content.topics.length > 0 && <ContentCard content={report.content} />}

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><MessageSquareQuote className="h-4 w-4 text-brand-600" />Evidence timeline</CardTitle><CardDescription>Anonymised quotes from the class, linked to the criterion they support.</CardDescription></CardHeader>
        <CardContent>
          {timeline.length === 0 ? <p className="text-sm text-slate-500">No quotes were cited.</p> : (
            <ol className="relative space-y-4 border-l border-slate-200 pl-6">
              {timeline.map((q, i) => (
                <li key={i} className="relative">
                  <span className="absolute -left-[31px] top-1 h-2.5 w-2.5 rounded-full bg-brand-500 ring-4 ring-white" />
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="font-mono font-semibold text-slate-700">{fmtTs(q.t)}</span>
                    {q.ks.map((k) => <Badge key={k} className="bg-brand-50 text-brand-700 ring-brand-100">{CRITERIA[k]?.title ?? k}</Badge>)}
                    <span className="text-slate-500">{q.speaker}</span>
                  </div>
                  <blockquote className="mt-1 text-sm text-slate-800">“{q.quote}”</blockquote>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>

      {report.guard_flags && report.guard_flags.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-xs"><span className="font-semibold text-slate-600">Input checks:</span>
          {report.guard_flags.map((f) => <span key={f} className="rounded-full bg-amber-100 px-2.5 py-1 font-medium text-amber-800 ring-1 ring-amber-200">{f.replace(/_/g, " ")}</span>)}
        </div>
      )}
      {report.warnings.length > 0 && (
        <Alert tone="warn"><div className="flex gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><ul className="space-y-1">{report.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></div></Alert>
      )}
    </div>
  );
}

function Stage({ on, label }: { on: boolean; label: string }) {
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${on ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200" : "bg-slate-50 text-slate-400 ring-1 ring-slate-200"}`}>{label}</span>;
}

function ContentCard({ content }: { content: NonNullable<Report["content"]> }) {
  const topics = content.topics ?? [];
  const max = Math.max(...topics.map((t) => t.minutes), 1);
  const subject = content.llm_subject || content.subject || "unknown";
  return (
    <Card>
      <CardHeader>
        <CardTitle>Lesson content coverage</CardTitle>
        <CardDescription>Subject: <span className="font-medium capitalize text-slate-700">{subject}</span>. Time per topic and how far each one got. Depth is scored 0–3: mentioned, explained, practised, recapped.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {topics.map((t) => (
          <div key={t.topic} className="space-y-1.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-medium capitalize text-slate-800">{t.topic} <span className="font-normal text-slate-400">· from {fmtTs(t.first_t)}</span></span>
              <div className="flex gap-1.5"><Stage on label="Introduced" /><Stage on={t.explained} label="Explained" /><Stage on={t.practised_turns > 0} label="Practised" /><Stage on={t.recapped} label="Recapped" /></div>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-brand-500" style={{ width: `${(100 * t.minutes) / max}%` }} /></div>
              <span className="w-24 text-right text-xs tabular-nums text-slate-500">{t.minutes.toFixed(1)} min · depth {t.depth}/3</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
