"""Multimodal LLM judge: text + derived audio/visual features -> structured rubric JSON.

Privacy: the payload is built only from the (already anonymised) Analysis. A final guard
redacts emails/phone numbers and refuses to send anything containing given name tokens."""
from __future__ import annotations

import json
import re

from ..models import LABELS, Analysis, CriterionResult, Quote, Report
from ..transcript import fmt_ts
from .rubric import CRITERIA, criterion_scores

SYSTEM = (
    "You assess recorded live online chess classes for children run by 8x8. Judge ONLY from the evidence provided: "
    "anonymised transcript excerpts, tagged quotes, and numeric features measured from the transcript, audio and video frames "
    "(you do not see the video). Use the rubric, which was derived from the organiser's own tutor feedback. "
    "Every rationale must cite a timestamp [mm:ss] that appears in the evidence or a numeric feature. "
    "Refer to people only as 'the tutor' or 'a student'. Be specific and actionable, never generic."
)

LEVELS = ("Label guidance from the organiser's examples: Excellent = strong rapport, everyone included and questioned individually, homework given. "
          "Good = good intro and inclusion with one clear gap (e.g. no homework, less pleasant interaction). "
          "Average = basics present but low energy, missing homework, lighting/clarity issues. "
          "Poor = no rapport or introductions, camera off or face not visible, no background, or repeated quality problems.")

_CRIT_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["score", "rationale", "timestamps"],
                "properties": {"score": {"type": "integer", "minimum": 1, "maximum": 5}, "rationale": {"type": "string"},
                               "timestamps": {"type": "array", "items": {"type": "string"}}}}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["label", "confidence", "summary", "criteria", "strengths", "improvements", "content"],
    "properties": {
        "label": {"type": "string", "enum": LABELS},
        "confidence": {"type": "number"},
        "summary": {"type": "string"},
        "criteria": {"type": "object", "additionalProperties": False, "required": list(CRITERIA),
                     "properties": {k: _CRIT_SCHEMA for k in CRITERIA}},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "improvements": {"type": "array", "items": {"type": "string"}},
        "content": {"type": "object", "additionalProperties": False, "required": ["subject", "topics"],
                    "properties": {"subject": {"type": "string"},
                                   "topics": {"type": "array", "items": {
                                       "type": "object", "additionalProperties": False,
                                       "required": ["topic", "introduced_at", "explained", "practised", "recapped", "depth"],
                                       "properties": {"topic": {"type": "string"}, "introduced_at": {"type": "string"},
                                                      "explained": {"type": "boolean"}, "practised": {"type": "boolean"},
                                                      "recapped": {"type": "boolean"}, "depth": {"type": "integer"}}}}}},
    },
}

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"\+?\d[\d \-]{8,}\d")


def build_payload(a: Analysis) -> str:
    rubric = "\n".join(f"- {k}: {v['title']} - {v['feedback']}" for k, v in CRITERIA.items())
    ev = []
    for crit, quotes in a.evidence.items():
        for q in quotes:
            ev.append(f"[{fmt_ts(q.t)}] ({crit}) {q.speaker}: {q.quote}")
    local = {k: v for k, v in criterion_scores(a.features).items() if v is not None}
    text = (f"RUBRIC\n{rubric}\n{LEVELS}\n\nCLASS: duration {a.duration_s / 60:.0f} min; transcript source {a.transcript_source}"
            f"{' (speaker roles estimated)' if a.roles_estimated else ''}.\n\n"
            f"MEASURED FEATURES (computed locally)\n{json.dumps(a.features, indent=1)}\n\n"
            f"LOCAL HEURISTIC CRITERION SCORES (1-5, for reference only)\n{json.dumps(local)}\n\n"
            f"LESSON CONTENT MAP (local keyword analysis; refine it: subject, topics, introduced/explained/practised/recapped, depth 0-3)\n"
            f"{json.dumps({'subject': a.content.get('subject'), 'topics': [{k: t[k] for k in ('topic', 'first_t', 'minutes', 'explained', 'practised_turns', 'recapped', 'depth')} for t in a.content.get('topics', [])]})}\n\n"
            f"TAGGED QUOTES\n" + "\n".join(ev) + f"\n\nTRANSCRIPT EXCERPTS\n{a.excerpt}\n\n"
            "If a modality is missing (e.g. no visual features), score that criterion 3 and say it was not assessed.")
    return _PHONE.sub("[phone]", _EMAIL.sub("[email]", text))


def assert_private(payload: str, forbidden_tokens: set[str]) -> None:
    low = payload.lower()
    leaked = sorted(t for t in forbidden_tokens if re.search(rf"\b{re.escape(t.lower())}\b", low))
    if leaked:
        raise PermissionError("Refusing to send payload containing personal names")


def _quotes_for(a: Analysis, stamps: list[str]) -> list[Quote]:
    allq = {fmt_ts(q.t): q for qs in a.evidence.values() for q in qs}
    return [allq[s.strip("[] ")] for s in stamps if s.strip("[] ") in allq][:3]


def to_report(a: Analysis, d: dict, judge_name: str) -> Report:
    if d.get("label") not in LABELS:
        raise ValueError("invalid label")
    known_ts = set(re.findall(r"\[(\d+:\d{2}(?::\d{2})?)\]", build_payload(a)))
    criteria, dropped = {}, 0
    for k in CRITERIA:
        c = d["criteria"][k]
        stamps = [s for s in c.get("timestamps", []) if s.strip("[] ") in known_ts]
        dropped += len(c.get("timestamps", [])) - len(stamps)
        criteria[k] = CriterionResult(score=int(min(max(int(c["score"]), 1), 5)), rationale=c["rationale"], evidence=_quotes_for(a, stamps))
    content = dict(a.content)
    lt = d.get("content", {}) or {}
    if lt.get("topics"):
        valid = [t for t in lt["topics"] if str(t.get("introduced_at", "")).strip("[] ") in known_ts]
        content = {**content, "llm_subject": lt.get("subject"), "llm_topics": valid}
        if len(valid) < len(lt["topics"]):
            dropped += len(lt["topics"]) - len(valid)
    warnings = list(a.warnings)
    if dropped:
        warnings.append(f"{dropped} cited timestamp(s) not found in the evidence were removed.")
    t = a.features.get("text", {})
    return Report(content=content, label=d["label"], confidence=float(min(max(d.get("confidence", 0.5), 0), 1)), summary=d["summary"],
                  criteria=criteria, strengths=d["strengths"][:5], improvements=d["improvements"][:5],
                  metrics={k: t[k] for k in ("student_turns_per_min", "students_speaking", "tutor_questions_per_min") if k in t}
                  | {"duration_min": round(a.duration_s / 60, 1)}, judge=judge_name, warnings=warnings)
