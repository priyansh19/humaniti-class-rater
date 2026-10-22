"use client";
import { RotateCcw } from "lucide-react";
import { type AdvancedConfig, DEFAULT_CONFIG, validateConfig } from "@/lib/advanced";
import { CRITERIA, LABELS } from "@/lib/format";

const PROVIDERS: Array<[AdvancedConfig["provider"], string]> = [
  ["local", "Local rubric scorer (deterministic)"], ["auto", "Auto (first configured LLM, else local)"],
  ["openrouter", "OpenRouter"], ["openai", "OpenAI"], ["gemini", "Gemini"], ["anthropic", "Anthropic"],
];

export function ConfigPanel({ value, onChange, judgeAvailable }: { value: AdvancedConfig; onChange: (c: AdvancedConfig) => void; judgeAvailable: boolean }) {
  const err = validateConfig(value);
  const set = (p: Partial<AdvancedConfig>) => onChange({ ...value, ...p });
  return (
    <div className="space-y-5 rounded-2xl border border-slate-800 bg-slate-950 p-5 font-mono text-[13px] text-slate-200 shadow-xl">
      <div className="flex items-center justify-between">
        <span className="text-pink-400">// rater.config</span>
        <button className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white" onClick={() => onChange(DEFAULT_CONFIG)}><RotateCcw className="h-3 w-3" />reset</button>
      </div>
      <Field k="model">
        <select className="w-full rounded-md bg-slate-900 px-2 py-1.5 ring-1 ring-slate-700" value={value.provider} onChange={(e) => set({ provider: e.target.value as AdvancedConfig["provider"] })}>
          {PROVIDERS.map(([v, l]) => <option key={v} value={v}>{v}: {l}</option>)}
        </select>
        {!judgeAvailable && value.provider !== "local" && <p className="mt-1 text-amber-300">No LLM key on the hosted service, so this falls back to the local scorer (reported in judge).</p>}
      </Field>
      <Field k="thresholds">
        <div className="grid grid-cols-3 gap-2">
          {value.thresholds.map((t, i) => (
            <label key={i} className="space-y-1"><span className="text-slate-400">{LABELS[i]}→{LABELS[i + 1]}</span>
              <input type="number" step={0.1} min={1} max={5} value={t} className="w-full rounded-md bg-slate-900 px-2 py-1 ring-1 ring-slate-700"
                onChange={(e) => { const th = [...value.thresholds] as AdvancedConfig["thresholds"]; th[i] = Number(e.target.value); set({ thresholds: th }); }} /></label>
          ))}
        </div>
      </Field>
      <Field k="weights">
        <div className="space-y-1.5">
          {Object.entries(value.weights).map(([k, w]) => (
            <label key={k} className="grid grid-cols-[1fr_6rem_2rem] items-center gap-2">
              <span className="truncate text-sky-300" title={CRITERIA[k]?.hint}>{k}</span>
              <input type="range" min={0} max={5} step={0.5} value={w} onChange={(e) => set({ weights: { ...value.weights, [k]: Number(e.target.value) } })} />
              <span className="text-right text-amber-300">{w}</span>
            </label>
          ))}
        </div>
      </Field>
      <Field k="embeddings">
        <label className="flex items-center gap-2"><input type="checkbox" checked={value.embeddings} onChange={(e) => set({ embeddings: e.target.checked })} />
          <span>{String(value.embeddings)}</span><span className="text-slate-500">(semantic content coverage; needs the worker)</span></label>
      </Field>
      <Field k="max_chars">
        <input type="number" min={1000} max={1000000} step={1000} value={value.max_chars} onChange={(e) => set({ max_chars: Number(e.target.value) })} className="w-40 rounded-md bg-slate-900 px-2 py-1 ring-1 ring-slate-700" />
      </Field>
      {err && <p className="rounded-md bg-rose-950 px-2 py-1.5 text-rose-300">error: {err}</p>}
    </div>
  );
}
function Field({ k, children }: { k: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><div className="text-violet-300">{k}:</div>{children}</div>;
}
