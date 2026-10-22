"""FastAPI worker (spec: docs/specs/worker-api.md)."""
from __future__ import annotations

import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .. import __version__
from ..analysis import analyse
from ..judge import judge
from ..judge.providers import detect
from ..media import MediaError
from . import ingest
from .ingest import IngestError, Uploads, download, fetch_text
from .store import JobStore

log = logging.getLogger("rater.api")
DATA = os.environ.get("RATER_DATA_DIR", os.path.join(os.getcwd(), "data"))
os.makedirs(os.path.join(DATA, "media"), exist_ok=True)
MAX_ACTIVE_PER_CLIENT = int(os.environ.get("RATER_MAX_ACTIVE_PER_CLIENT", "3"))

store = JobStore(os.path.join(DATA, "jobs.sqlite"))
uploads = Uploads(os.path.join(DATA, "uploads"))
pool = ThreadPoolExecutor(max_workers=int(os.environ.get("RATER_CONCURRENCY", "1")), thread_name_prefix="job")

app = FastAPI(title="8x8 Class Quality Rater - worker", version=__version__)
origins = [o.strip() for o in os.environ.get("RATER_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PUT"], allow_headers=["*"])

# overall progress = stage offset + stage fraction * stage span
STAGES = {"queued": (0, 0), "downloading": (0.0, 0.10), "probing": (0.10, 0.02), "transcribing": (0.12, 0.50),
          "audio": (0.62, 0.05), "frames": (0.67, 0.23), "judging": (0.90, 0.10), "done": (1.0, 0)}


def require_key(x_rater_key: str | None = Header(default=None)):
    expected = os.environ.get("RATER_API_KEY")
    if expected and x_rater_key != expected:
        raise HTTPException(401, "Invalid API key")


def client_id(request: Request) -> str:
    return request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()


def _run_job(jid: str, media_path: str | None, transcript_text: str | None, url: str | None, transcript_url: str | None):
    def prog(stage: str, frac: float):
        off, span = STAGES.get(stage, (0, 0))
        store.update(jid, status="running", stage=stage, progress=round(off + span * min(max(frac, 0), 1), 3))
    try:
        store.update(jid, status="running", stage="downloading" if url else "probing")
        if url:
            media_path = os.path.join(DATA, "media", f"{jid}.mp4")
            download(url, media_path, on_progress=lambda f: prog("downloading", f))
        if transcript_url and not transcript_text:
            transcript_text = fetch_text(transcript_url)
        a = analyse(media_path, transcript_text, on_progress=prog)
        prog("judging", 0.0)
        report = judge(a)
        report_d = report.model_dump()
        report_d["analysis"] = {"duration_s": a.duration_s, "transcript_source": a.transcript_source,
                                "roles_estimated": a.roles_estimated, "features": a.features}
        store.update(jid, status="done", stage="done", progress=1.0, message="", report=report_d)
    except (IngestError, MediaError, ValueError) as e:
        store.update(jid, status="failed", message=str(e))
    except Exception:
        log.exception("job %s failed", jid)
        store.update(jid, status="failed", message="Internal error while processing the recording")
    finally:
        if media_path and os.path.exists(media_path):
            os.remove(media_path)                     # never retain recordings


def _submit(request: Request, **kw) -> dict:
    cid = client_id(request)
    if store.active_for(cid) >= MAX_ACTIVE_PER_CLIENT:
        raise HTTPException(429, "Too many active jobs; wait for one to finish")
    jid = store.create(cid)
    pool.submit(_run_job, jid, **kw)
    return {"job_id": jid}


class UploadInit(BaseModel):
    filename: str
    size: int


class Complete(BaseModel):
    transcript_text: str | None = Field(default=None, max_length=5_000_000)


class LinkJob(BaseModel):
    url: str = Field(max_length=2048)
    transcript_url: str | None = Field(default=None, max_length=2048)
    transcript_text: str | None = Field(default=None, max_length=5_000_000)


class TranscriptOnly(BaseModel):
    transcript_text: str | None = Field(default=None, max_length=5_000_000)
    transcript_url: str | None = Field(default=None, max_length=2048)


@app.get("/health")
def health():
    return {"ok": True, "version": __version__, "judge": detect() or "local",
            "asr_model": os.environ.get("RATER_ASR_MODEL", "base"), "max_upload_bytes": 2 * 1024 ** 3, "chunk_size": ingest.CHUNK}


@app.post("/uploads", dependencies=[Depends(require_key)])
def upload_init(body: UploadInit):
    uid = uuid.uuid4().hex[:16]
    try:
        n = uploads.init(uid, body.size, body.filename)
    except IngestError as e:
        raise HTTPException(400, str(e)) from e
    return {"upload_id": uid, "chunk_size": ingest.CHUNK, "chunks": n}


@app.put("/uploads/{uid}/chunks/{n}", dependencies=[Depends(require_key)])
async def upload_chunk(uid: str, n: int, request: Request):
    data = await request.body()
    try:
        uploads.put(uid, n, data)
    except (IngestError, FileNotFoundError) as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True}


@app.post("/uploads/{uid}/complete", dependencies=[Depends(require_key)])
def upload_complete(uid: str, body: Complete, request: Request):
    dest = os.path.join(DATA, "media", f"{uid}.mp4")
    try:
        uploads.complete(uid, dest)
    except (IngestError, FileNotFoundError) as e:
        raise HTTPException(400, str(e)) from e
    return _submit(request, media_path=dest, transcript_text=body.transcript_text, url=None, transcript_url=None)


@app.post("/jobs", dependencies=[Depends(require_key)])
def create_link_job(body: LinkJob, request: Request):
    return _submit(request, media_path=None, transcript_text=body.transcript_text, url=body.url, transcript_url=body.transcript_url)


@app.get("/jobs/{jid}")
def get_job(jid: str):
    j = store.get(jid)
    if not j:
        raise HTTPException(404, "Job not found")
    if j["status"] == "queued":
        j["queue_position"] = store.queue_position(jid)
    return j


@app.post("/assess/transcript", dependencies=[Depends(require_key)])
def assess_transcript(body: TranscriptOnly):
    try:
        text = body.transcript_text or (fetch_text(body.transcript_url) if body.transcript_url else "")
        a = analyse(transcript_text=text)
    except (IngestError, ValueError) as e:
        raise HTTPException(400, str(e)) from e
    r = judge(a).model_dump()
    r["analysis"] = {"duration_s": a.duration_s, "transcript_source": a.transcript_source, "roles_estimated": a.roles_estimated,
                     "features": a.features}
    return r
