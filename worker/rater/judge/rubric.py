"""Rubric criteria (from feedbacks.pdf) and the fixed feature -> criterion-score mappings.

FROZEN before evaluation (docs/specs/eval.md). Each criterion = 1 + 4 * weighted mean of
monotone, clipped feature transforms. Criteria whose modality is missing are None.
"""
from __future__ import annotations

from dataclasses import dataclass

CRITERIA: dict[str, dict] = {
    "rapport": {"title": "Intro & rapport", "modality": "text",
                "feedback": "Greet and warm up, give new joiners time to introduce themselves; don't jump straight into revision."},
    "individual_attention": {"title": "Individual attention", "modality": "text",
                             "feedback": "Call on children individually by name and include everyone."},
    "energy": {"title": "Energy & pleasant interaction", "modality": "text",
               "feedback": "Energetic, happy, encouraging communication; avoid long dead air."},
    "homework_closure": {"title": "Homework & conclusion", "modality": "text",
                         "feedback": "Give homework and close the class with a clear wrap-up."},
    "presentation": {"title": "Camera, face, background & lighting", "modality": "visual",
                     "feedback": "Keep the 8x8 background, camera on with face visible, and sit in good light."},
    "av_quality": {"title": "Audio/video quality", "modality": "audio",
                   "feedback": "Students should not have to report audio/video problems repeatedly."},
    "teaching_aids": {"title": "Teaching aids", "modality": "text",
                      "feedback": "Use boards, puzzles or topic videos to make the lesson concrete."},
}


@dataclass(frozen=True)
class Comp:
    feature: str          # "text.x" | "audio.x" | "visual.x"
    lo: float
    hi: float
    weight: float = 1.0
    invert: bool = False


MAPPINGS: dict[str, list[Comp]] = {
    "rapport": [Comp("text.greetings_first5", 0, 6), Comp("text.student_turns_first5", 0, 15),
                Comp("text.newjoiner_prompts", 0, 2, 0.5), Comp("text.first_long_explanation_min", 1, 6)],
    "individual_attention": [Comp("text.student_turns_per_min", 2, 9, 2), Comp("text.student_coverage", 0.3, 0.9),
                             Comp("text.tutor_questions_per_min", 0.5, 3), Comp("text.students_named_by_tutor", 1, 6)],
    "energy": [Comp("text.praise_per_min", 0.2, 1.5), Comp("text.exclaims_per_min", 0.0, 1.0, 0.5),
               Comp("text.long_gaps_30s", 0, 10, 1.5, invert=True), Comp("text.tutor_talk_share", 0.5, 0.85, 0.5, invert=True)],
    "homework_closure": [Comp("text.homework_cues", 0, 3, 1.5), Comp("text.homework_last10", 0, 1), Comp("text.wrapup_last5", 0, 5)],
    "presentation": [Comp("visual.tutor_camera_off_frac", 0.0, 0.3, 2, invert=True), Comp("visual.video_brightness", 45, 110),
                     Comp("visual.face_in_video_frac", 0.1, 0.7), Comp("visual.brand_background_frac", 0.0, 0.5)],
    "av_quality": [Comp("text.av_complaints_per_100_student_turns", 0.5, 4, 2, invert=True),
                   Comp("audio.silence_frac", 0.15, 0.5, 1, invert=True), Comp("audio.clip_frac", 0.0, 0.01, 0.5, invert=True)],
    "teaching_aids": [Comp("text.activity_cues_per_hour", 2, 30), Comp("visual.screen_share_frac", 0.0, 0.4)],
}


def _get(features: dict[str, dict[str, float]], dotted: str) -> float | None:
    mod, key = dotted.split(".", 1)
    return features.get(mod, {}).get(key)


def criterion_scores(features: dict[str, dict[str, float]]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for crit, comps in MAPPINGS.items():
        num = den = 0.0
        for c in comps:
            v = _get(features, c.feature)
            if v is None:
                continue
            x = min(max((v - c.lo) / (c.hi - c.lo), 0.0), 1.0)
            num += c.weight * ((1 - x) if c.invert else x)
            den += c.weight
        out[crit] = round(1 + 4 * num / den, 3) if den else None   # unknown when none of its inputs exist
    return out
