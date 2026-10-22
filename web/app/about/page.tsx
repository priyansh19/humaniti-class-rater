import { BarChart3, ListChecks, Lock, Workflow } from "lucide-react";
import { PipelineStepper } from "@/components/pipeline-stepper";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/primitives";
import { BarChart, Collapsible } from "@/components/ui/motion";
import { EVAL_DATE, EVAL_SUMMARY } from "@/lib/eval";
import { CRITERIA } from "@/lib/format";

export const metadata = { title: "Method & evaluation · Class Quality Rater" };

export default function About() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl"><span className="rainbow-text">Method &amp; evaluation</span></h1>
        <p className="mt-1 text-sm text-slate-600">How a class becomes a rating. Tap a step.</p>
      </div>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Workflow className="h-4 w-4 text-violet-600" />Pipeline</CardTitle></CardHeader>
        <CardContent><PipelineStepper /></CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><BarChart3 className="h-4 w-4 text-pink-600" />Evaluation</CardTitle>
          <CardDescription>Leave-one-out on the 10 labelled sample classes (weak and quality-issue classes count as Poor, as approved by the organiser). With n = 10, one class is worth 10 points. {EVAL_DATE}.</CardDescription></CardHeader>
        <CardContent className="space-y-4">
          <BarChart rows={EVAL_SUMMARY.map((r) => ({ label: r.variant + (r.note ? ` (${r.note})` : ""), values: [
            { name: "exact", v: r.exact, color: "bg-gradient-to-r from-violet-500 to-pink-500" },
            { name: "±1", v: r.within1, color: "bg-gradient-to-r from-sky-400 to-emerald-400" },
          ] }))} />
          <p className="text-xs text-slate-500">Full tables, confusion matrices and superseded variants are in docs/EVAL.md. The LLM judge was not evaluated: no approved key was available.</p>
        </CardContent>
      </Card>
      <Collapsible title={`Rubric (${Object.keys(CRITERIA).length} criteria)`} icon={<ListChecks className="h-4 w-4 text-amber-600" />}>
        <p className="mb-3 text-sm text-slate-500">Every criterion comes from phrases in the organiser&apos;s feedback on the sample classes.</p>
        <ul className="stagger grid gap-2 sm:grid-cols-2">{Object.entries(CRITERIA).map(([k, c]) => (
          <li key={k} className="lift rounded-xl bg-slate-50 p-3 text-sm"><div className="font-medium">{c.title}</div><div className="text-slate-600">{c.hint}</div></li>
        ))}</ul>
      </Collapsible>
      <Collapsible title="Privacy" icon={<Lock className="h-4 w-4 text-emerald-600" />}>
        <div className="space-y-2 text-sm text-slate-700">
          <p>Recordings show children, so video, audio and frames are processed only on the analysis worker and deleted when the job finishes.</p>
          <p>The LLM receives only anonymised transcript excerpts (names replaced, emails and phone numbers redacted) and numeric features. A guard refuses to send any payload that contains a known name.</p>
        </div>
      </Collapsible>
    </div>
  );
}
