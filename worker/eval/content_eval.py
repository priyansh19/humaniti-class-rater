"""Domain-content coverage eval.

1. Agreement with the (three) content remarks in feedbacks.pdf, curated in gold.json["_content"].
2. Consistency between the VTT-based and the Whisper-based content map for the same class:
   subject agreement, top-topic agreement, topic-set Jaccard (topics with >= 1 min), and minutes rank correlation.

usage: python -m eval.content_eval   (needs data/cache/*.json and *.asr.json from eval.extract)"""
from __future__ import annotations

import glob
import json
import os

import numpy as np

from rater.content import topic_set

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "../data/cache")


def _load(asr: bool) -> dict[str, dict]:
    out = {}
    for p in glob.glob(os.path.join(CACHE, "*.json")):
        if p.endswith(".asr.json") == asr:
            with open(p) as fh:
                d = json.load(fh)
            out[d["id"]] = d["analysis"]
    return out


def _short(cid: str) -> str:
    return "-".join(cid.split("-")[:2])


def check(kind: str, a: dict) -> bool:
    c, f = a.get("content", {}), a["features"]
    m = c.get("metrics", {})
    if kind == "practice_present":
        return m.get("practised_frac", 0) > 0 or any(t["topic"] == "puzzles & tactics" for t in c.get("topics", []))
    if kind == "opens_with_revision":
        return m.get("opens_with_revision", 0) > 0
    if kind == "teaching_aids_gap":
        return f.get("visual", {}).get("screen_share_frac", 0) < 0.2   # little on-screen material shown
    raise ValueError(kind)


def _rank_corr(x, y):
    if len(x) < 3:
        return None
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def main():
    with open(os.path.join(HERE, "gold.json")) as fh:
        gold = json.load(fh)["_content"]
    vtt, asr = _load(False), _load(True)
    res = {"feedback_agreement": [], "vtt_vs_asr": []}
    for cid, a in sorted(vtt.items()):
        g = gold.get(_short(cid))
        if g:
            res["feedback_agreement"].append({"class": _short(cid), "check": g["check"], "vtt": check(g["check"], a),
                                              "asr": check(g["check"], asr[cid]) if cid in asr else None})
        if cid in asr:
            cv, ca = a["content"], asr[cid]["content"]
            sv, sa = topic_set(cv), topic_set(ca)
            mv = {t["topic"]: t["minutes"] for t in cv.get("topics", [])}
            ma = {t["topic"]: t["minutes"] for t in ca.get("topics", [])}
            common = sorted(set(mv) | set(ma))
            res["vtt_vs_asr"].append({
                "class": _short(cid), "subject_agree": cv.get("subject") == ca.get("subject"),
                "top_topic_agree": bool(cv.get("topics") and ca.get("topics") and cv["topics"][0]["topic"] == ca["topics"][0]["topic"]),
                "jaccard": round(len(sv & sa) / len(sv | sa), 2) if sv | sa else 1.0,
                "minutes_rank_corr": _rank_corr([mv.get(t, 0) for t in common], [ma.get(t, 0) for t in common]),
                "depth_vtt": cv.get("metrics", {}).get("mean_depth"), "depth_asr": ca.get("metrics", {}).get("mean_depth")})
    fa = res["feedback_agreement"]
    va = res["vtt_vs_asr"]
    corr = [r["minutes_rank_corr"] for r in va if r["minutes_rank_corr"] is not None]
    res["summary"] = {
        "feedback_checks_passed_vtt": f"{sum(r['vtt'] for r in fa)}/{len(fa)}",
        "feedback_checks_passed_asr": f"{sum(bool(r['asr']) for r in fa)}/{len(fa)}",
        "subject_agreement": f"{sum(r['subject_agree'] for r in va)}/{len(va)}",
        "top_topic_agreement": f"{sum(r['top_topic_agree'] for r in va)}/{len(va)}",
        "mean_topic_jaccard": round(float(np.mean([r["jaccard"] for r in va])), 2) if va else None,
        "mean_minutes_rank_corr": round(float(np.mean(corr)), 2) if corr else None}
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results/content.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps(res["summary"], indent=1))


if __name__ == "__main__":
    main()
