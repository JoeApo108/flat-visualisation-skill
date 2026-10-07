# Kitchen for the example flat -> app/kitchen.json (layout 'B', Blender coords as the first flat's kitchen.json: a = (x0, -y1, z0), b = (x1, -y0, z1)).
# One straight run on the living room's east wall (plan x 12.966), from the north wall (y 1.707) toward the window:
# filler 5 | fridge column 60 | sink 60 | dishwasher 60 | hob + oven 60 | drawers 60 | rounded end 25 (R 0.25, toward the room and the window).
# Same rules as the first flat: worktop 0.91, wall units 1.50-2.40 + top boxes to 2.70, tall/wall units end 5 cm under the ceiling, LED strip on top.
import json, math

WALL, Y0 = 12.966, 1.707
TOP, WT, WB, WD = 2.70, 0.91, 1.50, 0.35          # top of units, worktop top, wall unit bottom, wall unit depth
XC, XF = WALL - 0.596, WALL - 0.614                # base carcass front, base front face
XW, XWF = WALL - WD, WALL - WD - 0.018             # wall carcass front, wall front face
seg, y = {}, Y0
for name, w in (('filler', 0.05), ('fridge', 0.60), ('sink', 0.60), ('dw', 0.60), ('hob', 0.60), ('drawers', 0.60), ('end', 0.25)):
    seg[name] = (y, y + w); y += w
YE0, YE = seg['end']                               # rounded end: straight to YE0, quarter round to YE
RUN0 = seg['sink'][0]                              # base run (worktop) starts after the fridge column

box, cyl, arc = [], [], []
def bx(n, m, x0, y0, x1, y1, z0, z1): box.append({'n': n, 'm': m, 'a': [round(x0, 4), round(-y1, 4), z0], 'b': [round(x1, 4), round(-y0, 4), z1]})
def handle(n, ya, yb, z):                          # horizontal bar on a base/tall front
    bx(n, 'black_metal', XF - 0.025, ya, XF - 0.012, yb, z - 0.006, z + 0.006)
def whandle(n, ya, yb, z): bx(n, 'black_metal', XWF - 0.025, ya, XWF - 0.012, yb, z - 0.006, z + 0.006)

# filler + fridge column (tall, fridge-freezer, top box)
a, b = seg['filler']; bx('f_filler', 'front', XF, a + 0.002, XC, b, 0.155, TOP - 0.005); bx('filler_plinth', 'plinth', XC, a, WALL, b, 0, 0.15)
a, b = seg['fridge']
bx('fridge_carcass', 'carcass', XC, a, WALL, b, 0.15, 2.40); bx('fridge_topbox', 'carcass', XC, a, WALL, b, 2.40, TOP)
bx('fridge_plinth', 'plinth', XC + 0.05, a, WALL, b, 0, 0.15)
for n, z0, z1, h in (('f_freezer', 0.155, 0.95, (0.255, 0.755)), ('f_fridge', 0.953, 1.93, (1.0, 1.6)), ('f_fridge_top', 1.933, 2.40, None), ('f_fridge_topbox', 2.403, TOP - 0.005, None)):
    bx(n, 'front', XF, a + 0.003, XC, b - 0.003, z0, z1)
    if h: bx(n + '_h', 'black_metal', XF - 0.025, b - 0.045, XF - 0.012, b - 0.033, *h)      # vertical bar by the hinge-free edge
