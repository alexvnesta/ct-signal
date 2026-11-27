#!/usr/bin/env bash
# Post newly published cards to Bluesky. Silent no-op until both secrets
# exist, so the integration can merge before the account does.
set -uo pipefail
[ -z "${BSKY_HANDLE:-}" ] || [ -z "${BSKY_APP_PASSWORD:-}" ] && exit 0
git rev-parse HEAD~1 >/dev/null 2>&1 || exit 0

SESS=$(curl -s -X POST https://bsky.social/xrpc/com.atproto.server.createSession \
  -H 'content-type: application/json' \
  -d "{\"identifier\":\"$BSKY_HANDLE\",\"password\":\"$BSKY_APP_PASSWORD\"}")
SID=$(printf '%s' "$SESS" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("accessJwt") or d.get("access_token",""))')
DID=$(printf '%s' "$SESS" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("did",""))')
[ -z "$SID" ] || [ -z "$DID" ] && { echo "bsky: session failed" >&2; exit 0; }

# Read our own author feed to enforce 24h per-card dedup, 48h weather cooldown,
# and cross-desk rotation without a separate state file to drift out of sync.
FEED=$(curl -s -H "authorization: Bearer $SID" \
  "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed?actor=$DID&limit=30")

NEW=$(printf '%s' "$FEED" | python3 - <<'PY'
import datetime as dt, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
import select_bsky_posts as sel

cur_cards = json.load(open("output/cards.json"))["cards"]
old = subprocess.run(["git", "show", "HEAD~1:output/cards.json"],
                     capture_output=True, text=True).stdout
try:
    prev_cards = json.loads(old)["cards"]
except Exception:
    prev_cards = cur_cards

by_id = {c["id"]: c for c in cur_cards}
feed = json.load(sys.stdin)
now = dt.datetime.now(dt.timezone.utc)
cut24 = now - dt.timedelta(hours=24)
cut48 = now - dt.timedelta(hours=48)
recent_ids = set()
recent_weather = False
last_topic = None
for item in feed.get("feed", []):
    rec = (item.get("post") or {}).get("record") or {}
    stamp = rec.get("createdAt") or ""
    try:
        when = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        continue
    ids = re.findall(r"/story/([0-9a-f]{12})", rec.get("text") or "")
    for cid in ids:
        topic = (by_id.get(cid) or {}).get("topic")
        if last_topic is None and topic:
            last_topic = topic
        if when >= cut24:
            recent_ids.add(cid)
        if when >= cut48 and topic == "weather":
            recent_weather = True

picked = sel.select_candidates(
    cur_cards, prev_cards,
    recent_ids=recent_ids, last_topic=last_topic,
    recent_weather=recent_weather, limit=2,
)
print(" ".join(c["id"] for c in picked))
PY
)
[ -z "$NEW" ] && exit 0

for ID in $NEW; do
  BLOB_FILE=""
  IMG="assets/share-$ID.png"
  if [ -f "$IMG" ] && [ "$(wc -c < "$IMG")" -lt 1000000 ]; then
    curl -s -X POST https://bsky.social/xrpc/com.atproto.repo.uploadBlob \
      -H "authorization: Bearer $SID" -H 'content-type: image/png' \
      --data-binary @"$IMG" -o "/tmp/bsky_blob_$ID.json"
    if python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if (d.get("blob") or {}).get("ref") else 1)' "/tmp/bsky_blob_$ID.json"; then
      BLOB_FILE="/tmp/bsky_blob_$ID.json"
    fi
  fi
  git show "HEAD:output/cards.json" \
    | ID="$ID" BSKY_DID="$DID" OUT="/tmp/bsky_rec_$ID.json" \
      BSKY_BLOB_FILE="$BLOB_FILE" \
      python3 scripts/bsky_record.py \
  && curl -s -o /dev/null -w "bsky post $ID: %{http_code}\n" \
       -X POST https://bsky.social/xrpc/com.atproto.repo.createRecord \
       -H "authorization: Bearer $SID" -H 'content-type: application/json' \
       --data @"/tmp/bsky_rec_$ID.json"
done
