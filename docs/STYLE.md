# House style for generated prose

Card answers are template-composed, so the templates carry the whole voice.
These rules come from the `no-ai-slop` editing skill (Peter Yang,
github.com/petergyang/no-ai-slop) distilled to the patterns that apply to a
data desk, and they are enforced by `tests/test_prose_slop.py`.

## The rules that bit us at launch

- **No definition footnotes in prose.** `(50 states, DC and Puerto Rico)`
  sat at the end of every comparison answer — six copies, one of them
  contradicting its own count. Define the peer set once, in the board legend.
- **No em-dash tails.** Six answers ending ` — the Nth-highest…` is robotic
  rhythm. Wire style: comma, then the rank clause.
- **One terminal period.** The JSON-feed builder appended `.` to answers
  that already ended in `.`; RSS readers saw `.. Triggered by:`.
- **Say the verb.** "X posted the fastest growth, adding $Y of the N towns
  measured" was ungrammatical; "X led the N towns measured…, adding $Y" is
  not.
- **Concrete beats defined-jargon.** "peers" survives only because the
  legend defines it on the page where the chips appear; portability test —
  a sentence that could move to any report unchanged is filler.

## For hand-written copy (about, masthead, digest, marketing)

Lead with the state, not the pipeline ("Know where you live"). Active voice;
"is/has" when clearer than a fake-strong verb. No banned-phrase list is ever
a license to add synonyms for style — if the plain word is right, repeat it.
Distinctive rough edges stay: "a one-person newsroom with a heartbeat" is a
human aside, not polish.
