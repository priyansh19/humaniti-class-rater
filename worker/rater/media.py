"""ffmpeg/ffprobe helpers. Everything runs locally on the worker host."""
from __future__ import annotations

import json
import shutil
import subprocess

import numpy as np


class MediaError(RuntimeError):
    pass


def require_ffmpeg() -> None:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        raise MediaError("ffmpeg/ffprobe not found on PATH")


def probe(path: str) -> dict:
    require_ffmpeg()
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                             check=True, capture_output=True, timeout=60).stdout
    except subprocess.CalledProcessError as e:
        raise MediaError("Not a readable media file") from e
    info = json.loads(out)
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    return {
        "duration_s": float(info.get("format", {}).get("duration") or 0),
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        "has_video": v is not None,
        "width": int(v["width"]) if v else 0,
        "height": int(v["height"]) if v else 0,
    }


def pcm(path: str, rate: int = 16000, start: float | None = None, dur: float | None = None) -> np.ndarray:
    """Decode mono float32 PCM via ffmpeg (avoids PyAV/version issues)."""
    cmd = ["ffmpeg", "-v", "error", "-nostdin"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", path]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def frames(path: str, every_s: float = 15.0, width: int = 320):
    """Yield (t_seconds, BGR uint8 array) sampled every `every_s` seconds, streamed from ffmpeg (no temp files)."""
    p = probe(path)
    if not p["has_video"]:
        return
    w = width
    h = int(round(p["height"] * w / p["width"] / 2) * 2)
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-vf", f"fps=1/{every_s},scale={w}:{h}",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = w * h * 3
    i = 0
    try:
        while True:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            yield (i + 0.5) * every_s, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            i += 1
    finally:
        proc.stdout.close()
        proc.wait()
