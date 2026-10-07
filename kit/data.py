# Apartment data for the example flat (2+kk, 4.NP, courtyard side), in plan metres:
# x east (bathroom west wall face = 0), y south (hall north wall face = 0), z up. Same axes as the first flat (x east, y south).
# Source: developer PDF the sales PDF rendered at 300 dpi (src/plan.png, 165.2 px/m from the 0-5 m scale bar).
# Room ids follow the first flat's roles so the same config code works: 1 hall, 2 living + kitchen, 3 bathroom, 4 bedroom, 5 WC.
import json
from PIL import Image

S, OX, OY = 165.2, 118, 128                        # px per metre, origin in plan.png px
M = lambda v, o: round((v - o) / S, 3)
D = lambda xd, yd: (M(xd * 1.23, OX), M(yd * 1.23, OY))   # point read off the 2000 px wide preview of plan.png
def R(x0, y0, x1, y1):                             # rect from preview px
    (a, b), (c, d) = D(x0, y0), D(x1, y1)
    return [a, b, c, d]

# ---- walls: wallmask.png (black walls + grey shafts, opened 11 px) -> rectangles (identical row runs merged)
mask = Image.open('src/wallmask.png').convert('L'); W, H = mask.size; px = mask.load()
def runs(y):
    out, cur = [], None
    for x in range(W):
        if px[x, y] > 128:
            if cur and cur[1] == x - 1: cur[1] = x
            else: cur = [x, x]; out.append(cur)
    return [tuple(c) for c in out]
rects, open_ = [], {}
for y in range(H + 1):
    rs = set(runs(y)) if y < H else set()
    for r in list(open_):
        if r not in rs: rects.append((r[0], open_.pop(r), r[1] + 1, y))
    for r in rs:
        if r not in open_: open_[r] = y
walls = [[M(x0, OX), M(y0, OY), M(x1, OX), M(y1, OY)] for x0, y0, x1, y1 in rects if (x1 - x0) * (y1 - y0) > 40]
walls.append([7.222, 4.649, 7.361, 5.18])          # sliding-door pocket (the slot drawing splits it into thin lines)

rooms = [
    {'id': 1, 'name': 'Vstupní hala', 'en': 'Hall', 'area': 6.2, 'dims': '3.70 × 1.54 m', 'ceil': 2.40, 'rects': [[7.361, 0.0, 11.065, 1.538]], 'floor': 'vinyl', 'opts': ['paint', 'hallrobe']},
    {'id': 2, 'name': 'Obývací pokoj + kk', 'en': 'Living + kitchen', 'area': 27.2, 'dims': '5.60 × 4.28 m', 'ceil': 2.75, 'rects': [[7.361, 1.707, 12.966, 5.987]], 'floor': 'vinyl', 'opts': ['paint', 'kitchen']},
    {'id': 3, 'name': 'Koupelna', 'en': 'Bathroom', 'area': 5.0, 'dims': '1.79 × 2.79 m', 'ceil': 2.40, 'rects': [[0.0, 6.368, 1.786, 9.159]], 'floor': 'tile', 'tileH': 2.10, 'opts': ['paint', 'tiles']},
    {'id': 4, 'name': 'Pokoj', 'en': 'Bedroom', 'area': 15.0, 'dims': '5.18 × 2.94 m + nika', 'ceil': 2.75,
     'rects': [[3.178, 6.223, 7.125, 9.165], [1.949, 6.719, 3.178, 9.165], [5.932, 3.85, 7.222, 6.223]], 'floor': 'vinyl', 'opts': ['paint', 'bedrobe']},
    {'id': 5, 'name': 'WC', 'en': 'WC', 'area': 2.2, 'dims': '1.59 × 1.54 m', 'ceil': 2.40, 'rects': [[11.229, 0.406, 12.815, 1.538], [11.229, 0.0, 12.016, 0.406]], 'floor': 'tile', 'tileH': 1.20, 'opts': ['paint', 'tiles']},
]

# openings: lintel over the gap (door head 2.02, window head 2.40); windows: glass plane + outward normal n, door = french-door part
openings = [
    {'kind': 'door', 'rect': [7.906, 1.538, 8.789, 1.707]},               # hall -> living
    {'kind': 'door', 'rect': [11.065, 0.654, 11.229, 1.441]},             # hall -> WC
    {'kind': 'door', 'rect': [1.786, 8.275, 1.949, 9.062]},               # bedroom -> bathroom
    {'kind': 'door', 'rect': [7.222, 5.18, 7.361, 5.987], 'sliding': True},   # living -> bedroom niche (pocket door)
    {'kind': 'door', 'rect': [7.119, 0.103, 7.361, 1.09], 'entry': True},     # entrance from the corridor
    {'kind': 'window', 'rect': [8.916, 5.987, 12.446, 6.447], 'glass': 6.22, 'n': [0, 1], 'door': [11.50, 12.37]},   # living, south (courtyard)
    {'kind': 'window', 'rect': [7.125, 7.064, 7.585, 8.989], 'glass': 7.36, 'n': [1, 0], 'door': [8.05, 8.90]},      # bedroom, east (courtyard)
]

