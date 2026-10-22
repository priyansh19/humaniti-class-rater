"use client";
import { Cpu, KeyRound, Video } from "lucide-react";
import { useEffect, useState } from "react";
import { capabilities } from "@/lib/api";
import type { Capabilities } from "@/lib/types";

export function useCapabilities() {
  const [c, setC] = useState<Capabilities | null | undefined>(undefined);
  useEffect(() => { capabilities().then(setC); }, []);
  return c;
}

/** Says plainly what the hosted demo can and cannot do. Never blocks the transcript path. */
export function CapabilityBanner({ compact = false }: { compact?: boolean }) {
  const c = useCapabilities();
  if (c === undefined) return <div className="skeleton h-24 sm:h-16" />;
  const judge = c?.judge && c.judge !== "local" ? c.judge : null;
  return (
    <div className="stagger grid gap-2 rounded-2xl border border-violet-200 bg-gradient-to-r from-violet-50 via-pink-50 to-amber-50 p-3 text-sm sm:grid-cols-3">
      <Item icon={<Video className="h-4 w-4 text-pink-600" />} title={c?.video ? "Video analysis online" : "Transcript-only (hosted)"}
        body={c?.video ? "Recordings are processed on the worker." : "Video upload/link needs the analysis worker, which is not deployed. Paste or upload the Zoom transcript."} />
      <Item icon={<Cpu className="h-4 w-4 text-violet-600" />} title={judge ? `LLM judge: ${judge}` : "Local rubric scorer"}
        body={judge ? "Falls back to the local scorer if the LLM fails." : "No LLM key on the hosted service; the deterministic local scorer rates every class."} />
      {!compact && <Item icon={<KeyRound className="h-4 w-4 text-amber-600" />} title={c ? "Service healthy" : "Service unreachable"}
        body={c ? "See Status for exactly which keys unlock more." : "The assessment API did not respond. Try again shortly."} />}
    </div>
  );
}
function Item({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return <div className="flex gap-2 rounded-xl bg-white/70 p-2.5"><div className="mt-0.5">{icon}</div><div><div className="font-semibold text-slate-800">{title}</div><div className="text-xs text-slate-600">{body}</div></div></div>;
}
