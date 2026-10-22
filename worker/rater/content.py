"""Domain content coverage (spec: docs/specs/analysis.md §9).

Identifies the lesson subject and topics from the anonymised transcript (VTT or Whisper), then measures,
per topic: when it was introduced, whether it was explained, practised with students, and recapped,
time spent and a 0-3 depth score. Local keyword taxonomy; the LLM judge refines it (see judge/llm.py).
"""
from __future__ import annotations

import re

from .models import Utterance

# Chess taxonomy (8x8 is a chess academy). topic -> regex of surface forms.
TOPICS: dict[str, str] = {
    "piece movement & values": r"\b(how the (knight|bishop|rook|queen|king|pawn) moves?|moves? (diagonally|straight|in an l)|l[- ]shape|piece values?|worth \d+ points|\d+ points?)\b",
    "check & checkmate": r"\b(check ?mate|checkmate|mate in (one|two|three|\d)|in check|giving check|delivers? check)\b",
    "stalemate & draws": r"\b(stale ?mate|draw|threefold|repetition|insufficient material)\b",
    "openings & development": r"\b(opening|develop(ment)?|control (the )?cent(er|re)|cent(er|re) control|italian|sicilian|london|ruy lopez|queen'?s gambit|e4|d4|castl(e|ing))\b",
    "tactics: forks": r"\bforks?\b|double attack",
    "tactics: pins & skewers": r"\b(pins?|pinned|skewers?)\b",
    "tactics: discovered attacks": r"\bdiscover(ed|y)? (attack|check)\b",
    "mating patterns": r"\b(back[- ]rank|smothered|ladder mate|scholar'?s mate|fool'?s mate|anastasia|arabian)\b",
    "endgames": r"\b(end ?game|opposition|promot(e|ion)|passed pawn|king and pawn|queening)\b",
    "special moves": r"\b(en passant|castl(e|ing)|promot(e|ion))\b",
    "notation & coordinates": r"\b(notation|algebraic|[a-h] ?[1-8]\b|rank|file|coordinates?)\b",
    "puzzles & problem solving": r"\b(puzzles?|find the best move|best move|your turn|solve)\b",
    "game play & strategy": r"\b(tournament|play a game|blitz|rapid|strategy|plan|material|trade|exchange|sacrific(e|ing))\b",
}
EXPLAIN = re.compile(r"\b(this is called|it means|means that|because|so that|the idea|remember|rule|if you|when you|why)\b", re.IGNORECASE)
RECAP = re.compile(r"\b(today we (learn|learned|saw|did|covered)|recap|summary|to summari[sz]e|revision|last class|previous class)\b", re.IGNORECASE)
SUBJECT_HINT = re.compile(r"\b(chess|knight|bishop|rook|queen|king|pawn|checkmate|board|move)\b", re.IGNORECASE)


def _cluster(times: list[tuple[float, float]], gap: float = 90.0) -> list[tuple[float, float]]:
    spans: list[list[float]] = []
    for s, e in sorted(times):
        if spans and s - spans[-1][1] <= gap:
            spans[-1][1] = max(spans[-1][1], e)
        else:
            spans.append([s, e])
    return [(a, b) for a, b in spans]


def analyse_content(utts: list[Utterance]) -> dict:
    if not utts:
        return {"subject": "unknown", "subject_confidence": 0.0, "topics": [], "metrics": {}}
    end = max(u.end for u in utts)
    words = sum(len(u.text.split()) for u in utts) or 1
    hint = sum(len(SUBJECT_HINT.findall(u.text)) for u in utts)
    subj_conf = min(hint / words * 40, 1.0)
    topics = []
    for name, pat in TOPICS.items():
        rx = re.compile(pat, re.IGNORECASE)
        hits = [u for u in utts if rx.search(u.text)]
        if len(hits) < 2:
            continue
        spans = _cluster([(u.start, u.end + 20) for u in hits])
        seconds = sum(b - a for a, b in spans)
        tutor_hits = [u for u in hits if u.role == "tutor"]
        explained = [u for u in tutor_hits if len(u.text.split()) >= 12 and EXPLAIN.search(u.text)]
        practised = 0
        for a, b in spans:
            practised += sum(1 for u in utts if u.role == "student" and a <= u.start <= b + 30)
        recapped = [u for u in hits if u.start > end - 600 or RECAP.search(u.text)]
        depth = int(bool(explained)) + int(practised >= 3) + int(bool(recapped))
        ev = (explained or tutor_hits or hits)[:2]
        topics.append({
            "topic": name, "mentions": len(hits), "first_t": round(hits[0].start, 1), "minutes": round(seconds / 60, 1),
            "explained": bool(explained), "practised_turns": practised, "recapped": bool(recapped), "depth": depth,
            "evidence": [{"t": round(u.start, 1), "speaker": u.speaker, "quote": u.text[:160]} for u in ev],
        })
    topics.sort(key=lambda t: -t["minutes"])
    covered = sum(t["minutes"] for t in topics)
    n = len(topics)
    metrics = {
        "topics_detected": float(n),
        "topic_minutes_share": round(min(covered / max(end / 60, 1), 1.0), 3),
        "main_topic_minutes": topics[0]["minutes"] if topics else 0.0,
        "explained_frac": round(sum(t["explained"] for t in topics) / n, 3) if n else 0.0,
        "practised_frac": round(sum(t["practised_turns"] >= 3 for t in topics) / n, 3) if n else 0.0,
        "recapped_frac": round(sum(t["recapped"] for t in topics) / n, 3) if n else 0.0,
        "mean_depth": round(sum(t["depth"] for t in topics) / n, 3) if n else 0.0,
        "opens_with_revision": float(any(RECAP.search(u.text) for u in utts if u.role == "tutor" and u.start < 600)),
    }
    return {"subject": "chess" if subj_conf >= 0.3 else "unknown", "subject_confidence": round(subj_conf, 2),
            "topics": topics[:8], "metrics": metrics}


def topic_set(content: dict, min_minutes: float = 1.0) -> set[str]:
    return {t["topic"] for t in content.get("topics", []) if t["minutes"] >= min_minutes}
