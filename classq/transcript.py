"""Parse VTT / plain transcripts and compute pedagogy features."""
import re
from collections import Counter
from dataclasses import dataclass

TS = re.compile(r"(\d+):(\d\d):(\d\d)[.,](\d+)\s*-->\s*(\d+):(\d\d):(\d\d)[.,](\d+)")


@dataclass
class Cue:
    start: float
    end: float
    speaker: str
    text: str


def _sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + float("0." + ms)


def parse_vtt(text: str) -> list[Cue]:
    cues, cur = [], None
    for line in text.splitlines():
        line = line.strip()
        m = TS.search(line)
        if m:
            g = m.groups()
            cur = [_sec(*g[:4]), _sec(*g[4:]), []]
            cues.append(cur)
        elif line and cur is not None and not line.isdigit():
            cur[2].append(line)
        elif not line:
            cur = None if cur is None or cur[2] else cur
    out = []
    for s, e, lines in cues:
        t = " ".join(lines)
        spk, body = "", t
        mm = re.match(r"^([^:]{1,60}):\s*(.*)$", t)
        if mm:
            spk, body = mm.group(1).strip(), mm.group(2)
        out.append(Cue(s, e, spk, body))
    return out


def parse_any(text: str) -> list[Cue]:
    if "-->" in text:
        return parse_vtt(text)
    # plain text: one utterance per line, fake 4 s per line
    out = []
    for i, line in enumerate(l for l in text.splitlines() if l.strip()):
        mm = re.match(r"^([^:]{1,60}):\s*(.*)$", line)
        spk, body = (mm.group(1), mm.group(2)) if mm else ("", line)
        out.append(Cue(i * 4.0, i * 4.0 + 4, spk, body))
    return out


INTRO = re.compile(r"\b(good (morning|evening|afternoon)|hello|hi\b|how are you|introduce|your name|welcome|my name)", re.I)
HW = re.compile(r"\b(home ?work|assignment|worksheet|practice at home|homework)\b", re.I)
WRAP = re.compile(r"\b(bye|see you|next class|that's all|thank you|summary|today we (learn|did))", re.I)
PRAISE = re.compile(r"\b(good job|very good|excellent|great|awesome|well done|super|nice|perfect|wonderful|amazing|correct)\b", re.I)
AV = re.compile(r"(can'?t hear|cannot hear|not audible|not clear|not visible|can'?t see|cannot see|voice is breaking|lagging|disconnect|network issue|no sound|voice is not|am i visible|is it audible)", re.I)
NEWJOIN = re.compile(r"\b(new (student|joiner|friend)|introduce yourself|tell (me|us) your name|self.?introduction)", re.I)
VIDEO = re.compile(r"\b(video|screen|share|puzzle|game|quiz|activity)\b", re.I)


def anonymise(cues: list[Cue], teacher: str | None = None) -> tuple[list[Cue], dict]:
    teacher = teacher or guess_teacher(cues)
    names, mapping = [], {}
    for c in cues:
        if c.speaker and c.speaker not in names:
            names.append(c.speaker)
    k = 1
    for n in names:
        if n == teacher:
            mapping[n] = "Tutor"
        else:
            mapping[n] = f"Student{k}"
            k += 1
    # first-name tokens of everyone, to scrub from text
    tokens = {}
    for n, a in mapping.items():
        for tok in re.findall(r"[A-Za-z]{3,}", n):
            if tok.lower() not in {"iphone", "ipad", "android", "galaxy", "laptop", "the", "and"}:
                tokens[tok.lower()] = a
    pat = re.compile(r"\b(" + "|".join(map(re.escape, tokens)) + r")\b", re.I) if tokens else None
    out = []
    for c in cues:
        t = pat.sub(lambda m: tokens[m.group(1).lower()], c.text) if pat else c.text
        out.append(Cue(c.start, c.end, mapping.get(c.speaker, c.speaker), t))
    return out, mapping


def guess_teacher(cues: list[Cue]) -> str:
    cnt = Counter()
    for c in cues:
        cnt[c.speaker] += len(c.text.split())
    return cnt.most_common(1)[0][0] if cnt else ""


