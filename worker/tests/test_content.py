"""Domain content coverage: topic detection, stages, depth, evidence, and the eval helpers."""
from rater.content import analyse_content, topic_set
from rater.judge.rubric import FROZEN_KEYS, criterion_scores
from rater.models import Utterance


def U(t, role, text):
    return Utterance(start=t, end=t + 5, role=role, speaker="Tutor" if role == "tutor" else "Student 1", text=text)


LESSON = [
    U(10, "tutor", "Good evening everyone, in the last class we did checkmate patterns, quick revision."),
    U(120, "tutor", "Today we learn about the fork. A fork means one piece attacks two pieces at the same time, because the knight jumps."),
    U(150, "tutor", "See, the knight forks the king and the rook, so we win the rook."),
    U(200, "tutor", "Now your turn: find the fork in this puzzle. Which move?"),
    U(215, "student", "Knight to f7, fork!"),
    U(230, "tutor", "Excellent, that is a fork on the king and queen."),
    U(400, "tutor", "Another fork puzzle, solve this one, find the knight fork."),
    U(420, "student", "Knight e6 fork"),
    U(1500, "tutor", "So to summarise, today we learned the fork: one piece attacking two."),
]


def test_detects_subject_topic_and_stages():
    c = analyse_content(LESSON)
    assert c["subject"] == "chess"
    fork = next(t for t in c["topics"] if "fork" in t["topic"])
    assert fork["explained"] and fork["practised_turns"] >= 1 and fork["recapped"]
    assert 0 <= fork["depth"] <= 3 and fork["depth"] >= 2
    assert all({"t", "quote"} <= set(q) for q in fork["evidence"])
    assert c["metrics"]["opens_with_revision"] == 1.0


def test_empty_and_off_topic():
    assert analyse_content([])["topics"] == []
    c = analyse_content([U(0, "tutor", "Hello, can you hear me? My internet is slow today.")])
    assert c["subject"] == "unknown" and c["topics"] == []


def test_content_criterion_scored_but_not_in_frozen_model():
    c = analyse_content(LESSON)
    s = criterion_scores({"content": c["metrics"]})
    assert 1 <= s["content_coverage"] <= 5
    assert "content_coverage" not in FROZEN_KEYS


def test_topic_set_threshold():
    c = {"topics": [{"topic": "a", "minutes": 3}, {"topic": "b", "minutes": 0.2}]}
    assert topic_set(c) == {"a"}


def test_content_eval_checks():
    from eval.content_eval import _rank_corr, check
    a = {"content": {"metrics": {"practised_frac": 0.5, "opens_with_revision": 1.0}, "topics": []},
         "features": {"visual": {"screen_share_frac": 0.05}}}
    assert check("practice_present", a) and check("opens_with_revision", a) and check("teaching_aids_gap", a)
    assert _rank_corr([1, 2, 3], [1, 2, 3]) == 1.0 and _rank_corr([1], [1]) is None
