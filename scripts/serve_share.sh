#!/usr/bin/env bash
# Supervisor: keeps the full Gradio app (share link) alive; logs the share URL to share_url.txt.
cd "$(dirname "$0")/.."
export GRADIO_SHARE=1 PORT=${PORT:-7860} TMPDIR="$PWD/tmp"; mkdir -p tmp logs
while true; do
  ../.venv/bin/python -u app.py > logs/gradio.log 2>&1 &
  pid=$!
  for i in $(seq 1 90); do
    u=$(grep -oE 'https://[a-z0-9]+\.gradio\.live' logs/gradio.log | tail -1)
    [ -n "$u" ] && { echo "$u  $(date '+%F %T %Z')" > share_url.txt; break; }
    sleep 2
  done
  wait $pid
  echo "$(date '+%F %T') app exited ($?), restarting" >> logs/supervisor.log
  sleep 5
done
