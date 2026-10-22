# Spec: worker API (`worker/rater/api`)

FastAPI, single process, with an in-process job queue (one worker thread by default, `RATER_CONCURRENCY`). Job state is persisted in SQLite under `RATER_DATA_DIR`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | `{ok, version, judge, asr_model}` |
| POST | `/uploads` | `{filename, size}` → `{upload_id, chunk_size}` (8 MiB chunks, 2 GiB max) |
| PUT | `/uploads/{id}/chunks/{n}` | raw bytes. Idempotent, so retries are safe |
| POST | `/uploads/{id}/complete` | `{transcript_text?}` → `{job_id}`. Checks that all chunks arrived and assembles the file |
| POST | `/jobs` | `{url, transcript_url?/transcript_text?}` → `{job_id}`. The worker downloads the link (http/https only, private IPs refused, 2 GiB cap). Google Drive share links are normalised |
| GET | `/jobs/{id}` | `{status: queued, running, done or failed; stage; progress 0-1; message; report?}` |
| POST | `/assess/transcript` | synchronous transcript-only assessment (no media) |

Stages reported: `downloading → probing → transcribing → audio → frames → judging → done`.
Limits: 2 GiB per file, at most 150 minutes of media, and 3 queued jobs per client IP. Media is deleted once a job finishes.
CORS: only the web origin(s) in `RATER_ALLOWED_ORIGINS`.
Optional shared secret `RATER_API_KEY` (header `x-rater-key`), sent by the Next.js server-side proxy for JSON calls.

## Deployment
- `modal_app.py`: Modal ASGI app with ffmpeg, the faster-whisper model baked into the image, a Volume for data and a 2-hour timeout. **Not deployed until a Modal token exists and the organiser approves the host (SPEC Q1).**
- `Dockerfile`: the same app for Render or Railway (`uvicorn rater.api.app:app`).
