"""Embeddings service with a fake encoder (no torch in CI; the real model runs locally only)."""
import hashlib

import numpy as np
import pytest

from rater import embeddings as E
from rater.analysis import analyse
from rater.judge.llm import build_payload
from rater.models import Utterance


class Fake:
    """Deterministic bag-of-words embedder: similar words -> similar vectors."""
    def encode(self, x, prompt_name=None, convert_to_numpy=True, processing_kwargs=None):
        if isinstance(x, list):
            return np.array([self.encode(i) for i in x])
        s = x if isinstance(x, str) else " ".join(f"{k}" for k in x)
        v = np.zeros(768)
        for w in s.lower().replace(",", " ").split():
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 768] += 1
        return v / (np.linalg.norm(v) + 1e-9)


@pytest.fixture
def fake(monkeypatch):
    f = Fake()
    monkeypatch.setattr(E, "load", lambda *a, **k: f)
    return f


def U(t, role, text):
    return Utterance(start=t, end=t + 4, role=role, speaker="Tutor" if role == "tutor" else "Student 1", text=text)


def test_windows_cover_duration_and_fold_short_tail():
    assert E.windows(600) == [(0, 300), (300, 600)]
    assert E.windows(630) == [(0, 300), (300, 630)]
    assert E.windows(90) == [(0, 90)]


def test_probe_contrast_sign(fake):
    pos, neg, _ = E.PROBES["warm_rapport"]
    good = [E.Window(0, 300, vec={"text": E._norm(fake.encode(pos), 256)})]
    bad = [E.Window(0, 300, vec={"text": E._norm(fake.encode(neg), 256)})]
    assert E.probe_features(good)["warm_rapport.text"] > 0 > E.probe_features(bad)["warm_rapport.text"]


def test_retrieval_ranks_matching_window_first(fake):
    ws = [E.Window(0, 300, vec={"text": E._norm(fake.encode("random words about weather"), 256)}),
          E.Window(300, 600, vec={"text": E._norm(fake.encode(E.CRITERION_QUERIES["homework_closure"]), 256)})]
    top = E.retrieve(ws, k=1)["homework_closure"][0]
    assert top["t0"] == 300 and top["modality"] == "text"


def test_semantic_content_finds_topic(fake):
    ws = [E.Window(0, 300, vec={"text": E._norm(fake.encode(E.TOPIC_DESCRIPTIONS["tactics: forks"]), 256)})]
    c = E.semantic_content(ws)
    assert c["topics"][0]["topic"] == "tactics: forks" and c["topics"][0]["minutes"] > 0


def test_analysis_integration_transcript_only(fake):
    vtt = "WEBVTT\n\n" + "".join(f"00:{m:02d}:00.000 --> 00:{m:02d}:05.000\nAsha Rao: Good evening, today we learn the fork, give homework.\n\n"
                                 f"00:{m:02d}:10.000 --> 00:{m:02d}:12.000\nKid One: Knight fork!\n\n" for m in range(12))
    a = analyse(transcript_text=vtt, use_embeddings=True)
    assert "emb" in a.features and a.evidence_windows and "semantic" in a.content
    p = build_payload(a)
    assert "EVIDENCE WINDOWS" in p and "Asha" not in p and "Rao" not in p


def test_missing_dependency_is_a_warning(monkeypatch):
    def boom(*a, **k):
        raise ImportError("no torch")
    monkeypatch.setattr(E, "embed_class", boom)
    a = analyse(transcript_text="WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nTutor: hello everyone\n", use_embeddings=True)
    assert any("Embeddings requested" in w for w in a.warnings)


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("RATER_EMBEDDINGS", raising=False)
    a = analyse(transcript_text="WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nTutor: hello everyone\n")
    assert "emb" not in a.features
