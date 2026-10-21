---
title: Humaniti Class Rater
emoji: 🎓
colorFrom: indigo
colorTo: green
sdk: gradio
app_file: app.py
pinned: false
---

# 8x8 Class Quality Rater (Humaniti AI build challenge)

Upload an 8x8 kids' online class recording (MP4) and/or its transcript (Zoom VTT or TXT). The app rates the class
**Poor / Average / Good / Excellent** and backs the rating with specific, timestamped evidence.

## How it works
1. **Local media processing:** ffmpeg, OpenCV and faster-whisper run on CPU. Audio is turned into a transcript, using the uploaded VTT if there is one, and also into loudness and silence stats. Frames are sampled every 20 s to measure tutor face visibility, brightness and camera-off streaks.
2. **Transcript features** (`classq/transcript.py`): tutor talk share, student turns/min, questions/min, students addressed by name, greeting and rapport cues in the first 5 minutes, new-joiner introductions, homework, wrap-up, praise/min, AV complaints, long silences, and time to the first content.
3. **Rubric** (`classq/rubric.py`): seven themes taken from the organiser's tutor feedback (rapport/intro, individual engagement, energy, homework/conclusion, camera/face/lighting, AV quality, teaching aids). A deterministic scorer maps the features to 0–1 theme scores, then to an overall score, then to a label using ordinal cut-points.
4. **LLM judgement (optional)** (`classq/llm.py`): OpenRouter receives **text only**: anonymised transcript lines with names replaced by Tutor/StudentN, plus the numeric features. It returns JSON with a label, theme scores, strengths and improvements, each with a timestamp. If the LLM is unavailable, the app falls back to the local scorer.

**Privacy:** no video, audio or frames leave the machine or Space. Recordings, transcripts, frames and the feature cache are git-ignored. Uploads are not stored.

## Run locally
```bash
sudo apt-get install ffmpeg
pip install -r requirements.txt
export OPENROUTER_API_KEY=...          # optional; OPENROUTER_MODEL defaults to openai/gpt-4o-mini
python app.py                          # http://localhost:7860
pytest -q
```

## Reproduce the evaluation (needs the private dataset, not in the repo)
```bash
DATA_DIR="/path/to/class recordings" python scripts/build_features.py   # caches features in cache/ (git-ignored)
python scripts/eval.py          # leave-one-out + ablation -> EVAL.md, classq/cuts.json
python scripts/eval.py --llm    # also evaluate the LLM judge
```
See [EVAL.md](EVAL.md), [EXPLANATION.md](EXPLANATION.md) and [AI_HISTORY.md](AI_HISTORY.md).

## Limitations
There are only 10 labelled examples, so the numbers are only a sanity check. Whisper output has no speaker labels, so the student-level features are weaker when no VTT is supplied. The keyword cues are English-centric. Haar face detection is noisy on Zoom gallery layouts. Processing is CPU-only, so ASR on a 45-minute class takes several minutes; uploading the VTT is much faster.
