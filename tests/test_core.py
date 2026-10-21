import json
import os
import subprocess

import pytest

from classq import llm, transcript as T
from classq.rubric import LABELS, fit_cuts, overall, theme_scores, to_label

VTT = """WEBVTT

1
00:00:05.000 --> 00:00:07.000
Ms Tutor: Good evening everyone! How are you?

2
00:00:08.000 --> 00:00:09.000
Arun K: Fine ma'am.

3
00:00:10.000 --> 00:00:12.000
Ms Tutor: Arun, can you introduce yourself? You are a new student?

4
00:00:13.000 --> 00:00:15.000
Bina's iPad: I can't hear you.

5
00:20:00.000 --> 00:20:03.000
Ms Tutor: Very good Bina! Your homework is page 4. See you next class, bye.
"""


def test_parse_vtt():
    cues = T.parse_vtt(VTT)
    assert len(cues) == 5 and cues[0].speaker == "Ms Tutor" and cues[4].start == 1200


def test_features():
    f = T.features(T.parse_vtt(VTT))
    assert f["n_students_speaking"] == 2
    assert f["homework_mentions"] == 1 and f["av_complaints"] == 1
    assert f["students_addressed_by_name"] == 2
    assert f["intro_hits_first5"] >= 1 and f["newjoiner_intro_hits"] >= 1


def test_anonymise_removes_names():
    anon, mapping = T.anonymise(T.parse_vtt(VTT))
    blob = " ".join(c.speaker + " " + c.text for c in anon)
    assert "Arun" not in blob and "Bina" not in blob
    assert mapping["Ms Tutor"] == "Tutor"
    assert all("Arun" not in e and "Bina" not in e for e in T.evidence(T.parse_vtt(VTT)))


def test_plain_text_transcript():
    cues = T.parse_any("Tutor: hello\nKid: hi\n")
    assert len(cues) == 2 and cues[1].speaker == "Kid"


def test_scoring_monotone_and_labels():
    good = {"text": T.features(T.parse_vtt(VTT))}
    bad = {"text": {**good["text"], "intro_hits_first5": 0, "homework_mentions": 0, "praise_per_min": 0, "students_addressed_by_name": 0}}
    assert overall(theme_scores(good)) > overall(theme_scores(bad))
    assert to_label(0.0) == "Poor" and to_label(1.0) == "Excellent"


def test_fit_cuts_ordered():
    cuts = fit_cuts([0.2, 0.3, 0.5, 0.7, 0.9], ["Poor", "Poor", "Average", "Good", "Excellent"])
    assert cuts == sorted(cuts) and len(cuts) == 3


def test_llm_parse_and_prompt_has_no_media():
    out = llm.parse('noise {"label": "Good", "strengths": ["[02:10] x"], "improvements": []} tail')
    assert out["label"] == "Good"
    with pytest.raises(ValueError):
        llm.parse('{"label": "Great"}')
    cues = T.parse_vtt(VTT)
    p = llm.build_prompt({"text": T.features(cues), "evidence": T.evidence(cues), "excerpt": T.excerpt(cues)})
    assert "Arun" not in p and "Bina" not in p and LABELS[0] in p


@pytest.mark.parametrize("prov,env,payload", [
    ("openai", "OPENAI_API_KEY", {"choices": [{"message": {"content": '{"label": "Average"}'}}]}),
    ("anthropic", "ANTHROPIC_API_KEY", {"content": [{"type": "text", "text": '{"label": "Average"}'}]}),
    ("gemini", "GEMINI_API_KEY", {"candidates": [{"content": {"parts": [{"text": '{"label": "Average"}'}]}}]}),
])
def test_llm_providers_mocked(monkeypatch, prov, env, payload):
    for e in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER", "OPENROUTER_API_KEY"]:
        monkeypatch.delenv(e, raising=False)
    monkeypatch.setenv(env, "k")
    class R:
        status_code = 200
        def json(self):
            return payload
    sent = {}
    monkeypatch.setattr(llm.requests, "post", lambda url, **kw: sent.update(url=url, **kw) or R())
    assert llm.detect()[0] == prov
    out = llm.call("hi")
    assert out["label"] == "Average" and out["provider"].startswith(prov)
    assert "openrouter" not in sent["url"] and "files" not in sent


def test_no_llm_without_approved_key(monkeypatch):
    for e in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        monkeypatch.delenv(e, raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    assert not llm.enabled()


@pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode, reason="no ffmpeg")
def test_media_synthetic(tmp_path):
    from classq import media as M
    v = str(tmp_path / "t.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=5:duration=12", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=12", "-shortest", v], check=True, capture_output=True)
    fr = M.frame_features(v, every_s=4); au = M.audio_features(v)
    assert fr["frames_sampled"] >= 2 and 0 <= fr["face_present_frac"] <= 1
    assert "audio_silence_frac" in au


def test_gitignore_protects_data():
    gi = open(os.path.join(os.path.dirname(__file__), "..", ".gitignore")).read()
    for pat in ["*.mp4", "*.vtt", "cache/", "*.jpg", ".env"]:
        assert pat in gi


def test_web_endpoint_rate():
    from api.rate import rate
    r = rate({"transcript": VTT})
    assert r["label"] in LABELS and r["observations"]
    assert "Arun" not in json.dumps(r["evidence"])


def test_web_endpoint_rejects_private_url():
    from api.rate import fetch
    with pytest.raises(ValueError):
        fetch("http://127.0.0.1/x.vtt")
    with pytest.raises(ValueError):
        fetch("file:///etc/passwd")
