"""Transcript parsing (VTT / TXT / ASR segments), speaker roles and anonymisation."""
from __future__ import annotations

import re
from collections import Counter

from .models import Utterance

_TS = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->\s*(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})")
_SPK = re.compile(r"^([^:]{1,60}?):\s+(.*)$")
_DEVICE_WORDS = {"iphone", "ipad", "android", "galaxy", "laptop", "phone", "samsung", "redmi", "vivo", "oppo",
                 "the", "and", "zoom", "user", "guest", "sir", "mam", "maam"}


def _sec(h, m, s, ms) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse_vtt(text: str) -> list[tuple[float, float, str, str]]:
    """Return raw (start, end, speaker_name, text) tuples. Speaker is '' when absent."""
    out, cur = [], None
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        m = _TS.search(line)
        if m:
            g = m.groups()
            cur = [_sec(*g[:4]), _sec(*g[4:]), []]
            out.append(cur)
        elif not line:
            cur = None
        elif cur is not None and not (line.isdigit() and not cur[2]):
            cur[2].append(line)
    res = []
    for s, e, lines in out:
        body = " ".join(lines).strip()
        if not body:
            continue
        m = _SPK.match(body)
        res.append((s, e, m.group(1).strip(), m.group(2).strip()) if m else (s, e, "", body))
    return res


def parse_txt(text: str, seconds_per_line: float = 5.0) -> list[tuple[float, float, str, str]]:
    res = []
    for i, line in enumerate(x.strip() for x in text.splitlines() if x.strip()):
        m = _SPK.match(line)
        spk, body = (m.group(1).strip(), m.group(2).strip()) if m else ("", line)
        res.append((i * seconds_per_line, (i + 1) * seconds_per_line, spk, body))
    return res


def parse(text: str) -> tuple[list[tuple[float, float, str, str]], str]:
    if "-->" in text:
        return parse_vtt(text), "vtt"
    return parse_txt(text), "txt"


def name_tokens(name: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z\u00C0-\u024F]{3,}", name) if t.lower() not in _DEVICE_WORDS}


def assign_roles(raw: list[tuple[float, float, str, str]]) -> tuple[list[Utterance], bool, dict[str, str]]:
    """Label speakers. With names: tutor = most words. Without: heuristic roles (estimated=True).

    Returns (utterances, roles_estimated, mapping original_name -> anonymised label)."""
    labelled = sum(1 for r in raw if r[2]) >= 0.6 * max(len(raw), 1)
    if labelled:
        words = Counter()
        for _, _, spk, txt in raw:
            words[spk] += len(txt.split())
        tutor = words.most_common(1)[0][0] if words else ""
        mapping, k = {}, 0
        for _, _, spk, _ in raw:
            if spk and spk not in mapping:
                if spk == tutor:
                    mapping[spk] = "Tutor"
                else:
                    k += 1
                    mapping[spk] = f"Student {k}"
        utts = [Utterance(start=s, end=e, speaker=mapping.get(spk, "Unknown"),
                          role="tutor" if spk == tutor else ("student" if spk else "unknown"), text=t)
                for s, e, spk, t in raw]
        return utts, False, mapping
    # ASR / unlabelled: long turns -> tutor, short replies right after a tutor question -> student
    utts, prev_q = [], False
    for s, e, _, t in raw:
        n = len(t.split())
        role = "student" if (n <= 6 and prev_q) else "tutor"
        utts.append(Utterance(start=s, end=e, speaker="Tutor" if role == "tutor" else "Student (est.)", role=role, text=t))
        prev_q = role == "tutor" and t.rstrip().endswith("?")
    return utts, True, {}


def scrub(utts: list[Utterance], mapping: dict[str, str]) -> list[Utterance]:
    """Replace any speaker-name token appearing inside utterance text with its anonymised label."""
    tok2label: dict[str, str] = {}
    for name, label in mapping.items():
        for tok in name_tokens(name):
            tok2label.setdefault(tok, label)
    if not tok2label:
        return utts
    pat = re.compile(r"\b(" + "|".join(sorted(map(re.escape, tok2label), key=len, reverse=True)) + r")\b", re.IGNORECASE)
    return [u.model_copy(update={"text": pat.sub(lambda m: tok2label[m.group(1).lower()], u.text)}) for u in utts]


def from_text(text: str) -> tuple[list[Utterance], str, bool, set[str]]:
    """Parse + roles + anonymise. Returns (utterances, source, roles_estimated, student_name_tokens)."""
    raw, src = parse(text)
    utts, est, mapping = assign_roles(raw)
    student_tokens = set()
    for name, label in mapping.items():
        if label != "Tutor":
            student_tokens |= name_tokens(name)
    return scrub(utts, mapping), src, est, student_tokens


def from_segments(segments: list[tuple[float, float, str]]) -> list[Utterance]:
    utts, _, _ = assign_roles([(s, e, "", t) for s, e, t in segments])
    return utts


def fmt_ts(t: float) -> str:
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"
