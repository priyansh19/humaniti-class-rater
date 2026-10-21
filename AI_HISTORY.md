# AI interaction history (sanitized)

I built this with an AI agent assistant (Grok Bot) running on a private Linux box. Below is a condensed, sanitized log of the prompts and the main decisions. Credentials, personal details, and **all tutor and student names** are removed, and recordings are referred to by folder and batch code only.

## 1. Survey
**Prompt (me):** "Survey the challenge folder: read the brief, list files, ffprobe the 12 MP4s, read the VTTs, extract feedbacks.pdf and work out the ground-truth label and reasons for each recording, check tooling, and write NOTES.md with a plan. Recordings are confidential: don't upload them."
**AI actions:** ran `pdftotext` on the brief and feedback, `ffprobe` on each video (37–89 min, 1080p), and counted speakers in the VTTs. It noticed that the Zoom VTTs carry speaker names, which gives cheap tutor/student attribution but also means they are PII. It distilled seven rubric themes from the feedback and observed that "kept background" appears for nearly every class, so it is a basic check rather than a differentiator. It proposed mapping both *weak* and *quality issue* to Poor.

## 2. Plan refinement
**Prompt (me):** approved the plan: local transcription and frames; text-only LLM via OpenRouter; LOO eval plus a transcript-only vs multimodal ablation; Gradio on an HF Space.

## 3. Build
**Prompt (me):** "Build the app locally, install faster-whisper on CPU, write the transcript and frame features, score with OpenRouter (text only; check the key with a tiny call first), build a Gradio UI, add tests, run LOO eval and the ablation, and write README/EVAL/explanation/AI history. Keep media and names out of git."
**AI actions and debugging:**
- A 3-token OpenRouter ping returned **401 "API key expired"**. The AI kept the LLM path and added a deterministic local rubric scorer as an automatic fallback.
- OpenCV 5.0 had dropped `CascadeClassifier`, so the frame step crashed. It pinned `opencv-python-headless<5`.
- Demo transcripts were not matched to their videos, so it fixed the matching to work by language.
- First LOO result: 40% exact (transcript-only) and 30% (multimodal). It inspected the per-class features and found that student turns/min and long silences separate the tiers, that the AV regex counted "unmute" (which is common in *interactive* classes), and that Haar face detection is near-useless on gallery layouts. It re-weighted the themes, tightened the AV regex, and down-weighted visuals. The new result was 50% exact and 80% within one class (multimodal). This post-hoc tuning is disclosed in EVAL.md.
- Added a name anonymiser (speaker → Tutor/StudentN, name tokens scrubbed from the text) and a test that names never reach the LLM prompt.

## 4. Deploy
**Prompt (me):** provided working GitHub and HF tokens, and asked for the public repo `humaniti-class-rater` and an HF Space of the same name with `OPENROUTER_API_KEY` set as a Space secret. The AI pushed only code and docs; `.gitignore` excludes mp4/vtt/frames/cache/.env.

## 5. Client constraints update
**Prompt (me):** the client said the approved LLM services are the OpenAI, Gemini and Anthropic APIs, or fully local; OpenRouter is not approved. Mapping weak/quality-issue to Poor is OK if explained. Testers will upload or link full-length recordings.
**AI actions:** replaced the OpenRouter client with a provider-pluggable judge (Gemini → OpenAI → Anthropic, auto-detected from env keys, plain REST, text only), with mocked tests for each provider and a test that an OpenRouter key alone does *not* enable the LLM. Attempted a free Docker Space for the full MP4 app.
