# Example flat: direct sun on the floor of the living room and bedroom (sun plan). Built scene from apartment.py in the same session;
# loose furniture, curtains and door leaves are hidden (sun on the bare floor), floor under built-in units (kitchen, wardrobes) is left out.
# One BVH of all opaque geometry (glass, railings glass = transparent); 10 cm grid at floor level; 21st of every month, 5 min steps.
# Run: blender -b -P render/apartment.py -P render/sun_plan.py -- "<code>" out/x none 1
#   -> out/sun_plan_<floor>np.json, then: python3 render/sun_plan.py chart
import json, math, os, subprocess, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'   # kit root
FLOOR = json.load(open(HERE + os.environ.get('SITE', 'app/site.json')))['floor']
OUT = HERE + 'out/sun_plan_%dnp' % FLOOR
STEP, G = 5, 0.1
DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def compute():
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    sys.path.insert(0, HERE + 'render'); import sun as solar
    scn = bpy.context.scene
    apt = json.load(open(HERE + 'app/apartment.json')); kit = json.load(open(HERE + 'app/kitchen.json'))['B']
    for ob in scn.objects:
        if ob.get('furn'): ob.hide_viewport = True
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for ob in scn.objects:
        if ob.type != 'MESH' or ob.hide_viewport or ob.name.startswith('glass'): continue
        if ob.data.materials and ob.data.materials[0] and ob.data.materials[0].name == 'glass': continue
        ev = ob.evaluated_get(dg); me = ev.to_mesh(); mw = ob.matrix_world; b = len(verts)
        verts += [mw @ v.co for v in me.vertices]; polys += [[b + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    tree = BVHTree.FromPolygons(verts, polys)
    print('BVH', len(verts), 'verts', len(polys), 'polys', flush=True)
    built = [f['r'] for f in apt['furniture'] if f['kind'] == 'robe'] + [[12.33, 1.707, 12.966, kit['seg']['end'][1] + 0.03]]
    inside = lambda x, y, rs: any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in rs)
    pts = []
    for rid in (2, 4):
        for x0, y0, x1, y1 in next(r for r in apt['rooms'] if r['id'] == rid)['rects']:
            for i in range(int((x1 - x0) / G)):
                for j in range(int((y1 - y0) / G)):
                    x, y = round(x0 + (i + 0.5) * G, 3), round(y0 + (j + 0.5) * G, 3)
                    if not inside(x, y, built): pts.append((rid, x, y))
    P = [Vector((x, -y, 0.02)) for _, x, y in pts]
    months = []
    for mo in range(1, 13):
        day = '2026-%02d-21' % mo; mins = [0] * len(P)
        for m in range(0, 1440, STEP):
            i = solar.sun_local(day, m / 60); el = i['elevation']
            if el <= 0: continue
            e, a = math.radians(el), math.radians(i['azimuth'] - solar.FACADE_AZ)
            d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
            if d.y >= 0 and d.x <= 0: continue                                  # behind both windows (south: -Y, east: +X)
            for k, p in enumerate(P):
                if tree.ray_cast(p + d * 1e-3, d)[0] is None: mins[k] += STEP
        months.append(mins); print('SUNPLAN', day, sum(1 for v in mins if v), 'points lit', flush=True)
    json.dump({'floor': FLOOR, 'grid': G, 'pts': pts, 'months': months}, open(OUT + '.json', 'w'))


def chart():
    from PIL import Image, ImageDraw, ImageFont
    D = json.load(open(OUT + '.json'))
    plan = Image.open(HERE + 'src/plan.png').convert('RGB')
    S, OX, OY = 165.2, 118, 128                                                  # plan.png px per metre, origin
    crop = (40, 40, 2340, 1700)
    font = lambda sz, b=False: ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial%s.ttf' % (' Bold' if b else ''), sz)
    RAMP = ['#fde4d6', '#fbc6a8', '#f6a077', '#ef7b4a', '#d95926', '#b4441b', '#8a3212']   # one hue (orange = sun), light -> dark
    hrs = lambda m: m / 60

    def panel(values, bins, title, sub, unit):
        im = plan.crop(crop).copy(); im = Image.blend(im, Image.new('RGB', im.size, 'white'), 0.35)
        ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        for (rid, x, y), v in zip(D['pts'], values):
            if v <= 0: continue
            k = next((i for i, b in enumerate(bins[1:]) if v < b), len(bins) - 2)
            px, py = x * S + OX - crop[0], y * S + OY - crop[1]; h = D['grid'] * S / 2
            d.rectangle([px - h, py - h, px + h, py + h], fill=RAMP[min(k, len(RAMP) - 1)] + 'e6')
        im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB')
        im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
        out = Image.new('RGB', (im.width, im.height + 150), '#fcfcfb'); out.paste(im, (0, 120)); dd = ImageDraw.Draw(out)
        dd.text((24, 14), title, font=font(30, True), fill='#0b0b0b'); dd.text((24, 54), sub, font=font(20), fill='#52514e')
        x = 24
        for i in range(len(bins) - 1):
            dd.rectangle([x, 90, x + 26, 108], fill=RAMP[i]); lab = ('%g-%g %s' % (bins[i], bins[i + 1], unit)) if i < len(bins) - 2 else ('%g+ %s' % (bins[i], unit))
            dd.text((x + 32, 88), lab, font=font(17), fill='#0b0b0b'); x += 40 + dd.textlength(lab, font=font(17))
        return out

    M = D['months']
    day_bins = [0, 0.5, 1, 2, 3, 4, 6, 99]
    panels = [panel([hrs(v) for v in M[11]], day_bins, '21. prosince', 'hodiny přímého slunce na podlaze za den', 'h'),
              panel([hrs(v) for v in M[2]], day_bins, '21. března (≈ 21. září)', 'hodiny přímého slunce na podlaze za den', 'h'),
              panel([hrs(v) for v in M[5]], day_bins, '21. června', 'hodiny přímého slunce na podlaze za den', 'h'),
              panel([sum(hrs(M[m][k]) * DAYS[m] for m in range(12)) for k in range(len(D['pts']))], [0, 50, 100, 200, 300, 450, 600, 9999],
                    'Celý rok', 'hodiny přímého slunce na podlaze za rok (z 21. dne každého měsíce)', 'h')]
    W, H = panels[0].width, panels[0].height
    sheet = Image.new('RGB', (2 * W + 30, 2 * H + 150), '#fcfcfb'); d = ImageDraw.Draw(sheet)
    d.text((24, 18), 'Ukázkový byt (%d.NP) - sluneční plán: kam dopadá přímé slunce' % D['floor'], font=font(36, True), fill='#0b0b0b')
    d.text((24, 66), 'Bez volného nábytku a závěsů; pod kuchyní a vestavěnými skříněmi se nepočítá. Okolí: křídla našeho domu, sousední balkony, sousední blok, '
           'plánovaný blok L (8 pater, odhad).', font=font(19), fill='#52514e')
    d.text((24, 94), 'Model z prodejního PDF (±3 cm) a OpenStreetMap; jasná obloha (oblačnost se nepočítá). Čas: 5min krok, místní čas.', font=font(19), fill='#52514e')
    for i, p in enumerate(panels): sheet.paste(p, ((i % 2) * (W + 30), 140 + (i // 2) * H))
    sheet.save(OUT + '.png'); print('saved', OUT + '.png', sheet.size)


if 'chart' in sys.argv:
    chart()
else:
    compute()
    print('CHART', subprocess.run([os.environ.get('PYTHON', 'python3'), os.path.abspath(__file__), 'chart'], env={**os.environ}).returncode, flush=True)
