# Spec: analysis core (`worker/rater`)

## Inputs
- `media_path` (MP4/MOV/MKV/WEBM), and optionally `transcript_text` (VTT, or TXT with `Speaker: text` lines).

## Stages
1. **probe**: ffprobe duration and streams. Reject anything without audio, or longer than 150 minutes.
2. **transcript**: if a VTT is given, parse it (speaker labels taken from the `Name: text` prefix). Otherwise run faster-whisper (`base`, int8, CPU, VAD) on 16 kHz mono audio, chunked in 10-minute windows so progress can be reported.
3. **speaker roles**: with labels, the tutor is the speaker with the most words. Without labels (ASR), each segment gets a heuristic role: the tutor holds the long turns, and short replies after a tutor question count as students. These estimates are marked `estimated`.
4. **anonymise**: the tutor becomes `Tutor` and students become `Student 1..n`. Any name token from the speaker list is scrubbed from the text. Every downstream artefact uses anonymised text only.
5. **text features** (per class, all normalised per minute or as fractions):
   - engagement: student turns/min, distinct students speaking, student coverage (share of speaking students with at least 3 turns), tutor questions/min, tutor talk share
   - rapport/intro: greeting cues and student turns in the first 5 minutes, new-joiner self-introduction prompts, time until the first long tutor explanation
   - energy: praise/encouragement cues per min, exclamations per min, tutor words/min
   - homework/closure: homework cues (anywhere, and in the last 10 minutes), wrap-up cues in the last 5 minutes
   - flow: long silences (gaps over 30 s), the longest gap
   - AV complaints: "can't hear", "not visible", "voice breaking", "network" and similar (excluding mute/unmute)
6. **audio features**: 1 s RMS windows → silence fraction, loudness median, dynamic range, and clipping fraction. A spectral-flatness proxy estimates noisiness.
7. **visual features**: one frame every 15 s at 320 px. Each frame is classified as `screen_share` (high edge density or many distinct colours), `camera_off` (near-uniform dark-grey frame) or `video`. Measured from those:
   - share of each layout
   - brightness in video frames (lighting)
   - face present in video frames (Haar, large faces only)
   - brand-background likelihood (dark background with large bright blocks in the upper half)
   - **tutor camera-off fraction**: camera-off frames that coincide with the tutor speaking, using transcript timestamps
8. **evidence**: rule-tagged, timestamped, anonymised quotes per criterion (at most 8 per criterion).

## Outputs
`Analysis` (pydantic): `meta`, `features{text,audio,visual}`, `evidence{criterion:[{t, speaker, quote}]}`, `transcript_source` (vtt|asr).
Media files, frames and audio are deleted once a job finishes.
