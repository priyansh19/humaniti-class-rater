"use client";
import { FileText, FileVideo, Link2, Loader2, ScrollText, ShieldCheck, Sparkles, Upload, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { Alert, Button, Card, CardContent, Input, Progress, Textarea } from "@/components/ui/primitives";
import { WorkerStatus, useWorker } from "@/components/worker-status";
import type { AdvancedConfig } from "@/lib/advanced";
import { ApiError, assessTranscript, createLinkJob, uploadRecording } from "@/lib/api";
import { cn } from "@/lib/cn";
import { fmtBytes } from "@/lib/format";
import type { Report } from "@/lib/types";
import { checkFile, checkText, checkUrl } from "@/lib/validate";

type Mode = "transcript" | "upload" | "link";
const SAMPLE = `WEBVTT

00:00:05.000 --> 00:00:09.000
Tutor: Good evening everyone! How was your week?

00:00:10.000 --> 00:00:12.000
Student A: Good! I solved three puzzles.

00:00:13.000 --> 00:00:20.000
Tutor: Excellent, well done! Today we learn the knight fork. What does a fork attack?

00:00:21.000 --> 00:00:24.000
Student B: Two pieces at the same time!

00:00:25.000 --> 00:00:34.000
Tutor: Great job. Let's set up the board. Everyone, find the fork in this position.`;

export function AssessForm({ advanced, onResult }: { advanced?: AdvancedConfig; onResult?: (r: Report, name: string) => void }) {
  const router = useRouter();
  const worker = useWorker();
  const online = !!worker.health;
  const [mode, setMode] = useState<Mode>("transcript");
  const [file, setFile] = useState<File | null>(null);
  const [tFile, setTFile] = useState<File | null>(null);
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
    const c = checkFile(f, online);
    if (!c.ok) return setError(c.error);
    if (c.kind === "video") { setFile(f); setMode("upload"); } else { setTFile(f); setText(""); }
  };

  async function submit() {
    setError(null); setBusy(true); setProgress(0);
    try {
      if (mode === "transcript") {
        const raw = text.trim() ? text : tFile ? await tFile.text() : "";
        if (!raw.trim() && tUrl.trim()) {
          const e = checkUrl(tUrl); if (e) throw new Error(e);
        } else {
          const e = checkText(raw, advanced?.max_chars); if (e) throw new Error(e);
        }
        const report = await assessTranscript(raw.trim() ? raw : null, raw.trim() ? null : tUrl.trim(), advanced);
        const name = tFile?.name || (tUrl.trim() ? tUrl.trim().split("/").pop() || "linked transcript" : "pasted transcript");
        if (onResult) { onResult(report, name); setBusy(false); return; }
        sessionStorage.setItem("transcript-report", JSON.stringify(report));
        router.push("/report");
        return;
      }
      const transcript = tFile ? await tFile.text() : null;
      let id: string;
      if (mode === "upload") {
        if (!file) throw new Error("Choose a recording first.");
        abort.current = new AbortController();
        id = await uploadRecording(file, transcript, setProgress, abort.current.signal);
      } else {
        const e = checkUrl(url); if (e) throw new Error(e);
        id = await createLinkJob(url.trim(), tUrl.trim() || undefined, transcript);
      }
      router.push(`/jobs/${id}`);
    } catch (e) {
      const msg = e instanceof ApiError && e.status === 429 ? "Rate limit reached. Please wait a few minutes before the next assessment." : e instanceof Error ? e.message : "Something went wrong.";
      setError(msg);
      setBusy(false);
    }
  }

  const tabs: Array<{ key: Mode; label: string; icon: React.ReactNode; disabled?: boolean }> = [
    { key: "transcript", label: "Transcript", icon: <ScrollText className="h-4 w-4" /> },
    { key: "upload", label: "Upload video", icon: <Upload className="h-4 w-4" />, disabled: !online },
    { key: "link", label: "Video link", icon: <Link2 className="h-4 w-4" />, disabled: !online },
  ];

  return (
    <Card className="overflow-hidden border-violet-200 shadow-lg shadow-violet-100">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-violet-100 bg-gradient-to-r from-violet-50 to-pink-50 px-5 py-3">
        <div className="flex gap-1 rounded-xl bg-white/80 p-1 ring-1 ring-violet-100" role="tablist">
          {tabs.map((t) => (
            <button key={t.key} role="tab" aria-selected={mode === t.key} disabled={t.disabled || busy} onClick={() => setMode(t.key)}
              title={t.disabled ? "Needs the video analysis worker (offline on the hosted demo)" : undefined}
              className={cn("flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition", mode === t.key ? "bg-violet-600 font-medium text-white shadow" : "text-slate-600 hover:text-violet-800", t.disabled && "cursor-not-allowed opacity-40")}>
              {t.icon}{t.label}
            </button>
          ))}
        </div>
        <WorkerStatus {...worker} />
      </div>
      <CardContent className="space-y-4 pt-5">
        {mode === "transcript" && (
          <div className="space-y-3">
            <label onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
              className={cn("checker flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-2xl border-2 border-dashed px-6 py-6 text-center transition", drag ? "border-pink-500 bg-pink-50" : "border-violet-300 hover:border-pink-400")}>
              <input type="file" className="sr-only" accept=".vtt,.txt,.srt,text/vtt,text/plain,video/*" onChange={(e) => pick(e.target.files?.[0])} disabled={busy} />
              <FileText className="h-8 w-8 text-violet-600" />
              {tFile ? (
                <div className="flex items-center gap-2 text-sm"><span className="font-medium">{tFile.name}</span><span className="text-slate-500">· {fmtBytes(tFile.size)}</span>
                  <button type="button" onClick={(e) => { e.preventDefault(); setTFile(null); }} aria-label="Remove file"><X className="h-4 w-4 text-slate-500" /></button></div>
              ) : (
                <><div className="text-sm font-medium">Drop the Zoom transcript (.vtt / .txt) here, or click to choose</div><div className="text-xs text-slate-500">Up to 5 MB · speaker labels optional</div></>
              )}
            </label>
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium" htmlFor="tx">…or paste it</label>
              <button type="button" className="inline-flex items-center gap-1 text-xs font-medium text-pink-700 hover:underline" onClick={() => { setText(SAMPLE); setTFile(null); }} disabled={busy}><Sparkles className="h-3.5 w-3.5" />Try a tiny sample</button>
            </div>
            <Textarea id="tx" placeholder={"WEBVTT\n\n00:00:05.000 --> 00:00:08.000\nTutor: Good evening everyone!"} value={text} onChange={(e) => { setText(e.target.value); if (e.target.value) setTFile(null); }} disabled={busy} />
            <Input placeholder="…or a public link to a .vtt / .txt transcript" value={tUrl} onChange={(e) => setTUrl(e.target.value)} disabled={busy} aria-label="Transcript link" />
            <Alert tone="info">Transcript mode cannot see the camera, background or lighting, so those criteria are not scored.</Alert>
          </div>
        )}
        {mode === "upload" && (
          <label onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
            className={cn("checker flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-6 py-10 text-center", drag ? "border-pink-500 bg-pink-50" : "border-violet-300")}>
            <input type="file" className="sr-only" accept="video/mp4,video/quicktime,video/x-matroska,video/webm,.mp4,.mov,.mkv,.webm" onChange={(e) => pick(e.target.files?.[0])} disabled={busy} />
            <FileVideo className="h-9 w-9 text-violet-600" />
            {file ? <div className="text-sm"><span className="font-medium">{file.name}</span> <span className="text-slate-500">· {fmtBytes(file.size)}</span></div>
              : <div className="text-sm font-medium">Drop a class recording (MP4, MOV, MKV, WEBM · up to 2 GB)</div>}
          </label>
        )}
        {mode === "link" && (
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="url">Public link to the recording</label>
            <Input id="url" placeholder="https://drive.google.com/file/d/…/view" value={url} onChange={(e) => setUrl(e.target.value)} disabled={busy} />
          </div>
        )}
        {busy && mode === "upload" && (
          <div className="space-y-1"><div className="flex justify-between text-xs text-slate-600"><span>Uploading in chunks…</span><span>{Math.round(progress * 100)}%</span></div><Progress value={progress * 100} /></div>
        )}
        {error && <Alert tone="error">{error}</Alert>}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <p className="flex items-center gap-1.5 text-xs text-slate-500"><ShieldCheck className="h-4 w-4 text-emerald-600" /> Names are anonymised before scoring. Nothing is stored on the server.</p>
          <div className="flex gap-2">
            {busy && mode === "upload" && <Button variant="outline" onClick={() => { abort.current?.abort(); setBusy(false); }}>Cancel</Button>}
            <Button size="lg" onClick={submit} disabled={busy || (mode === "upload" && !file)} className="bg-gradient-to-r from-violet-600 to-pink-600 hover:from-violet-700 hover:to-pink-700">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {busy ? "Assessing…" : "Assess class"}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
