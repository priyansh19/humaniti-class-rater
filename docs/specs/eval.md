# Spec: evaluation (`worker/eval`)

- **Data:** the 10 labelled classes with the A6 mapping (4 Poor, 2 Average, 2 Good, 2 Excellent). The 2 demo classes are unlabelled robustness checks.
- **Protocol:** leave-one-out. The feature set, the criterion mappings and the model family are frozen in this spec before any eval run. Only the ordinal-model parameters are fitted, on the 9 training classes of each fold.
- **Primary metric:** exact accuracy. Secondary: within-one accuracy, MAE in classes, and a 4×4 confusion matrix.
- **Baselines:** majority class (Poor, 40%), and v1's 50%.
- **Ablations** (same protocol):
  1. transcript-only
  2. transcript + audio
  3. transcript + audio + frames (full)
  4. LLM judge (needs an approved key; zero-shot, so no fitting is involved) vs the local scorer
- **Failure analysis:** for each misclassified class, which criteria disagree with its feedback note.
- **Output:** `docs/EVAL.md`, using anonymised ids (folder plus batch code). No names.
- **Honesty:** with n=10, one class is worth 10 percentage points. Report the numbers as indicative, together with every variant tried.

## Added: model comparison and content coverage
- `eval.llm_eval --tag <model>` runs a zero-shot judge per model (nothing is fitted, so there is no fold leakage). `--repeat N` measures consistency. `eval.compare` scores every tag on the six quality metrics, plus fallbacks and latency, and writes `docs/EVAL_MODELS.md`. Families: open-source (Qwen, Llama, DeepSeek) for development, frontier (GPT, Gemini, Claude via OpenRouter) for final numbers.
- `eval.content_eval` checks (a) agreement with the three content remarks in feedbacks.pdf (`gold.json["_content"]`), and (b) consistency between the VTT and Whisper content maps: subject, top topic, topic-set Jaccard (topics of 1 min or more), and minutes rank correlation.
- Exploratory variant "full + content coverage" is reported separately from the pre-registered variants.
