#!/usr/bin/env bash
# One-shot worker deploy to Modal + wire the Vercel frontend to it.
# Needs: MODAL_TOKEN_ID, MODAL_TOKEN_SECRET, VERCEL_TOKEN. Optional: OPENROUTER_API_KEY, RATER_OPENROUTER_MODEL,
# RATER_OPENROUTER_FALLBACK_MODEL, RATER_API_KEY. Never echoes secrets.
set -euo pipefail
cd "$(dirname "$0")/../worker"
: "${MODAL_TOKEN_ID:?set MODAL_TOKEN_ID}"; : "${MODAL_TOKEN_SECRET:?set MODAL_TOKEN_SECRET}"
WEB_ORIGIN="${WEB_ORIGIN:-https://humaniti-class-rater-web.vercel.app}"
args=(RATER_ALLOWED_ORIGINS="$WEB_ORIGIN")
for v in OPENROUTER_API_KEY RATER_OPENROUTER_MODEL RATER_OPENROUTER_FALLBACK_MODEL RATER_API_KEY; do
  [ -n "${!v:-}" ] && args+=("$v=${!v}")
done
modal secret create --force rater-secrets "${args[@]}" >/dev/null
url=$(modal deploy modal_app.py 2>&1 | tee /dev/stderr | grep -oE 'https://[a-z0-9-]+\.modal\.run' | head -1)
[ -n "$url" ] || { echo "deploy failed: no URL"; exit 1; }
curl -fsS "$url/health" && echo
cd ../web
printf '%s' "$url" | vercel env add NEXT_PUBLIC_WORKER_URL production --force --token "$VERCEL_TOKEN" >/dev/null
vercel deploy --prod --yes --token "$VERCEL_TOKEN" >/dev/null
echo "worker: $url   web: $WEB_ORIGIN (now uses the worker for MP4 upload/link)"
