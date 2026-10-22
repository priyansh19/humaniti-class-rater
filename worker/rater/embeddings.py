"""Embeddings microservice core: EmbeddingGemma 2, LOCAL only (recordings never leave the machine).

Segments a class into ~5-min windows and embeds each modality per window into one shared space:
  audio  : mono 16 kHz PCM for the window (25 tok/s -> 300 s = 7.5K tokens < 8K context)
  video  : frames at ~0.2 fps, at most 58 per window, as a frame list (vision budget configurable)
  text   : the anonymised transcript lines in the window (Document prompt)
Vectors are MRL-truncated (default 256-d) and L2-normalised.

Uses: (a) retrieval of timestamped evidence windows per rubric criterion, (b) zero-shot rubric probes
(window similarity to text descriptions) as features, (c) semantic content coverage.
Optional dependency: torch + sentence-transformers (requirements-embeddings.txt)."""
from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from .models import Utterance

MODEL_ID = os.environ.get("RATER_EMBED_MODEL", "google/embeddinggemma-2")
WINDOW_S = 300.0
FPS = 0.2
MAX_FRAMES = 58
AUDIO_TOKENS = 7600                       # 25 tok/s -> 304 s
AUDIO_KW = {"audio": {"max_length": int(WINDOW_S * 16000), "truncation": True}}


@dataclass
class Window:
    t0: float
    t1: float
    text: str = ""
    vec: dict[str, list[float]] = field(default_factory=dict)      # modality -> embedding


def windows(duration: float, size: float = WINDOW_S) -> list[tuple[float, float]]:
    n = max(1, int(np.ceil(duration / size)))
    out = [(i * size, min((i + 1) * size, duration)) for i in range(n)]
    if len(out) > 1 and out[-1][1] - out[-1][0] < 60:          # fold a <1-min tail into the previous window
        out[-2] = (out[-2][0], out[-1][1])
        out.pop()
    return out


def window_text(utts: list[Utterance], t0: float, t1: float, max_chars: int = 12000) -> str:
    return "\n".join(f"{u.speaker}: {u.text}" for u in utts if t0 <= u.start < t1)[:max_chars]


_MODEL = {}


def load(modalities: tuple[str, ...] = ("text", "audio", "video"), dtype: str | None = "bf16"):
    """Loads only the encoders needed (vision/audio encoders are optional per the model card)."""
    key = (modalities, dtype)
    if key not in _MODEL:
        import torch
        from sentence_transformers import SentenceTransformer
        cfg = {}
        if "audio" not in modalities:
            cfg["audio_config"] = None
        if "video" not in modalities and "image" not in modalities:
            cfg["vision_config"] = None
        dt = {"bf16": torch.bfloat16, "fp32": torch.float32}[dtype or "bf16"]       # never fp16 (model card: NaNs)
        torch.set_num_threads(int(os.environ.get("RATER_EMBED_THREADS", os.cpu_count() or 4)))
        _MODEL.clear()                                            # keep one model in RAM
        m = SentenceTransformer(MODEL_ID, device="cpu", config_kwargs=cfg, model_kwargs={"torch_dtype": dt})
        # The shipped audio processor caps input at 30 s (max_length 480000 samples, audio_seq_length 750 tokens),
        # silently truncating a 5-min window; verified (30 s vs 300 s embeddings had cos 1.00). Raise to the 8K context.
        proc = getattr(m[0], "processor", None)
        if proc is not None and hasattr(proc, "audio_seq_length"):
            proc.audio_seq_length = AUDIO_TOKENS
        _MODEL[key] = m
    return _MODEL[key]


def _norm(v: np.ndarray, dim: int) -> list[float]:
    v = np.asarray(v, float)[:dim]
    return (v / (np.linalg.norm(v) + 1e-12)).round(5).tolist()


