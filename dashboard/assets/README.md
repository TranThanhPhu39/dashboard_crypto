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
