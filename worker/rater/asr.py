"""Local speech-to-text with faster-whisper, chunked so progress can be reported."""
from __future__ import annotations

import os
from collections.abc import Callable
from functools import lru_cache

from .media import pcm


@lru_cache(maxsize=2)
def _model(size: str):
    from faster_whisper import WhisperModel
    return WhisperModel(size, device="cpu", compute_type="int8",
                        cpu_threads=int(os.environ.get("RATER_ASR_THREADS", os.cpu_count() or 2)))


def transcribe(path: str, duration_s: float, model_size: str | None = None, chunk_s: float = 600,
               on_progress: Callable[[float], None] | None = None, language: str | None = None) -> list[tuple[float, float, str]]:
    model = _model(model_size or os.environ.get("RATER_ASR_MODEL", "base"))
    segs: list[tuple[float, float, str]] = []
    t = 0.0
    while t < duration_s:
        audio = pcm(path, 16000, start=t, dur=chunk_s)
        if audio.size:
            out, _ = model.transcribe(audio, language=language, vad_filter=True, beam_size=1)
            segs += [(t + s.start, t + s.end, s.text.strip()) for s in out if s.text.strip()]
        t += chunk_s
        if on_progress:
            on_progress(min(t / max(duration_s, 1), 1.0))
    return segs
