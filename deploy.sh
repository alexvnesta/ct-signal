#!/usr/bin/env bash
# Event-day driver: run one pipeline cycle, then push the generated site to
# GitHub (Vercel git integration treats the push as the deploy).
#
# Standing heartbeat: the `pulse` GitHub Action (CI is the single producer).
# This script is for event-day overdrive from a workstation and for the CI
# publish step (--deploy). Rules learned the hard way:
#   - never publish a failed cycle (a half-generated tree must not deploy);
#   - always pull --rebase before push and retry (CI and humans share master);
#   - commit only generated paths, under the bot identity, so human edits are
#     never swept into a "feed:" commit and provenance stays honest.
# Usage:
#   ./deploy.sh            # loop: cycle + push every 15 min (event days)
#   ./deploy.sh --once     # single cycle + push
#   ./deploy.sh --deploy   # publish current output/ only (used by CI)
#   ./deploy.sh --pin      # snapshot current feed as fixtures/last_feed.json
set -uo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python
LOG=.pulse.log
GEN=(index.html board.json feed.json feed.xml sitemap.xml llms.txt us.json
     methodology.html sources.html
     assets story topic town archive output/cards.json output/index.html
     output/board.json output/us.json output/digest data/asked_log.json
     data/failures.log data/validation_report.json)

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" | tee -a "$LOG"; }
rotate() { if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 200000 ]; then
  tail -n 2000 "$LOG" > "$LOG.t" && mv "$LOG.t" "$LOG"; fi; }

bot() { git -c user.name=ct-signal-bot -c user.email=bot@ctsignal.org "$@"; }

sync_push() {  # rebase onto whatever landed meanwhile, retry a few times
  local try
  for try in 1 2 3; do
    if git pull --rebase --autostash -q origin master \
       && git push -q origin master; then
      return 0
    fi
    git rebase --abort 2>/dev/null || true
    sleep $((try * 5))
  done
  return 1
}

publish() {
  cp output/index.html output/board.json .
  cp us.json output/us.json
  local EXIST=()
  for f in "${GEN[@]}"; do [[ -e "$f" ]] && EXIST+=("$f"); done
  bot add -A -- "${EXIST[@]}" || { log "ADD FAILED — not publishing blind"; return 1; }
  if bot diff --cached --quiet --exit-code; then
    log "no changes, nothing to push $(date +%H:%M:%S)"
    return 0
  fi
  bot commit -q -m "feed: $(date +%H:%M) card refresh"
  if sync_push; then
    log "pushed $(date +%H:%M:%S) — vercel will redeploy"
  else
    log "PUSH FAILED after 3 tries — commit stays local, next cycle retries"
    return 1
  fi
}

cycle() {
  rotate
  if $PY run.py --once >> "$LOG" 2>&1; then
    publish
  else
    log "CYCLE FAILED — previous site stays published (see $LOG)"
    bot add -A -- data/failures.log 2>/dev/null || true
    if ! bot diff --cached --quiet --exit-code; then
      bot commit -q -m "pulse: cycle failure logged $(date +%H:%M)"
      sync_push || log "failure-log push failed too"
    fi
    return 1
  fi
}

case "${1:-loop}" in
  --once)   cycle ;;
  --deploy) publish ;;
  --pin)
    cp output/cards.json fixtures/last_feed.json
    [ -f output/us.json ] || cp us.json output/us.json
    bot add -A -- fixtures/last_feed.json output/us.json
    if ! bot diff --cached --quiet --exit-code; then
      bot commit -q -m "pin feed snapshot $(date +%H:%M)"
      sync_push && log "feed pinned + pushed"
    else
      log "pin unchanged"
    fi
    ;;
  *)  while true; do cycle; sleep 900; done ;;
esac
