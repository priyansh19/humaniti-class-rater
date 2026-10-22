"use client";
import { FileVideo, Link2, Loader2, ScrollText, ShieldCheck, Upload, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { Alert, Button, Card, CardContent, Input, Progress, Textarea } from "@/components/ui/primitives";
import { WorkerStatus, useWorker } from "@/components/worker-status";
import { assessTranscript, createLinkJob, uploadRecording } from "@/lib/api";
import { cn } from "@/lib/cn";
import { fmtBytes } from "@/lib/format";

type Mode = "upload" | "link" | "transcript";
const MAX = 2 * 1024 ** 3;

export function AssessForm() {
  const router = useRouter();
  const worker = useWorker();
  const online = !!worker.health;
  const [mode, setMode] = useState<Mode>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [vtt, setVtt] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [tUrl, setTUrl] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const abort = useRef<AbortController | null>(null);

  const pick = (f: File | undefined | null) => {
    setError(null);
    if (!f) return;
    if (!/\.(mp4|mov|mkv|webm|m4v)$/i.test(f.name)) return setError("Please choose an MP4, MOV, MKV or WEBM recording.");
    if (f.size > MAX) return setError("Recordings up to 2 GB are supported.");
    setFile(f);
  };

  async function submit() {
    setError(null); setBusy(true); setProgress(0);
    try {
      if (mode === "transcript") {
        const raw = text.trim() || (vtt ? await vtt.text() : "");
        if (!raw && !tUrl.trim()) throw new Error("Paste a transcript, choose a VTT/TXT file, or give a link to one.");
        const report = await assessTranscript(raw || null, raw ? null : tUrl.trim());
        sessionStorage.setItem("transcript-report", JSON.stringify(report));
        router.push("/report");
        return;
      }
      const transcript = vtt ? await vtt.text() : null;
      let id: string;
      if (mode === "upload") {
        if (!file) throw new Error("Choose a recording first.");
        abort.current = new AbortController();
        id = await uploadRecording(file, transcript, setProgress, abort.current.signal);
      } else {
        if (!/^https?:\/\//i.test(url.trim())) throw new Error("Enter a public http(s) link to the recording.");
        id = await createLinkJob(url.trim(), tUrl.trim() || undefined, transcript);
      }
      router.push(`/jobs/${id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setBusy(false);
    }
  }

  const tabs: Array<{ key: Mode; label: string; icon: React.ReactNode; disabled?: boolean }> = [
    { key: "upload", label: "Upload recording", icon: <Upload className="h-4 w-4" />, disabled: !online },
    { key: "link", label: "Recording link", icon: <Link2 className="h-4 w-4" />, disabled: !online },
    { key: "transcript", label: "Transcript only", icon: <ScrollText className="h-4 w-4" /> },
  ];
  const effective: Mode = !online && mode !== "transcript" && !worker.loading ? "transcript" : mode;

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-3">
        <div className="flex gap-1 rounded-xl bg-slate-100 p-1" role="tablist">
          {tabs.map((t) => (
            <button key={t.key} role="tab" aria-selected={effective === t.key} disabled={t.disabled || busy} onClick={() => setMode(t.key)}
              className={cn("flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition", effective === t.key ? "bg-white font-medium text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900", t.disabled && "cursor-not-allowed opacity-40")}>
              {t.icon}{t.label}
            </button>
          ))}
        </div>
        <WorkerStatus {...worker} />
      </div>
      <CardContent className="space-y-4 pt-5">
        {effective === "upload" && (
          <label onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
            className={cn("checker flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition", drag ? "border-brand-500 bg-brand-50" : "border-slate-300 hover:border-brand-500")}>
            <input type="file" className="sr-only" accept="video/mp4,video/quicktime,video/x-matroska,video/webm,.mp4,.mov,.mkv,.webm" onChange={(e) => pick(e.target.files?.[0])} disabled={busy} />
            <FileVideo className="h-9 w-9 text-brand-600" />
            {file ? (
              <div className="text-sm"><span className="font-medium">{file.name}</span> <span className="text-slate-500">· {fmtBytes(file.size)}</span></div>
            ) : (
              <>
                <div className="text-sm font-medium">Drop a class recording here, or click to choose</div>
                <div className="text-xs text-slate-500">MP4, MOV, MKV or WEBM · up to 2 GB · 40–90 minute classes supported</div>
              </>
            )}
          </label>
        )}
        {effective === "link" && (
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="url">Public link to the recording</label>
            <Input id="url" placeholder="https://drive.google.com/file/d/…/view  or  https://…/class.mp4" value={url} onChange={(e) => setUrl(e.target.value)} disabled={busy} />
            <p className="text-xs text-slate-500">Google Drive and Dropbox share links work if they are shared as "anyone with the link".</p>
          </div>
        )}
        {effective === "transcript" && (
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="tx">Class transcript (Zoom VTT or "Speaker: text" lines)</label>
            <Textarea id="tx" placeholder={"WEBVTT\n\n1\n00:00:05.000 --> 00:00:08.000\nTutor: Good evening everyone!"} value={text} onChange={(e) => setText(e.target.value)} disabled={busy} />
            <Input placeholder="…or a public link to a .vtt / .txt transcript" value={tUrl} onChange={(e) => setTUrl(e.target.value)} disabled={busy} />
            <Alert tone="warn">Transcript mode cannot see the camera, background or lighting. Those criteria are not scored.</Alert>
          </div>
        )}
        {effective !== "transcript" || !text ? (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-300 px-3 py-1.5 hover:bg-slate-50">
              <ScrollText className="h-4 w-4 text-slate-500" />
              <span>{vtt ? vtt.name : effective === "transcript" ? "Choose VTT/TXT file" : "Optional: add the Zoom VTT transcript (faster, speaker-aware)"}</span>
              <input type="file" accept=".vtt,.txt,text/vtt,text/plain" className="sr-only" onChange={(e) => setVtt(e.target.files?.[0] ?? null)} disabled={busy} />
            </label>
            {vtt && <button className="text-slate-500 hover:text-slate-900" onClick={() => setVtt(null)} aria-label="Remove transcript"><X className="h-4 w-4" /></button>}
          </div>
        ) : null}
        {busy && effective === "upload" && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-600"><span>Uploading securely in chunks…</span><span>{Math.round(progress * 100)}%</span></div>
            <Progress value={progress * 100} />
          </div>
        )}
        {error && <Alert tone="error">{error}</Alert>}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <p className="flex items-center gap-1.5 text-xs text-slate-500"><ShieldCheck className="h-4 w-4 text-emerald-600" /> Video never leaves the analysis worker; it is deleted after the job.</p>
          <div className="flex gap-2">
            {busy && effective === "upload" && <Button variant="outline" onClick={() => { abort.current?.abort(); setBusy(false); }}>Cancel</Button>}
            <Button size="lg" onClick={submit} disabled={busy || (effective === "upload" && !file)}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {busy ? "Working…" : "Assess class"}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
