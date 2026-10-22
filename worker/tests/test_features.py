import numpy as np
from conftest import NAMES

from rater import audio, evidence, text_features, transcript, visual


def _utts(vtt_text):
    utts, _, _, toks = transcript.from_text(vtt_text)
    return utts, toks


def test_text_features(vtt_text):
    utts, toks = _utts(vtt_text)
    f = text_features.compute(utts, toks)
    assert set(f) == set(text_features.FEATURE_NAMES)
    assert f["students_speaking"] == 2
    assert f["students_named_by_tutor"] == 2
    assert f["homework_cues"] == 1 and f["homework_last10"] == 1
    assert f["av_complaints"] == 1
    assert f["newjoiner_prompts"] >= 1 and f["greetings_first5"] >= 1
    assert f["longest_gap_s"] > 1000


def test_mute_is_not_an_av_complaint():
    utts, _, _, _ = transcript.from_text("A Tutor: please unmute yourself and answer the question now\nKid: ok\n")
    assert text_features.compute(utts)["av_complaints"] == 0


def test_evidence_is_anonymised_and_timestamped(vtt_text):
    utts, _ = _utts(vtt_text)
    ev = evidence.collect(utts)
    assert ev["homework_closure"] and ev["homework_closure"][0].t == 1200.0
    assert ev["av_quality"][0].speaker == "Student 2"
    blob = str(ev) + evidence.excerpt(utts)
    assert not any(n in blob for n in NAMES)


def test_audio_silence_vs_tone():
    rate = 8000
    t = np.arange(rate * 20) / rate
    x = np.concatenate([0.3 * np.sin(2 * np.pi * 220 * t), np.zeros(rate * 20, np.float32)]).astype(np.float32)
    f = audio.compute_from_signal(x, rate)
    assert 0.4 < f["silence_frac"] < 0.6 and f["clip_frac"] == 0


def test_visual_layout_classifier():
    grey = np.full((180, 320, 3), 30, np.uint8)
    board = np.kron((np.indices((18, 32)).sum(0) % 2) * 200 + 30, np.ones((10, 10))).astype(np.uint8)
    board = np.stack([board[:180, :320]] * 3, -1)
    assert visual.classify(grey) == "camera_off"
    assert visual.classify(board) == "screen_share"


def test_tutor_camera_off_alignment(vtt_text):
    utts, _ = _utts(vtt_text)
    grey = np.full((180, 320, 3), 30, np.uint8)
    # frames at t=6 (tutor speaking, camera off) and t=18 (student speaking, camera off)
    f = visual.compute([(6.0, grey), (18.0, grey)], utts)
    assert f["camera_off_frac"] == 1.0 and f["tutor_camera_off_frac"] == 1.0