def encode_text(texts: list[str], prompt: str | None = None, dim: int = 256, model=None) -> np.ndarray:
    m = model or load(("text",))
    e = m.encode(texts, prompt_name=prompt, convert_to_numpy=True) if prompt else m.encode(texts, convert_to_numpy=True)
    return np.array([_norm(v, dim) for v in e])


def embed_class(media_path: str | None, utts: list[Utterance], duration: float, *, modalities=("text", "audio", "video"),
                dim: int = 256, vision_tokens: int = 70, fps: float = FPS, on_progress: Callable[[float], None] | None = None,
                dtype: str | None = None) -> list[Window]:
    from .media import frames, pcm
    mods = tuple(m for m in modalities if m == "text" or media_path)
    dtype = dtype or os.environ.get("RATER_EMBED_DTYPE", "bf16")
    model = load(mods, dtype)
    out = []
    ws = windows(duration)
    for i, (t0, t1) in enumerate(ws):
        w = Window(t0, t1, window_text(utts, t0, t1))
        if "text" in mods and w.text:
            w.vec["text"] = _norm(model.encode(w.text, prompt_name="Document", convert_to_numpy=True), dim)
        if "audio" in mods:
            x = pcm(media_path, rate=16000, start=t0, dur=min(t1 - t0, 320))
            if len(x) > 16000:
                w.vec["audio"] = _norm(model.encode({"audio": x[: int(WINDOW_S * 16000)].astype(np.float32)}, convert_to_numpy=True,
                                                    processing_kwargs=AUDIO_KW), dim)
        if "video" in mods:
            from PIL import Image                                 # only needed for frames
            imgs = [Image.fromarray(f[:, :, ::-1]) for t, f in frames(media_path, every_s=1 / fps, width=448, start=t0, dur=t1 - t0)][:MAX_FRAMES]
            if imgs:
                w.vec["video"] = _norm(model.encode({"video": imgs}, convert_to_numpy=True, processing_kwargs={
                    "video": {"max_frames": MAX_FRAMES, "fps": None, "max_soft_tokens": vision_tokens}}), dim)
        out.append(w)
        if on_progress:
            on_progress((i + 1) / len(ws))
    return out


# ---------------- (b) zero-shot rubric probes ----------------
# Each probe is a (positive, negative) description pair; the feature is mean over windows of sim(pos) - sim(neg).
# Contrasts cancel modality-wide similarity offsets. Declared before any eval run; not tuned.
PROBES: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "energetic_tutor": ("a cheerful, smiling, energetic teacher talking enthusiastically to children",
                        "a flat, monotone, tired teacher speaking slowly", ("video", "audio")),
    "camera_on_face": ("a person's face clearly visible on a webcam", "a black screen, camera turned off, no face visible", ("video",)),
    "clean_audio": ("clear speech recorded with a good microphone", "noisy, distorted, crackling, breaking-up audio", ("audio",)),
    "children_answering": ("children answering a teacher's questions and talking excitedly",
                           "one adult talking alone for a long time", ("audio", "text")),
    "board_teaching": ("a chess board shared on screen with pieces and moves being explained",
                       "a person sitting in a room with no teaching material shown", ("video",)),
    "warm_rapport": ("a teacher greeting children by name, asking how they are and praising them",
                     "a teacher starting the lesson immediately without greeting anyone", ("text", "audio")),
}


def probe_features(ws: list[Window], dim: int = 256, model=None) -> dict[str, float]:
    texts = [s for p in PROBES.values() for s in p[:2]]
    E = encode_text(texts, None, dim, model)
    out = {}
    for i, (name, (_, _, mods)) in enumerate(PROBES.items()):
        pos, neg = E[2 * i], E[2 * i + 1]
        for m in mods:
            vs = [np.array(w.vec[m]) for w in ws if m in w.vec]
            if vs:
                d = np.array([v @ pos - v @ neg for v in vs])
                out[f"{name}.{m}"] = round(float(d.mean()), 4)
                out[f"{name}.{m}.min"] = round(float(d.min()), 4)
    return out


