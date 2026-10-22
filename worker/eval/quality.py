"""Quality metrics for returned assessments, beyond label match (scored against eval/gold.json).

1 label      exact / within-1 accuracy vs the organiser's label
2 reasons    share of observations (strengths + improvements) that map to a real rubric theme
3 evidence   faithfulness: cited quotes exist in the transcript evidence at that timestamp AND were tagged for the
             criterion they support; timestamps quoted in free text exist in the evidence
4 coverage   recall of the gold feedback points (theme + polarity) recovered by the report
5 specific   share of observations carrying a concrete anchor (number, timestamp or quote) and no generic filler
6 consistency repeat-run agreement (label, and mean |delta| of criterion scores)
"""
from __future__ import annotations

import json
import os
import re

from rater.models import LABELS

GOLD_PATH = os.path.join(os.path.dirname(__file__), "gold.json")
THEMES = ["rapport", "individual_attention", "energy", "homework_closure", "presentation", "av_quality"]

# Keyword map from free text to rubric themes (used for LLM-written observations). Deterministic and auditable.
THEME_WORDS = {
    "rapport": r"rapport|greet|intro(duc)?|warm[- ]?up|welcome|new joiner|self[- ]intro|ice[- ]?break",
    "individual_attention": r"individual|by name|each (child|student)|every(one| child)|includ|call(ed|s|ing)? on|one[- ]to[- ]one|student turns|participat|questions?",
    "energy": r"energ|enthusias|pleasant|happ(y|ier)|prais|encourag|tone|dead air|silen|lively",
    "homework_closure": r"home ?work|\bhw\b|wrap[- ]?up|conclu|recap|summar|clos(e|ing)",
    "presentation": r"camera|face|background|light(ing)?|bright|visible|8x8|webcam",
    "av_quality": r"audio|sound|hear|microphone|\bmic\b|network|lag|connect|video quality|av\b|echo|noise",
}
TITLE_THEME = {"Intro & rapport": "rapport", "Individual attention": "individual_attention", "Energy & pleasant interaction": "energy",
               "Homework & conclusion": "homework_closure", "Camera, face, background & lighting": "presentation",
               "Audio/video quality": "av_quality", "Teaching aids": "teaching_aids"}
GENERIC = re.compile(r"\b(good job overall|overall (good|fine|nice)|could be better|needs improvement|keep it up|room for improvement|"
                     r"great class|nice class|well done overall|in general)\b", re.IGNORECASE)
ANCHOR = re.compile(r"\[?\d{1,2}:\d{2}(:\d{2})?\]?|\d+(\.\d+)?\s?(%|/min|min|s\b|x\b|times|students?|questions|cues)|\"[^\"]{8,}\"|“[^”]{8,}”")
TS = re.compile(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]")


def load_gold() -> dict:
    with open(GOLD_PATH) as fh:
        g = json.load(fh)
    return {k: v for k, v in g.items() if not k.startswith("_")}


def gold_key(class_id: str) -> str:
    return "-".join(class_id.split("-")[:2])


def themes_of(text: str) -> set[str]:
    for title, th in TITLE_THEME.items():
        if text.startswith((title, "Relative strength - " + title)):
            return {th}
    return {t for t, pat in THEME_WORDS.items() if re.search(pat, text, re.IGNORECASE)}


def observations(report: dict) -> list[tuple[str, str]]:
    return [("+", s) for s in report.get("strengths", [])] + [("-", s) for s in report.get("improvements", [])]


def fmt_ts(t: float) -> str:
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def score_report(report: dict, gold: dict | None, evidence: dict[str, list[dict]]) -> dict:
    obs = observations(report)
    # 2 reason quality
    mapped = [bool(themes_of(t) & set(THEMES + ["teaching_aids"])) for _, t in obs]
    # 3 evidence faithfulness
    tagged = {(round(q["t"], 1), q["quote"]): crit for crit, qs in evidence.items() for q in qs}
    tagged_multi: dict[tuple, set] = {}
    for crit, qs in evidence.items():
        for q in qs:
            tagged_multi.setdefault((round(q["t"], 1), q["quote"]), set()).add(crit)
    cited = [(k, q) for k, c in report.get("criteria", {}).items() for q in c.get("evidence", [])]
    exists = [(round(q["t"], 1), q["quote"]) in tagged for _, q in cited]
    supports = [k in tagged_multi.get((round(q["t"], 1), q["quote"]), set()) or (k == "presentation") for k, q in cited]
    known_ts = {fmt_ts(q["t"]) for qs in evidence.values() for q in qs}
    text_ts = [m for _, t in obs for m in TS.findall(t)] + [m for c in report.get("criteria", {}).values() for m in TS.findall(c.get("rationale", ""))]
    ts_ok = [m in known_ts for m in text_ts]
    # 5 specificity
    specific = [bool(ANCHOR.search(t)) and not GENERIC.search(t) for _, t in obs]
    out = {
        "reasons_mapped": _frac(mapped), "evidence_exists": _frac(exists), "evidence_supports": _frac(supports),
        "text_timestamps_real": _frac(ts_ok), "specificity": _frac(specific), "n_observations": len(obs), "n_cited": len(cited),
    }
    # 1 label + 4 coverage
    if gold:
        yi, pi = LABELS.index(gold["label"]), LABELS.index(report["label"])
        out["label_exact"] = float(yi == pi)
        out["label_within1"] = float(abs(yi - pi) <= 1)
        crit = report.get("criteria", {})
        hits = []
        for p in gold["points"]:
            th, pol = p["theme"], p["polarity"]
            sc = crit.get(th, {}).get("score")
            by_score = sc is not None and ((pol == "+" and sc >= 4) or (pol == "-" and sc <= 2))
            by_obs = any(o_pol == pol and th in themes_of(t) for o_pol, t in obs)
            hits.append(by_score or by_obs)
        out["coverage"] = _frac(hits)
        out["coverage_hits"] = int(sum(hits))
        out["coverage_total"] = len(hits)
    return out


def consistency(runs: list[dict]) -> dict:
    """runs: >=2 reports for the same class."""
    labels = [r["label"] for r in runs]
    keys = set.intersection(*[set(r["criteria"]) for r in runs])
    deltas = [abs(runs[0]["criteria"][k]["score"] - r["criteria"][k]["score"]) for r in runs[1:] for k in keys]
    return {"label_agree": float(len(set(labels)) == 1), "criterion_mean_abs_delta": sum(deltas) / len(deltas) if deltas else 0.0}


def aggregate(rows: list[dict]) -> dict:
    keys = ["label_exact", "label_within1", "reasons_mapped", "evidence_exists", "evidence_supports", "text_timestamps_real", "specificity", "coverage"]
    out = {}
    for k in keys:
        vals = [r[k] for r in rows if r.get(k) is not None]
        out[k] = round(sum(vals) / len(vals), 3) if vals else None
    hits = sum(r.get("coverage_hits", 0) for r in rows)
    tot = sum(r.get("coverage_total", 0) for r in rows)
    out["coverage_micro"] = round(hits / tot, 3) if tot else None
    out["coverage_points"] = f"{hits}/{tot}"
    return out


def _frac(xs: list[bool]) -> float | None:
    return round(sum(xs) / len(xs), 3) if xs else None
