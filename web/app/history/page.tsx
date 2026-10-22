"use client";
import { Download, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { ReportView } from "@/components/report-view";
import { Button } from "@/components/ui/primitives";
import { type HistoryItem, clearHistory, downloadText, loadHistory, toMarkdown } from "@/lib/advanced";
import { LABEL_STYLE } from "@/lib/format";

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => setItems(loadHistory()), []);
  const sel = items.find((i) => i.id === open);
  return (
    <div className="space-y-6 pt-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-3xl font-extrabold"><span className="rainbow-text">History</span></h1>
          <p className="text-sm text-slate-600">Your last 20 Advanced-mode runs. Stored only in this browser; the server keeps nothing.</p></div>
        {items.length > 0 && <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => downloadText("assessments.md", items.map((i) => `<!-- ${i.at} · ${i.name} -->\n` + toMarkdown(i.report)).join("\n---\n\n"), "text/markdown")}><Download className="h-3.5 w-3.5" />Export all</Button>
          <Button variant="outline" size="sm" onClick={() => { clearHistory(); setItems([]); }}><Trash2 className="h-3.5 w-3.5" />Clear</Button></div>}
      </div>
      {items.length === 0 ? <div className="rounded-2xl border-2 border-dashed border-amber-300 bg-amber-50 p-10 text-center text-sm text-amber-800">No runs yet. Assess a class in Advanced mode and it will appear here.</div> : (
        <ul className="grid gap-2 sm:grid-cols-2">
          {items.map((i) => (
            <li key={i.id}><button onClick={() => setOpen(open === i.id ? null : i.id)} className="flex w-full items-center justify-between rounded-xl border bg-white px-4 py-3 text-left shadow-sm hover:ring-2 hover:ring-pink-300">
              <span><span className="block font-medium">{i.name}</span><span className="text-xs text-slate-500">{new Date(i.at).toLocaleString()}</span></span>
              <span className={`rounded-lg px-2 py-0.5 text-sm font-semibold ${LABEL_STYLE[i.report.label]}`}>{i.report.label}{i.report.custom && i.report.custom.label !== i.report.label ? ` / ${i.report.custom.label}` : ""}</span>
            </button></li>
          ))}
        </ul>
      )}
      {sel && <ReportView report={sel.report} />}
    </div>
  );
}
