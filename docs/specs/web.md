# Spec: web (`web/`)

Next.js (App Router, TypeScript) + Tailwind + shadcn-style components. Deployed as a **new** Vercel project (`humaniti-class-rater-web`). The v1 project stays live until this one replaces it.

## Screens
1. **Assess**: a drop zone for the MP4 (plus an optional VTT), or a link field. A worker-status badge shows whether the worker is online or offline.
2. **Progress**: a stage stepper (upload % → queued → transcribing → audio → frames → judging), polling `GET /jobs/{id}` every 3 s. The job id stays in the URL, so a page reload resumes.
3. **Report**:
   - the label badge and a confidence bar
   - a scorecard of the 7 criteria (1–5 with a rationale)
   - a timeline of timestamped evidence quotes
   - strengths and improvements (actionable), plus key metrics
   - the judge used, and warnings
   - JSON download
4. **About**: method, rubric, privacy notes and eval numbers.

## Data flow
- The browser uploads chunks **directly to the worker** (`NEXT_PUBLIC_WORKER_URL`), because Vercel request-body limits rule out proxying video.
- Transcript-only mode (paste or upload a VTT, or a link) goes to the worker's `/assess/transcript`. When no worker is configured, the web shows an explicit offline state and does not fake results.
- Polling uses plain fetch.

## v3 pages

- `/`: Brief mode. Includes the capability banner, and the video tabs are disabled when no worker is available.
- `/advanced`: the config panel, with a brief-vs-custom comparison.
- `/history`: localStorage history (last 20) with export.
- `/status`: capabilities and the missing keys.
- Reports offer JSON and Markdown export and show the guard flags.
- The theme is a multicolour gradient (violet, pink, amber, sky).
