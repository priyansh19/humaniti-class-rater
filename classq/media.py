"""Local-only media processing: audio extraction, ASR, frame checks. Nothing leaves the machine."""
import json
import os
import subprocess
import tempfile

import numpy as np


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", path])
    return float(out)


def extract_frames(path, every_s=20, width=480, outdir=None):
    outdir = outdir or tempfile.mkdtemp(prefix="frames_")
    run(["ffmpeg", "-y", "-i", path, "-vf", f"fps=1/{every_s},scale={width}:-2", "-q:v", "4",
         os.path.join(outdir, "f_%05d.jpg")])
    return outdir, sorted(os.path.join(outdir, f) for f in os.listdir(outdir) if f.endswith(".jpg"))


def frame_features(path, every_s=20) -> dict:
    import cv2
    d, files = extract_frames(path, every_s)
    face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    bright, faces, dark, diffs, sat_tiles = [], [], 0, [], []
    prev = None
    for f in files:
        img = cv2.imread(f)
        if img is None:
            continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        b = float(g.mean())
        bright.append(b)
        if b < 25:
            dark += 1
        fs = face.detectMultiScale(g, 1.1, 5, minSize=(24, 24))
        faces.append(len(fs))
        if prev is not None:
            diffs.append(float(np.abs(g.astype(int) - prev.astype(int)).mean()))
        prev = g
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        sat_tiles.append(float(hsv[..., 1].mean()))
    for f in files:
        os.remove(f)
    os.rmdir(d)
    n = max(len(bright), 1)
    faces_a = np.array(faces or [0])
    return {
        "frames_sampled": len(bright),
        "mean_brightness": round(float(np.mean(bright or [0])), 1),
        "dark_frame_frac": round(dark / n, 3),
        "face_present_frac": round(float((faces_a > 0).mean()), 3),
        "mean_faces": round(float(faces_a.mean()), 2),
        "no_face_streak_max_min": round(_max_streak(faces_a == 0) * every_s / 60, 1),
        "static_frac": round(float(np.mean([d < 2 for d in diffs])) if diffs else 0, 3),
        "screen_change_mean": round(float(np.mean(diffs)) if diffs else 0, 2),
        "mean_saturation": round(float(np.mean(sat_tiles or [0])), 1),
    }


def _max_streak(mask):
    best = cur = 0
    for v in mask:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def audio_features(path) -> dict:
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.raw")
        run(["ffmpeg", "-y", "-i", path, "-ac", "1", "-ar", "8000", "-f", "s16le", wav])
        x = np.fromfile(wav, dtype=np.int16).astype(np.float32) / 32768
    if x.size == 0:
        return {}
    win = 8000
    n = x.size // win
    rms = np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms)
    thr = np.percentile(db, 90) - 30
    return {
        "audio_silence_frac": round(float((db < thr).mean()), 3),
        "audio_loudness_db_p50": round(float(np.median(db)), 1),
        "audio_dynamic_range_db": round(float(np.percentile(db, 95) - np.percentile(db, 10)), 1),
        "audio_clip_frac": round(float((np.abs(x) > 0.99).mean()), 5),
    }


def transcribe(path, model_size="base", max_minutes=60, language=None) -> str:
    """Local faster-whisper on CPU; returns VTT text (no speaker labels)."""
    from faster_whisper import WhisperModel
    m = WhisperModel(model_size, device="cpu", compute_type="int8")
    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, "a.raw")
        run(["ffmpeg", "-y", "-i", path, "-t", str(max_minutes * 60), "-ac", "1", "-ar", "16000", "-f", "s16le", raw])
        audio = np.fromfile(raw, dtype=np.int16).astype(np.float32) / 32768
        segs, _ = m.transcribe(audio, language=language, vad_filter=True)
        lines = ["WEBVTT", ""]
        from .transcript import fmt
        for s in segs:
            lines += [f"{_v(s.start)} --> {_v(s.end)}", f"Speaker: {s.text.strip()}", ""]
    return "\n".join(lines)


def _v(t):
    t = float(t)
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{t % 60:06.3f}"


def cache_json(path, data=None):
    if data is None:
        return json.load(open(path)) if os.path.exists(path) else None
    json.dump(data, open(path, "w"), indent=1)
