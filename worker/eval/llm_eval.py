"""Run the configured LLM judge (zero-shot, no fitting) on every cached class; caches reports (git-ignored).

Model comparison: run once per model with a tag, e.g.
  RATER_LLM_PROVIDER=local RATER_LOCAL_LLM_URL=http://127.0.0.1:8081/v1 python -m eval.llm_eval --tag qwen2.5-7b-local
  RATER_LLM_PROVIDER=openrouter RATER_OPENROUTER_MODEL=openai/gpt-4o-mini RATER_OPENROUTER_FALLBACK_MODEL= python -m eval.llm_eval --tag gpt-4o-mini
Reports go to data/llm/<tag>/ (git-ignored); eval.run --llm-tags a,b summarises them. --repeat N reruns for consistency."""
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
    tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "default"
    rep = int(sys.argv[sys.argv.index("--repeat") + 1]) if "--repeat" in sys.argv else 1
    out_dir = os.path.join(OUT, tag)
    os.makedirs(out_dir, exist_ok=True)
    for p in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
        if p.endswith(".asr.json") != asr:
            continue
        with open(p) as fh:
            d = json.load(fh)
        for i in range(rep):
            out = os.path.join(out_dir, os.path.basename(p).replace(".json", f".r{i}.json" if i else ".json"))
            if os.path.exists(out):
                continue
            t = time.time()
            r = judge(Analysis(**d["analysis"]))
            with open(out, "w") as fh:
                json.dump({"id": d["id"], "label": d["label"], "report": r.model_dump(), "seconds": round(time.time() - t)}, fh)
            print(tag, d["id"], d["label"], "->", r.label, r.judge, f"{time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main()
