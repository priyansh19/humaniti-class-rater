#!/usr/bin/env bash
# Vendors the media-free part of the worker's rater package into web/api/rater for the Vercel Python fallback.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"; src="$here/../worker/rater"; dst="$here/api/rater"
rm -rf "$dst"; mkdir -p "$dst/judge"
cp "$src"/{__init__,models,transcript,text_features,evidence,analysis,audio,visual,media}.py "$dst/"
cp "$src"/judge/*.py "$dst/judge/"
[ -f "$src/judge/model.json" ] && cp "$src/judge/model.json" "$dst/judge/"
cp "$src/api/ingest.py" "$dst/api_ingest_lite.py"
echo "synced rater core -> api/rater"
