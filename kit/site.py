# Surroundings of the example flat (courtyard side) -> app/site.json (render/apartment.py, render/sun.py). Worked example: location, street and
# building data are anonymised (PIN, OWN_ID); our building is modelled as the developer's U (key plan in the sales PDF) with courtyard, balconies,
# the neighbouring block (Street View) and a planned L block (PDF site key). Rewrite the site-specific parts for a new flat.
# Run: python3 site.py [floor]   (default 4 -> app/site.json; other floor n -> app/site_<n>np.json)
# Sources: site/osm.json (OpenStreetMap via Overpass, ODbL: building footprints + levels, green areas) and
#          site/street_map.png (Google Maps screenshot, 10.7 px/m from its 20 m scale bar: street edges and widths),
#          site/streetview_*.png (Street View, June 2025: storeys and heights of the block opposite, overriding OSM levels).
# Run: python3 site/osm_site.py
import json, math, random

import sys
import os
H = os.path.dirname(os.path.abspath(__file__)) + '/'   # kit root
OUT = H + 'app/' + ('site.json' if len(sys.argv) < 2 or sys.argv[1] == '4' else 'site_%snp.json' % sys.argv[1])
FLOOR = int(sys.argv[1]) if len(sys.argv) > 1 else 4
PIN = (0.0, 0.0)                        # flat (lat, lon), set yours; = map px (563, 318) of the street-map screenshot
PXM = 214 / 20                          # px per metre (20 m scale bar = 214 px)
THETA = 1.34                            # main street edges run 1.34° north of east (line fit, both kerbs, Google map)
FACADE_AZ = round(360 - THETA, 2)       # outward normal of our street facade (azimuth, clockwise from north)
STREET = round(-(0.1 + (FLOOR - 1) * 3.1), 2)   # street level below our floor (4.NP: -9.4)
FLAT_CX, FLAT_CY = 9.0, 4.5                 # plan point inside the flat (distance filters, facade orientation test)
RADIUS = 350                            # m, buildings around the flat
OWN_ID = 0                              # OSM id of our own building (modelled separately), set yours
OWN_FLOORS = 8                          # storeys of our building; our flat is on 4.NP
# heights checked on Street View (June 2025), metres above the street; they replace the OSM-level estimate
HEIGHT_OVERRIDE = {
    # <OSM way id>: (height m, 'source note'),
}

phi = math.radians(PIN[0])
MLAT = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
MLON = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
ct, st = math.cos(math.radians(THETA)), math.sin(math.radians(THETA))
ll2m = lambda lat, lon: ((lon - PIN[1]) * MLON, (lat - PIN[0]) * MLAT)          # metres east / north of the pin
rot = lambda x, y: (x * ct + y * st, -x * st + y * ct)                          # u along the main street (east), v across (north)
gpx = lambda px, py: rot((px - 563) / PXM, (318 - py) / PXM)                   # Google map px -> (u, v)

osm = json.load(open(H + 'site/osm.json'))
own = next((e for e in osm['elements'] if e['id'] == OWN_ID), None)
assert own, 'set PIN and OWN_ID for your building (site/osm.json has no element %d)' % OWN_ID
own_uv = [rot(*ll2m(p['lat'], p['lon'])) for p in own['geometry']]
north = sorted(own_uv, key=lambda p: -p[1])[:2]                                 # the two corners of the street facade
VF = sum(p[1] for p in north) / 2                                               # facade line (outer face)
UW, UE = min(p[0] for p in north), max(p[0] for p in north)
# developer's key plan (PDF, 10.4 px/m when scaled to the OSM length 98 m): street wing 14.9 m deep, west wing 18.0 m wide;
# the flat sits in the inner corner: living room facade = inner face of the street wing, bedroom facade = inner face of the west wing
UI, VI = UW + 18.0, VF - 14.9                                                  # courtyard corner (u, v)
CXP, CYP = 7.585, 6.447                                                         # the same corner in plan (bedroom east / living south outer faces)
P = lambda u, v: (round(u - UI + CXP, 3), round(VI - v + CYP, 3))               # (u, v) -> plan (x east, y south)
X = lambda u: round(u - UI + CXP, 3)
Y = lambda v: round(VI - v + CYP, 3)

