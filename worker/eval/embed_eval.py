"""EmbeddingGemma 2 evaluation (local only). Reads data/emb/*.json (eval.embed_extract) + data/cache.

1. Ablation, nested LOO (inner LOO selects the model; outer fold never seen): current v2.2 pool vs
   v2.2 + embedding probes vs probes only. Pools are declared in rater/judge/selection.py.
2. Retrieval (a): does a top-2 retrieved window contain a keyword-tagged evidence quote for that criterion?
   Compared with the chance rate for 2 random windows.
3. Semantic content (c) vs keyword content: VTT/Whisper agreement and the feedback 'practice' check.
Probes/retrieval/content are recomputed from stored window vectors with the current code (text queries only).
usage: python -m eval.embed_eval   (needs torch + sentence-transformers for the text queries)"""
from __future__ import annotations

import glob
import json
import os
from math import comb

import numpy as np

from rater import embeddings as E
from rater.content import topic_set
from rater.judge.selection import candidates_probes, candidates_v22, flat, select
from rater.models import LABELS, Analysis

from .run import metrics

HERE = os.path.dirname(__file__)
EMB = os.path.join(HERE, "../data/emb")
CACHE = os.path.join(HERE, "../data/cache")


def _windows(rec):
    return [E.Window(w["t0"], w["t1"], vec=w["vec"]) for w in rec["windows"]]


def load():
    recs = {}
    for p in glob.glob(os.path.join(EMB, "*.json")):
        with open(p) as fh:
            r = json.load(fh)
        key = os.path.basename(p)[:-5]
        ws = _windows(r)
        r["probes"], r["retrieval"], r["content"] = E.probe_features(ws), E.retrieve(ws), E.semantic_content(ws)
        recs[key] = r
    return recs


def cache(kind):
    out = {}
    for p in glob.glob(os.path.join(CACHE, "*.json")):
        if p.endswith(".asr.json") == (kind == "asr"):
            with open(p) as fh:
                d = json.load(fh)
            out[d["id"]] = d
    return out


PARTIAL = os.path.join(HERE, "../data/emb_eval_partial.json")      # resumable: per (kind, pool) results


def _partial() -> dict:
    if os.path.exists(PARTIAL):
        with open(PARTIAL) as fh:
            return json.load(fh)
    return {}


def cached_nested(tag, F, y, pool):
    part = _partial()
    if tag not in part:
        r = nested(F, y, pool)
        part = _partial()
        part[tag] = {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in r.items()}
        with open(PARTIAL, "w") as fh:
            json.dump(part, fh)
        print("cached", tag, flush=True)
    return part[tag]


def nested(F, y, pool):
    P, ch = [], []
    for i in range(len(F)):
        nm, mdl, _ = select(F[:i] + F[i + 1:], y[:i] + y[i + 1:], pool=pool)
        P.append(mdl.predict(F[i])[0])
        ch.append(nm)
    m = metrics(y, P)
    m["chosen"] = ch
    m["pred"] = P
    return m


