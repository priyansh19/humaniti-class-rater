import { AssessForm } from "@/components/assess-form";
import { CapabilityBanner } from "@/components/capability-banner";

const STEPS = [
  ["1 · Reads", "Speaker-labelled Zoom transcript: who talks, how often children respond, questions, praise, homework, long silences.", "from-violet-500 to-fuchsia-500"],
  ["2 · Scores", "Rubric criteria taken from the organiser's own tutor feedback, each scored 1–5 with the numbers behind it.", "from-pink-500 to-rose-500"],
  ["3 · Explains", "One of Poor, Average, Good or Excellent, with timestamped, anonymised quotes and concrete improvements.", "from-amber-400 to-orange-500"],
];

export default function Home() {
  return (
    <div className="space-y-8">
      <section className="space-y-3 pt-4">
        <span className="inline-block rounded-full bg-gradient-to-r from-violet-600 to-pink-600 px-3 py-1 text-xs font-semibold text-white shadow">8x8 · kids&apos; online chess classes</span>
        <h1 className="max-w-3xl text-[28px] font-extrabold leading-tight tracking-tight sm:text-5xl">How good was <span className="rainbow-text">this class?</span></h1>
        <p className="max-w-2xl text-slate-600">
          Give it a class and get a rating of <b className="text-rose-600">Poor</b>, <b className="text-amber-600">Average</b>, <b className="text-sky-600">Good</b> or <b className="text-emerald-600">Excellent</b>, with specific, evidence-based reasons.
        </p>
      </section>
      <CapabilityBanner />
      <AssessForm />
      <section className="stagger grid gap-3 sm:grid-cols-3 sm:gap-4">
        {STEPS.map(([t, d, g]) => (
          <div key={t} className="lift overflow-hidden rounded-2xl border border-white bg-white/80 shadow-sm">
            <div className={`h-1.5 bg-gradient-to-r ${g}`} />
            <div className="p-4"><div className="font-semibold">{t}</div><p className="mt-1 text-sm text-slate-600">{d}</p></div>
          </div>
        ))}
      </section>
    </div>
  );
}
