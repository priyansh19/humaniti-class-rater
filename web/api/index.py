"""Vercel Python function: thin HTTP layer over rater.hosted (spec: docs/specs/hosted-api.md).
Transcript-only. The rater core is vendored at build time by scripts/sync-rater.sh."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel, Field, ValidationError  # noqa: E402

from rater import hosted  # noqa: E402
from rater.guardrails import GuardError  # noqa: E402

app = FastAPI(docs_url=None, redoc_url=None)
BRIEF_LIMIT = hosted.RateLimiter(30, 600)
ADV_LIMIT = hosted.RateLimiter(10, 600)   # Advanced mode: tighter product-style restriction


class Body(BaseModel):
    transcript_text: str | None = Field(default=None, max_length=3_000_000)
    transcript_url: str | None = Field(default=None, max_length=2048)
    advanced: dict | None = None


def err(code: str, message: str, status: int):
    return JSONResponse({"error": code, "detail": message}, status_code=status)


@app.exception_handler(ValidationError)
async def _ve(_, e):
    return err("invalid_request", "; ".join(x["msg"] for x in e.errors())[:400], 422)


@app.post("/api/py/assess")
async def assess(request: Request):
    ip = (request.headers.get("x-forwarded-for") or "anon").split(",")[0].strip()
    try:
        raw = await request.json()
    except Exception:  # noqa: BLE001
        return err("invalid_request", "Body must be JSON.", 400)
    try:
        body = Body.model_validate(raw)
        cfg = hosted.AdvancedConfig.model_validate(body.advanced) if body.advanced is not None else None
    except ValidationError as e:
        return err("invalid_request", "; ".join(x["msg"] for x in e.errors())[:400], 422)
    if not (ADV_LIMIT if cfg else BRIEF_LIMIT).allow(ip):
        return err("rate_limited", "Too many assessments from this browser; please wait a few minutes.", 429)
    try:
        text = body.transcript_text if (body.transcript_text or "").strip() else (hosted.fetch_transcript(body.transcript_url) if body.transcript_url else "")
        return hosted.assess_text(text, cfg)
    except GuardError as e:
        return err(e.code, e.message, e.status)
    except Exception as e:  # noqa: BLE001 - never a bare 500 for the tester
        return err("internal", f"The analysis failed unexpectedly ({type(e).__name__}). Please try another transcript.", 500)


@app.get("/api/py/health")
def health():
    return {"ok": True, **hosted.capabilities()}
