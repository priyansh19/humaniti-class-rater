"""Embed every local class (EmbeddingGemma 2, CPU, local only) -> data/emb/<id>.json (git-ignored).

Stores per-window vectors (256-d), probe features, retrieval and semantic content, plus runtime/RSS.
Text windows use the cached anonymised VTT utterances; '<id>.asr' variants use the Whisper utterances.
usage: python -m eval.embed_extract [--only ID]"""
from __future__ import annotations

import glob
import json
import os
import resource
import sys
import time

from rater import embeddings as E
from rater.models import Utterance

from .dataset import items

HERE = os.path.dirname(__file__)
ROOT = os.environ.get("RATER_DATASET", os.path.join(os.path.dirname(__file__), "../../../dataset/class recordings"))
CACHE = os.path.join(HERE, "../data/cache")
OUT = os.path.join(HERE, "../data/emb")


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    vids = {it["id"]: it["video"] for it in items(ROOT)}
    for p in sorted(glob.glob(os.path.join(CACHE, "*.json")), key=lambda q: (q.endswith(".asr.json"), q)):
        with open(p) as fh:
            d = json.load(fh)
        asr = p.endswith(".asr.json")
        key = d["id"] + (".asr" if asr else "")
        out = os.path.join(OUT, key + ".json")
        if (only and d["id"] != only) or os.path.exists(out):
            continue
        utts = [Utterance(**u) for u in d["utterances"]]
        dur = d["analysis"]["duration_s"]
        t = time.time()
        # media embeddings are identical for VTT/ASR variants: embed media once (VTT run), text-only for ASR
        mods = ("text",) if asr else ("text", "audio", "video")
        ws = E.embed_class(vids[d["id"]], utts, dur, modalities=mods)
        if asr:
            base = os.path.join(OUT, d["id"] + ".json")
            if os.path.exists(base):
                with open(base) as fh:
                    bw = {w["t0"]: w["vec"] for w in json.load(fh)["windows"]}
                for w in ws:
                    w.vec.update({m: v for m, v in bw.get(w.t0, {}).items() if m != "text"})
        rec = {"id": d["id"], "label": d["label"], "duration_s": dur, "seconds": round(time.time() - t),
               "maxrss_MB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024,
               "windows": [{"t0": w.t0, "t1": w.t1, "vec": w.vec} for w in ws]}
        # probes / retrieval / semantic content are computed in eval.embed_eval from these vectors (one text model load)
        with open(out, "w") as fh:
            json.dump(rec, fh)
        print(key, f"{dur / 60:.0f} min", f"{rec['seconds']}s", f"rss {rec['maxrss_MB']}MB", flush=True)


if __name__ == "__main__":
    main()
