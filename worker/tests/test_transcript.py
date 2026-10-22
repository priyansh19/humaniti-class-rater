from conftest import NAMES

from rater import transcript as T


def test_parse_vtt_speakers_and_times(vtt_text):
    raw = T.parse_vtt(vtt_text)
    assert len(raw) == 13
    assert raw[0][2] == "Meera Tutor" and raw[11][0] == 1200.0


def test_parse_vtt_hours_and_multiline():
    raw = T.parse_vtt("WEBVTT\n\n1\n01:02:03.500 --> 01:02:05.000\nA B: line one\nline two\n")
    assert raw == [(3723.5, 3725.0, "A B", "line one line two")]


def test_parse_txt():
    raw, src = T.parse("Tutor: hello class\nKid: hi\n")
    assert src == "txt" and raw[1][2] == "Kid" and raw[1][0] == 5.0


def test_roles_tutor_is_most_words(vtt_text):
    utts, src, est, _ = T.from_text(vtt_text)
    assert src == "vtt" and not est
    assert utts[0].speaker == "Tutor" and utts[0].role == "tutor"
    assert {u.speaker for u in utts if u.role == "student"} == {"Student 1", "Student 2"}


def test_anonymisation_removes_every_name(vtt_text):
    utts, *_ = T.from_text(vtt_text)
    blob = " ".join(u.speaker + " " + u.text for u in utts)
    for n in NAMES:
        assert n not in blob
    assert "Student 2, can you introduce yourself" in blob


def test_asr_roles_are_estimated():
    utts = T.from_segments([(0, 5, "Hello class, today we study openings and the centre. Who knows e4?"),
                            (5, 6, "Me sir"), (6, 12, "Good, the pawn controls the centre squares well")])
    assert [u.role for u in utts] == ["tutor", "student", "tutor"]


def test_fmt_ts():
    assert T.fmt_ts(65) == "01:05" and T.fmt_ts(3725) == "1:02:05"
