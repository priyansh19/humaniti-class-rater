"""Run the configured LLM judge (zero-shot, no fitting) on every cached class; caches reports (git-ignored).

usage: RATER_LOCAL_LLM_URL=http://127.0.0.1:8081/v1 python -m eval.llm_eval [--asr]"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

from rater.judge import judge
from rater.models import Analysis

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "../data/cache")
OUT = os.path.join(HERE, "../data/llm")


def main():
    asr = "--asr" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    for p in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
        if p.endswith(".asr.json") != asr:
            continue
        with open(p) as fh:
            d = json.load(fh)
        out = os.path.join(OUT, os.path.basename(p))
        if os.path.exists(out):
            continue
        t = time.time()
        r = judge(Analysis(**d["analysis"]))
        with open(out, "w") as fh:
            json.dump({"id": d["id"], "label": d["label"], "report": r.model_dump(), "seconds": round(time.time() - t)}, fh)
        print(d["id"], d["label"], "->", r.label, r.judge, f"{time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main()
