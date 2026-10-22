import pytest
from conftest import NAMES

from rater.analysis import analyse
from rater.media import MediaError, probe


def test_transcript_only(vtt_text):
    a = analyse(transcript_text=vtt_text)
    assert a.transcript_source == "vtt" and set(a.features) == {"text"}
    assert not any(n in a.model_dump_json() for n in NAMES)


def test_full_media_with_transcript(synthetic_mp4, vtt_text):
    stages = []
    a = analyse(synthetic_mp4, vtt_text, frame_every_s=5, on_progress=lambda s, p: stages.append(s))
    assert set(a.features) == {"text", "audio", "visual"}
    assert a.features["visual"]["frames"] >= 5
    assert {"probing", "audio", "frames"} <= set(stages)
    assert probe(synthetic_mp4)["duration_s"] == pytest.approx(30, abs=1)


def test_rejects_non_media(tmp_path):
    p = tmp_path / "x.mp4"
    p.write_text("not a video")
    with pytest.raises(MediaError):
        analyse(str(p), "A: hi\nB: hello\n")


def test_requires_input():
    with pytest.raises(ValueError):
        analyse()
