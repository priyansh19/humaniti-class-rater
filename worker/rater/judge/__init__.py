"""Judge entry point: LLM fallback chain (OpenRouter primary -> secondary -> configured others) -> local scorer."""
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
    if provider == "auto":
        chain = providers.chain()
    else:
        try:
            chain = [providers.get(provider)]
        except providers.ProviderError as e:
            local.warnings.append(f"LLM unavailable ({e}); local scorer used.")
            return local
    if not chain:
        return local
    payload = llm.build_payload(a)
    llm.assert_private(payload, forbidden_tokens or set())
    tried = []
    for p in chain:
        for attempt in range(2):
            try:
                d = p.complete_json(llm.SYSTEM, payload if attempt == 0 else payload + "\n\nReturn ONLY valid JSON matching the schema.", llm.SCHEMA)
                rep = llm.to_report(a, d, f"{p.name}:{p.model}")
                if tried:
                    rep.warnings.append(f"Fell back from {', '.join(tried)}.")
                rep.warnings.append(f"Local scorer estimate: {local.label}.")
                return rep
            except providers.ProviderError as e:      # HTTP/auth errors: no point retrying the same model
                log.warning("judge %s:%s failed: %s", p.name, p.model, e)
                break
            except Exception as e:  # noqa: BLE001 - invalid JSON/schema: one repair retry
                log.warning("judge %s:%s attempt %d invalid: %s", p.name, p.model, attempt + 1, type(e).__name__)
        tried.append(f"{p.name}:{p.model}")
    local.warnings.append(f"LLM judge unavailable ({', '.join(tried)} failed); local scorer used.")
    return local
