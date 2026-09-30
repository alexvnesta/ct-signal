#!/usr/bin/env bash
# Event-day driver: generate cards, then push the feed to GitHub
# (Vercel git integration redeploys automatically on push).
# Usage:
#   ./deploy.sh            # loop: cycle + push every 15 min
#   ./deploy.sh --once     # single cycle + push
#   ./deploy.sh --pin      # snapshot current feed as fixtures/last_feed.json, push
set -euo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python

cycle() {
  $PY run.py --once || echo "WARN: cycle failed, publishing previous feed"
}

deploy() {
  cp output/index.html output/feed.json output/board.json .
  cp us.json output/us.json
  git add index.html feed.json board.json
  if git diff --cached --quiet --exit-code -- index.html feed.json board.json; then
    echo "no card changes, nothing to push $(date +%H:%M:%S)"
    return
  fi
  git commit -q -m "feed: $(date +%H:%M) card refresh"
  git push -q
  echo "pushed $(date +%H:%M:%S) — vercel will redeploy"
}

case "${1:-loop}" in
  --once)
    cycle; deploy
    ;;
  --pin)
    cp output/feed.json fixtures/last_feed.json
    [ -f output/us.json ] || cp us.json output/us.json
    git add fixtures/last_feed.json
    git commit -q -m "pin feed snapshot $(date +%H:%M)" && git push -q
    echo "feed pinned + pushed ($(date +%H:%M:%S))"
    ;;
  *)
    while true; do
      cycle
      deploy
      sleep 900
    done
    ;;
esac
