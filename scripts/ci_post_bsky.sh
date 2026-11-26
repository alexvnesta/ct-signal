#!/usr/bin/env bash
# Post newly published cards to Bluesky. Silent no-op until both secrets
# exist, so the integration can merge before the account does.
set -uo pipefail
[ -z "${BSKY_HANDLE:-}" ] || [ -z "${BSKY_APP_PASSWORD:-}" ] && exit 0
git rev-parse HEAD~1 >/dev/null 2>&1 || exit 0

NEW=$(python3 - <<'PY'
import json, subprocess

cards = json.load(open("output/cards.json"))["cards"]
cur = {c["id"]: (c.get("answer_values") or {}).get("date") for c in cards}
old = subprocess.run(["git", "show", "HEAD~1:output/cards.json"],
                     capture_output=True, text=True).stdout
try:
    prev = {c["id"]: (c.get("answer_values") or {}).get("date")
            for c in json.loads(old)["cards"]}
except Exception:
    # No previous cards.json in history (first push after the file shipped):
    # post nothing rather than dumping the whole backlog at the audience.
    prev = cur

def ct_trigger(c):
    h = c.get("headline") or {}
    return (c.get("stream") == "ct" or h.get("stream") == "ct"
            or int(h.get("ct_hits") or 0) >= 2)

def notable_weather(c):
    # The weather card is refreshed every day. A 4°F daily wobble is not news
    # worth the feed; only a genuinely large anomaly earns a post.
    if c.get("topic") != "weather":
        return True
    try:
        return abs(float((c.get("answer_values") or {}).get("value"))) >= 5.0
    except (TypeError, ValueError):
        return False

# New cards and cards whose data date moved. Then throttle: CT triggers first,
# non-weather national/local second, weather last, at most two posts per cycle.
candidates = [c for c in cards
              if c["id"] not in prev or prev[c["id"]] != cur[c["id"]]]
candidates = [c for c in candidates if notable_weather(c)]
candidates = sorted(candidates, key=lambda c: (
    0 if ct_trigger(c) else 1 if c.get("topic") != "weather" else 2))
print(" ".join(c["id"] for c in candidates[:2]))
PY
)
[ -z "$NEW" ] && exit 0

SESS=$(curl -s -X POST https://bsky.social/xrpc/com.atproto.server.createSession \
  -H 'content-type: application/json' \
  -d "{\"identifier\":\"$BSKY_HANDLE\",\"password\":\"$BSKY_APP_PASSWORD\"}")
SID=$(printf '%s' "$SESS" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("accessJwt") or d.get("access_token",""))')
DID=$(printf '%s' "$SESS" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("did",""))')
[ -z "$SID" ] || [ -z "$DID" ] && { echo "bsky: session failed" >&2; exit 0; }

# Same card within 24h is a duplicate, not a fresh signal. Reading our own
# author feed gives the guard without a second state file to keep in sync.
FEED=$(curl -s -H "authorization: Bearer $SID" \
  "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed?actor=$DID&limit=30")
RECENT=$(printf '%s' "$FEED" | python3 -c '
import datetime as dt, json, re, sys
d = json.load(sys.stdin)
cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
ids = set()
for item in d.get("feed", []):
    rec = (item.get("post") or {}).get("record") or {}
    stamp = rec.get("createdAt") or ""
    try:
        when = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        continue
    if when >= cut:
        ids.update(re.findall(r"/story/([0-9a-f]{12})", rec.get("text") or ""))
print(" ".join(sorted(ids)))
')

for ID in $NEW; do
  case " $RECENT " in
    *" $ID "*) echo "bsky skip $ID: already posted in last 24h"; continue ;;
  esac
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
