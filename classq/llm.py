"""Provider-pluggable LLM judge (Gemini / OpenAI / Anthropic). Sends ONLY anonymised transcript text + numeric features. Never media."""
import json
import os
import re

import requests

from .rubric import LABELS, RUBRIC

# Approved providers only (client list): Gemini, OpenAI, Anthropic. Auto-detected from env keys.
PROVIDERS = {
    "gemini": (("GEMINI_API_KEY", "GOOGLE_API_KEY"), "gemini-2.5-flash"),
    "openai": (("OPENAI_API_KEY",), "gpt-4o-mini"),
    "anthropic": (("ANTHROPIC_API_KEY",), "claude-3-5-haiku-latest"),
}


def detect():
    """Return (provider, key, model) or None. LLM_PROVIDER / LLM_MODEL env vars override."""
    order = [os.environ["LLM_PROVIDER"]] if os.environ.get("LLM_PROVIDER") in PROVIDERS else list(PROVIDERS)
    for p in order:
        envs, model = PROVIDERS[p]
        key = next((os.environ[e] for e in envs if os.environ.get(e)), None)
        if key:
            return p, key, os.environ.get("LLM_MODEL", model)
    return None


def enabled() -> bool:
    return detect() is not None


SYSTEM = ("You are an expert reviewer of 8x8's live online classes for children. Judge the class against the rubric. "
          "Use ONLY the evidence given. Every observation must cite a timestamp or a numeric feature. "
          "Never use names; refer to 'the tutor' or 'a student'. Reply with JSON only.")


def build_prompt(feats: dict, local: dict | None = None) -> str:
    payload = {k: feats.get(k) for k in ("text", "frames", "audio")}
    return f"""{RUBRIC}

FEATURES (computed locally; frames/audio are summaries, no media is shared):
{json.dumps(payload, indent=1)}

LOCAL RUBRIC SCORER (heuristic, 0-1 per theme): {json.dumps(local or {})}

TAGGED TRANSCRIPT LINES (anonymised):
{chr(10).join(feats.get('evidence', [])[:40])}

TRANSCRIPT EXCERPT: opening and closing minutes (anonymised):
{feats.get('excerpt', '')[:6000]}

Return JSON: {{"label": one of {LABELS}, "confidence": 0-1,
 "theme_scores": {{"intro_rapport":1-5,"individual_engagement":1-5,"energy_pleasantness":1-5,"homework_conclusion":1-5,"visual_professionalism":1-5,"av_quality":1-5}},
 "strengths": [3-5 specific observations with [mm:ss] or feature evidence],
 "improvements": [3-5 specific, actionable observations with evidence],
 "summary": "2 sentences"}}"""


def _request(provider, key, model, system, user, max_tokens=1500, timeout=90):
    if provider == "openai":
        r = requests.post("https://api.openai.com/v1/chat/completions", timeout=timeout,
                          headers={"Authorization": f"Bearer {key}"},
                          json={"model": model, "temperature": 0, "max_tokens": max_tokens,
                                "response_format": {"type": "json_object"},
                                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        get = lambda d: d["choices"][0]["message"]["content"]
    elif provider == "anthropic":
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=timeout,
                          headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                          json={"model": model, "max_tokens": max_tokens, "temperature": 0, "system": system,
                                "messages": [{"role": "user", "content": user}]})
        get = lambda d: "".join(c.get("text", "") for c in d["content"])
    elif provider == "gemini":
        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                          timeout=timeout, headers={"x-goog-api-key": key},
                          json={"systemInstruction": {"parts": [{"text": system}]},
                                "contents": [{"role": "user", "parts": [{"text": user}]}],
                                "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens,
                                                     "responseMimeType": "application/json"}})
        get = lambda d: d["candidates"][0]["content"]["parts"][0]["text"]
    else:
        raise ValueError(provider)
    if r.status_code != 200:
        raise RuntimeError(f"{provider} HTTP {r.status_code}")
    return get(r.json())


def call(prompt: str, provider=None, key=None, model=None) -> dict:
    det = detect()
    if provider is None:
        if not det:
            raise RuntimeError("No approved LLM key set (GEMINI_API_KEY/GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY)")
        provider, key, model = det
    model = model or PROVIDERS[provider][1]
    out = parse(_request(provider, key, model, SYSTEM, prompt))
    out["provider"] = f"{provider}:{model}"
    return out


def parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    d = json.loads(m.group(0) if m else text)
    if d.get("label") not in LABELS:
        raise ValueError(f"bad label {d.get('label')}")
    d.setdefault("strengths", []); d.setdefault("improvements", [])
    return d


def ping() -> bool:
    det = detect()
    if not det:
        return False
    try:
        _request(*det, "Reply with JSON.", 'Return {"ok": true}', max_tokens=20, timeout=30)
        return True
    except Exception:
        return False
