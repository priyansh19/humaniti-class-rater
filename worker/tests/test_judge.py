import json

import httpx
import pytest
from conftest import NAMES

from rater.analysis import analyse
from rater.judge import judge, llm, providers
from rater.judge.local import build_report
from rater.judge.ordinal import fit
from rater.judge.rubric import CRITERIA, criterion_scores
from rater.models import LABELS

KEYS = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "RATER_LLM_PROVIDER", "RATER_LLM_MODEL", "RATER_LOCAL_LLM_URL"]


@pytest.fixture
def analysis(vtt_text):
    return analyse(transcript_text=vtt_text)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in KEYS + ["OPENROUTER_API_KEY"]:
        monkeypatch.delenv(k, raising=False)


def _llm_answer(label="Good", ts="00:21"):
    return {"label": label, "confidence": 0.7, "summary": "s",
            "criteria": {k: {"score": 4, "rationale": "r", "timestamps": [ts, "59:59"]} for k in CRITERIA},
            "strengths": ["a"], "improvements": ["b"]}


def test_criterion_scores_text_only_has_no_visual(analysis):
    c = criterion_scores(analysis.features)
    assert c["presentation"] is None and all(1 <= v <= 5 for v in c.values() if v is not None)


def test_more_engagement_scores_higher(analysis):
    base = criterion_scores(analysis.features)["individual_attention"]
    more = {**analysis.features, "text": {**analysis.features["text"], "student_turns_per_min": 20}}
    assert criterion_scores(more)["individual_attention"] > base


def test_ordinal_fit_predict_monotone():
    rows = [{"a": float(i), "b": float(i % 2)} for i in range(8)]
    labels = [LABELS[min(i // 2, 3)] for i in range(8)]
    m = fit(rows, labels, ["a", "b"])
    assert m.predict({"a": 0, "b": 0})[0] == "Poor" and m.predict({"a": 7, "b": 1})[0] == "Excellent"
    assert m.predict({"a": None, "b": 1})[0] in LABELS   # missing -> imputed


def test_local_report_is_complete_and_anonymous(analysis):
    r = build_report(analysis)
    assert r.label in LABELS and r.judge == "local"
    assert set(r.criteria) == set(CRITERIA) - {"presentation"}
    assert r.improvements and r.strengths
    assert not any(n in r.model_dump_json() for n in NAMES)


def test_no_key_means_local(analysis, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")          # not an approved provider
    assert providers.detect() is None
    assert judge(analysis).judge == "local"


@pytest.mark.parametrize("prov,env", [("gemini", "GEMINI_API_KEY"), ("openai", "OPENAI_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY"),
                                      ("local", "RATER_LOCAL_LLM_URL")])
def test_each_provider_mocked(analysis, monkeypatch, prov, env):
    monkeypatch.setenv(env, "http://127.0.0.1:8081/v1" if prov == "local" else "test-key")
    ans = _llm_answer()
    bodies = {"local": {"choices": [{"message": {"content": json.dumps(ans)}}]},"gemini": {"candidates": [{"content": {"parts": [{"text": json.dumps(ans)}]}}]},
              "openai": {"choices": [{"message": {"content": json.dumps(ans)}}]},
              "anthropic": {"content": [{"type": "tool_use", "input": ans}]}}
    sent = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.update(url=url, body=json)
        return httpx.Response(200, json=bodies[prov], request=httpx.Request("POST", url))
    monkeypatch.setattr(providers.httpx, "post", fake_post)
    r = judge(analysis)
    assert r.judge.startswith(prov) and r.label == "Good"
    assert "openrouter" not in sent["url"]
    blob = json.dumps(sent["body"])
    assert not any(n in blob for n in NAMES)                 # no names leave the box
    assert "mp4" not in blob.lower() and "base64" not in blob.lower()
    # hallucinated timestamp 59:59 removed, real one kept
    assert any("removed" in w for w in r.warnings)
    assert any(c.evidence for c in r.criteria.values())


def test_cloud_key_preferred_over_local(monkeypatch):
    monkeypatch.setenv("RATER_LOCAL_LLM_URL", "http://127.0.0.1:8081/v1")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert providers.detect() == "gemini"


def test_invalid_llm_output_falls_back(analysis, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(providers.httpx, "post", lambda url, **kw: httpx.Response(
        200, json={"choices": [{"message": {"content": '{"label": "Great"}'}}]}, request=httpx.Request("POST", url)))
    r = judge(analysis)
    assert r.judge == "local" and any("LLM judge failed" in w for w in r.warnings)


def test_http_error_falls_back(analysis, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(providers.httpx, "post", lambda url, **kw: httpx.Response(401, json={}, request=httpx.Request("POST", url)))
    assert judge(analysis).judge == "local"


def test_privacy_guard_blocks_names(analysis):
    payload = llm.build_payload(analysis)
    llm.assert_private(payload, {"meera", "kavya"})          # anonymised payload passes
    with pytest.raises(PermissionError):
        llm.assert_private(payload + " Kavya", {"kavya"})


def test_payload_redacts_contact_details(analysis):
    a = analysis.model_copy(update={"excerpt": "mail me at a.b@example.com or +91 98765 43210"})
    p = llm.build_payload(a)
    assert "example.com" not in p and "98765" not in p
