# Embeddings service (`worker/rater/embeddings.py`)

**Model:** EmbeddingGemma 2 (`google/embeddinggemma-2`, Apache-2.0, 740M; text, image, audio and video in one 768-d space; 8K context). It runs **locally on CPU only**. Recordings and frames never leave the machine. The model weights are downloaded once from Hugging Face.

## Inputs to outputs
| step | detail |
|---|---|
| windows | ~5-min windows (`WINDOW_S=300`); a tail under 1 min is folded into the previous window |
| audio | mono 16 kHz PCM for the window, encoded as `{"audio": array}`. **The shipped processor caps audio at 30 s** (`max_length=480000`, `audio_seq_length=750`) and truncates silently. We raise these to 300 s and 7600 tokens (25 tok/s, within the 8K context). Verified: before the fix, a 30 s clip and a 300 s window gave cos 1.00 |
| video | frames at 0.2 fps (at most 58 per window, 448 px wide), encoded as `{"video": [PIL]}` with `max_soft_tokens=70` per frame (the documented minimum budget) |
| text | the window's anonymised transcript lines, prompt `Document` |
| vectors | MRL-truncated to 256-d, L2-renormalised; bf16 weights (never fp16, per the model card) |

## Uses
- **(a) Evidence-window retrieval.** For each rubric criterion, a fixed query returns the top-2 windows across modalities. The text modality uses the `SearchQuery` prompt; cross-modal queries use plain text. The windows (time range, modality, similarity, anonymised text) go into the judge payload as `EVIDENCE WINDOWS`.
- **(b) Zero-shot rubric probes.** Each probe is a (positive, negative) pair of text descriptions. Its feature is the mean over windows of sim(pos) - sim(neg), with the min also stored. There are six probes: energetic tutor, camera on/face, clean audio, children answering, board teaching, warm rapport. Each is computed per relevant modality. All were declared before the eval and are not tuned.
- **(c) Semantic content coverage.** Each text window is scored against chess topic descriptions and an off-topic description. A window's minutes are split among the topics within 0.02 of the best one, if they beat off-topic by 0.02. The result is stored in `content.semantic`, alongside the keyword map.

## Integration and switches
`analyse(..., use_embeddings=True)` or `RATER_EMBEDDINGS=1` turns the service on. It adds `features.emb`, `evidence_windows` and `content.semantic`. If the dependency is missing, a warning is added and the step is skipped. Dependencies (`requirements-embeddings.txt`) are optional and kept out of the slim worker image and the Vercel function. The default is **off**; adoption is decided by `eval.embed_eval` (see EVAL.md).

## Budget (measured on the build box: 8 CPU, about 5 GB free RAM)
Measured for a 60-min class, bf16, 70 vision tokens, 256-d: see EVAL.md "Embeddings". fp32 peaked at 5.6 GB RSS, over budget. bf16 at 140 vision tokens doubled the video time.

## Eval
`python -m eval.embed_extract`, then `python -m eval.embed_eval`. This runs the nested-LOO ablation (current pool, + probes, probes only), retrieval agreement with keyword evidence against chance, and semantic vs keyword content (VTT/Whisper agreement).