# base run carcass, plinth, worktop, splashback (cut back to the rounded end)
bx('base_carcass', 'carcass', XC, RUN0, WALL, YE0, 0.15, 0.87)
bx('base_plinth', 'plinth', XC + 0.05, RUN0, WALL, YE0, 0, 0.15)
bx('worktop_long', 'worktop', XC - 0.03, RUN0, WALL, YE0, 0.87, WT)
bx('splash_long', 'splash', WALL - 0.012, RUN0, WALL, YE, WT, WB)
# sink 60: two doors, bowl + tap
a, b = seg['sink']; m = (a + b) / 2
bx('f_sink_a', 'front', XF, a + 0.003, XC, m - 0.002, 0.155, 0.865); handle('f_sink_a_h', a + 0.03, m - 0.03, 0.815)
bx('f_sink_b', 'front', XF, m + 0.002, XC, b - 0.003, 0.155, 0.865); handle('f_sink_b_h', m + 0.03, b - 0.03, 0.815)
CUT = [[XC + 0.08, -(b - 0.06), 0.70], [WALL - 0.08, -(a + 0.06), 0.95]]
BOWL = [[XC + 0.08, -(b - 0.06), 0.71], [WALL - 0.08, -(a + 0.06), 0.905]]
cyl.append({'n': 'tap_base', 'm': 'black_metal', 'a': [WALL - 0.046, -(m + 0.016), WT], 'b': [WALL - 0.014, -(m - 0.016), 1.22]})
cyl.append({'n': 'tap_spout', 'm': 'black_metal', 'a': [WALL - 0.226, -(m + 0.012), 1.198], 'b': [WALL - 0.026, -(m - 0.012), 1.222]})
# dishwasher 60 (integrated)
a, b = seg['dw']; bx('f_dw', 'front', XF, a + 0.003, XC, b - 0.003, 0.155, 0.865); handle('f_dw_h', a + 0.15, b - 0.15, 0.815)
# hob 60 + oven under it
a, b = seg['hob']
bx('f_ovendrawer', 'front', XF, a + 0.003, XC, b - 0.003, 0.155, 0.265); handle('f_ovendrawer_h', a + 0.15, b - 0.15, 0.215)
bx('oven_front', 'black_glass', XF, a + 0.003, XC, b - 0.003, 0.27, 0.86); bx('oven_window', 'hob_ring', XF - 0.001, a + 0.07, XF, b - 0.07, 0.40, 0.70)
bx('oven_handle', 'steel', XF - 0.025, a + 0.05, XF - 0.012, b - 0.05, 0.812, 0.828)
bx('hob', 'black_glass', XC + 0.04, a + 0.01, WALL - 0.08, b - 0.01, WT, WT + 0.006)
for dx, dy, r in ((0.12, 0.15, 0.09), (0.12, 0.44, 0.10), (0.38, 0.15, 0.08), (0.38, 0.44, 0.09)):
    cx, cy = XC + 0.04 + dx, a + dy
    cyl.append({'n': 'hob_zone', 'm': 'hob_ring', 'a': [cx - r, -(cy + r), WT + 0.0061], 'b': [cx + r, -(cy - r), WT + 0.0063]})
# drawers 60: three drawers
a, b = seg['drawers']
for i, (z0, z1) in enumerate(((0.155, 0.40), (0.403, 0.63), (0.633, 0.865))):
    bx(f'f_drawer{i}', 'front', XF, a + 0.003, XC, b - 0.003, z0, z1); handle(f'f_drawer{i}_h', a + 0.15, b - 0.15, z1 - 0.05)
