#!/usr/bin/env bash
# Event-day driver: generate cards, then push the feed to GitHub
# (Vercel git integration redeploys automatically on push).
# Usage:
#   ./deploy.sh            # loop: cycle + push every 15 min
#   ./deploy.sh --once     # single cycle + push
#   ./deploy.sh --deploy   # publish current output/ only (used by CI)
#   ./deploy.sh --pin      # snapshot current feed as fixtures/last_feed.json, push
set -euo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python

cycle() {
  $PY run.py --once || echo "WARN: cycle failed, publishing previous feed"
}

deploy() {
  # write_all already regenerates the static pages, feeds (rss/json/sitemap),
  # assets/site.css, and story/ at the repo root. Only the two pipeline
  # intermediates that live in output/ need to be staged at root.
  cp output/index.html output/board.json .
  cp us.json output/us.json
  git add -A
  if git diff --cached --quiet --exit-code; then
    echo "no changes, nothing to push $(date +%H:%M:%S)"
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
  --deploy)
    deploy
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
