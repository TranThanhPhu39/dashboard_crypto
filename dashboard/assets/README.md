# Decorative world map

`ne_110m_land.geojson` is Natural Earth 1:110m land geometry, downloaded from the
[Natural Earth vector repository](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson).
Natural Earth data is [public domain](https://www.naturalearthdata.com/about/terms-of-use/).

Pinned SHA-256: `9e0729ee253ca7d7a5c4ae9395fb1902264c5377c52e224d13dd85010e2835d9`.
The committed source is enough to rebuild offline; no runtime request is made.

Run `py -3.11 -X utf8 tools/build_crypto_scenery.py`, then
`py -3.11 -X utf8 tools/refresh_dashboard_design.py` to update the dashboard.
The generator projects coastlines to a decorative equirectangular scene and
excludes Antarctica. The network, hubs and BTC/ETH emblems are decorative;
they do not represent measured transactions, financial flows or research data.
Nine decorative packets follow the same visible curves in native SVG motion,
with staggered 3–5 second trips. Mobile shows four packets. The SVG timeline
pauses when the document is hidden or reduced motion is enabled.
`world-packets.svg` keeps the moving particles in a separate SVG layer from
the static coastline.

## Rubik font

`fonts/rubik-latin-wght.woff2` and `fonts/rubik-latin-ext-wght.woff2` are the
original variable-weight (300–900) normal-style Rubik v31 webfont subsets from
Google Fonts. Sources:
[Latin](https://fonts.gstatic.com/s/rubik/v31/iJWKBXyIfDnIV7nBrXw.woff2),
[Latin extended](https://fonts.gstatic.com/s/rubik/v31/iJWKBXyIfDnIV7nPrXyi0A.woff2).
Their SHA-256 hashes are, respectively:

- `691cd1d9b4c0cdf31a1dcf04259c86f92c85e69f6622abab7964d81e36890691`
- `09472f217ad1ebb61a7669cf532f9f2f80685e07652ee862fde9a79665aef479`

The [Rubik project](https://github.com/googlefonts/rubik) uses the SIL Open Font
License 1.1; the complete notice is in `fonts/Rubik-OFL.txt` and is embedded in
each dashboard HTML alongside the font. The license was obtained from
`google/fonts` commit `8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5`.

`src/dashboard_fonts.py` embeds these files during presentation refresh, so
the offline dashboard and Pages need no remote font requests. Rubik does not
cover every Vietnamese character; the CSS system-font fallback covers missing
glyphs. Text, controls, numbers and SVG labels use the same family stack in
both themes.
