"use client";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/primitives";
import { health, workerConfigured } from "@/lib/api";
import type { Health } from "@/lib/types";

export function useWorker() {
  const [state, setState] = useState<{ loading: boolean; health: Health | null }>({ loading: workerConfigured(), health: null });
  useEffect(() => {
    if (!workerConfigured()) return;
    let alive = true;
    health().then((h) => alive && setState({ loading: false, health: h }));
    return () => { alive = false; };
  }, []);
  return state;
}

export function WorkerStatus({ loading, health: h }: { loading: boolean; health: Health | null }) {
  if (loading) return <Badge className="bg-slate-50 text-slate-600 ring-slate-200">Checking analysis worker…</Badge>;
  if (h) return (
    <Badge className="bg-emerald-50 text-emerald-700 ring-emerald-200">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Worker online · judge: {h.judge} · ASR: whisper-{h.asr_model}
    </Badge>
  );
  return (
    <Badge className="bg-amber-50 text-amber-800 ring-amber-200">
      <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> Video worker offline: transcript mode only
    </Badge>
  );
}
