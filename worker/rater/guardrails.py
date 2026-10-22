"""Input guardrails for transcript assessment (spec: docs/specs/guardrails.md).

Each check either raises GuardError (hard reject with a user-facing code + message) or returns warnings
and a confidence cap that the caller applies to the report. Pure functions: no network, no media.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

MAX_CHARS = 3_000_000           # ~ a 3-hour VTT is ~400 KB; 3 M chars is a generous hard cap
MIN_UTTERANCES = 3              # fewer than this cannot support any rubric judgement
SHORT_CLASS_MIN = 10.0          # dataset classes are 38-89 min; under 10 min -> low confidence
SPEAKER_RE = re.compile(r"^\s*(?:\d{1,2}:\d{2}(?::\d{2})?\s+)?[^:\n]{1,40}:\s+\S", re.MULTILINE)
_COMMON_EN = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "is", "it", "you", "we", "i", "he", "she", "they", "this", "that", "what", "how", "why", "can", "do", "did", "does", "are", "was", "were", "be", "have", "has", "had", "not", "no", "yes", "ok", "okay", "good", "great", "very", "now", "so", "let", "lets", "let's", "your", "my", "our", "me", "us", "move", "knight", "bishop", "rook", "queen", "king", "pawn", "check", "mate", "checkmate", "board", "piece", "pieces", "game", "play", "class", "today", "homework"}


class GuardError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass
class GuardResult:
    text: str
    warnings: list[str] = field(default_factory=list)
    confidence_cap: float = 1.0
    flags: list[str] = field(default_factory=list)

    def cap(self, c: float, flag: str, warning: str) -> None:
        self.confidence_cap = min(self.confidence_cap, c)
        self.flags.append(flag)
        self.warnings.append(warning)


def _words(text: str) -> list[str]:
    body = re.sub(r"^\s*(WEBVTT.*|\d+|[\d:.,]+\s*-->\s*[\d:.,]+.*)$", " ", text, flags=re.MULTILINE)
    return re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)?", body.lower())


def english_share(words: list[str]) -> float:
    if not words:
        return 0.0
    try:
        from wordfreq import zipf_frequency
        hit = sum(1 for w in words if w in _COMMON_EN or zipf_frequency(w, "en") >= 2.5)
    except Exception:  # noqa: BLE001 - wordfreq missing: fall back to the small built-in list
        hit = sum(1 for w in words if w in _COMMON_EN)
    return hit / len(words)


def latin_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if "LATIN" in unicodedata.name(c, "")) / len(letters)


def check_text(text: str | None, max_chars: int = MAX_CHARS) -> GuardResult:
    if text is None or not text.strip():
        raise GuardError("empty", "The transcript is empty. Paste a Zoom VTT or 'Speaker: text' lines, or upload a .vtt/.txt file.", 400)
    if len(text) > max_chars:
        raise GuardError("too_large", f"The transcript is {len(text):,} characters; the limit is {max_chars:,}.", 413)
    if "\x00" in text or sum(1 for c in text[:20000] if unicodedata.category(c) == "Cc" and c not in "\n\r\t") > 50:
        raise GuardError("binary", "This looks like a binary file, not a text transcript. Upload the .vtt or .txt transcript instead.", 415)
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\ufeff", ""))
    r = GuardResult(text=text)
    words = _words(text)
    if len(words) < 15:
        raise GuardError("too_short", "There is too little speech in this transcript to assess a class (fewer than 15 words).", 422)
    lat, en = latin_share(text), english_share(words)
    if lat < 0.5:
        r.cap(0.3, "non_english", "The transcript is mostly in a non-Latin script. The rubric cues are English-only, so most criteria "
                                  "cannot be measured; treat this rating as very low confidence.")
    elif en < 0.35:
        if len(set(words)) / len(words) > 0.8 or en < 0.15:
            raise GuardError("garbled", "The transcript does not look like readable speech (very few recognisable words). "
                                        "Check that the right file was uploaded and that it is not encrypted or corrupted.", 422)
        r.cap(0.35, "non_english", "Most words are not English. The rubric cues are English-only, so the rating is low confidence.")
    if not text.lstrip().upper().startswith("WEBVTT") and len(SPEAKER_RE.findall(text)) < 3:
        r.cap(0.6, "no_speakers", "No speaker labels were found, so tutor and student turns are estimated from the text; "
                                  "interaction metrics are approximate.")
    return r


def check_analysis(r: GuardResult, n_utterances: int, duration_s: float) -> None:
    if n_utterances < MIN_UTTERANCES:
        raise GuardError("too_short", f"Only {n_utterances} utterance(s) were found; at least {MIN_UTTERANCES} are needed.", 422)
    if duration_s / 60 < SHORT_CLASS_MIN:
        r.cap(0.4, "short_class", f"This class is only {duration_s / 60:.1f} min long (dataset classes are 38-89 min). "
                                  "Per-minute rates are noisy and end-of-class checks may not apply.")