F = []
def add(kind, rect, z0=0, z1=1, mat='oak', m=False, **kw):     # rect in preview px, or metres with m=True
    F.append(dict(kind=kind, r=list(rect) if m else R(*rect), z=[z0, z1], m=mat, **kw))
# living room
add('rug', (1185, 590, 1425, 785), 0, 0.012, 'rug')
add('tvunit', (1085, 540, 1125, 790), 0, 0.5, 'oak')
add('tv', (1086, 618, 1092, 738), 0.95, 1.66, 'screen', face='+x')
add('sofa', (1334, 560, 1452, 803), 0, 0.82, 'fabric', back='+x')
add('coffeetable', (1210, 630, 1304, 724), 0, 0.40, 'oak')
add('floorlamp', (1462, 772, 1492, 802), 0, 1.60, 'black')
add('plant', (1135, 835, 1175, 875), 0, 1.10, 'leaf')
add('table', (1528, 336, 1635, 547), 0, 0.75, 'oak')
for cx, cy, face in ((1493, 397, '+x'), (1493, 492, '+x'), (1669, 397, '-x'), (1669, 492, '-x')):
    add('chair', (cx - 28, cy - 28, cx + 28, cy + 28), 0, 0.84, 'chairwood', face=face)
add('pendant', (1569, 429, 1594, 454), 1.55, 2.75, 'black')
add('curtain', (8.95, 5.89, 9.60, 5.91), 0.02, 2.55, 'curtain', m=True)
add('curtain', (11.80, 5.89, 12.42, 5.91), 0.02, 2.55, 'curtain', m=True)
# bedroom
add('rug', (560, 1060, 905, 1290), 0, 0.012, 'rug2')
add('bed', (592, 945, 828, 1207), 0, 1.10, 'fabric3', head='-y')
add('nightstand', (537, 945, 589, 997), 0, 0.48, 'oak')
add('nightstand', (831, 945, 883, 997), 0, 0.48, 'oak')
add('robe', (358, 1007, 446, 1200), 0, 2.70, 'bedrobe', face='+x')    # 5 cm under the 2.75 ceiling, LED strip on top (as the first flat)
add('robe', (5.935, 3.85, 7.215, 4.48), 0, 2.70, 'bedrobe', face='+y', m=True)
add('plant', (930, 1270, 970, 1310), 0, 1.25, 'leaf')
add('curtain', (7.03, 7.14, 7.05, 7.70), 0.02, 2.55, 'curtain', m=True)
add('curtain', (7.03, 8.36, 7.05, 8.91), 0.02, 2.55, 'curtain', m=True)
# bathroom
add('bath', (96, 960, 337, 1058), 0, 0.58, 'white')
add('toilet', (96, 1086, 162, 1138), 0.30, 0.42, 'white', face='+x')
add('vanity', (96, 1168, 152, 1246), 0.45, 0.85, 'oak', face='+x')
add('mirror', (96, 1170, 100, 1244), 1.05, 1.85, 'mirror', face='+x')
add('washer', (96, 1255, 175, 1335), 0, 0.85, 'white', face='+x')
add('towelrail', (324, 1105, 330, 1180), 0.55, 1.45, 'chrome')
add('rug', (180, 1120, 240, 1200), 0, 0.012, 'bathmat')
# WC
add('toilet', (1752, 210, 1815, 262), 0.30, 0.42, 'white', face='-x')
add('basin', (1630, 105, 1685, 140), 0.78, 0.86, 'white', face='+y')
add('mirror', (1632, 105, 1683, 109), 1.05, 1.50, 'mirror', face='+y')
# hall
add('robe', (1272, 105, 1580, 190), 0, 2.30, 'hallrobe', face='+y')
add('entrydoor', (7.20, 0.12, 7.25, 1.07), 0, 2.02, 'entrydoor', m=True)
add('rug', (1092, 135, 1160, 235), 0, 0.012, 'doormat')
# french-window railings (glass + top rail) on the outer face
for r in ((8.92, 6.41, 12.44, 6.43), (7.555, 7.07, 7.575, 8.98)):
    add('box', r, 0.02, 1.05, 'glass', m=True)
    add('box', r, 1.02, 1.07, 'black', m=True)

# door leaves, open 90 degrees as drawn (hinge -> leaf direction)
doors = [
    {'hinge': [7.95, 1.707], 'dir': [0, 1], 'w': 0.80},     # hall -> living, opens into the living room
    {'hinge': [11.229, 1.40], 'dir': [1, 0], 'w': 0.70},    # hall -> WC, opens into the WC
    {'hinge': [1.786, 9.02], 'dir': [-1, 0], 'w': 0.70},    # bedroom -> bathroom, opens into the bathroom
]

json.dump({'rooms': rooms, 'openings': openings, 'furniture': F, 'walls': walls, 'doors': doors}, open('app/apartment.json', 'w'), ensure_ascii=False)
area = lambda r: sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in r['rects'])
print(len(walls), 'walls', len(F), 'furniture;', ', '.join(f"{r['en']} {area(r):.1f} (sheet {r['area']})" for r in rooms), '; total %.1f' % sum(area(r) for r in rooms))
