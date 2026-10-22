"""Hosted transcript-only assessment service (spec: docs/specs/hosted-api.md).

Used by the Vercel Python function. Brief mode = shipped scorer, no options. Advanced mode accepts a bounded
config (provider, label cut-points, criterion weights, embeddings flag) and returns the brief result plus a
custom-config result, so tuning never changes the default answer.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from pydantic import BaseModel, Field, field_validator

from .analysis import analyse
from .guardrails import MAX_CHARS, GuardError, GuardResult, check_analysis, check_text
from .judge import judge, providers
from .judge.rubric import CRITERIA, criterion_scores
from .models import LABELS

ADV_MAX_CHARS = 1_000_000


class AdvancedConfig(BaseModel):
    provider: str = Field(default="local", pattern=r"^(local|auto|openrouter|openai|gemini|anthropic)$")
    thresholds: list[float] = Field(default_factory=lambda: [2.4, 3.1, 3.8], min_length=3, max_length=3)
    weights: dict[str, float] = Field(default_factory=dict)
    embeddings: bool = False
    max_chars: int = Field(default=ADV_MAX_CHARS, ge=1000, le=ADV_MAX_CHARS)

    @field_validator("thresholds")
    @classmethod
    def _ordered(cls, v):
        if any(not 1 <= x <= 5 for x in v) or not v[0] < v[1] < v[2]:
            raise ValueError("thresholds must be increasing values between 1 and 5")
        return v

    @field_validator("weights")
    @classmethod
    def _w(cls, v):
        bad = [k for k in v if k not in CRITERIA]
        if bad:
            raise ValueError(f"unknown criteria: {bad}")
        if any(not 0 <= x <= 5 for x in v.values()):
            raise ValueError("weights must be between 0 and 5")
        return v


def capabilities() -> dict:
    llm = providers.detect()
    return {
        "mode": "transcript-only",
        "judge": llm or "local",
        "video": False,
        "embeddings": False,
        "missing": {
            "llm_judge": None if llm else "OPENROUTER_API_KEY (valid), or a direct OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY",
            "video_processing": "MODAL_TOKEN_ID + MODAL_TOKEN_SECRET (and organiser approval of Modal as host), then NEXT_PUBLIC_WORKER_URL",
            "embeddings": "Needs the video worker (EmbeddingGemma 2 runs locally on CPU; too large for a Vercel function)",
        },
    }


class RateLimiter:
    """Per-client sliding window. Best-effort: Vercel instances are not shared, so this caps bursts, not totals."""

    def __init__(self, limit: int, window_s: float):
        self.limit, self.window = limit, window_s
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


def custom_label(features: dict, cfg: AdvancedConfig) -> dict:
    crit = {k: v for k, v in criterion_scores(features).items() if v is not None}
    w = {k: cfg.weights.get(k, 1.0) for k in crit}
    tot = sum(w.values())
    score = sum(crit[k] * w[k] for k in crit) / tot if tot else 3.0
    idx = sum(score >= t for t in cfg.thresholds)
    return {"label": LABELS[idx], "score": round(score, 3), "weights": w, "thresholds": cfg.thresholds}


def _apply_guard(rep: dict, g: GuardResult) -> dict:
    if g.confidence_cap < rep["confidence"]:
        rep["confidence"] = round(g.confidence_cap, 2)
    rep["warnings"] = list(dict.fromkeys(g.warnings + rep.get("warnings", [])))
    rep["guard_flags"] = g.flags
    return rep


def assess_text(text: str | None, advanced: AdvancedConfig | None = None) -> dict:
    g = check_text(text, max_chars=advanced.max_chars if advanced else MAX_CHARS)
    try:
        a, utts = analyse(transcript_text=g.text, use_embeddings=False, return_utterances=True)
    except ValueError as e:
        raise GuardError("unparseable", f"The transcript could not be parsed: {e}", 422) from e
    check_analysis(g, n_utterances=len(utts), duration_s=a.duration_s)
    provider = "local" if advanced is None and not os.environ.get("RATER_HOSTED_LLM") else (advanced.provider if advanced else "auto")
    rep = judge(a, provider=provider).model_dump()
    rep = _apply_guard(rep, g)
    rep["analysis"] = {"duration_s": a.duration_s, "transcript_source": a.transcript_source,
                       "roles_estimated": a.roles_estimated, "features": a.features}
    rep["mode"] = "advanced" if advanced else "brief"
    if advanced:
        rep["custom"] = custom_label(a.features, advanced)
        if advanced.embeddings:
            rep["warnings"].append("Embeddings were requested but are not available on the hosted transcript-only service; skipped.")
    return rep


def fetch_transcript(url: str, max_bytes: int = 5_000_000) -> str:
    """Fetch a public .vtt/.txt link with SSRF checks; map every failure to a GuardError the UI can show."""
    import httpx
    try:
        from .api.ingest import IngestError, check_public_url, normalise_link
    except ImportError:  # vendored copy on Vercel (scripts/sync-rater.sh)
        from .api_ingest_lite import IngestError, check_public_url, normalise_link
    url = (url or "").strip()
    if len(url) > 2048:
        raise GuardError("bad_link", "That link is too long.", 400)
    try:
        check_public_url(url)
        r = httpx.get(normalise_link(url), timeout=20, follow_redirects=False)
    except IngestError as e:
        raise GuardError("bad_link", str(e), 400) from e
    except httpx.HTTPError as e:
        raise GuardError("bad_link", f"The link could not be fetched ({type(e).__name__}).", 400) from e
    if r.is_redirect:
        raise GuardError("bad_link", "The link redirects elsewhere; paste the direct link to the .vtt/.txt file.", 400)
    if r.status_code != 200:
        raise GuardError("bad_link", f"The link returned HTTP {r.status_code}. Is it shared publicly?", 400)
    ctype = r.headers.get("content-type", "")
    if "text/html" in ctype:
        raise GuardError("bad_link", "The link points to a web page, not a transcript file (share it as 'anyone with the link').", 400)
    if ctype.startswith(("video/", "audio/")):
        raise GuardError("video_needs_worker", "That link is a video. Video processing needs the analysis worker, which is offline on "
                                               "this hosted demo; paste the Zoom transcript instead.", 400)
    if len(r.content) > max_bytes:
        raise GuardError("too_large", "The linked file is larger than 5 MB.", 413)
    return r.text
