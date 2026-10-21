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

## Live demo (transcript-only web version)
**https://humaniti-class-rater.vercel.app**: upload or paste a Zoom VTT / `Speaker: text` TXT transcript, or give a public link to one.
Try it with [`examples/synthetic_class.txt`](examples/synthetic_class.txt), a synthetic class with no real people.

Limits of the web version, which come from the Vercel serverless limits:
- **Transcripts only.** No video, so no Whisper ASR and no camera/face/lighting/audio features. Those need the full local app (`python app.py`). The web rating therefore equals the *transcript-only* variant in [EVAL.md](EVAL.md): 50% exact, 70% within one class.
- Transcripts are capped at 3 MB (requests at about 4.5 MB). Links must be public http(s); private and internal addresses are refused. Requests time out after 60 s.
- Uses the local rubric scorer. The LLM judge switches on automatically when `OPENROUTER_API_KEY` is set in the Vercel project's environment.
- Nothing is stored; transcripts are processed in memory.

The full app (`app.py`, Gradio) accepts an **MP4 upload, a transcript upload, or a link to either**. `scripts/serve_share.sh` runs it under a restart loop with a Gradio share link and writes the URL to `share_url.txt`.

## How it works
1. **Local media processing:** ffmpeg, OpenCV and faster-whisper run on CPU. Audio is turned into a transcript, using the uploaded VTT if there is one, and also into loudness and silence stats. Frames are sampled every 20 s to measure tutor face visibility, brightness and camera-off streaks.
2. **Transcript features** (`classq/transcript.py`): tutor talk share, student turns/min, questions/min, students addressed by name, greeting and rapport cues in the first 5 minutes, new-joiner introductions, homework, wrap-up, praise/min, AV complaints, long silences, and time to the first content.
3. **Rubric** (`classq/rubric.py`): seven themes taken from the organiser's tutor feedback (rapport/intro, individual engagement, energy, homework/conclusion, camera/face/lighting, AV quality, teaching aids). A deterministic scorer maps the features to 0–1 theme scores, then to an overall score, then to a label using ordinal cut-points.
4. **LLM judgement (optional)** (`classq/llm.py`): OpenRouter receives **text only**: anonymised transcript lines with names replaced by Tutor/StudentN, plus the numeric features. It returns JSON with a label, theme scores, strengths and improvements, each with a timestamp. If the LLM is unavailable, the app falls back to the local scorer.

**Privacy:** no video, audio or frames leave the machine or Space. Recordings, transcripts, frames and the feature cache are git-ignored. Uploads are not stored.

## Run locally
```bash
sudo apt-get install ffmpeg
pip install -r requirements-full.txt   # requirements.txt is the slim Vercel set
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
