# Art sources

The shipping brand art (masthead band, social covers, digest header, story
covers) is drawn by `scripts/_skyline.py`: the Hartford skyline at listed
scale. Every tower is a real building at its published height — the art is
a chart of something. Heights and floor counts from Wikipedia's
"List of tallest buildings in Hartford" (CC BY-SA 4.0); layout follows the
view from the Connecticut River. Lit windows are seeded per building name,
so renders are byte-stable. One row is deliberately unused: the table's
"Travelers Tower" entry contradicts itself on date (1919 vs 2024 prose),
so its 527 ft is unconfirmed and gets no pixels.

Retired diffusion sources (kept for the record; no longer rendered into any
shipping asset): Stable Horde / SDXL anonymous-worker outputs, duotoned in
the old `make_assets.py` pipeline.

- `hero-waveform.webp`  → old OG cover and social cards
- `hero-skyline.webp`   → old profile banner (generic city, unreadable
                          signature glyph — replaced by the drawn skyline)
- `hero-contours.webp`  → old digest email header band

`scripts/ct_poly.json`: Connecticut outline extracted from Natural Earth 10m
admin-1 boundaries (public domain, ne_10m_admin_1_states_provinces).
