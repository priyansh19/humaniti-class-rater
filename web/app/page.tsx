import { AssessForm } from "@/components/assess-form";

export default function Home() {
  return (
    <div className="space-y-8">
      <section className="space-y-3 pt-4">
        <span className="inline-block rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700 ring-1 ring-brand-100">8x8 · kids&apos; online chess classes</span>
        <h1 className="max-w-3xl text-3xl font-bold tracking-tight sm:text-4xl">How good was this class?</h1>
        <p className="max-w-2xl text-slate-600">
          Upload a class recording or share a link. The analysis covers what was said, how the class sounded and what was on screen, then rates it
          <b> Poor, Average, Good or Excellent</b> against a rubric built from the organiser&apos;s own tutor feedback. Every reason is tied to a timestamp.
        </p>
      </section>
      <AssessForm />
      <section className="grid gap-4 sm:grid-cols-3">
        {[
          ["Listens", "Local Whisper transcription; who talks, how often children respond, questions, praise, homework, dead air."],
          ["Watches", "Frame sampling: camera-off moments while the tutor speaks, face visibility, lighting, 8x8 background, screen sharing."],
          ["Judges", "A structured rubric judgement with timestamped evidence. Only anonymised text and numbers reach the LLM."],
        ].map(([t, d]) => (
          <div key={t} className="rounded-2xl border border-slate-200 bg-white p-4"><div className="font-semibold">{t}</div><p className="mt-1 text-sm text-slate-600">{d}</p></div>
        ))}
      </section>
    </div>
  );
}
