"""Rubric derived from the organiser's feedback notes, plus a deterministic local scorer.

Each theme gets a 0-1 score from features. The weights are set by hand from the feedback
themes, not fitted. Only the label cut-points are learned (from training folds in LOO eval).
"""
import numpy as np

LABELS = ["Poor", "Average", "Good", "Excellent"]

RUBRIC = """8x8 class-quality rubric (derived from the organiser's tutor feedback):
1. Intro & rapport: greets warmly, builds rapport before content, gives NEW JOINERS time to self-introduce; does not jump straight into revision.
2. Individual engagement: calls students by name, asks each child questions individually, includes everyone (one-to-one consideration).
3. Energy & pleasantness: energetic, happy, pleasant interaction; praise and encouragement.
4. Homework & conclusion: assigns homework, clear wrap-up/conclusion.
5. Visual professionalism: 8x8 virtual background kept, tutor camera ON and face visible, good lighting; background must not hurt clarity.
6. AV quality: no repeated audio/video complaints from students ("can't hear", "not visible").
7. Teaching aids (bonus): topic videos, puzzles, screen activities.
Tiers: Excellent = strong on 1-4 with rapport + individual questions + HW. Good = good intro and inclusion but one gap (e.g. no HW or less pleasant). Average = basics present (background, individual questions) but low energy / missing HW / clarity or lighting issues. Poor = no rapport/intro, camera off or face not visible, no background, or repeated quality problems."""


def _clip(x, lo, hi):
    return float(np.clip((x - lo) / (hi - lo), 0, 1))


def theme_scores(f: dict, multimodal: bool = True) -> dict:
    t = f.get("text", {})
    dur = max(t.get("duration_min", 1), 1)
    s = {
        "intro_rapport": 0.4 * _clip(t.get("intro_hits_first5", 0), 1, 10) + 0.3 * (1 - _clip(t.get("first_long_teacher_utt_s", 0), 60, 300))
        + 0.3 * _clip(t.get("newjoiner_intro_hits", 0), 0, 2),
        "individual_engagement": 0.6 * _clip(t.get("student_turns_per_min", 0), 2, 9) + 0.2 * _clip(t.get("teacher_questions_per_min", 0), 0.5, 3)
        + 0.2 * _clip(t.get("n_students_speaking", 0), 2, 8),
        "energy_pleasantness": 0.4 * _clip(t.get("praise_per_min", 0), 0.1, 1.2) + 0.6 * (1 - _clip(t.get("long_silences_30s", 0), 0, 10)),
        "homework_conclusion": 0.6 * _clip(t.get("homework_mentions", 0), 0, 3) + 0.4 * _clip(t.get("wrapup_hits_last5", 0), 0, 6),
        "av_quality": 1 - _clip(t.get("av_complaints", 0) / max(t.get("student_turns_per_min", 1) * dur, 1), 0.005, 0.03),
    }
    if multimodal and "frames" in f:
        fr, au = f["frames"], f.get("audio", {})
        s["visual_professionalism"] = 0.5 * _clip(fr.get("face_present_frac", 0), 0.3, 0.9) + 0.3 * _clip(fr.get("mean_brightness", 0), 50, 120) \
            + 0.2 * (1 - _clip(fr.get("no_face_streak_max_min", 0), 2, 15))
        s["av_quality"] = 0.6 * s["av_quality"] + 0.4 * (1 - _clip(au.get("audio_silence_frac", 0), 0.15, 0.5))
    return {k: round(v, 3) for k, v in s.items()}


WEIGHTS = {"intro_rapport": 0.18, "individual_engagement": 0.32, "energy_pleasantness": 0.2,
           "homework_conclusion": 0.12, "av_quality": 0.08, "visual_professionalism": 0.10}


def overall(themes: dict) -> float:
    w = {k: WEIGHTS[k] for k in themes}
    return round(sum(themes[k] * w[k] for k in themes) / sum(w.values()), 4)


def fit_cuts(scores, labels):
    """Cut-points between ordinal classes: midpoint of adjacent class means (fallback to defaults)."""
    default = [0.35, 0.5, 0.65]
    means = {}
    for s, l in zip(scores, labels):
        means.setdefault(l, []).append(s)
    m = [np.mean(means[l]) if l in means else None for l in LABELS]
    cuts = []
    for i in range(3):
        a, b = m[i], m[i + 1]
        cuts.append((a + b) / 2 if a is not None and b is not None else default[i])
    return sorted(cuts)


def to_label(score, cuts=(0.35, 0.5, 0.65)):
    return LABELS[int(np.searchsorted(cuts, score))]
