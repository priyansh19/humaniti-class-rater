import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/primitives";
import { CRITERIA } from "@/lib/format";
import { EVAL_DATE, EVAL_SUMMARY } from "@/lib/eval";

export const metadata = { title: "Method & evaluation · Class Quality Rater" };

export default function About() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Method &amp; evaluation</h1>
      <Card>
        <CardHeader><CardTitle>Pipeline</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm text-slate-700">
          <p><b>1. Ingest.</b> The browser sends the recording in resumable 8 MB chunks straight to the analysis worker, or the worker fetches a public link (Drive and Dropbox links are supported).</p>
          <p><b>2. Listen.</b> faster-whisper transcribes locally (or the Zoom VTT is used, which gives speaker labels). Names are replaced with Tutor / Student N before anything else happens.</p>
          <p><b>3. Measure.</b> Transcript features (student turns per minute, questions, greetings, new-joiner introductions, praise, homework, silences, AV complaints), audio features (silence, loudness, clipping) and frame features (screen layout, tutor camera off while speaking, face, lighting, 8x8 background).</p>
          <p><b>4. Judge.</b> A structured-JSON rubric judgement by Gemini, OpenAI or Anthropic (the organiser-approved APIs) or a fully local LLM. Cited timestamps are checked against the real evidence. A local heuristic scorer is the fallback.</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Rubric</CardTitle><CardDescription>Every criterion comes from phrases in the organiser&apos;s feedback on the sample classes.</CardDescription></CardHeader>
        <CardContent><ul className="grid gap-2 sm:grid-cols-2">{Object.entries(CRITERIA).map(([k, c]) => (
          <li key={k} className="rounded-xl bg-slate-50 p-3 text-sm"><div className="font-medium">{c.title}</div><div className="text-slate-600">{c.hint}</div></li>
        ))}</ul></CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Evaluation</CardTitle><CardDescription>Leave-one-out on the 10 labelled sample classes (weak and quality-issue classes count as Poor, as approved by the organiser). With n = 10, one class is worth 10 points.{EVAL_DATE ? ` Run ${EVAL_DATE}.` : ""}</CardDescription></CardHeader>
        <CardContent>
          {EVAL_SUMMARY.length === 0 ? <p className="text-sm text-slate-500">See docs/EVAL.md in the repository.</p> : (
            <table className="w-full text-left text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2">Variant</th><th>Exact</th><th>Within ±1</th><th>Note</th></tr></thead>
              <tbody>{EVAL_SUMMARY.map((r) => <tr key={r.variant} className="border-t border-slate-100"><td className="py-2 pr-2">{r.variant}</td><td className="tabular-nums">{r.exact}</td><td className="tabular-nums">{r.within1}</td><td className="text-slate-500">{r.note}</td></tr>)}</tbody></table>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Privacy</CardTitle></CardHeader>
        <CardContent className="space-y-1 text-sm text-slate-700">
          <p>Recordings show children, so video, audio and frames are processed only on the analysis worker and deleted when the job finishes.</p>
          <p>The LLM receives only anonymised transcript excerpts (names replaced, emails and phone numbers redacted) and numeric features. A guard refuses to send any payload that contains a known name.</p>
        </CardContent>
      </Card>
    </div>
  );
}
