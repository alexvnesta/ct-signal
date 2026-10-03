#!/usr/bin/env bash
# Post newly published cards to Bluesky. Silent no-op until both secrets
# exist, so the integration can merge before the account does.
set -uo pipefail
[ -z "${BSKY_HANDLE:-}" ] || [ -z "${BSKY_APP_PASSWORD:-}" ] && exit 0
git rev-parse HEAD~1 >/dev/null 2>&1 || exit 0

NEW=$(python3 - <<'PY'
import json, subprocess
cur = {c["id"]: (c.get("answer_values") or {}).get("date")
       for c in json.load(open("output/cards.json"))["cards"]}
old = subprocess.run(["git", "show", "HEAD~1:output/cards.json"],
                     capture_output=True, text=True).stdout
try:
    prev = {c["id"]: (c.get("answer_values") or {}).get("date")
            for c in json.loads(old)["cards"]}
except Exception:
    # No previous cards.json in history (first push after the file shipped):
    # post nothing rather than dumping the whole backlog at the audience.
    prev = cur
# Post new cards and cards whose data date moved: a revalidated number is
# worth telling people about ("the rent card just ticked to the 2024 print"),
# and an updated card keeps its id, so an id-only diff would never show it.
print(" ".join(i for i, d in cur.items() if i not in prev or prev[i] != d))
PY
)
[ -z "$NEW" ] && exit 0

SESS=$(curl -s -X POST https://bsky.social/xrpc/com.atproto.server.createSession \
  -H 'content-type: application/json' \
  -d "{\"identifier\":\"$BSKY_HANDLE\",\"password\":\"$BSKY_APP_PASSWORD\"}")
SID=$(printf '%s' "$SESS" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("accessJwt") or d.get("access_token",""))')
DID=$(printf '%s' "$SESS" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("did",""))')
[ -z "$SID" ] || [ -z "$DID" ] && { echo "bsky: session failed" >&2; exit 0; }

for ID in $NEW; do
  git show "HEAD:output/cards.json" \
    | ID="$ID" BSKY_DID="$DID" OUT="/tmp/bsky_rec_$ID.json" \
      python3 scripts/bsky_record.py \
  && curl -s -o /dev/null -w "bsky post $ID: %{http_code}\n" \
       -X POST https://bsky.social/xrpc/com.atproto.repo.createRecord \
       -H "authorization: Bearer $SID" -H 'content-type: application/json' \
       --data @"/tmp/bsky_rec_$ID.json"
done
