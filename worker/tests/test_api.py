import importlib
import os
import shutil
import time

import pytest
from conftest import NAMES
from fastapi.testclient import TestClient


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("RATER_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("RATER_API_KEY", raising=False)
    for k in ["OPENROUTER_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "RATER_LOCAL_LLM_URL"]:
        monkeypatch.delenv(k, raising=False)
    from rater.api import app as appmod
    from rater.api import ingest
    appmod = importlib.reload(appmod)
    monkeypatch.setattr(ingest, "CHUNK", 64 * 1024)      # force multi-chunk uploads with small test media
    return TestClient(appmod.app), appmod


def _fixture():
    with open(os.path.join(os.path.dirname(__file__), "fixtures/synthetic_class.vtt"), encoding="utf-8") as fh:
        return fh.read()


def _wait(client, jid, timeout=120):
    t = time.time()
    while time.time() - t < timeout:
        j = client.get(f"/jobs/{jid}").json()
        if j["status"] in ("done", "failed"):
            return j
        time.sleep(0.3)
    raise AssertionError("job timed out")


def test_health(api):
    c, _ = api
    h = c.get("/health").json()
    assert h["ok"] and h["judge"] == "local"


def test_chunked_upload_end_to_end(api, synthetic_mp4, vtt_text):
    c, appmod = api
    with open(synthetic_mp4, "rb") as fh:
        data = fh.read()
    init = c.post("/uploads", json={"filename": "class.mp4", "size": len(data)}).json()
    cs = init["chunk_size"]
    assert init["chunks"] > 1
    for n in reversed(range(init["chunks"])):          # out of order + one retry
        c.put(f"/uploads/{init['upload_id']}/chunks/{n}", content=data[n * cs:(n + 1) * cs]).raise_for_status()
    c.put(f"/uploads/{init['upload_id']}/chunks/0", content=data[:cs]).raise_for_status()
    jid = c.post(f"/uploads/{init['upload_id']}/complete", json={"transcript_text": vtt_text}).json()["job_id"]
    j = _wait(c, jid)
    assert j["status"] == "done", j["message"]
    r = j["report"]
    assert r["label"] in ["Poor", "Average", "Good", "Excellent"] and r["criteria"] and r["improvements"]
    assert "visual" in r["analysis"]["features"]
    assert not any(n in str(r) for n in NAMES)
    assert not os.listdir(os.path.join(appmod.DATA, "media"))      # recording deleted after processing


def test_upload_validation(api):
    c, _ = api
    assert c.post("/uploads", json={"filename": "x.exe", "size": 10}).status_code == 400
    assert c.post("/uploads", json={"filename": "x.mp4", "size": 3 * 1024 ** 3}).status_code == 400
    init = c.post("/uploads", json={"filename": "x.mp4", "size": 100}).json()
    assert c.put(f"/uploads/{init['upload_id']}/chunks/0", content=b"short").status_code == 400
    assert c.post(f"/uploads/{init['upload_id']}/complete", json={}).status_code == 400   # missing chunks
    assert c.put("/uploads/../../etc/chunks/0", content=b"x").status_code in (400, 404)


def test_link_job(api, synthetic_mp4, monkeypatch):
    c, appmod = api
    monkeypatch.setattr(appmod, "download", lambda url, dest, on_progress=None: shutil.copy(synthetic_mp4, dest))
    monkeypatch.setattr(appmod, "fetch_text", lambda url: _fixture())
    jid = c.post("/jobs", json={"url": "https://example.com/a.mp4", "transcript_url": "https://example.com/a.vtt"}).json()["job_id"]
    j = _wait(c, jid)
    assert j["status"] == "done" and j["report"]["analysis"]["transcript_source"] == "vtt"


def test_link_job_rejects_private_address(api):
    c, _ = api
    jid = c.post("/jobs", json={"url": "http://127.0.0.1:8080/x.mp4"}).json()["job_id"]
    j = _wait(c, jid)
    assert j["status"] == "failed" and "private" in j["message"]


def test_transcript_endpoint(api, vtt_text):
    c, _ = api
    r = c.post("/assess/transcript", json={"transcript_text": vtt_text}).json()
    assert r["label"] and "presentation" not in r["criteria"]
    assert c.post("/assess/transcript", json={"transcript_text": ""}).status_code == 400


def test_api_key_enforced(api, monkeypatch):
    c, _ = api
    monkeypatch.setenv("RATER_API_KEY", "s3cret")
    assert c.post("/assess/transcript", json={"transcript_text": "A: hi"}).status_code == 401
    assert c.get("/health").status_code == 200


def test_unknown_job(api):
    c, _ = api
    assert c.get("/jobs/doesnotexist").status_code == 404


def test_per_client_limit(api, monkeypatch):
    c, appmod = api
    monkeypatch.setattr(appmod.pool, "submit", lambda *a, **k: None)   # keep jobs queued
    for _ in range(appmod.MAX_ACTIVE_PER_CLIENT):
        assert c.post("/jobs", json={"url": "https://example.com/a.mp4"}).status_code == 200
    assert c.post("/jobs", json={"url": "https://example.com/a.mp4"}).status_code == 429
