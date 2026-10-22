"""Approved LLM providers only (SPEC A4): Gemini, OpenAI, Anthropic. Plain REST via httpx.

Each provider implements complete_json(system, user, schema) -> dict and must never be given media."""
from __future__ import annotations

import copy
import json
import os
import re

import httpx

DEFAULTS = {"gemini": "gemini-2.5-flash", "openai": "gpt-4o-mini", "anthropic": "claude-sonnet-4-5", "local": "local",
            "openrouter": "qwen/qwen-2.5-72b-instruct"}
OPENROUTER_FALLBACK_DEFAULT = "meta-llama/llama-3.3-70b-instruct"
# "local" = a fully local OpenAI-compatible server (e.g. llama.cpp `llama-server`); its "key" is the base URL.
ENV_KEYS = {"openrouter": ("OPENROUTER_API_KEY",), "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "openai": ("OPENAI_API_KEY",),
            "anthropic": ("ANTHROPIC_API_KEY",), "local": ("RATER_LOCAL_LLM_URL",)}
# Auto-detection order. OpenRouter first by owner decision (SPEC Q2: not on the client's approved list - flagged).
ORDER = ("openrouter", "gemini", "openai", "anthropic", "local")


class ProviderError(RuntimeError):
    pass


def _key(name: str) -> str | None:
    return next((os.environ[e] for e in ENV_KEYS[name] if os.environ.get(e)), None)


def detect() -> str | None:
    forced = os.environ.get("RATER_LLM_PROVIDER")
    if forced in ENV_KEYS:
        return forced if _key(forced) else None
    return next((p for p in ORDER if _key(p)), None)


def _gemini_schema(s):
    s = copy.deepcopy(s)
    if isinstance(s, dict):
        s.pop("additionalProperties", None)
        if "type" in s:
            s["type"] = s["type"].upper()
        for k in ("properties",):
            if k in s:
                s[k] = {kk: _gemini_schema(v) for kk, v in s[k].items()}
        if "items" in s:
            s["items"] = _gemini_schema(s["items"])
    return s


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ProviderError("No JSON object in model output")
    return json.loads(m.group(0))


class Provider:
    name = ""

    def __init__(self, model: str | None = None, timeout: float = 120):
        self.key = _key(self.name)
        if not self.key:
            raise ProviderError(f"No API key for {self.name}")
        self.model = model or os.environ.get("RATER_LLM_MODEL") or DEFAULTS[self.name]
        self.timeout = timeout

    def _post(self, url, headers, body) -> dict:
        r = httpx.post(url, headers=headers, json=body, timeout=self.timeout)
        if r.status_code != 200:
            raise ProviderError(f"{self.name} HTTP {r.status_code}")
        return r.json()


class Gemini(Provider):
    name = "gemini"

    def complete_json(self, system, user, schema):
        d = self._post(f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                       {"x-goog-api-key": self.key},
                       {"systemInstruction": {"parts": [{"text": system}]},
                        "contents": [{"role": "user", "parts": [{"text": user}]}],
                        "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                             "responseSchema": _gemini_schema(schema)}})
        return _parse_json(d["candidates"][0]["content"]["parts"][0]["text"])


def _strip_bounds(s):
    if isinstance(s, dict):
        return {k: _strip_bounds(v) for k, v in s.items() if k not in ("minimum", "maximum")}
    return s


class OpenAI(Provider):
    name = "openai"

    def complete_json(self, system, user, schema):
        schema = _strip_bounds(schema)
        d = self._post("https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {self.key}"},
                       {"model": self.model, "temperature": 0,
                        "response_format": {"type": "json_schema", "json_schema": {"name": "assessment", "strict": True, "schema": schema}},
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        return _parse_json(d["choices"][0]["message"]["content"])


class Anthropic(Provider):
    name = "anthropic"

    def complete_json(self, system, user, schema):
        d = self._post("https://api.anthropic.com/v1/messages", {"x-api-key": self.key, "anthropic-version": "2023-06-01"},
                       {"model": self.model, "max_tokens": 4000, "temperature": 0, "system": system,
                        "tools": [{"name": "submit_assessment", "description": "Submit the class assessment", "input_schema": schema}],
                        "tool_choice": {"type": "tool", "name": "submit_assessment"},
                        "messages": [{"role": "user", "content": user}]})
        block = next((b for b in d.get("content", []) if b.get("type") == "tool_use"), None)
        if not block:
            raise ProviderError("anthropic returned no tool_use block")
        return block["input"]


class OpenRouter(Provider):
    """Single gateway to many models. Model ids via RATER_OPENROUTER_MODEL / RATER_OPENROUTER_FALLBACK_MODEL."""
    name = "openrouter"

    def __init__(self, model=None, timeout: float = 180):
        super().__init__(model or os.environ.get("RATER_OPENROUTER_MODEL"), timeout)

    def complete_json(self, system, user, schema):
        d = self._post("https://openrouter.ai/api/v1/chat/completions",
                       {"Authorization": f"Bearer {self.key}", "X-Title": "8x8 class rater"},
                       {"model": self.model, "temperature": 0, "max_tokens": 4000,
                        "response_format": {"type": "json_schema", "json_schema": {"name": "assessment", "strict": True,
                                                                                   "schema": _strip_bounds(schema)}},
                        "provider": {"require_parameters": True, "data_collection": "deny"},
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        if "choices" not in d:
            raise ProviderError("openrouter returned no choices")
        return _parse_json(d["choices"][0]["message"]["content"])


def chain() -> list[Provider]:
    """Ordered judges to try: OpenRouter primary -> OpenRouter secondary -> (direct/local providers if configured)."""
    out: list[Provider] = []
    forced = os.environ.get("RATER_LLM_PROVIDER")
    if forced == "local-only":
        return out
    names = [forced] if forced in ENV_KEYS else [p for p in ORDER if _key(p)]
    for n in names:
        try:
            if n == "openrouter":
                out.append(OpenRouter())
                fb = os.environ.get("RATER_OPENROUTER_FALLBACK_MODEL", OPENROUTER_FALLBACK_DEFAULT)
                if fb and fb != out[-1].model:
                    out.append(OpenRouter(fb))
            else:
                out.append(REGISTRY[n]())
        except ProviderError:
            continue
    return out


class Local(Provider):
    """Fully local LLM behind an OpenAI-compatible API (llama.cpp server). Nothing leaves the host."""
    name = "local"

    def __init__(self, model=None, timeout: float = 1800):
        super().__init__(model, timeout)
        self.base = self.key.rstrip("/")

    def complete_json(self, system, user, schema):
        d = self._post(f"{self.base}/chat/completions", {},
                       {"model": self.model, "temperature": 0, "max_tokens": 2500,
                        "response_format": {"type": "json_schema", "json_schema": {"name": "assessment", "schema": _strip_bounds(schema)}},
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        return _parse_json(d["choices"][0]["message"]["content"])


REGISTRY = {"openrouter": OpenRouter, "gemini": Gemini, "openai": OpenAI, "anthropic": Anthropic, "local": Local}


def get(name: str | None = None) -> Provider | None:
    name = name or detect()
    return REGISTRY[name]() if name else None
