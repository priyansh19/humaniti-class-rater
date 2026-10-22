"""Timestamped, anonymised evidence quotes per rubric criterion."""
from __future__ import annotations

from .models import Quote, Utterance
from .text_features import P
from .transcript import fmt_ts

_RULES = {
    "rapport": lambda u: u.start < 600 and (P["greeting"].search(u.text) or P["newjoiner"].search(u.text)),
    "individual_attention": lambda u: u.role == "tutor" and "Student " in u.text and "?" in u.text,
    "energy": lambda u: u.role == "tutor" and P["praise"].search(u.text),
    "homework_closure": lambda u: P["homework"].search(u.text) or (P["wrapup"].search(u.text) and u.role == "tutor"),
    "av_quality": lambda u: P["av"].search(u.text),
    "teaching_aids": lambda u: u.role == "tutor" and P["activity"].search(u.text),
}


def collect(utts: list[Utterance], per_criterion: int = 8) -> dict[str, list[Quote]]:
    out: dict[str, list[Quote]] = {}
    for key, rule in _RULES.items():
        hits = [u for u in utts if rule(u)]
        if len(hits) > per_criterion:
            step = len(hits) / per_criterion
            hits = [hits[int(i * step)] for i in range(per_criterion)]
        out[key] = [Quote(t=round(u.start, 1), speaker=u.speaker, quote=u.text[:180]) for u in hits]
    return out


def excerpt(utts: list[Utterance], max_chars: int = 9000) -> str:
    if not utts:
        return ""
    end = max(u.end for u in utts)
    mid = end / 2
    windows = [("OPENING", 0, 360), ("MIDDLE SAMPLE", mid - 120, mid + 120), ("CLOSING", end - 300, end + 1)]
    parts = []
    for name, a, b in windows:
        lines = [f"[{fmt_ts(u.start)}] {u.speaker}: {u.text}" for u in utts if a <= u.start < b]
        parts.append(f"--- {name} ---\n" + "\n".join(lines))
    text = "\n".join(parts)
    return text if len(text) <= max_chars else text[: max_chars - 20] + "\n...[truncated]"