# flat location (facade point in front of the flat centre) -> lat/lon for the solar calculation
fu, fv = UI, VI
fx, fy = fu * ct - fv * st, fu * st + fv * ct
LAT, LON = PIN[0] + fy / MLAT, PIN[1] + fx / MLON

# ---- street layout across the main street (v, metres north of the pin line), from the Google map + OSM green strip
V_KERB_S, V_KERB_N = (318 - 345.4) / PXM * ct, (318 - 223.2) / PXM * ct       # carriageway 11.4 m
V_OPP = (318 - 184.7) / PXM * ct                                               # opposite block facade (also in OSM)
V_GREEN = (-13.5, -6.7)                                                         # OSM village_green strip
UH = (gpx(18, 650)[0], gpx(119, 650)[0])                                        # west side-street carriageway (u)
UJ = (gpx(1290, 650)[0], gpx(1462, 650)[0])                                     # east side-street carriageway (u)
SW = 3.0                                                                        # side-street sidewalks
FAR = 420

boxes, polys = [], []
def rect(m, u0, v0, u1, v1, z0, z1):
    (x0, y0), (x1, y1) = P(u0, v0), P(u1, v1)
    boxes.append([m, min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), round(STREET + z0, 3), round(STREET + z1, 3)])
def split(a, b, holes):
    out, cur = [], a
    for h0, h1 in sorted(holes):
        if h1 <= cur or h0 >= b: continue
        if h0 > cur: out.append((cur, h0))
        cur = max(cur, h1)
    if cur < b: out.append((cur, b))
    return out
side = [(UH[0] - SW, UH[1] + SW), (UJ[0] - SW, UJ[1] + SW)]
# carriageways
rect('asphalt', -FAR, V_KERB_S, FAR, V_KERB_N, -0.3, 0)
for a, b in (UH, UJ): rect('asphalt', a, -FAR, b, V_KERB_S, -0.3, 0); rect('asphalt', a, V_KERB_N, b, FAR, -0.3, 0)
# main street: sidewalks, kerbs, green strip, forecourt of our building
for a, b in split(-FAR, FAR, side):
    rect('sidewalk', a, V_GREEN[1], b, V_KERB_S - 0.15, -0.3, 0.15); rect('sidewalk', a, V_KERB_N + 0.15, b, V_OPP, -0.3, 0.15)
    rect('curb', a, V_KERB_S - 0.15, b, V_KERB_S, 0, 0.15); rect('curb', a, V_KERB_N, b, V_KERB_N + 0.15, 0, 0.15)
for a, b in split(UH[1] + SW, UJ[0] - SW, []):
    rect('grass', a, V_GREEN[0], b, V_GREEN[1], -0.3, 0.12); rect('sidewalk', a, VF, b, V_GREEN[0], -0.3, 0.15)
# side-street sidewalks (north and south of the main street)
for a, b in UH, UJ:
    for v0, v1 in ((-FAR, V_KERB_S), (V_KERB_N, FAR)):
        rect('sidewalk', a - SW, v0, a, v1, -0.3, 0.15); rect('sidewalk', b, v0, b + SW, v1, -0.3, 0.15)
# tram tracks (embedded rails, both directions) and the centre line
for vt in (V_KERB_S + 2.85, V_KERB_N - 2.85):
    for dv in (-0.7175, 0.7175):
        for a, b in split(-FAR, FAR, [UH, UJ]): rect('steel', a, vt + dv - 0.035, b, vt + dv + 0.035, -0.01, 0.006)
    rect('black', -FAR, vt - 0.008, FAR, vt + 0.008, 6.0, 6.016)                       # overhead contact wire
u = -FAR
while u < FAR:
    if not any(a - 4 < u < b + 1 for a, b in (UH, UJ)): rect('linemark', u, (V_KERB_S + V_KERB_N) / 2 - 0.06, u + 3, (V_KERB_S + V_KERB_N) / 2 + 0.06, -0.01, 0.004)
    u += 6
