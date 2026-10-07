# Example flat: direct-sun minutes per window on the 21st of every month (copy of render/sun_hours.py for the first flat, windows on any facade, no balcony).
# Ray-cast from points just outside the glass toward the sun through the built scene (our building's wings, neighbours' balconies, the neighbouring block,
# planned L block, window reveals). A moment counts as sunlit when > 10 % of the points see the sun.
# Run (scene built by apartment.py in the same session):
#   blender -b -P render/apartment.py -P render/sun_hours.py -- "<code>" out/x none 1            (4.NP)
import csv, json, math, os, subprocess, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'   # kit root
FLOOR = json.load(open(HERE + os.environ.get('SITE', 'app/site.json')))['floor']
OUT = HERE + 'out/sun_hours_%dnp' % FLOOR
STEP = 5                                                    # minutes
ROOMS = ['Obývací pokoj + kuchyň (okno na jih)', 'Pokoj (okno na východ)']
MONTHS = ['led', 'úno', 'bře', 'dub', 'kvě', 'čvn', 'čvc', 'srp', 'zář', 'říj', 'lis', 'pro']


def compute():
    import bpy
    from mathutils import Vector
    sys.path.insert(0, HERE + 'render'); import sun as solar
    scn = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get()
    apt = json.load(open(HERE + 'app/apartment.json'))
    wins = [o for o in apt['openings'] if o['kind'] == 'window']        # living (south) first, bedroom (east)
    pts = []
    for o in wins:                                          # 6 cm outside the glass, 10 x 6 points; Blender (x, -y, z)
        x0, y0, x1, y1 = o['rect']; (nx, ny), g = o['n'], o['glass']
        a0, a1 = (x0, x1) if ny else (y0, y1)
        ps = []
        for i in range(10):
            a = a0 + 0.06 + (a1 - a0 - 0.12) * (i + 0.5) / 10
            for j in range(6):
                z = 0.04 + 2.3 * (j + 0.5) / 6
                x, y = (a, g + ny * 0.06) if ny else (g + nx * 0.06, a)
                ps.append(Vector((x, -y, z)))
        pts.append(ps)
    glass = lambda ob: ob.name.startswith('glass') or bool(ob.data and getattr(ob.data, 'materials', None) and ob.data.materials[0] and ob.data.materials[0].name == 'glass')

    def lit_share(ps, d):
        n = 0
        for p in ps:
            q = p
            for _ in range(6):                               # glass (railings, panes) lets the sun through
                ok, loc, _, _, ob, _ = scn.ray_cast(dg, q + d * 1e-3, d)
                if not ok: n += 1; break
                if not glass(ob): break
                q = loc
        return n / len(ps)

    rows = []
    for mo in range(1, 13):
        day = '2026-%02d-21' % mo
        t = solar.sun_times(day); zone = solar.sun_local(day, '12:00')['zone']
        lit = {r: [] for r in ROOMS}
        for m in range(0, 1440, STEP):
            i = solar.sun_local(day, m / 60); el = i['elevation']
            if el <= 0: continue
            e, a = math.radians(el), math.radians(i['azimuth'] - solar.FACADE_AZ)
            d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
            for r, ps in zip(ROOMS, pts):
                if lit_share(ps, d) > 0.10: lit[r].append(m)
        for r in ROOMS:
            iv = []
            for m in lit[r]:
                if iv and m - iv[-1][1] <= STEP: iv[-1][1] = m
                else: iv.append([m, m])
            hm = lambda x: '%02d:%02d' % divmod(int(round(x)) % 1440, 60)
            rows.append({'room': r, 'date': day, 'zone': zone, 'sunrise': hm(t['sunrise'][0].hour * 60 + t['sunrise'][0].minute + t['sunrise'][0].second / 60),
                         'sunset': hm(t['sunset'][0].hour * 60 + t['sunset'][0].minute + t['sunset'][0].second / 60),
                         'sun_minutes': len(lit[r]) * STEP, 'intervals': '; '.join('%s-%s' % (hm(a), hm(b + STEP)) for a, b in iv)})
            print('SUNHOURS', r, day, zone, rows[-1]['sun_minutes'], rows[-1]['intervals'], flush=True)
    with open(OUT + '.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def chart():
    from PIL import Image, ImageDraw, ImageFont
    rows = list(csv.DictReader(open(OUT + '.csv', encoding='utf-8')))
    S = 2                                                  # pixel scale
    font = lambda sz: ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', sz * S)
    INK, MUTED, GRID, SURF, DAY, SUN = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb', '#dedcd5', '#eb6834'
    T0, T1, LW, CW, RH, TOP = 4 * 60, 22 * 60, 64, 560, 15, 82
    PH = 12 * RH
    W, H = (LW + CW + 120) * S, (TOP + len(ROOMS) * (PH + 52) + 40) * S
    im = Image.new('RGB', (W, H), SURF); d = ImageDraw.Draw(im)
    X = lambda m: (LW + (m - T0) / (T1 - T0) * CW) * S
    mins = lambda s: int(s[:2]) * 60 + int(s[3:5])
    d.text((LW * S, 10 * S), 'Ukázkový byt (%d.NP, dvůr) - přímé slunce, 21. den v měsíci' % FLOOR, font=font(15), fill=INK)
    d.text((LW * S, 32 * S), 'místní čas SEČ/SELČ, 5min krok; okolí: náš dům (U), sousední blok, plánovaný blok L (8 pater, odhad)', font=font(10), fill=MUTED)
    d.rectangle([LW * S, 56 * S, (LW + 14) * S, 64 * S], fill=DAY); d.text(((LW + 20) * S, 53 * S), 'slunce nad obzorem', font=font(11), fill=MUTED)
    d.rectangle([(LW + 150) * S, 56 * S, (LW + 164) * S, 64 * S], fill=SUN); d.text(((LW + 170) * S, 53 * S), 'přímé slunce (> 10 % plochy skla)', font=font(11), fill=MUTED)
    for k, room in enumerate(ROOMS):
        y0 = TOP + k * (PH + 52) + 22
        d.text((LW * S, (y0 - 18) * S), room, font=font(12), fill=INK)
        for h in range(T0 // 60, T1 // 60 + 1, 2):
            d.line([X(h * 60), y0 * S, X(h * 60), (y0 + PH) * S], fill=GRID, width=S)
            d.text((X(h * 60) - 9 * S, (y0 + PH + 3) * S), '%d:00' % h, font=font(9), fill=MUTED)
        for r in (r for r in rows if r['room'] == room):
            mo = int(r['date'][5:7]); yy = (y0 + (mo - 1) * RH) * S
            d.text((8 * S, yy + 1 * S), MONTHS[mo - 1], font=font(10), fill=MUTED)
            d.rounded_rectangle([X(mins(r['sunrise'])), yy + 2 * S, X(mins(r['sunset'])), yy + (RH - 2) * S], radius=3 * S, fill=DAY)
            for iv in filter(None, r['intervals'].split('; ')):
                a, b = iv.split('-')
                d.rounded_rectangle([X(mins(a)), yy + 3 * S, max(X(mins(b)), X(mins(a)) + 3 * S), yy + (RH - 3) * S], radius=2 * S, fill=SUN)
            mm = int(r['sun_minutes'])
            d.text(((LW + CW + 8) * S, yy + 1 * S), '%d h %02d min' % divmod(mm, 60) if mm else '0', font=font(10), fill=INK if mm else MUTED)
    im.save(OUT + '.png')


if 'chart' in sys.argv:
    chart()
else:
    compute()
    print('CHART', subprocess.run([os.environ.get('PYTHON', 'python3'), os.path.abspath(__file__), 'chart'], env={**os.environ}).returncode, flush=True)