# rounded end 25 (as the first flat): straight box to the wall + quarter round toward the room (-x) and the window (+y plan = -Y Blender)
CX = XC + 0.25
bx('end_base', 'carcass', CX, YE0, WALL, YE, 0.15, 0.87); bx('end_plinth', 'plinth', CX, YE0, WALL, YE - 0.05, 0, 0.15)
bx('end_worktop', 'worktop', CX, YE0, WALL, YE + 0.03, 0.87, WT); bx('f_end_panel', 'front', CX, YE, WALL, YE + 0.018, 0.155, 0.865)
arc.append({'n': 'arc_base', 'm': 'carcass', 'c': [CX, -YE0], 'r0': 0, 'r1': 0.25, 'a0': 180, 'a1': 270, 'z0': 0.15, 'z1': 0.87})
arc.append({'n': 'arc_f_base', 'm': 'front', 'c': [CX, -YE0], 'r0': 0.25, 'r1': 0.268, 'a0': 180, 'a1': 270, 'z0': 0.155, 'z1': 0.865})
arc.append({'n': 'arc_worktop', 'm': 'worktop', 'c': [CX, -YE0], 'r0': 0, 'r1': 0.28, 'a0': 180, 'a1': 270, 'z0': 0.87, 'z1': WT})
arc.append({'n': 'arc_plinth', 'm': 'plinth', 'c': [CX, -YE0], 'r0': 0, 'r1': 0.20, 'a0': 180, 'a1': 270, 'z0': 0.0, 'z1': 0.15})
# wall units over sink .. drawers, 1.50-2.40 doors + top boxes to 2.70; hood above the hob, microwave above the drawers; rounded end
bx('wall_carcass', 'carcass', XW, RUN0, WALL, YE0, WB, TOP)
CW = WALL - 0.10
bx('end_wall', 'carcass', CW, YE0, WALL, YE, WB, TOP); bx('w_end_panel', 'front', CW, YE, WALL, YE + 0.018, WB, TOP - 0.005)
arc.append({'n': 'arc_wall', 'm': 'carcass', 'c': [CW, -YE0], 'r0': 0, 'r1': 0.25, 'a0': 180, 'a1': 270, 'z0': WB, 'z1': TOP})
arc.append({'n': 'arc_f_wall', 'm': 'front', 'c': [CW, -YE0], 'r0': 0.25, 'r1': 0.268, 'a0': 180, 'a1': 270, 'z0': WB, 'z1': 2.40})
arc.append({'n': 'arc_f_wall_top', 'm': 'front', 'c': [CW, -YE0], 'r0': 0.25, 'r1': 0.268, 'a0': 180, 'a1': 270, 'z0': 2.403, 'z1': TOP - 0.005})
for n in ('sink', 'dw', 'hob', 'drawers'):
    a, b = seg[n]; w = {'sink': 'w_drainer', 'dw': 'w_mid', 'hob': 'w_hood', 'drawers': 'w_mw'}[n]
    if n == 'hob':
        bx('hood_visor', 'steel', XWF - 0.05, a + 0.007, XW + 0.02, b - 0.007, WB, WB + 0.05)
        bx(w, 'front', XWF, a + 0.003, XW, b - 0.003, WB + 0.053, 2.40); whandle(w + '_h', a + 0.15, b - 0.15, WB + 0.097)
    elif n == 'drawers':
        bx('mw_front', 'black_glass', XWF, a + 0.003, XW, b - 0.003, WB + 0.02, 1.90); bx('mw_panel', 'hob_ring', XWF - 0.001, b - 0.13, XWF, b - 0.01, WB + 0.04, 1.88)
        bx(w, 'front', XWF, a + 0.003, XW, b - 0.003, 1.903, 2.40); whandle(w + '_h', a + 0.15, b - 0.15, 1.947)
    else:
        bx(w, 'front', XWF, a + 0.003, XW, b - 0.003, WB, 2.40); whandle(w + '_h', a + 0.15, b - 0.15, WB + 0.044)
    bx(w + '_top', 'front', XWF, a + 0.003, XW, b - 0.003, 2.403, TOP - 0.005)
bx('led_long', 'led_cove', XW + 0.03, RUN0, XW + 0.06, YE0, WB - 0.004, WB)           # under-cabinet LED at the front edge, lights the worktop (LED switch)
box[-1]['dir'] = [0, 0, -1]
# LED cove strips on top of every unit that reaches TOP: at the front edge (toward the room = -x, the units stand on the east wall),
# tilted 30° from vertical toward the room, so the light leaves the 5 cm gap and washes the ceiling in front of the units
TILT = 30
for o in [o for o in box if o['m'] == 'carcass' and abs(o['b'][2] - TOP) < 1e-6]:
    (x0, y0, _), (x1, y1, _) = o['a'], o['b']
    if min(x1 - x0, y1 - y0) < 0.2: continue
    box.append({'n': 'cove_' + o['n'], 'm': 'led_cove', 'a': [x0 + 0.02, y0 + 0.03, TOP], 'b': [x0 + 0.032, y1 - 0.03, TOP + 0.006],
                'dir': [-round(math.sin(math.radians(TILT)), 4), 0, round(math.cos(math.radians(TILT)), 4)]})

json.dump({'B': {'box': box, 'cyl': cyl, 'arc': arc, 'cut': CUT, 'bowl': BOWL, 'seg': seg}}, open('app/kitchen.json', 'w'), ensure_ascii=False)
print(len(box), 'boxes', len(arc), 'arcs; run %.3f-%.3f (%.2f m)' % (Y0, YE, YE - Y0), {k: (round(a, 3), round(b, 3)) for k, (a, b) in seg.items()})