# zebra crossings (measured on the map, px): bars 0.5 m wide every 1 m
def zebra_across_u(px0, px1, v0, v1):          # crossing over the main street (bars along u)
    a, b = gpx(px0, 300)[0], gpx(px1, 300)[0]; v = v0 + 0.25
    while v < v1 - 0.25: rect('linemark', a, v, b, v + 0.5, -0.01, 0.005); v += 1.0
def zebra_across_v(py0, py1, u0, u1):          # crossing over a side street (bars along v)
    a, b = gpx(600, py0)[1], gpx(600, py1)[1]; u = u0 + 0.25
    while u < u1 - 0.25: rect('linemark', u, min(a, b), u + 0.5, max(a, b), -0.01, 0.005); u += 1.0
zebra_across_u(150, 192, V_KERB_S, V_KERB_N); zebra_across_u(1240, 1285, V_KERB_S, V_KERB_N)
zebra_across_v(362, 398, *UH); zebra_across_v(180, 215, *UH); zebra_across_v(385, 435, *UJ); zebra_across_v(118, 165, *UJ)
# traffic signals at the east junction
for uu, vv in ((UJ[0] - 1.0, V_KERB_S - 1.0), (UJ[0] - 1.0, V_KERB_N + 1.0), (UJ[1] + 1.0, V_KERB_S - 1.0), (UJ[1] + 1.0, V_KERB_N + 1.0)):
    rect('lampgrey', uu - 0.06, vv - 0.06, uu + 0.06, vv + 0.06, 0.1, 3.4); rect('black', uu - 0.15, vv - 0.15, uu + 0.15, vv + 0.15, 2.4, 3.3)

# ---- buildings from OSM (footprint polygons, extruded to levels x 3.2 m)
def rings(e):
    if e['type'] == 'way': return [e['geometry']]
    segs = [m['geometry'] for m in e.get('members', []) if m.get('role') == 'outer' and m.get('geometry')]
    out = []
    while segs:
        r = segs.pop(0)
        while (r[0]['lat'], r[0]['lon']) != (r[-1]['lat'], r[-1]['lon']):
            k = (r[-1]['lat'], r[-1]['lon'])
            nxt = next((s for s in segs if (s[0]['lat'], s[0]['lon']) == k or (s[-1]['lat'], s[-1]['lon']) == k), None)
            if not nxt: break
            segs.remove(nxt); r = r + (nxt[1:] if (nxt[0]['lat'], nxt[0]['lon']) == k else nxt[::-1][1:])
        out.append(r)
    return out
def num(v, d):
    try: return float(str(v).split()[0])
    except (ValueError, IndexError): return d
def levels(t, area):
    lv = num(t.get('building:levels'), 0)
    flats = num(t.get('building:flats'), 0)
    if flats >= 6 and lv <= 2: lv = 0                 # OSM here has many "1 level" houses with dozens of flats: wrong, estimate below
    if not lv: lv = min(8, max(3, round(flats * 75 / area))) if flats and area > 30 else (3 if area > 60 else 1)
    return lv
def height(e, t, area):
    if e['id'] in HEIGHT_OVERRIDE: return HEIGHT_OVERRIDE[e['id']][0]
    if 'height' in t: return num(t['height'], 10)
    lv = levels(t, area)
    office = t.get('building') in ('office', 'commercial') or 'building:part' in t
    # residential: ground floor 4.0 m + 3.2 m storeys + 0.8 m parapet (1930s houses opposite: 6 storeys = 20.8 m, as on Street View)
    h = lv * 3.6 + 0.8 if office else 4.0 + (lv - 1) * 3.2 + 0.8
    return h + num(t.get('roof:levels'), 0) * 1.6
def inside(pt, poly):
    x, y, c = pt[0], pt[1], False
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i - 1], poly[i]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0): c = not c
    return c
