# Art sources

Hero artworks were generated with free community-GPU diffusion inference
(Stable Horde, SDXL-class models, anonymous worker pool) and are treated as
unencumbered outputs; each was then duotoned and re-composed in `make_assets.py`
so every pixel that ships also passes through our own tooling.

- `hero-waveform.webp`  → OG cover and social cards
- `hero-skyline.webp`   → profile banner art
- `hero-contours.webp`  → digest email header band

`scripts/ct_poly.json`: Connecticut outline extracted from Natural Earth 10m
admin-1 boundaries (public domain, ne_10m_admin_1_states_provinces).
