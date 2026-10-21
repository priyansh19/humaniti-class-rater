# Evaluation report

Data: the 10 labelled 8x8 recordings, 2 per folder. Folder → label: excellent→Excellent, good→Good, average→Average, **weak→Poor, quality issue→Poor**, so there are 4 Poor, 2 Average, 2 Good and 2 Excellent. Two unlabelled demo recordings are robustness checks. Ids are folder + batch code only; no tutor or student names appear here.

Method: a deterministic rubric scorer. The theme weights were set by hand from the feedback notes, not fitted by optimisation. Only the 3 ordinal cut-points are fitted, each on the 9 training classes inside every leave-one-out fold. The chance baseline (always Poor) is 40%.

## Summary
| variant | exact acc | within-1 acc | MAE (classes) |
|---|---|---|---|
| transcript-only | 50% | 70% | 0.80 |
| multimodal | 50% | 80% | 0.70 |

## transcript-only: confusion matrix
| true \ pred | Poor | Average | Good | Excellent |
|---|---|---|---|---|
| Poor | 2 | 0 | 2 | 0 |
| Average | 1 | 1 | 0 | 0 |
| Good | 1 | 0 | 0 | 1 |
| Excellent | 0 | 0 | 0 | 2 |

## multimodal: confusion matrix
| true \ pred | Poor | Average | Good | Excellent |
|---|---|---|---|---|
| Poor | 2 | 1 | 1 | 0 |
| Average | 1 | 1 | 0 | 0 |
| Good | 1 | 0 | 0 | 1 |
| Excellent | 0 | 0 | 0 | 2 |

## Per-class (LOO)
| id | true | transcript-only | multimodal | multimodal score |
|---|---|---|---|---|
| average_B435_2026-08-28 | Average | Poor | Poor | 0.312 |
| average_B516_2026-09-03 | Average | Average | Average | 0.367 |
| excellent_B472_2026-08-24 | Excellent | Excellent | Excellent | 0.691 |
| excellent_B491_2026-06-29 | Excellent | Excellent | Excellent | 0.788 |
| good_B435_2026-07-25 | Good | Poor | Poor | 0.304 |
| good_B552_2026-09-02 | Good | Excellent | Excellent | 0.721 |
| quality_issue_B392_2026-09-02 | Poor | Good | Average | 0.413 |
| quality_issue_B441_2026-08-26 | Poor | Poor | Poor | 0.321 |
| weak_B482_2026-09-02 | Poor | Poor | Poor | 0.153 |
| weak_B558_2026-09-05 | Poor | Good | Good | 0.462 |

## Theme scores (multimodal)
| id | intro_rapport | individual_engagement | energy_pleasantness | homework_conclusion | av_quality | visual_professionalism |
|---|---|---|---|---|---|---|
| average_B435_2026-08-28 | 0.28 | 0.30 | 0.32 | 0.20 | 0.79 | 0.14 |
| average_B516_2026-09-03 | 0.44 | 0.42 | 0.12 | 0.87 | 0.13 | 0.14 |
| excellent_B472_2026-08-24 | 0.47 | 0.93 | 0.62 | 0.67 | 1.00 | 0.23 |
| excellent_B491_2026-06-29 | 0.70 | 1.00 | 0.97 | 0.40 | 0.96 | 0.22 |
| good_B435_2026-07-25 | 0.36 | 0.37 | 0.30 | 0.07 | 0.60 | 0.06 |
| good_B552_2026-09-02 | 0.30 | 0.87 | 0.87 | 1.00 | 0.99 | 0.16 |
| quality_issue_B392_2026-09-02 | 0.38 | 0.48 | 0.37 | 0.40 | 0.81 | 0.01 |
| quality_issue_B441_2026-08-26 | 0.50 | 0.51 | 0.01 | 0.00 | 0.63 | 0.16 |
| weak_B482_2026-09-02 | 0.06 | 0.17 | 0.00 | 0.20 | 0.54 | 0.21 |
| weak_B558_2026-09-05 | 0.32 | 0.56 | 0.69 | 0.07 | 0.76 | 0.15 |

## Demo recordings (robustness, unlabelled)
| id | multimodal score | label (full-data cuts) | notes |
|---|---|---|---|
| demo_Demo_english.mp4 | 0.541 | Good | 2 student speakers, 44.0 min |
| demo_Demo_malayalam.mp4 | 0.370 | Average | 1 student speakers, 51.6 min |

Full-data cut-points (used by the app): [0.338, 0.426, 0.626]

## Caveats
- **Honest leakage note:** the hand-set theme weights were revised once, after looking at all 10 classes' features. The first version scored 40% exact (transcript-only) and 30% (multimodal). LOO only protects the cut-points, so expect lower accuracy on unseen data.
- The frame features (Haar face detection on Zoom gallery or screen-share layouts) are weak. They nudge within-1 accuracy up, not exact accuracy.
- n=10 is tiny, so one class is worth 10 percentage points. Treat these numbers as a sanity check, not a benchmark.
- Folder labels are coarse, and 'weak' vs 'quality issue' differ in kind: one is pedagogy, the other AV/camera.
- The keyword features are English-centric. The Malayalam demo shows how they degrade.
- The LLM variant was **not evaluated**: no approved provider key (Gemini/OpenAI/Anthropic) was available. Re-run with `python scripts/eval.py --llm` once one is set.
