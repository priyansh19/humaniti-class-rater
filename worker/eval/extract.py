"""Extract and cache Analysis objects for the local dataset (cache is git-ignored).

usage: python -m eval.extract [--asr] [--only ID]"""
from __future__ import annotations

import argparse
import json
import os
import time

from rater.analysis import analyse

from .dataset import items

ROOT = os.environ.get("RATER_DATASET", os.path.join(os.path.dirname(__file__), "../../../dataset/class recordings"))
CACHE = os.path.join(os.path.dirname(__file__), "../data/cache")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asr", action="store_true", help="ignore the VTT and transcribe with local Whisper")
    ap.add_argument("--only")
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    for it in items(ROOT):
        if a.only and it["id"] != a.only:
            continue
        out = os.path.join(CACHE, f"{it['id']}{'.asr' if a.asr else ''}.json")
        if os.path.exists(out):
            continue
        t = time.time()
        vtt = None
        if not a.asr:
            with open(it["vtt"], encoding="utf-8") as fh:
                vtt = fh.read()
        an = analyse(it["video"], vtt)
        with open(out, "w") as fh:
            json.dump({"id": it["id"], "folder": it["folder"], "label": it["label"], "analysis": an.model_dump()}, fh)
        print(f"{it['id']} {'asr' if a.asr else 'vtt'} {time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main()
