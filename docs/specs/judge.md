# Spec: judge (`worker/rater/judge`)

## Rubric (derived from feedbacks.pdf, nothing invented)
| key | criterion | feedback phrases it covers |
|---|---|---|
| `rapport` | Intro & rapport | "good rapport building", "good intro", "directly entered into class without proper rapport building", "should give a time for the new joiners for self-introduction", "need a better intro and conclusion" |
| `individual_attention` | Individual attention | "asked questions by calling individually", "consider everyone in the class", "one-to-one interaction" |
| `energy` | Energy & pleasant interaction | "need more energetic communication", "need more pleasant interaction", "need a good happier communication" |
| `homework_closure` | Homework & conclusion | "given HWs", "should give HWs", "need a better… conclusion" |
| `presentation` | Camera, face, background, lighting | "kept 8*8 background", "no background", "can't see his face", "tutor's camera was turned off", "can sit in space where have light", "clarity issues… while keeping the background" |
| `av_quality` | AV / technical quality | "informed about the quality issues several times" |
| `teaching_aids` | Teaching aids (bonus) | "can play topic related videos", "puzzles solving time" |

## Interface
`judge(analysis, provider="auto") -> Report`. The report has:
- `label` (Poor|Average|Good|Excellent), `confidence`, `summary`
- `criteria[key] = {score 1-5, rationale, evidence:[{t, quote}]}`
- `strengths[]`, `improvements[]` (each actionable, citing a timestamp or a feature)
- `judge` (provider:model or `local`), and `warnings[]`

## Providers
Auto-detected: `GEMINI_API_KEY`/`GOOGLE_API_KEY` → Gemini (`gemini-2.5-flash`, `responseSchema`), `OPENAI_API_KEY` → OpenAI (`json_schema` strict), `ANTHROPIC_API_KEY` → Anthropic (tool-use with an input schema). The provider can be overridden with `RATER_LLM_PROVIDER` and `RATER_LLM_MODEL`.
The payload holds the anonymised evidence quotes, transcript excerpts (opening, closing and a sample from the middle), numeric features, and the local scorer's per-criterion estimates. **It never contains media, names or raw audio.** Responses are validated against the pydantic schema. One repair retry is allowed, then the judge falls back to local.

## Local scorer (always runs; it is the fallback and the eval baseline)
- Each criterion score (1–5) is a fixed monotone mapping of its features, specified here before the eval.
- The overall label comes from an ordinal model on the criterion scores. Its parameters are fitted only on the training folds during eval, and on all 10 classes for the shipped model.
- The scorer generates the rationale text from templates over the features and evidence.