centre = lambda r: (sum(p['lon'] for p in r) / len(r), sum(p['lat'] for p in r) / len(r))
parts = [centre(r) for e in osm['elements'] if 'building:part' in e.get('tags', {}) for r in rings(e)]
buildings, windows = [], []
rnd = random.Random(7)
for e in osm['elements']:
    t = e.get('tags', {})
    if e['id'] == OWN_ID or not ('building' in t or 'building:part' in t): continue
    if 'building:part' not in t and any(inside(c, [(p['lon'], p['lat']) for p in r]) for r in rings(e) for c in parts): continue   # drawn by its parts
    if t.get('building') in ('roof', 'construction') and 'building:levels' not in t: continue
    for r in rings(e):
        pts = [P(*rot(*ll2m(p['lat'], p['lon']))) for p in r]
        if pts[0] == pts[-1]: pts = pts[:-1]
        if len(pts) < 3 or min(math.hypot(x - FLAT_CX, y - FLAT_CY) for x, y in pts) > RADIUS: continue
        area = sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts))) / 2   # shoelace, > 0 = counter-clockwise
        if area < 0: pts.reverse()                                          # counter-clockwise in plan (x, y)
        h = round(height(e, t, abs(area)), 2)
        buildings.append({'p': pts, 'h': h, 'm': len(buildings) % 6, 'n': t.get('name', t.get('addr:housenumber', '')), 'lv': t.get('building:levels', ''),
                          'part': 'building:part' in t, 'id': e['id'], 'osm_h': round(num(t.get('building:levels'), 0) * 3.2 + 0.6, 1)})
# site key in the developer PDF (src/site_key.png px) -> (u, v): affine through three own-building corners (NW, NE, SW); SE checks the fit
KEY = {(182, 146): (UW, VF), (449, 177): (UE, VF - 0.12), (171, 244): (UW, -62.7)}
(k1, w1), (k2, w2), (k3, w3) = KEY.items()
det = (k2[0] - k1[0]) * (k3[1] - k1[1]) - (k3[0] - k1[0]) * (k2[1] - k1[1])
def key_uv(px, py):
    a = ((px - k1[0]) * (k3[1] - k1[1]) - (k3[0] - k1[0]) * (py - k1[1])) / det
    b = ((k2[0] - k1[0]) * (py - k1[1]) - (px - k1[0]) * (k2[1] - k1[1])) / det
    return tuple(w1[i] + a * (w2[i] - w1[i]) + b * (w3[i] - w1[i]) for i in (0, 1))
print('key fit: own building SE corner %s vs OSM (59.5, -60.3)' % [round(c, 1) for c in key_uv(430, 266)])
# planned L block along the east and north streets (not in OSM, a vacant fenced lot on Street View May 2024): height assumed = 8 storeys
LPLAN = [P(*key_uv(*k)) for k in ((380, 268), (430, 266), (383, 495), (225, 477), (229, 437), (343, 438))]
area = sum(LPLAN[i - 1][0] * LPLAN[i][1] - LPLAN[i][0] * LPLAN[i - 1][1] for i in range(len(LPLAN))) / 2
buildings.append({'p': LPLAN if area > 0 else LPLAN[::-1], 'h': 27.2, 'm': 2, 'n': 'planned L block', 'lv': '8?', 'part': False, 'id': 0, 'osm_h': 0, 'planned': True})

