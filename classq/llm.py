"""OpenRouter scorer. Sends ONLY anonymised transcript text + numeric features. Never media."""
import json
import os
import re

import requests

from .rubric import LABELS, RUBRIC

URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

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


def call(prompt: str, key: str | None = None, timeout=90) -> dict:
    key = key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    r = requests.post(URL, timeout=timeout, headers={"Authorization": f"Bearer {key}"},
                      json={"model": MODEL, "temperature": 0, "response_format": {"type": "json_object"},
                            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]})
    if r.status_code != 200:
        raise RuntimeError(f"OpenRouter HTTP {r.status_code}: {r.json().get('error', {}).get('message', '')[:120]}")
    return parse(r.json()["choices"][0]["message"]["content"])


def parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    d = json.loads(m.group(0) if m else text)
    if d.get("label") not in LABELS:
        raise ValueError(f"bad label {d.get('label')}")
    d.setdefault("strengths", []); d.setdefault("improvements", [])
    return d


def ping(key=None) -> bool:
    key = key or os.environ.get("OPENROUTER_API_KEY")
    try:
        r = requests.post(URL, timeout=30, headers={"Authorization": f"Bearer {key}"},
                          json={"model": MODEL, "max_tokens": 3, "messages": [{"role": "user", "content": "OK"}]})
        return r.status_code == 200
    except Exception:
        return False
