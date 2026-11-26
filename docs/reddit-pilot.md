# Reddit pilot — r/dataisbeautiful

**Status:** ready to post; not posted. Reddit's web UI currently gates the
account behind login/reCAPTCHA and old.reddit.com returns 403, so this packet
is the launch artifact rather than a claimed post.

## Pick

One image post, not a link post. The chart is the product; the site link goes
in the first comment so the post itself reads as OC data viz, not promotion.

- Subreddit: `r/dataisbeautiful`
- Image: `/Users/alex/development/ct-signal/assets/share-0785479c5e31.png`
  (1428×528 PNG, 139,698 bytes, chart title and legend baked in)
- Story: https://ctsignal.org/story/0785479c5e31
- Card id: `0785479c5e31`
- Data date: 2026-11-25 (30-day window ending that day)
- Flair: OC

## Title (copy exactly)

`[OC] Connecticut ran 4.5°F warmer than normal over the past 30 days — daily readings at Bradley Intl and Danbury, each against its own 1991–2020 normals`

Why this title: it states the result first, names both stations so the two
lines are legible without opening the comments, and puts the method in the
title instead of hiding it. It avoids "hottest ever" claims the data does not
support.

## First comment (post immediately after the image)

> Two Connecticut stations — Bradley International (orange) and Danbury
> (gray) — plotted daily against each station's own 1991–2020 normals. The
> 30-day mean anomaly ending Nov 25 was +4.5°F.
>
> Source: NOAA ACIS StnData (`data.rcc-acis.org`), query
> `sid=KBDL,KDXR elems=maxt,mint,pcpn normals=1991-2020`.
> Chart built with Altair/Vega-Lite. Exact query and story:
> https://ctsignal.org/story/0785479c5e31
>
> CT Signal is an automated Connecticut data desk; every figure names its
> public dataset. Corrections are public: https://ctsignal.org/corrections

## Posting mechanics

1. Open https://www.reddit.com/r/dataisbeautiful/submit (logged-in account).
2. Choose **Images & Video**, upload the PNG above.
3. Title: paste the title exactly, including `[OC]`.
4. Post, then immediately add the first comment.
5. Do not cross-post the same image elsewhere on day one. One subreddit,
   one post, one comment — the pilot is about signal, not volume.

## Timing and follow-through

- Prefer a weekday morning US Eastern (about 08:00–10:00 ET), when
  r/dataisbeautiful has fresh eyes. A Friday morning is acceptable; avoid
  dumping it late Thursday night.
- Watch the first 90 minutes for removal/flair requests. If a moderator asks
  for the source in the title, edit the title field only if Reddit allows it;
  otherwise answer in the comment.
- Record the post URL and first-hour score/comments in this file after
  posting, so the next chart can learn from one real audience instead of a
  guess.
- Do not post the next chart until this one has had a day to settle. The
  account is new; cadence beats volume.

## Rule risks to check at post time

- r/dataisbeautiful requires OC and a visible source; the comment supplies
  both. If the subreddit requires the source in the title, prepend
  `Source: NOAA ACIS` before `[OC]`.
- Self-promotion is tolerated when the image is the content, but a bare site
  link is not. Keep the URL in the comment.
- No claimed causation: the chart shows anomaly, not "climate change caused
  this storm." The answer_text stays descriptive.