for b in buildings:   # window panes on facades within 160 m that face the flat (not on party walls)
    pts, h = b['p'], b['h']
    if min(math.hypot(x - FLAT_CX, y - FLAT_CY) for x, y in pts) > 160 or b['part']: continue
    for i in range(len(pts)):
        (x0, y0), (x1, y1) = pts[i - 1], pts[i]
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 4: continue
        nx, ny = (y1 - y0) / L, -(x1 - x0) / L                         # outward normal
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        if nx * (FLAT_CX - mx) + ny * (FLAT_CY - my) < 0.25 * math.hypot(FLAT_CX - mx, FLAT_CY - my): continue
        if any(o is not b and inside((mx + nx * 0.6, my + ny * 0.6), o['p']) for o in buildings): continue
        nfl = max(1, int((h - 1.5) // 3.2))
        for k in range(1, nfl) if nfl > 1 else [0]:
            z = STREET + 0.1 + k * 3.2 + 0.9
            s = 1.0
            while s + 1.4 <= L - 0.6:
                fa, fb = s / L, (s + 1.4) / L
                windows.append(['winLit' if rnd.random() < 0.13 else 'win', round(x0 + (x1 - x0) * fa + nx * 0.02, 3), round(y0 + (y1 - y0) * fa + ny * 0.02, 3),
                                round(x0 + (x1 - x0) * fb + nx * 0.02, 3), round(y0 + (y1 - y0) * fb + ny * 0.02, 3), round(z, 2), round(z + 1.6, 2)])
                s += 2.8

# green areas from OSM (park east of the east street, strips) as flat patches
for e in osm['elements']:
    t = e.get('tags', {})
    if not (t.get('landuse') in ('grass', 'village_green') or t.get('leisure') == 'park'): continue
    for r in rings(e):
        pts = [P(*rot(*ll2m(p['lat'], p['lon']))) for p in r][:-1]
        if len(pts) >= 3 and min(math.hypot(x - FLAT_CX, y - FLAT_CY) for x, y in pts) < RADIUS:
            area = sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts))) / 2   # shoelace, > 0 = counter-clockwise
            polys.append(['grass', round(STREET + 0.125 + 0.0006 * len(polys), 4), pts if area > 0 else pts[::-1]])   # distinct z: no coplanar overlaps

# ---- street furniture (deterministic): trees in the green strip, lamps, cars, benches, people
trees, lamps, cars, benches, people = [], [], [], [], []
yg0, yg1 = Y(V_GREEN[1]), Y(V_GREEN[0])
x = X(UH[1] + SW) + 4
while x < X(UJ[0] - SW) - 3:
    trees.append([round(x + rnd.uniform(-1, 1), 2), round(rnd.uniform(yg0 + 1.6, yg1 - 1.6), 2), round(rnd.uniform(7, 10), 2)]); x += rnd.uniform(7.5, 10)
x = -FAR + 20
while x < FAR - 20:
    if not any(X(a) - 6 < x < X(b) + 6 for a, b in (UH, UJ)): lamps.append([x, Y(V_KERB_S - 0.6), -1])
    x += 24
for i, (cx, lane) in enumerate(((-30, 0), (-8, 1), (16, 0), (33, 1), (-48, 1), (42, 0), (95, 0), (-90, 1))):
    cars.append([cx, round(Y(V_KERB_S + 2.85) if lane == 0 else Y(V_KERB_N - 2.85), 2), i % 5, 'x'])
for i, vv in enumerate((V_KERB_N + 8, V_KERB_N + 13.5, V_KERB_N + 19, V_KERB_N + 30, V_KERB_N + 35.5, V_KERB_S - 12, V_KERB_S - 17.5)):   # parked along the west side street
    cars.append([X(UH[0] + 1.1) if i % 2 else X(UH[1] - 1.1), Y(vv), (i + 2) % 5, 'y'])
for bx in (-30, -6, 22, 40):
    benches.append([bx, Y(V_GREEN[0] - 0.6)])
for _ in range(36):
    zone = rnd.random()
    if zone < 0.45: y = rnd.uniform(Y(V_GREEN[1] - 0.6), Y(V_KERB_S + 0.6)); x = rnd.uniform(-60, 75)          # south sidewalk
    elif zone < 0.75: y = rnd.uniform(-1.6, Y(V_GREEN[0] + 1.0)); x = rnd.uniform(X(UH[1] + SW) + 2, X(UJ[0] - SW) - 2)   # forecourt
    else: y = rnd.uniform(Y(V_OPP - 0.6), Y(V_KERB_N + 0.6)); x = rnd.uniform(-60, 75)                     # north sidewalk
    yaw = rnd.choice((0, math.pi)) + rnd.uniform(-0.25, 0.25)
    people.append([round(x, 2), round(y, 2), round(yaw, 3), round(rnd.uniform(1.58, 1.92), 2)])
    if rnd.random() < 0.3:
        people.append([round(x + rnd.uniform(-0.3, 0.3), 2), round(y + 0.55, 2), round(yaw, 3), round(rnd.uniform(1.58, 1.9), 2)])

