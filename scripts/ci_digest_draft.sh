#!/usr/bin/env bash
# When the weekly digest changes, file it with Buttondown as a DRAFT
# (never auto-send: a human presses send). No-op without BUTTONDOWN_KEY.
set -uo pipefail
[ -z "${BUTTONDOWN_KEY:-}" ] && exit 0
git rev-parse HEAD~1 >/dev/null 2>&1 || exit 0
FILE=$(git diff HEAD~1 HEAD --name-only | grep -m1 '^output/digest/.*\.html$' || true)
[ -z "$FILE" ] && exit 0
WEEK=$(basename "$FILE" .html)
python3 - "$FILE" "$WEEK" <<'PY'
import json, sys, urllib.request
body = open(sys.argv[1]).read()
payload = {
    "subject": f"CT Signal weekly board — {sys.argv[2]}",
    "body_html": body,
    "tags": ["digest"],
    "unpublished": True,          # draft; human reviews and sends
}
req = urllib.request.Request(
    "https://api.buttondown.com/v1/emails",
    data=json.dumps(payload).encode(),
    headers={"Authorization": f"Token {__import__('os').environ['BUTTONDOWN_KEY']}",
             "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        print(f"buttondown draft filed: HTTP {r.status}")
except Exception as exc:
    print(f"buttondown draft failed ({type(exc).__name__}) — will retry next digest",
          file=sys.stderr)
PY