# ---------------- (a) evidence-window retrieval ----------------
CRITERION_QUERIES = {
    "rapport": "teacher warmly greets the children, asks their names and how their day was",
    "individual_attention": "teacher calls on a specific child by name and asks them a question",
    "energy": "teacher sounds excited and praises the children enthusiastically",
    "homework_closure": "teacher summarises the lesson, gives homework and says goodbye",
    "presentation": "teacher's face is visible on camera in a well lit room with a branded background",
    "av_quality": "children say they cannot hear or see; audio is breaking up",
    "teaching_aids": "a chess board or puzzle is shared on screen to explain the move",
    "content_coverage": "the teacher explains a chess concept and the children practise it",
}


def retrieve(ws: list[Window], k: int = 2, dim: int = 256, model=None) -> dict[str, list[dict]]:
    """Top-k windows per criterion by max similarity over available modalities (SearchQuery prompt for text)."""
    keys = list(CRITERION_QUERIES)
    Q_text = encode_text([CRITERION_QUERIES[c] for c in keys], "SearchQuery", dim, model)
    Q_x = encode_text([CRITERION_QUERIES[c] for c in keys], None, dim, model)        # cross-modal: plain text
    out = {}
    for ci, c in enumerate(keys):
        scored = []
        for w in ws:
            s = {m: float(np.array(v) @ (Q_text[ci] if m == "text" else Q_x[ci])) for m, v in w.vec.items()}
            if s:
                best = max(s, key=s.get)
                scored.append({"t0": w.t0, "t1": w.t1, "score": round(s[best], 3), "modality": best})
        out[c] = sorted(scored, key=lambda d: -d["score"])[:k]
    return out


# ---------------- (c) semantic content coverage ----------------
TOPIC_DESCRIPTIONS = {
    "openings & development": "chess opening principles: develop knights and bishops, control the centre, castle early",
    "tactics: forks": "a fork: one chess piece attacks two enemy pieces at the same time",
    "tactics: pins & skewers": "a pin or skewer: attacking a piece that shields a more valuable piece behind it",
    "check & checkmate": "giving check and delivering checkmate to the king; checkmate patterns",
    "piece movement & rules": "how chess pieces move and capture, castling, en passant, pawn promotion rules",
    "endgames": "chess endgames: king and pawn endings, opposition, promoting a pawn",
    "puzzles & problem solving": "solving chess puzzles: find the best move in this position",
    "notation & coordinates": "chess notation and board coordinates, files and ranks like e4 or Nf3",
    "strategy & planning": "chess strategy: piece value, trading, planning, weak squares",
}
OFF_TOPIC = "small talk, greetings, technical problems, waiting for students to join"


def semantic_content(ws: list[Window], dim: int = 256, margin: float = 0.02, model=None) -> dict:
    names = list(TOPIC_DESCRIPTIONS)
    Q = encode_text([TOPIC_DESCRIPTIONS[n] for n in names] + [OFF_TOPIC], "SearchQuery", dim, model)
    topics: dict[str, dict] = {}
    for w in ws:
        if "text" not in w.vec:
            continue
        s = Q @ np.array(w.vec["text"])
        off, best = s[-1], s[:-1].max()
        # a window's time is split equally among topics within `margin` of the best one, if they beat off-topic
        hits = [i for i in range(len(names)) if s[i] > off + margin and s[i] >= best - margin]
        for i in hits:
            n = names[i]
            d = topics.setdefault(n, {"topic": n, "first_t": w.t0, "minutes": 0.0, "peak": 0.0})
            d["minutes"] += (w.t1 - w.t0) / 60 / len(hits)
            d["peak"] = max(d["peak"], round(float(s[i] - off), 3))
    tl = sorted(topics.values(), key=lambda d: (-d["minutes"], -d["peak"]))
    for d in tl:
        d["minutes"] = round(d["minutes"], 1)
    return {"topics": tl, "method": f"embeddinggemma-2 {dim}d"}
