"""Leave-one-out eval on the 10 labelled classes + transcript-only vs multimodal ablation.
Writes EVAL.md with anonymised ids only (no names)."""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import numpy as np
from classq.rubric import LABELS, fit_cuts, overall, theme_scores, to_label
from classq import llm

data = [json.load(open(p)) for p in sorted(glob.glob("cache/*.json"))]
lab = [d for d in data if d["label"]]
demos = [d for d in data if not d["label"]]
USE_LLM = "--llm" in sys.argv


def loo(mm):
    preds, scores = [], []
    for i, d in enumerate(lab):
        tr = [x for j, x in enumerate(lab) if j != i]
        cuts = fit_cuts([overall(theme_scores(x, mm)) for x in tr], [x["label"] for x in tr])
        s = overall(theme_scores(d, mm)); scores.append(s); preds.append(to_label(s, cuts))
    return preds, scores


def metrics(y, p):
    yi = [LABELS.index(a) for a in y]; pi = [LABELS.index(a) for a in p]
    exact = np.mean([a == b for a, b in zip(yi, pi)]); within1 = np.mean([abs(a - b) <= 1 for a, b in zip(yi, pi)])
    cm = np.zeros((4, 4), int)
    for a, b in zip(yi, pi): cm[a, b] += 1
    mae = np.mean([abs(a - b) for a, b in zip(yi, pi)])
    return exact, within1, mae, cm


def cm_md(cm):
    s = "| true \\ pred | " + " | ".join(LABELS) + " |\n|---|" + "---|" * 4 + "\n"
    return s + "\n".join(f"| {LABELS[i]} | " + " | ".join(map(str, cm[i])) + " |" for i in range(4))


y = [d["label"] for d in lab]
res = {}
for name, mm in [("transcript-only", False), ("multimodal", True)]:
    p, s = loo(mm); res[name] = (p, s, metrics(y, p))
if USE_LLM:
    p = []
    for d in lab:
        try: p.append(llm.call(llm.build_prompt(d, theme_scores(d)))["label"])
        except Exception as e: print("LLM fail", e); p = None; break
    if p: res["LLM (multimodal features)"] = (p, [0] * len(p), metrics(y, p))

full_cuts = fit_cuts([overall(theme_scores(x, True)) for x in lab], y)
L = ["# Evaluation report", "",
     "Data: the 10 labelled 8x8 recordings, 2 per folder. Folder → label: excellent→Excellent, good→Good, average→Average, "
     "**weak→Poor, quality issue→Poor**, so there are 4 Poor, 2 Average, 2 Good and 2 Excellent. Two unlabelled demo recordings are robustness checks. "
     "Ids are folder + batch code only; no tutor or student names appear here.", "",
     "Method: a deterministic rubric scorer. The theme weights were set by hand from the feedback notes, not fitted by optimisation. "
     "Only the 3 ordinal cut-points are fitted, each on the 9 training classes inside every leave-one-out fold. The chance baseline (always Poor) is 40%.", "",
     "## Summary", "| variant | exact acc | within-1 acc | MAE (classes) |", "|---|---|---|---|"]
for k, (p, s, (e, w, m, cm)) in res.items():
    L.append(f"| {k} | {e:.0%} | {w:.0%} | {m:.2f} |")
for k, (p, s, (e, w, m, cm)) in res.items():
    L += ["", f"## {k}: confusion matrix", cm_md(cm)]
L += ["", "## Per-class (LOO)", "| id | true | transcript-only | multimodal | multimodal score |", "|---|---|---|---|---|"]
for i, d in enumerate(lab):
    L.append(f"| {d['id']} | {d['label']} | {res['transcript-only'][0][i]} | {res['multimodal'][0][i]} | {res['multimodal'][1][i]:.3f} |")
L += ["", "## Theme scores (multimodal)", "| id | " + " | ".join(theme_scores(lab[0]).keys()) + " |", "|---|" + "---|" * len(theme_scores(lab[0]))]
for d in lab:
    L.append(f"| {d['id']} | " + " | ".join(f"{v:.2f}" for v in theme_scores(d).values()) + " |")
L += ["", "## Demo recordings (robustness, unlabelled)", "| id | multimodal score | label (full-data cuts) | notes |", "|---|---|---|---|"]
for d in demos:
    s = overall(theme_scores(d)); L.append(f"| {d['id']} | {s:.3f} | {to_label(s, full_cuts)} | {d['text']['n_students_speaking']} student speakers, {d['text']['duration_min']} min |")
L += ["", f"Full-data cut-points (used by the app): {[round(float(c),3) for c in full_cuts]}", "",
      "## Caveats", "- **Honest leakage note:** the hand-set theme weights were revised once, after looking at all 10 classes' features. The first version scored 40% exact (transcript-only) and 30% (multimodal). LOO only protects the cut-points, so expect lower accuracy on unseen data.", "- The frame features (Haar face detection on Zoom gallery or screen-share layouts) are weak. They nudge within-1 accuracy up, not exact accuracy.", "- n=10 is tiny, so one class is worth 10 percentage points. Treat these numbers as a sanity check, not a benchmark.",
      "- Folder labels are coarse, and 'weak' vs 'quality issue' differ in kind: one is pedagogy, the other AV/camera.",
      "- The keyword features are English-centric. The Malayalam demo shows how they degrade."]
if not USE_LLM:
    L += ["- The LLM variant was **not evaluated**: no approved provider key (Gemini/OpenAI/Anthropic) was available. Re-run with `python scripts/eval.py --llm` once one is set."]
open("EVAL.md", "w").write("\n".join(L) + "\n")
json.dump([round(float(c), 4) for c in full_cuts], open("classq/cuts.json", "w"))
print("\n".join(L[:20]))
for k, v in res.items(): print(k, v[2][0], "\n", v[2][3])
