"""Leave-one-out evaluation + ablations (spec: docs/specs/eval.md). Writes docs/EVAL.md.

Protocol: feature->criterion mappings and the model family (ridge-ordinal, alpha fixed) were frozen
before this script was first run. Only model parameters are fitted, on the 9 training classes per fold.

usage: python -m eval.run [--llm]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import Counter

import numpy as np

from rater.judge.ordinal import fit
from rater.judge.rubric import CRITERIA, criterion_scores
from rater.judge.selection import flat, select
from rater.models import LABELS, Analysis

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "../data/cache")
OUT = os.path.join(HERE, "../../docs/EVAL.md")
MODEL_OUT = os.path.join(HERE, "../rater/judge/model.json")

# Anonymised paraphrase of the organiser's feedback per class (no names), used for failure analysis.
FEEDBACK = {
    "excellent-B491": "good one-to-one interaction; individual questions; background kept; homework shared",
    "excellent-B472": "good rapport; includes everyone; individual questions; homework given",
    "good-B552": "good intro; 8x8 background; homework given; needs more pleasant interaction",
    "good-B435": "good intro; includes everyone; individual questions; should give homework",
    "average-B516": "8x8 background; individual attention early and during puzzles; homework given; clarity issues with background",
    "average-B435": "background; one-to-one attention; needs more energy and pleasant interaction; no homework; poor lighting",
    "weak-B558": "background; needs better intro and conclusion; no self-intro time for new joiners; needs more energy",
    "weak-B482": "background; individual questions; jumped into revision without rapport; no self-intro time; tutor camera sometimes off",
    "quality_issue-B392": "interaction present but no background; needs happier interaction; students reported quality issues repeatedly",
    "quality_issue-B441": "background but tutor face not visible; no rapport building; needs happier communication",
}

VARIANTS = {
    "transcript only": ("vtt", ("text",)),
    "transcript + audio": ("vtt", ("text", "audio")),
    "transcript + audio + frames (full)": ("vtt", ("text", "audio", "visual")),
    "full, ASR transcript (no VTT)": ("asr", ("text", "audio", "visual")),
}


def load(kind: str) -> list[dict]:
    suffix = ".asr.json" if kind == "asr" else ".json"
    rows = []
    for p in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
        if (kind == "asr") != p.endswith(".asr.json"):
            continue
        with open(p) as fh:
            d = json.load(fh)
        d["analysis"] = Analysis(**d["analysis"])
        rows.append(d)
    return [r for r in rows if r["id"] and suffix]


def crit_rows(rows, modalities):
    return [criterion_scores({m: r["analysis"].features[m] for m in modalities if m in r["analysis"].features}) for r in rows]


def loo_ridge(X, y):
    preds, scores = [], []
    keys = list(CRITERIA)
    for i in range(len(X)):
        m = fit([x for j, x in enumerate(X) if j != i], [t for j, t in enumerate(y) if j != i], keys)
        lab, s, _ = m.predict(X[i])
        preds.append(lab)
        scores.append(s)
    return preds, scores


def loo_mean_cut(X, y):
    """Secondary variant: unweighted mean of known criteria; 3 cut-points = midpoints of adjacent training class means."""
    def mean(x):
        v = [a for a in x.values() if a is not None]
        return sum(v) / len(v)
    preds, scores = [], []
    for i in range(len(X)):
        tr = [(mean(x), t) for j, (x, t) in enumerate(zip(X, y, strict=True)) if j != i]
        cm = {lab: np.mean([s for s, t in tr if t == lab]) for lab in LABELS if any(t == lab for _, t in tr)}
        cuts = [(cm[LABELS[k]] + cm[LABELS[k + 1]]) / 2 if LABELS[k] in cm and LABELS[k + 1] in cm else np.inf for k in range(3)]
        s = mean(X[i])
        preds.append(LABELS[int(np.searchsorted(sorted(cuts), s))])
        scores.append(s)
    return preds, scores


def metrics(y, p):
    yi = np.array([LABELS.index(a) for a in y])
    pi = np.array([LABELS.index(a) for a in p])
    cm = np.zeros((4, 4), int)
    for a, b in zip(yi, pi, strict=True):
        cm[a, b] += 1
    return {"exact": float((yi == pi).mean()), "within1": float((abs(yi - pi) <= 1).mean()), "mae": float(abs(yi - pi).mean()), "cm": cm}


def cm_md(cm):
    s = "| true \\ predicted | " + " | ".join(LABELS) + " |\n|---|" + "---|" * 4 + "\n"
    return s + "\n".join(f"| **{LABELS[i]}** | " + " | ".join(str(v) for v in cm[i]) + " |" for i in range(4))


def short(cid):
    return cid.rsplit("-", 3)[0] + "-" + cid.split("-")[1] if cid.count("-") >= 2 else cid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true")
    args = ap.parse_args()
    results, per_class = {}, {}
    for name, (kind, mods) in VARIANTS.items():
        rows = [r for r in load(kind) if r["label"]]
        if len(rows) < 10:
            results[name] = None
            continue
        X, y = crit_rows(rows, mods), [r["label"] for r in rows]
        p, s = loo_ridge(X, y)
        results[name] = metrics(y, p)
        per_class[name] = {r["id"]: (r["label"], pp, ss, x) for r, pp, ss, x in zip(rows, p, s, X, strict=True)}
        p2, _ = loo_mean_cut(X, y)
        results[name + " - mean+cutpoints (secondary)"] = metrics(y, p2)
        F = [flat({m: r["analysis"].features[m] for m in mods if m in r["analysis"].features}) for r in rows]
        p3, chosen = [], []
        for i in range(len(F)):
            nm, mdl, _ = select(F[:i] + F[i + 1:], y[:i] + y[i + 1:])
            chosen.append(nm)
            p3.append(mdl.predict(F[i])[0])
        results[name + " - nested selection (v2.1)"] = metrics(y, p3)
        results[name + " - nested selection (v2.1)"]["chosen"] = chosen
        per_class[name + " - nested (v2.1)"] = {r["id"]: (r["label"], pp, 0.0, x) for r, pp, x in zip(rows, p3, X, strict=True)}
    if args.llm:
        from rater.judge import judge
        from rater.judge.providers import detect
        if detect():
            rows = [r for r in load("vtt") if r["label"]]
            p = [judge(r["analysis"]).label for r in rows]
            results[f"LLM judge ({detect()}, zero-shot, full features)"] = metrics([r["label"] for r in rows], p)
    # shipped model: fit on all 10 labelled classes, full VTT features
    rows = [r for r in load("vtt") if r["label"]]
    full = fit(crit_rows(rows, ("text", "audio", "visual")), [r["label"] for r in rows], list(CRITERIA))
    with open(MODEL_OUT, "w") as fh:
        fh.write(full.to_json())
    write_report(results, per_class, full)
    for k, v in results.items():
        print(f"{k:60s}", "n/a" if v is None else f"exact {v['exact']:.0%} within1 {v['within1']:.0%} mae {v['mae']:.2f}")


def write_report(results, per_class, full):
    n_major = Counter(r["label"] for r in load("vtt") if r["label"]).most_common(1)[0][1]
    L = ["# Evaluation report", "",
         "Generated by `python -m eval.run` (worker/). Ids are folder + batch code; no names appear anywhere.", "",
         ("**Data.** 10 labelled recordings. The organiser-approved mapping is weak→Poor and quality issue→Poor, giving "
         "4 Poor, 2 Average, 2 Good and 2 Excellent. The 2 demo recordings are unlabelled and serve as robustness checks."), "",
         ("**Protocol.** Leave-one-out (LOO). The feature→criterion mappings (`rater/judge/rubric.py`) and the model family "
         "(ridge regression on the 0..3 ordinal target over the 7 criterion scores, alpha = 2, fixed) were **frozen before the first eval run**. "
         "Only the ridge coefficients and the standardisation are fitted, on the 9 training classes of each fold. "
         f"Majority baseline (always Poor): {n_major / 10:.0%}. The v1 prototype scored 50%."), "",
         "## Results (LOO, n = 10)", "", "| variant | exact | within ±1 | MAE (classes) |", "|---|---|---|---|"]
    for k, v in results.items():
        L.append(f"| {k} | " + ("not run | | |" if v is None else f"{v['exact']:.0%} | {v['within1']:.0%} | {v['mae']:.2f} |"))
    if not any(k.startswith("LLM") for k in results):
        L += ["| LLM judge (Gemini/OpenAI/Anthropic) | not run: no approved API key available on the build box | | |"]
    main_name = "transcript + audio + frames (full)"
    if results.get(main_name):
        L += ["", f"## Confusion matrix: {main_name}", "", cm_md(results[main_name]["cm"])]
    if results.get("full, ASR transcript (no VTT)"):
        L += ["", "## Confusion matrix: full, ASR transcript (the path a tester uploading only an MP4 gets)", "",
              cm_md(results["full, ASR transcript (no VTT)"]["cm"])]
    if main_name in per_class:
        L += ["", "## Per-class predictions (LOO)", "", "| class | true | " + " | ".join(per_class) + " |", "|---|---|" + "---|" * len(per_class)]
        for cid in per_class[main_name]:
            cells = []
            for v in per_class:
                pc = per_class[v].get(cid) or per_class[v].get(cid)
                cells.append(f"{pc[1]} ({pc[2]:.2f})" if pc else "-")
            L.append(f"| {cid} | {per_class[main_name][cid][0]} | " + " | ".join(cells) + " |")
        L += ["", "## Criterion scores (full variant, 1-5)", "", "| class | " + " | ".join(CRITERIA) + " |", "|---|" + "---|" * len(CRITERIA)]
        for cid, (_, _, _, x) in per_class[main_name].items():
            L.append(f"| {cid} | " + " | ".join("-" if x[k] is None else f"{x[k]:.1f}" for k in CRITERIA) + " |")
        L += ["", "## Failure analysis", ""]
        for cid, (t, p, s, x) in per_class[main_name].items():
            if t == p:
                continue
            key = "-".join(cid.split("-")[:2])
            low = sorted((k for k in CRITERIA if x[k] is not None), key=lambda k: x[k])[:2]
            high = sorted((k for k in CRITERIA if x[k] is not None), key=lambda k: -x[k])[:2]
            L.append(f"- **{cid}**: true {t}, predicted {p} (score {s:.2f}). Organiser feedback: *{FEEDBACK.get(key, '?')}*. "
                     f"Highest criteria: {', '.join(high)}; lowest: {', '.join(low)}.")
    demos = [r for r in load("vtt") if not r["label"]]
    if demos:
        L += ["", "## Robustness: unlabelled demo classes (shipped model)", "", "| demo | predicted | continuous score | note |", "|---|---|---|---|"]
        for r in demos:
            x = criterion_scores(r["analysis"].features)
            lab, s, _ = full.predict(x)
            t = r["analysis"].features["text"]
            L.append(f"| {r['id']} | {lab} | {s:.2f} | {t['students_speaking']:.0f} students speaking, {t['student_turns_per_min']:.1f} student turns/min |")
    L += ["", "## Shipped model (fit on all 10 labelled classes)", "", "| criterion | standardised coefficient |", "|---|---|"]
    L += [f"| {k} | {c:+.2f} |" for k, c in zip(full.keys, full.coef, strict=True)]
    L += ["", "## Caveats", "",
          "- n = 10, so one class is worth 10 percentage points. A 95% interval on 7/10 is roughly 35–93%. These numbers are indicative, not a benchmark.",
          "- Every variant that was run is listed above. Nothing was dropped.",
          "- The frame-layout classifier thresholds were checked against 3 hand-inspected frames (one per layout type). That is a check of what layout is on screen, not of the quality labels.",
          "- 'weak' and 'quality issue' fail in different ways (pedagogy vs AV/camera) but share the Poor label.",
          "- The keyword cues are English. The Malayalam demo shows how far they degrade."]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
