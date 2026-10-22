# Hosted API spec (`web/api/index.py` → `rater/hosted.py`)

A Vercel Python function behind the rewrite `/api/py/*`. The rater core is vendored at build time by `scripts/sync-rater.sh` (it runs in `vercel-build`).

## Endpoints

- `GET /api/py/health` returns `{ok, mode, judge, video, embeddings, missing{llm_judge, video_processing, embeddings}}`.
- `POST /api/py/assess` takes `{transcript_text?, transcript_url?, advanced?}` and returns a Report, plus `guard_flags`, `mode` and (when advanced) `custom{label, score, weights, thresholds}`.
- Errors are always JSON `{error, detail}`, with these status codes:

| Status | Meaning |
|---|---|
| 400 | Bad body |
| 422 | Guard or validation failure |
| 429 | Rate limit |
| 502 | Fetch failure |
| 500 | Internal error (no stack trace in the response) |

## AdvancedConfig

| Field | Values | Default | Validation |
|---|---|---|---|
| `provider` | `local`, `auto`, `openrouter`, `openai`, `gemini`, `anthropic` | n/a | must be one of the listed values |
| `thresholds` | 3 numbers | `[2.4, 3.1, 3.8]` | strictly increasing, each within [1, 5] |
| `weights` | criterion key → number | n/a | known criteria only, each within [0, 5], not all zero |
| `embeddings` | bool | n/a | if true on the hosted service, a warning is returned |
| `max_chars` | number | n/a | 1,000 to 1,000,000 |

The custom label is the weighted mean of the criterion scores, mapped through the thresholds. The web preview (`previewLabel`) uses the same formula.

## Limits

Brief allows 30 requests and Advanced 10 requests per 10 minutes per client IP. The limiter is a sliding window per instance, so it is best-effort.

## Capabilities and missing keys

| Capability | Needs |
|---|---|
| LLM judge | A valid `OPENROUTER_API_KEY`, or `OPENAI_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` |
| Video | `MODAL_TOKEN_ID` + `MODAL_TOKEN_SECRET`, organiser approval of Modal, then `NEXT_PUBLIC_WORKER_URL` |
| Embeddings | The worker |