def main():
    recs = load()
    res = {"runtime": {}, "ablation": {}, "retrieval": {}, "content": {}}
    for k, r in recs.items():
        if not k.endswith(".asr"):
            res["runtime"][k] = {"minutes": round(r["duration_s"] / 60), "seconds": r["seconds"], "maxrss_MB": r["maxrss_MB"]}
    probe_keys = sorted({f"emb.{k}" for r in recs.values() for k in r["probes"] if not k.endswith(".min")})
    for kind in ("vtt", "asr"):
        c = cache(kind)
        ids = sorted(i for i in c if c[i]["label"] and (i + (".asr" if kind == "asr" else "")) in recs)
        if len(ids) < 10:
            res["ablation"][kind] = f"only {len(ids)} labelled classes embedded"
            continue
        y = [c[i]["label"] for i in ids]
        F = []
        for i in ids:
            a = Analysis(**c[i]["analysis"])
            f = flat({m: v for m, v in a.features.items() if m != "content"})
            f.update({f"emb.{k}": v for k, v in recs[i + (".asr" if kind == "asr" else "")]["probes"].items()})
            F.append(f)
        res["ablation"][kind] = {
            "current (v2.2 pool)": cached_nested(f"{kind}:current", F, y, candidates_v22()),
            "current + embedding probes": cached_nested(f"{kind}:plus", F, y, candidates_probes(probe_keys)),
            "embedding probes only": cached_nested(f"{kind}:probes", F, y, candidates_probes(probe_keys, with_criteria=False)),
            "ids": ids, "true": y}
    # retrieval agreement
    hit, chance, n = 0, 0.0, 0
    per = {}
    for i, d in cache("vtt").items():
        if i not in recs:
            continue
        r, nw = recs[i], len(recs[i]["windows"])
        for crit, qs in Analysis(**d["analysis"]).evidence.items():
            top = r["retrieval"].get(crit, [])
            if not qs or not top or nw < 3:
                continue
            inq = {int(q.t // E.WINDOW_S) for q in qs}
            inq = {min(x, nw - 1) for x in inq}
            got = any(any(w["t0"] <= q.t < w["t1"] + 1 for q in qs) for w in top)
            k = len(inq)
            p_chance = 1 - comb(nw - k, len(top)) / comb(nw, len(top)) if nw - k >= len(top) else 1.0
            hit += got
            chance += p_chance
            n += 1
            per.setdefault(crit, [0, 0])
            per[crit][0] += got
            per[crit][1] += 1
    res["retrieval"] = {"top2_contains_keyword_evidence": round(hit / n, 2) if n else None,
                        "chance": round(chance / n, 2) if n else None, "n": n,
                        "per_criterion": {k: f"{a}/{b}" for k, (a, b) in per.items()}}
    # semantic vs keyword content
    vt, asr = cache("vtt"), cache("asr")
    sem_j, kw_j, sem_top, kw_top, m = [], [], 0, 0, 0
    for i in vt:
        if i in recs and i + ".asr" in recs and i in asr:
            sv, sa = recs[i]["content"]["topics"], recs[i + ".asr"]["content"]["topics"]
            Sv, Sa = {t["topic"] for t in sv if t["minutes"] >= 1}, {t["topic"] for t in sa if t["minutes"] >= 1}
            sem_j.append(len(Sv & Sa) / len(Sv | Sa) if Sv | Sa else 1.0)
            sem_top += bool(sv and sa and sv[0]["topic"] == sa[0]["topic"])
            kv, ka = vt[i]["analysis"]["content"], asr[i]["analysis"]["content"]
            Kv, Ka = topic_set(kv), topic_set(ka)
            kw_j.append(len(Kv & Ka) / len(Kv | Ka) if Kv | Ka else 1.0)
            kw_top += bool(kv.get("topics") and ka.get("topics") and kv["topics"][0]["topic"] == ka["topics"][0]["topic"])
            m += 1
    practice = [i for i in recs if i.startswith("average-B516") and not i.endswith(".asr")]
    res["content"] = {"n": m, "semantic_top_topic_agree": f"{sem_top}/{m}", "keyword_top_topic_agree": f"{kw_top}/{m}",
                      "semantic_mean_jaccard": round(float(np.mean(sem_j)), 2) if sem_j else None,
                      "keyword_mean_jaccard": round(float(np.mean(kw_j)), 2) if kw_j else None,
                      "feedback_practice_check_semantic": bool(practice and any(t["topic"] == "puzzles & problem solving"
                                                                                for t in recs[practice[0]]["content"]["topics"]))}
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results/embeddings.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    for kind, v in res["ablation"].items():
        if isinstance(v, dict):
            for name in ("current (v2.2 pool)", "current + embedding probes", "embedding probes only"):
                print(kind, f"{name:28s}", f"exact {v[name]['exact']:.0%} within1 {v[name]['within1']:.0%} mae {v[name]['mae']:.2f}")
        else:
            print(kind, v)
    print(json.dumps({k: res[k] for k in ("retrieval", "content")}, indent=1))
    print(json.dumps(res["runtime"]))


if __name__ == "__main__":
    _ = LABELS
    main()
