# Guardrails spec (`rater/guardrails.py`)

Input validation that runs before scoring, in both the worker and the hosted API. Hard failures raise `GuardError(code, message)`, which the API returns as HTTP 422 `{error: code, detail: message}`. Soft problems return flags, cap the confidence and add a plain-English warning.

| Case | Code | Behaviour |
|---|---|---|
| Empty or whitespace input | `empty` | reject |
| More than 3,000,000 characters (hosted: the `max_chars` cap) | `too_large` | reject |
| NUL bytes or binary content | `binary` | reject |
| Mostly non-word characters | `garbled` | reject |
| Fewer than 15 words | `too_short` | reject |
| Non-Latin script | `non_english` | flag; confidence cap 0.3 |
| Low English share | `non_english` | flag; confidence cap 0.35 (garbled if extreme) |
| No speaker labels | `no_speakers` | flag; confidence cap 0.6; tutor role inferred |
| Class under 10 minutes or fewer than 3 utterances | `short_class` | flag; confidence cap 0.4 |
| Bad link: non-http(s), private IP, over 2,048 characters, redirect, non-200, HTML, over 5 MB | `bad_link` | reject |
| Video or audio link on the hosted service | `video_needs_worker` | reject with guidance |
| Judge failure (any provider error) | n/a | falls back to the local scorer; `judge` reports `local` and a warning is added |

The client mirrors these checks in `web/lib/validate.ts` for instant feedback: file types, the 5 MB transcript cap, the 2 GB video cap, the video-needs-worker case, and URL checks. The server stays authoritative.

Tests: `worker/tests/test_guardrails.py` (36 tests) and `web/tests/app-v3.test.ts`.