# ---- our building (developer's key plan, see UI/VI): U footprint, courtyard facades with window panes, balconies; the flat is cut out
UEI = 42.1 + 2.0 * (VI + 58.8) / 20.4                                       # east wing inner face (OSM line 42.1,-58.8 .. 44.1,-38.4) at the street wing's inner face
OWN_U = [(UW, VF), (UW, -62.7), (UI, -62.7), (UI, VI), (UEI, VI), (42.1, -58.8), (59.5, -60.3), (UE, VF - 0.12)]
own_poly = [P(u, v) for u, v in OWN_U]
if sum(own_poly[i - 1][0] * own_poly[i][1] - own_poly[i][0] * own_poly[i - 1][1] for i in range(len(own_poly))) < 0: own_poly.reverse()
FLAT = [(7.119, -0.333), (13.196, -0.333), (13.196, 6.447), (7.585, 6.447), (7.585, 9.377), (-0.387, 9.377), (-0.387, 5.981), (5.521, 5.981), (5.521, 3.65), (7.119, 3.65)]
FL3 = 3.1
ci = min(range(len(own_poly)), key=lambda i: math.dist(own_poly[i], (CXP, CYP)))
notch = [(13.196, CYP), (13.196, -0.333), (7.119, -0.333), (7.119, 3.65), (5.521, 3.65), (5.521, 5.981), (-0.387, 5.981), (-0.387, 9.377), (CXP, 9.377)]
if abs(own_poly[ci - 1][0] - CXP) < 0.01: notch.reverse()          # previous vertex on the west wing face: walk the notch from there
floor_poly = own_poly[:ci] + notch + own_poly[ci + 1:]
own_floors = [round(STREET + 0.1 + k * FL3, 3) for k in range(OWN_FLOORS)]
# courtyard faces, ordered so that (dy, -dx) is the outward normal (as the OSM facades above)
faces = [(P(UEI, VI), P(UI, VI)), (P(UI, VI), P(UI, -62.7)), (P(42.1, -58.8), P(UEI, VI))]
own_windows = []
for (x0, y0), (x1, y1) in faces:
    L = math.hypot(x1 - x0, y1 - y0); nx, ny = (y1 - y0) / L, -(x1 - x0) / L
    for zf in own_floors:
        s = 1.0
        while s + 1.4 <= L - 0.6:
            fa, fb = s / L, (s + 1.4) / L
            ax, ay, bx_, by_ = x0 + (x1 - x0) * fa, y0 + (y1 - y0) * fa, x0 + (x1 - x0) * fb, y0 + (y1 - y0) * fb
            ours = abs(zf) < 0.5 and ((abs(ay - CYP) < 0.1 and min(ax, bx_) < 13.4 and max(ax, bx_) > 7.4) or (abs(ax - CXP) < 0.1 and min(ay, by_) < 9.6 and max(ay, by_) > 6.2))
            if not ours:
                own_windows.append(['winLit' if rnd.random() < 0.13 else 'win', round(ax + nx * 0.02, 3), round(ay + ny * 0.02, 3), round(bx_ + nx * 0.02, 3), round(by_ + ny * 0.02, 3), round(zf + 0.1, 2), round(zf + 2.3, 2)])
            s += 3.0
# balconies (plan rect, slab tops, railing): our courtyard side measured on the key plan; neighbouring block's east facade from Street View (every ~6 m, stacked)
balconies = []
for u0, u1 in ((-11.05, -7.1), (-3.55, 0.39), (4.43, 8.37), (12.1, 16.8), (20.5, 24.1), (28.3, 32.1), (36.1, 39.8)):
    (x0, y0), (x1, y1) = P(u0, VI), P(u1, VI - 2.4); balconies.append({'r': [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], 'z': own_floors[1:], 'rail': 'glass', 'wall': '-y'})
for v0, v1 in ((-47.2, -51.2), (-58.7, -62.6)):
    (x0, y0), (x1, y1) = P(UI, v0), P(UI + 2.1, v1); balconies.append({'r': [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], 'z': own_floors[1:], 'rail': 'glass', 'wall': '-x'})
