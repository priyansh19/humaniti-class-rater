"""Pedagogy features from an anonymised transcript (spec: analysis.md §5)."""
from __future__ import annotations

import re
from itertools import pairwise

from .models import Utterance

P = {
    "greeting": re.compile(r"\b(good (morning|evening|afternoon)|hello|hi|hey|how are you|how was your day|welcome)\b", re.IGNORECASE),
    "newjoiner": re.compile(r"(new (student|joiner|friend|member)s?|introduce (yourself|yourselves)|self[- ]?introduction|tell (me|us) (your|about yourself)|what is your name)", re.IGNORECASE),
    "praise": re.compile(r"\b(good job|very good|excellent|great|awesome|well done|super|nice|perfect|wonderful|amazing|brilliant|fantastic|correct|right answer|good)\b", re.IGNORECASE),
    "homework": re.compile(r"\b(home ?works?|hws?|assignments?|worksheets?|practice (at|from) home)\b", re.IGNORECASE),
    "wrapup": re.compile(r"\b(bye|see you|next class|that'?s all (for today)?|summary|today we (learn|learned|did|saw)|any doubts|any questions)\b", re.IGNORECASE),
    "av": re.compile(r"(can'?t hear|cannot hear|not audible|voice is (not|breaking)|breaking|not visible|can'?t see|cannot see|screen (is )?not (visible|clear)|not clear|lagging|network (issue|problem)|no sound|echo)", re.IGNORECASE),
    "activity": re.compile(r"\b(puzzles?|video|game|quiz|let'?s play|activity|lichess|chess\.com|board)\b", re.IGNORECASE),
    "question": re.compile(r"\?"),
}

FEATURE_NAMES = [
    "student_turns_per_min", "students_speaking", "student_coverage", "tutor_questions_per_min", "tutor_talk_share",
    "students_named_by_tutor", "greetings_first5", "student_turns_first5", "newjoiner_prompts", "first_long_explanation_min",
    "praise_per_min", "exclaims_per_min", "tutor_wpm", "homework_cues", "homework_last10", "wrapup_last5",
    "long_gaps_30s", "longest_gap_s", "av_complaints", "av_complaints_per_100_student_turns", "activity_cues_per_hour",
]


def compute(utts: list[Utterance], student_name_tokens: set[str] | None = None) -> dict[str, float]:
    if not utts:
        return {k: 0.0 for k in FEATURE_NAMES}
    end = max(u.end for u in utts)
    dur_min = max(end / 60, 1.0)
    tutor = [u for u in utts if u.role == "tutor"]
    students = [u for u in utts if u.role == "student"]
    tw = sum(len(u.text.split()) for u in tutor)
    sw = sum(len(u.text.split()) for u in students)
    turns: dict[str, int] = {}
    for u in students:
        turns[u.speaker] = turns.get(u.speaker, 0) + 1
    covered = sum(1 for v in turns.values() if v >= 3)
    first5 = [u for u in utts if u.start < 300]
    gaps = [b.start - a.end for a, b in pairwise(utts)]
    named = 0
    if student_name_tokens:
        # names are scrubbed to "Student N" labels inside tutor text; count distinct labels the tutor uses
        named = len({m for u in tutor for m in re.findall(r"Student \d+", u.text)})
    first_long = next((u.start for u in tutor if len(u.text.split()) >= 25), end)
    av = sum(1 for u in utts if P["av"].search(u.text))
    tutor_speech_min = max(sum(u.end - u.start for u in tutor) / 60, 0.1)
    return {
        "student_turns_per_min": round(len(students) / dur_min, 3),
        "students_speaking": float(len(turns)),
        "student_coverage": round(covered / len(turns), 3) if turns else 0.0,
        "tutor_questions_per_min": round(sum(len(P["question"].findall(u.text)) for u in tutor) / dur_min, 3),
        "tutor_talk_share": round(tw / max(tw + sw, 1), 3),
        "students_named_by_tutor": float(named),
        "greetings_first5": float(sum(1 for u in first5 if P["greeting"].search(u.text))),
        "student_turns_first5": float(sum(1 for u in first5 if u.role == "student")),
        "newjoiner_prompts": float(sum(1 for u in tutor if P["newjoiner"].search(u.text))),
        "first_long_explanation_min": round(first_long / 60, 2),
        "praise_per_min": round(sum(len(P["praise"].findall(u.text)) for u in tutor) / dur_min, 3),
        "exclaims_per_min": round(sum(u.text.count("!") for u in tutor) / dur_min, 3),
        "tutor_wpm": round(tw / tutor_speech_min, 1),
        "homework_cues": float(sum(1 for u in utts if P["homework"].search(u.text))),
        "homework_last10": float(sum(1 for u in utts if u.start > end - 600 and P["homework"].search(u.text))),
        "wrapup_last5": float(sum(1 for u in utts if u.start > end - 300 and P["wrapup"].search(u.text))),
        "long_gaps_30s": float(sum(1 for g in gaps if g > 30)),
        "longest_gap_s": round(max(gaps, default=0.0), 1),
        "av_complaints": float(av),
        "av_complaints_per_100_student_turns": round(100 * av / max(len(students), 10), 3),
        "activity_cues_per_hour": round(sum(1 for u in tutor if P["activity"].search(u.text)) / dur_min * 60, 2),
    }