def features(cues: list[Cue]) -> dict:
    if not cues:
        return {"n_cues": 0}
    teacher = guess_teacher(cues)
    dur = max(c.end for c in cues) / 60 or 1
    tw = sum(len(c.text.split()) for c in cues if c.speaker == teacher)
    sw = sum(len(c.text.split()) for c in cues if c.speaker != teacher)
    students = {c.speaker for c in cues if c.speaker and c.speaker != teacher}
    st_turns = Counter(c.speaker for c in cues if c.speaker and c.speaker != teacher)
    tcues = [c for c in cues if c.speaker == teacher]
    t_q = sum(c.text.count("?") for c in tcues)
    # teacher addressing students by (first) name
    firsts = set()
    for s in students:
        for tok in re.findall(r"[A-Za-z]{3,}", s):
            if tok.lower() not in {"iphone", "ipad", "android", "laptop", "galaxy"}:
                firsts.add(tok.lower())
    addressed = set()
    for c in tcues:
        for w in re.findall(r"[A-Za-z]{3,}", c.text.lower()):
            if w in firsts:
                addressed.add(w)
    first5 = [c for c in cues if c.start < 300]
    last5 = [c for c in cues if c.start > max(c.end for c in cues) - 300]
    gaps = [b.start - a.end for a, b in zip(cues, cues[1:])]
    long_sil = sum(1 for g in gaps if g > 30)
    first_content = next((c.start for c in tcues if len(c.text.split()) > 12), 0)
    f = {
        "duration_min": round(dur, 1),
        "n_cues": len(cues),
        "n_students_speaking": len(students),
        "teacher_talk_ratio": round(tw / max(tw + sw, 1), 3),
        "student_turns_per_min": round(sum(st_turns.values()) / dur, 2),
        "student_turn_balance": round(min(st_turns.values()) / max(st_turns.values()), 3) if len(st_turns) > 1 else 0.0,
        "teacher_questions_per_min": round(t_q / dur, 2),
        "students_addressed_by_name": len(addressed),
        "intro_hits_first5": sum(bool(INTRO.search(c.text)) for c in first5),
        "newjoiner_intro_hits": sum(bool(NEWJOIN.search(c.text)) for c in cues),
        "homework_mentions": sum(bool(HW.search(c.text)) for c in cues),
        "homework_in_last10": sum(bool(HW.search(c.text)) for c in cues if c.start > max(x.end for x in cues) - 600),
        "wrapup_hits_last5": sum(bool(WRAP.search(c.text)) for c in last5),
        "praise_per_min": round(sum(len(PRAISE.findall(c.text)) for c in tcues) / dur, 2),
        "av_complaints": sum(bool(AV.search(c.text)) for c in cues),
        "activity_mentions": sum(bool(VIDEO.search(c.text)) for c in tcues),
        "long_silences_30s": long_sil,
        "first_long_teacher_utt_s": round(first_content, 1),
    }
    return f


def evidence(cues: list[Cue], max_items: int = 40) -> list[str]:
    """Timestamped, anonymised lines that match rubric patterns (for the LLM / UI)."""
    anon, _ = anonymise(cues)
    out = []
    for c in anon:
        tags = [n for n, p in [("INTRO", INTRO), ("HW", HW), ("WRAP", WRAP), ("PRAISE", PRAISE),
                               ("AV", AV), ("NEWJOIN", NEWJOIN)] if p.search(c.text)]
        if tags:
            out.append(f"[{fmt(c.start)}] ({','.join(tags)}) {c.speaker}: {c.text[:160]}")
    if len(out) > max_items:
        step = len(out) / max_items
        out = [out[int(i * step)] for i in range(max_items)]
    return out


def excerpt(cues: list[Cue], minutes=(0, 6), tail_minutes=5, max_chars=6000) -> str:
    anon, _ = anonymise(cues)
    end = max(c.end for c in anon) if anon else 0
    head = [c for c in anon if minutes[0] * 60 <= c.start < minutes[1] * 60]
    tail = [c for c in anon if c.start > end - tail_minutes * 60]
    txt = "\n".join(f"[{fmt(c.start)}] {c.speaker}: {c.text}" for c in head)
    txt += "\n...\n" + "\n".join(f"[{fmt(c.start)}] {c.speaker}: {c.text}" for c in tail)
    return txt[:max_chars]


def fmt(s: float) -> str:
    s = int(s)
    return f"{s // 3600:d}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"
