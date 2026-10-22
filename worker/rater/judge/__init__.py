"""Judge entry point: LLM (if an approved key is configured) with validation + local fallback."""
from __future__ import annotations

import logging

from ..models import Analysis, Report
from . import llm, providers
from .local import build_report

log = logging.getLogger(__name__)


def judge(a: Analysis, provider: str | None = "auto", forbidden_tokens: set[str] | None = None) -> Report:
    local = build_report(a)
    if provider in (None, "local"):
        return local
    try:
        p = providers.get(None if provider == "auto" else provider)
    except providers.ProviderError as e:
        local.warnings.append(f"LLM unavailable ({e}); local scorer used.")
        return local
    if p is None:
        return local
    payload = llm.build_payload(a)
    llm.assert_private(payload, forbidden_tokens or set())
    last = None
    for attempt in range(2):
        try:
            d = p.complete_json(llm.SYSTEM, payload if attempt == 0 else payload + "\n\nReturn ONLY valid JSON matching the schema.", llm.SCHEMA)
            rep = llm.to_report(a, d, f"{p.name}:{p.model}")
            rep.warnings.append(f"Local scorer estimate: {local.label}.")
            return rep
        except Exception as e:  # noqa: BLE001 - any provider/validation failure falls back
            last = e
            log.warning("LLM judge attempt %d failed: %s", attempt + 1, type(e).__name__)
    local.warnings.append(f"LLM judge failed ({type(last).__name__}); local scorer used.")
    return local
