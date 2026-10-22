"""Orchestrates the analysis stages and reports progress (spec: analysis.md)."""
from __future__ import annotations

from collections.abc import Callable

from . import audio as audio_mod
from . import evidence as ev
from . import text_features, transcript, visual
from .content import analyse_content
from .media import MediaError, frames, probe
from .models import Analysis, Quote

Progress = Callable[[str, float], None]
MAX_DURATION_S = 150 * 60


def analyse(media_path: str | None = None, transcript_text: str | None = None, *, use_audio: bool = True,
            use_visual: bool = True, frame_every_s: float = 15.0, on_progress: Progress | None = None, return_utterances: bool = False):
    prog = on_progress or (lambda stage, p: None)
    warnings: list[str] = []
    duration = 0.0
    if media_path:
        prog("probing", 0.0)
        info = probe(media_path)
        duration = info["duration_s"]
        if duration > MAX_DURATION_S:
            raise MediaError(f"Recording is {duration/60:.0f} min; the limit is {MAX_DURATION_S//60} min")
        if not info["has_audio"]:
            raise MediaError("Recording has no audio track")
    # transcript
    student_tokens: set[str] = set()
    if transcript_text and transcript_text.strip():
        utts, source, est, student_tokens = transcript.from_text(transcript_text)
    elif media_path:
        from .asr import transcribe
        prog("transcribing", 0.0)
        segs = transcribe(media_path, duration, on_progress=lambda p: prog("transcribing", p))
        utts, source, est = transcript.from_segments(segs), "asr", True
        warnings.append("Transcript produced by local ASR without speaker labels; tutor/student roles are estimated.")
    else:
        raise ValueError("Provide a recording or a transcript")
    if len(utts) < 5:
        warnings.append("Very little speech was found; the assessment is low-confidence.")
    duration = duration or (max((u.end for u in utts), default=0.0))
    feats: dict[str, dict[str, float]] = {"text": text_features.compute(utts, student_tokens)}
    content = analyse_content(utts)
    feats["content"] = content["metrics"]
    if media_path and use_audio:
        prog("audio", 0.0)
        feats["audio"] = audio_mod.compute(media_path)
    if media_path and use_visual:
        n_expected = max(int(duration // frame_every_s), 1)
        prog("frames", 0.0)
        feats["visual"] = visual.compute(frames(media_path, frame_every_s), utts,
                                         on_frame=lambda i: prog("frames", min((i + 1) / n_expected, 1.0)))
    evidence = ev.collect(utts)
    evidence["content_coverage"] = [Quote(**q) for t in content["topics"] for q in t["evidence"]][:8]
    a = Analysis(duration_s=round(duration, 1), transcript_source=source, roles_estimated=est, features=feats,
                 evidence=evidence, excerpt=ev.excerpt(utts), content=content, warnings=warnings)
    if return_utterances:
        return a, utts
    return a
