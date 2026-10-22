"use client";
import { ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton", className)} aria-hidden />;
}

export function Collapsible({ title, icon, defaultOpen = false, children, className }: { title: React.ReactNode; icon?: React.ReactNode; defaultOpen?: boolean; children: React.ReactNode; className?: string }) {
  return (
    <details open={defaultOpen} className={cn("group rounded-2xl border border-slate-200 bg-white shadow-sm", className)}>
      <summary className="tap flex cursor-pointer items-center justify-between gap-3 rounded-2xl px-4 py-3.5 hover:bg-slate-50 sm:px-5">
        <span className="flex min-w-0 items-center gap-2 font-semibold text-slate-900">{icon}{title}</span>
        <ChevronDown className="chev h-4 w-4 shrink-0 text-slate-500 transition-transform duration-200" />
      </summary>
      <div className="px-4 pb-4 sm:px-5 sm:pb-5">{children}</div>
    </details>
  );
}

/** Animates 0 → value once the element scrolls into view. Returns the final value immediately under reduced motion. */
export function useCountUp(value: number, ms = 700) {
  const [v, setV] = useState(0);
  const ref = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    const reduce = typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || !el || typeof IntersectionObserver === "undefined") { setV(value); return; }
    let raf = 0;
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const t0 = performance.now();
      const tick = (t: number) => { const p = Math.min(1, (t - t0) / ms); setV(value * (1 - Math.pow(1 - p, 3))); if (p < 1) raf = requestAnimationFrame(tick); };
      raf = requestAnimationFrame(tick);
    });
    io.observe(el);
    return () => { io.disconnect(); cancelAnimationFrame(raf); };
  }, [value, ms]);
  return [v, ref] as const;
}

export function CountUp({ value, suffix = "", decimals = 0 }: { value: number; suffix?: string; decimals?: number }) {
  const [v, ref] = useCountUp(value);
  return <span ref={ref as React.RefObject<HTMLSpanElement>} className="tabular-nums">{v.toFixed(decimals)}{suffix}</span>;
}

/** Horizontal bar chart; bars grow in on mount. */
export function BarChart({ rows, max = 100, suffix = "%" }: { rows: Array<{ label: string; values: Array<{ v: number; color: string; name: string }> }>; max?: number; suffix?: string }) {
  return (
    <div className="space-y-3">
      {rows.map((r) => (
        <div key={r.label} className="space-y-1">
          <div className="text-xs font-medium text-slate-700 sm:text-sm">{r.label}</div>
          {r.values.map((x) => (
            <div key={x.name} className="flex items-center gap-2">
              <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div className={cn("grow-x h-full rounded-full", x.color)} style={{ width: `${(x.v / max) * 100}%` }} />
              </div>
              <span className="w-20 shrink-0 text-right text-xs tabular-nums text-slate-600">{x.name} <b>{x.v}{suffix}</b></span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