for v0, v1 in ((-46.1, -49.3), (-54.1, -57.6)):
    uf = 42.1 + 2.0 * ((v0 + v1) / 2 + 58.8) / 20.4
    (x0, y0), (x1, y1) = P(uf - 2.2, v0), P(uf, v1); balconies.append({'r': [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], 'z': own_floors[1:], 'rail': 'glass', 'wall': '+x'})
rez_floors = [round(STREET + 4.0 + i * 3.2, 2) for i in range(6)]          # neighbouring block: 4.0 m ground floor, then 3.2 m storeys
v = -71.0
while v > -134:
    (x0, y0), (x1, y1) = P(-17.7, v), P(-17.7 + 1.5, v - 3.0); balconies.append({'r': [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], 'z': rez_floors, 'rail': 'metal', 'wall': '-x'})
    v -= 6.0
# courtyard: lawn between the wings, trees as drawn on the PDF site key (new planting: 6-9 m), a few people and benches
court = [P(UI, VI), P(UEI, VI), P(42.1, -58.8), P(*key_uv(343, 438)), P(*key_uv(229, 437)), P(-17.7, key_uv(229, 437)[1]), P(-17.7, -62.7), P(UI, -62.7)]
if sum(court[i - 1][0] * court[i][1] - court[i][0] * court[i - 1][1] for i in range(len(court))) < 0: court.reverse()
polys.append(['grass', round(STREET + 0.13, 4), [[round(x, 3), round(y, 3)] for x, y in court]])
for kx, ky in ((255, 262), (248, 296), (268, 290), (240, 330), (272, 332), (322, 272), (332, 270), (350, 286), (347, 299), (330, 316), (345, 357),
               (322, 355), (303, 382), (326, 380), (240, 378), (242, 407), (271, 408), (288, 402), (300, 404), (292, 430), (318, 420)):
    x, y = P(*key_uv(kx, ky)); trees.append([round(x, 2), round(y, 2), round(rnd.uniform(6, 9), 2)])
for _ in range(10):
    x, y = P(rnd.uniform(UI + 6, UEI - 6), rnd.uniform(VI - 8, VI - 45))
    people.append([round(x, 2), round(y, 2), round(rnd.uniform(-3.1, 3.1), 3), round(rnd.uniform(1.58, 1.9), 2)])
for u, v in ((5, -55), (15, -55), (25, -70)):
    x, y = P(u, v); benches.append([round(x, 2), round(y, 2)])

site = {
    'note': 'generated by site.py; plan coords of the example flat (x east, y south, z up; our floor z=0, street z=%s, floor %d.NP). '
            'Buildings: OpenStreetMap contributors (ODbL) + developer key plan (own building, planned L block). Street widths: Google map measured at %.1f px/m.' % (STREET, FLOOR, PXM),
    'lat': round(LAT, 6), 'lon': round(LON, 6), 'facade_az': FACADE_AZ, 'street': STREET, 'floor': FLOOR,
    'own': {'poly': own_poly, 'floor_poly': floor_poly, 'floors': OWN_FLOORS, 'fl': FL3, 'top': round(STREET + 0.1 + OWN_FLOORS * FL3, 2), 'flat': FLAT, 'windows': own_windows},
    'balconies': balconies, 'boxes': boxes, 'polys': polys, 'buildings': buildings, 'windows': windows,
    'trees': trees, 'lamps': lamps, 'cars': cars, 'benches': benches, 'people': people,
}
json.dump(site, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print(OUT, 'floor', FLOOR, 'street', STREET, 'flat lat/lon %.6f %.6f  facade az %.2f' % (LAT, LON, FACADE_AZ))
print('courtyard corner u %.2f v %.2f; own building inner faces: street wing y %.2f, west wing x %.2f; neighbouring block east face x %.2f from y %.2f' % (UI, VI, CYP, CXP, X(-17.7), Y(-62.7)))
print('L block (plan):', [tuple(round(c, 1) for c in p) for p in LPLAN])
print(len(buildings), 'buildings', len(windows), 'windows', len(balconies), 'balconies', len(trees), 'trees', len(people), 'people')
