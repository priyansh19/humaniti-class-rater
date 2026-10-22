"""Ordinal logistic model + v2.2 selection."""
import numpy as np

from rater.judge.ologit import fit
from rater.judge.selection import OL, candidates_v22, from_json, to_json

L = ["Poor", "Average", "Good", "Excellent"]


def test_recovers_monotone_signal():
    x = np.linspace(-2, 2, 40)
    y = [L[min(int((v + 2) / 1.0), 3)] for v in x]
    m = fit([{"a": v} for v in x], y, ["a"], lam=0.1)
    assert m.w[0] > 0 and m.theta == sorted(m.theta)
    assert np.mean([m.predict({"a": v})[0] == t for v, t in zip(x, y, strict=True)]) > 0.8
    assert abs(m.proba({"a": 0.0}).sum() - 1) < 1e-9


def test_unobserved_feature_returns_none_and_missing_value_imputed():
    assert fit([{"a": None}, {"a": None}], ["Poor", "Good"], ["a"]) is None
    m = fit([{"a": 1.0}, {"a": 3.0}, {"a": None}], ["Poor", "Good", "Average"], ["a"])
    assert m.predict({"a": None})[0] in L


def test_candidate_set_is_small_and_on_rubric_criteria_only():
    c = candidates_v22()
    assert len(c) == 56 and all(n.startswith("ologit:") for n in c)


def test_json_roundtrip():
    m = OL(fit([{"crit.x": float(i)} for i in range(8)], L * 2, ["crit.x"]))
    m2 = from_json(to_json("ologit:1.0:x", m))
    assert m2.predict({"crit.x": 7.0})[0] == m.predict({"crit.x": 7.0})[0]
