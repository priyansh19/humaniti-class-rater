"""Edge cases for the hosted Brief-mode path (spec: docs/specs/guardrails.md)."""
import pytest

from rater import hosted
from rater.guardrails import GuardError, check_text
from rater.hosted import AdvancedConfig, RateLimiter, assess_text, custom_label


def code(fn):
    with pytest.raises(GuardError) as e:
        fn()
    return e.value.code


def test_happy_path_brief(vtt_text):
    r = assess_text(vtt_text)
    assert r["label"] in {"Poor", "Average", "Good", "Excellent"} and r["mode"] == "brief" and r["judge"] == "local"
    assert r["criteria"] and "custom" not in r


@pytest.mark.parametrize("t", [None, "", "   \n\t  ", "WEBVTT\n\n"])
def test_empty(t):
    assert code(lambda: assess_text(t)) in {"empty", "too_short"}


def test_huge():
    assert code(lambda: check_text("Tutor: hello class " * 200_000)) == "too_large"


def test_advanced_cap_is_tighter():
    assert code(lambda: assess_text("Tutor: hello there class " * 50, AdvancedConfig(max_chars=1000))) == "too_large"


def test_binary():
    assert code(lambda: check_text("\x00\x01\x02 Tutor: hi " * 50)) == "binary"


def test_garbled():
    import random
    rnd = random.Random(1)
    junk = " ".join("".join(rnd.choice("qxzjkvwbfg") for _ in range(7)) for _ in range(300))
    assert code(lambda: check_text(junk)) == "garbled"


def test_non_english_script_is_low_confidence():
    hindi = "\n".join(f"Tutor: बच्चों आज हम घोड़े की चाल सीखेंगे {i}" for i in range(40))
    r = assess_text(hindi)
    assert "non_english" in r["guard_flags"] and r["confidence"] <= 0.3


def test_no_speaker_labels(vtt_text):
    plain = "\n".join(line.split(":", 1)[-1] for line in vtt_text.splitlines() if "-->" not in line and line.strip() and not line.startswith("WEBVTT") and not line.strip().isdigit())
    r = assess_text(plain)
    assert "no_speakers" in r["guard_flags"] and r["confidence"] <= 0.6


def test_very_short_class():
    t = ("WEBVTT\n\n" + "\n\n".join(f"00:0{i}:00.000 --> 00:0{i}:05.000\nTutor: Good evening everyone, what does the knight do on this board?\n\n"
                                    f"00:0{i}:06.000 --> 00:0{i}:09.000\nStudent A: it jumps in an L shape" for i in range(4)))
    r = assess_text(t)
    assert "short_class" in r["guard_flags"] and r["confidence"] <= 0.4


def test_too_few_words():
    assert code(lambda: assess_text("Tutor: hi\nStudent: hi")) == "too_short"


def test_judge_failure_falls_back_to_local(vtt_text, monkeypatch):
    class Boom:
        name, model = "openrouter", "x"

        def complete_json(self, *a, **k):
            raise hosted.providers.ProviderError("401 expired key")
    monkeypatch.setattr(hosted.providers, "chain", lambda: [Boom()])
    r = assess_text(vtt_text, AdvancedConfig(provider="auto"))
    assert r["judge"] == "local" and any("local scorer used" in w for w in r["warnings"])


def test_advanced_custom_label_and_embeddings_warning(vtt_text):
    r = assess_text(vtt_text, AdvancedConfig(weights={"energy": 5}, thresholds=[1.5, 2.0, 2.5], embeddings=True))
    assert r["mode"] == "advanced" and r["custom"]["label"] in {"Poor", "Average", "Good", "Excellent"}
    assert any("Embeddings" in w for w in r["warnings"])


def test_custom_label_thresholds_monotone():
    f = {"text": {}}
    lo = custom_label(f, AdvancedConfig(thresholds=[4.0, 4.5, 4.9]))["label"]
    hi = custom_label(f, AdvancedConfig(thresholds=[1.1, 1.2, 1.3]))["label"]
    assert ["Poor", "Average", "Good", "Excellent"].index(lo) <= ["Poor", "Average", "Good", "Excellent"].index(hi)


@pytest.mark.parametrize("kw", [{"thresholds": [3, 2, 4]}, {"thresholds": [0, 2, 3]}, {"weights": {"nope": 1}},
                                {"weights": {"energy": 9}}, {"provider": "evil"}, {"max_chars": 10}])
def test_advanced_config_validation(kw):
    with pytest.raises(ValueError):
        AdvancedConfig(**kw)


def test_rate_limiter():
    rl = RateLimiter(2, 60)
    assert rl.allow("a", 0) and rl.allow("a", 1) and not rl.allow("a", 2) and rl.allow("b", 2) and rl.allow("a", 70)


@pytest.mark.parametrize("url,c", [("ftp://x/y.vtt", "bad_link"), ("http://127.0.0.1/a.vtt", "bad_link"),
                                   ("http://169.254.169.254/latest", "bad_link"), ("https://" + "a" * 3000, "bad_link"),
                                   ("not a url", "bad_link")])
def test_bad_links(url, c):
    assert code(lambda: hosted.fetch_transcript(url)) == c


class _Resp:
    def __init__(self, status=200, ctype="text/vtt", body=b"WEBVTT", redirect=False):
        self.status_code, self.headers, self.content, self.is_redirect = status, {"content-type": ctype}, body, redirect
        self.text = body.decode("utf-8", "replace")


@pytest.mark.parametrize("resp,c", [(_Resp(404), "bad_link"), (_Resp(ctype="text/html"), "bad_link"),
                                    (_Resp(ctype="video/mp4"), "video_needs_worker"), (_Resp(redirect=True), "bad_link"),
                                    (_Resp(body=b"x" * 5_000_001), "too_large")])
def test_link_responses(monkeypatch, resp, c):
    import httpx
    monkeypatch.setattr(hosted, "_noop", None, raising=False)
    monkeypatch.setattr("rater.api.ingest.check_public_url", lambda u: None)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: resp)
    assert code(lambda: hosted.fetch_transcript("https://example.com/t.vtt")) == c


def test_link_ok(monkeypatch, vtt_text):
    import httpx
    monkeypatch.setattr("rater.api.ingest.check_public_url", lambda u: None)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(body=vtt_text.encode()))
    assert hosted.fetch_transcript("https://example.com/t.vtt").startswith("WEBVTT")


def test_payload_never_contains_names(vtt_text):
    import json

    from conftest import NAMES
    r = json.dumps(assess_text(vtt_text))
    assert not any(n in r for n in NAMES)


def test_capabilities_lists_missing_keys(monkeypatch):
    for k in ["OPENROUTER_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "RATER_LLM_PROVIDER"]:
        monkeypatch.delenv(k, raising=False)
    c = hosted.capabilities()
    assert c["judge"] == "local" and c["video"] is False and "MODAL_TOKEN_ID" in c["missing"]["video_processing"]
