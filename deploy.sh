#!/usr/bin/env bash
# Event-day driver: generate cards, then push the static feed to Vercel.
# Usage:
#   ./deploy.sh            # loop: cycle + deploy every 15 min
#   ./deploy.sh --once     # single cycle + deploy
#   ./deploy.sh --pin      # snapshot current feed as fixtures/last_feed.json, deploy
set -euo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python

cycle() {
  $PY run.py --once || echo "WARN: cycle failed, deploying previous feed"
}

deploy() {
  cp output/index.html output/feed.json .
  vercel deploy --prod --yes && echo "deployed $(date +%H:%M:%S)"
}

case "${1:-loop}" in
  --once)
    cycle; deploy
    ;;
  --pin)
    cp output/feed.json fixtures/last_feed.json
    echo "feed pinned to fixtures/last_feed.json ($(date +%H:%M:%S))"
    deploy
    ;;
  *)
    while true; do
      cycle
      deploy
      sleep 900
    done
    ;;
esac
