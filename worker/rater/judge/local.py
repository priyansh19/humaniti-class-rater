"""Deterministic local judge: criterion scores -> ordinal label + templated, evidence-backed report."""
from __future__ import annotations

import os
from functools import lru_cache

from ..models import Analysis, CriterionResult, Report
from ..transcript import fmt_ts
from .ordinal import OrdinalModel
from .rubric import CRITERIA, criterion_scores

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.json")


@lru_cache(maxsize=1)
def shipped_model() -> OrdinalModel | None:
    return OrdinalModel.from_json(open(MODEL_PATH).read()) if os.path.exists(MODEL_PATH) else None


def _f(a: Analysis, mod: str, key: str, default: float = 0.0) -> float:
    return a.features.get(mod, {}).get(key, default)


def rationale(key: str, a: Analysis) -> str:
    t = a.features.get("text", {})
    v = a.features.get("visual", {})
    au = a.features.get("audio", {})
    if key == "rapport":
        return (f"{t.get('greetings_first5', 0):.0f} greeting cues and {t.get('student_turns_first5', 0):.0f} student turns in the first 5 min; "
                f"{t.get('newjoiner_prompts', 0):.0f} prompts for self-introduction; first long explanation at {t.get('first_long_explanation_min', 0):.1f} min.")
    if key == "individual_attention":
        return (f"{t.get('student_turns_per_min', 0):.1f} student turns/min from {t.get('students_speaking', 0):.0f} students "
                f"({100 * t.get('student_coverage', 0):.0f}% spoke 3+ times); tutor asked {t.get('tutor_questions_per_min', 0):.1f} questions/min "
                f"and addressed {t.get('students_named_by_tutor', 0):.0f} students by name.")
    if key == "energy":
        return (f"{t.get('praise_per_min', 0):.2f} praise/encouragement cues per min; {t.get('long_gaps_30s', 0):.0f} silences over 30 s "
                f"(longest {t.get('longest_gap_s', 0):.0f} s); tutor speaks {100 * t.get('tutor_talk_share', 0):.0f}% of words.")
    if key == "homework_closure":
        return (f"Homework mentioned {t.get('homework_cues', 0):.0f}x ({t.get('homework_last10', 0):.0f} in the last 10 min); "
                f"{t.get('wrapup_last5', 0):.0f} wrap-up cues in the last 5 min.")
    if key == "presentation":
        if not v:
            return "Not assessed (no video analysed)."
        return (f"Tutor camera off in {100 * v.get('tutor_camera_off_frac', 0):.0f}% of sampled moments while the tutor was speaking; "
                f"face visible in {100 * v.get('face_in_video_frac', 0):.0f}% of video frames; brightness {v.get('video_brightness', 0):.0f}/255; "
                f"8x8-style background detected in {100 * v.get('brand_background_frac', 0):.0f}% of video frames.")
    if key == "av_quality":
        s = f"{t.get('av_complaints', 0):.0f} audio/video complaints in the transcript"
        if au:
            s += f"; {100 * au.get('silence_frac', 0):.0f}% of the recording is silent"
        return s + "."
    if key == "teaching_aids":
        s = f"{t.get('activity_cues_per_hour', 0):.0f} references to boards/puzzles/activities per hour"
        if v:
            s += f"; screen share visible in {100 * v.get('screen_share_frac', 0):.0f}% of frames"
        return s + "."
    return ""


IMPROVE = {
    "rapport": "Spend the first few minutes greeting each child and invite new joiners to introduce themselves before starting revision.",
    "individual_attention": "Call on each child by name with a direct question at least every few minutes so that everyone participates.",
    "energy": "Use more praise and enthusiasm, and avoid long stretches of silence; keep children talking.",
    "homework_closure": "End with a short recap and assign specific homework.",
    "presentation": "Keep the camera on with your face visible against the 8x8 background, and sit facing a light source.",
    "av_quality": "Check the microphone and network before class; respond quickly when children report they can't hear or see.",
    "teaching_aids": "Use the board, puzzles or short topic videos to make concepts concrete.",
}


def _ev(a: Analysis, key: str, n: int = 3):
    src = "rapport" if key == "rapport" else key
    return list(a.evidence.get(src, []))[:n]


def build_report(a: Analysis, model: OrdinalModel | None = None) -> Report:
    crit = criterion_scores(a.features)
    model = model or shipped_model()
    if model is None:
        known = [v for v in crit.values() if v is not None]
        s = (sum(known) / len(known) - 1) / 4 * 3
        from ..models import LABELS
        label, conf = LABELS[int(min(max(round(s), 0), 3))], 0.4
    else:
        label, s, conf = model.predict(crit)
    criteria = {k: CriterionResult(score=round(v), rationale=rationale(k, a), evidence=_ev(a, k))
                for k, v in crit.items() if v is not None}
    ranked = sorted(criteria.items(), key=lambda kv: crit[kv[0]])
    strengths = [f"{CRITERIA[k]['title']}: {c.rationale}" + (f" e.g. [{fmt_ts(c.evidence[0].t)}] \"{c.evidence[0].quote[:90]}\"" if c.evidence else "")
                 for k, c in reversed(ranked) if c.score >= 4][:3]
    improvements = [f"{CRITERIA[k]['title']} ({c.score}/5): {IMPROVE[k]} Observed: {c.rationale}" for k, c in ranked if c.score <= 3][:4]
    if not strengths:
        best = ranked[-1]
        strengths = [f"Relative strength - {CRITERIA[best[0]]['title']}: {best[1].rationale}"]
    weakest = ", ".join(CRITERIA[k]["title"].lower() for k, _ in ranked[:2])
    summary = f"Rated {label}. Weakest areas: {weakest}."
    t = a.features.get("text", {})
    metrics = {k: t[k] for k in ("student_turns_per_min", "students_speaking", "tutor_questions_per_min", "praise_per_min",
                                 "long_gaps_30s", "homework_cues") if k in t}
    metrics["duration_min"] = round(a.duration_s / 60, 1)
    return Report(label=label, confidence=conf, summary=summary, criteria=criteria, strengths=strengths,
                  improvements=improvements, metrics=metrics, judge="local", warnings=list(a.warnings))
