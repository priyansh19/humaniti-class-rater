"""Vercel Python fallback: transcript-only assessment (no video). Uses the vendored rater core (see scripts/sync-rater.sh)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from rater.analysis import analyse  # noqa: E402
from rater.api_ingest_lite import IngestError, fetch_text  # noqa: E402
from rater.judge import judge  # noqa: E402

app = FastAPI(docs_url=None, redoc_url=None)


class Body(BaseModel):
    transcript_text: str | None = Field(default=None, max_length=3_000_000)
    transcript_url: str | None = Field(default=None, max_length=2048)


@app.post("/api/py/assess")
def assess(body: Body):
    try:
        text = body.transcript_text or (fetch_text(body.transcript_url) if body.transcript_url else "")
        a = analyse(transcript_text=text)
    except (IngestError, ValueError) as e:
        raise HTTPException(400, str(e)) from e
    r = judge(a).model_dump()
    r["analysis"] = {"duration_s": a.duration_s, "transcript_source": a.transcript_source, "roles_estimated": a.roles_estimated, "features": a.features}
    return r


@app.get("/api/py/health")
def health():
    from rater.judge.providers import detect
    return {"ok": True, "judge": detect() or "local", "mode": "transcript-only"}
