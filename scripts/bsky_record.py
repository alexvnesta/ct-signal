"""Build one Bluesky createRecord payload for a freshly published card.

stdin: cards.json (HEAD version); env: ID (card id), BSKY_DID, OUT (path).
Voice rule: the post states the answer, links the receipts, adds nothing.
"""
import datetime
import json
import os
import sys

card = next(c for c in json.load(sys.stdin)["cards"]
            if c["id"] == os.environ["ID"])
url = f"https://ctsignal.org/story/{card['id']}"
text = (f"{card['question']}\n\n{card['answer_text']}\n\n{url}\n"
        "Every number fetched, never typed — sources on the page.")
if len(text) > 300:
    text = text[:297] + "..."
rec = {
    "repo": os.environ["BSKY_DID"],
    "collection": "app.bsky.feed.post",
    "record": {
        "text": text,
        "createdAt": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "embed": {"$type": "app.bsky.embed.external", "external": {
            "uri": url, "title": card["question"],
            "description": card["answer_text"][:200]}},
    },
}
json.dump(rec, open(os.environ.get("OUT", "/tmp/bsky_rec.json"), "w"))
