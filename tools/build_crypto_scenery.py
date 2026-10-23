"""Build the offline decorative SVG from committed Natural Earth land geometry.

This asset contains no research observations or actual transaction flows.
Run: py -3.11 -X utf8 tools/build_crypto_scenery.py
"""
from pathlib import Path
import hashlib
import json
import random

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'dashboard/assets/ne_110m_land.geojson'
SOURCE_HASH = '9e0729ee253ca7d7a5c4ae9395fb1902264c5377c52e224d13dd85010e2835d9'


def project(lon, lat):
    return 800 + lon * 3.9, 465 - lat * 4.5


def point(xy):
    return f'{xy[0]:.1f},{xy[1]:.1f}'


def build():
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_HASH:
        raise ValueError('Decorative coastline source changed; review and pin it first.')
    land = []
    for feature in json.loads(raw)['features']:
        geometry = feature['geometry']
        polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
        for polygon in polygons:
            if max(p[1] for p in polygon[0]) < -60:
                continue  # Antarctica lies outside the decorative scene.
            segments = []
            for ring in polygon:
                segments.append('M' + 'L'.join(point(project(*p[:2])) for p in ring) + 'Z')
            land.append(''.join(segments))

    # Static triangulated texture clipped to the actual coastline.
    rng = random.Random(39)
    grid = [[(85+c*110+rng.uniform(-24,24), 75+r*96+rng.uniform(-20,20))
             for c in range(14)] for r in range(8)]
    mesh = []
    for r, row in enumerate(grid):
        for c, p in enumerate(row):
            targets = []
            if c+1 < len(row):
                targets.append(row[c+1])
            if r+1 < len(grid):
                targets.append(grid[r+1][c])
                if c+1 < len(row):
                    targets.append(grid[r+1][c+1])
            mesh.extend('M'+point(p)+'L'+point(q) for q in targets)

    locations = [(-122.4,37.8),(-74,40.7),(-79.4,43.7),(-0.1,51.5),
                 (8.7,50.1),(2.4,48.9),(-21.9,64.1),(24.9,60.2),
                 (18.4,-33.9),(-46.6,-23.6),(55.3,25.2),(72.9,19.1),
                 (103.8,1.4),(100.5,13.8),(114.2,22.3),(127,37.6),
                 (139.7,35.7),(151.2,-33.9),(106.8,-6.2),(3.4,6.5),
                 (-99.1,19.4),(-70.7,-33.4),(36.8,-1.3),(31.2,30)]
    hubs = [project(*p) for p in locations]
    edges = [(0,1),(0,2),(0,3),(0,16),(0,20),(1,2),(1,3),(1,9),(1,20),
             (2,6),(3,4),(3,5),(3,6),(3,7),(3,10),(3,19),(3,23),(4,7),
             (4,10),(4,14),(5,9),(5,19),(6,7),(7,15),(8,9),(8,12),(8,19),
             (8,22),(9,21),(10,11),(10,12),(10,22),(10,23),(11,12),(11,14),
             (12,13),(12,14),(12,17),(12,18),(13,14),(14,15),(14,16),(14,17),
             (15,16),(16,17),(17,18),(19,22),(20,21),(22,23)]
    links = []
    for a,b in edges:
        p,q = hubs[a],hubs[b]
        rise = min(70, abs(q[0]-p[0])*.11)
        mid = ((p[0]+q[0])/2, (p[1]+q[1])/2-rise)
        links.append('M'+point(p)+'Q'+point(mid)+' '+point(q))
    nodes = ''.join(f'<g transform="translate({point(p)})"><circle class="world-node-halo" r="23"/><circle class="world-node-ring" r="7"/><circle class="world-node-core" r="2.5"/></g>' for p in hubs)
    # Reuse exact visible curves. Native SVG motion needs no per-frame JS loop.
    routes = [0,2,6,7,14,18,30,37,41]
    durations = [3.2,4.4,3.8,4.8,3.5,5.0,4.1,4.6,3.0]
    motion_defs = ''.join(f'<path id="orbitPacketRoute{i}" d="{links[route]}"/>' for i,route in enumerate(routes))
    packets = ''.join(
        f'<g class="world-packet" data-duration="{duration:.1f}" data-route="orbitPacketRoute{i}">'
        '<circle class="world-packet-halo" r="14"/><path class="world-packet-tail" d="M-17 0H-3"/>'
        '<circle class="world-packet-core" r="3.2"/>'
        f'<animateMotion dur="{duration:.1f}s" begin="{-i*.47:.2f}s" repeatCount="indefinite" rotate="auto">'
        f'<mpath href="#orbitPacketRoute{i}"/></animateMotion></g>'
        for i,duration in enumerate(durations))

    svg = '''<svg class="global-map-canvas" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" fill="none" focusable="false" aria-hidden="true">
  <!-- Natural Earth 1:110m land, public domain. See dashboard/assets/README.md. -->
  <defs>
    <linearGradient id="orbitLandDepth" x1="0" y1="0" x2=".7" y2="1"><stop class="land-highlight"/><stop offset=".36" class="land-mid"/><stop offset="1" class="land-depth"/></linearGradient>
    <radialGradient id="orbitOceanHalo"><stop class="ocean-center"/><stop offset="1" stop-color="transparent"/></radialGradient>
    <radialGradient id="orbitNodeGlow"><stop stop-color="#e5fcff" stop-opacity=".9"/><stop offset=".18" stop-color="#71e8ff" stop-opacity=".5"/><stop offset="1" stop-color="#38cfff" stop-opacity="0"/></radialGradient>
    <g id="orbitBitcoinMark"><path d="M-9-15V15M-13-13H2C14-13 14-1 2-1H-9M-9-1H4C17-1 17 13 4 13H-13M-3-20V-13M4-20V-13M-3 13V20M4 13V20"/></g>
    <g id="orbitEthereumMark"><path class="ethereum-upper" d="M0-22 14 0 0 9-14 0Z"/><path class="ethereum-lower" d="M-14 5 0 14 14 5 0 24Z"/></g>
    <path id="orbitLandShape" fill-rule="evenodd" clip-rule="evenodd" d="LAND_PATHS"/>
    <clipPath id="orbitLandClip"><use href="#orbitLandShape" fill="white"/></clipPath>
    <g id="orbitWorldMesh">
      <ellipse class="world-ocean" cx="820" cy="420" rx="770" ry="420"/>
      <use class="world-coast-aura" href="#orbitLandShape"/>
      <use class="world-land" href="#orbitLandShape"/>
      <g clip-path="url(#orbitLandClip)"><path class="world-triangles" d="MESH_PATH"/></g>
      <g class="world-links"><path d="LINK_PATH"/></g>
      <g class="world-nodes">NODES</g>
      <g class="world-coin world-bitcoin" transform="translate(323,339)"><circle class="coin-halo" r="68"/><circle r="46"/><circle class="coin-inner" r="38"/><use class="bitcoin-mark" href="#orbitBitcoinMark"/><text class="crypto-label" y="72">BTC / BITCOIN</text></g>
      <g class="world-coin world-ethereum" transform="translate(1218,401)"><circle class="coin-halo" r="68"/><circle r="46"/><circle class="coin-inner" r="38"/><use href="#orbitEthereumMark"/><text class="crypto-label" y="72">ETH / ETHEREUM</text></g>
      <g class="world-chain" transform="translate(943,662)"><path d="M-40 0H40"/><rect x="-65" y="-20" width="40" height="40" rx="8"/><rect x="-20" y="-20" width="40" height="40" rx="8"/><rect x="25" y="-20" width="40" height="40" rx="8"/><path d="M-53-5-45-10-37-5V5L-45 10-53 5ZM-8-5 0-10 8-5V5L0 10-8 5ZM37-5 45-10 53-5V5L45 10 37 5Z"/></g>
    </g>
  </defs>
  <use href="#orbitWorldMesh"/>
</svg>
'''.replace('LAND_PATHS',''.join(land)).replace('MESH_PATH',''.join(mesh)).replace('LINK_PATH',''.join(links)).replace('NODES',nodes)
    target = ROOT/'dashboard/world-network.svg'
    target.write_text(svg, encoding='utf-8', newline='\n')
    # Keep animated pixels in their own composited SVG, away from the coastline.
    motion = '<svg class="global-map-canvas world-motion-layer" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" fill="none" focusable="false" aria-hidden="true"><defs><radialGradient id="orbitPacketGlow"><stop stop-color="#e5fcff" stop-opacity=".9"/><stop offset=".18" stop-color="#71e8ff" stop-opacity=".5"/><stop offset="1" stop-color="#38cfff" stop-opacity="0"/></radialGradient>'+motion_defs+'</defs><g class="world-packets">'+packets+'</g></svg>\n'
    (ROOT/'dashboard/world-packets.svg').write_text(motion, encoding='utf-8', newline='\n')
    print(f'Built offline coastline scenery: {len(land)} polygons, {len(edges)} links, {len(hubs)} hubs, {target.stat().st_size} bytes.')


if __name__ == '__main__':
    build()
