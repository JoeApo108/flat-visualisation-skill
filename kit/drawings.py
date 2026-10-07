# Example flat drawings (style of the first flat's annotate.py / variants.py): room dimensions, kitchen plan, kitchen elevation.
# Plan coords in metres from data.py / kitchen.py; background = developer plan src/plan.png (165.2 px/m).
# Run: python3 drawings.py -> out/byt_rooms.png, out/byt_kitchen_plan.png, out/byt_kitchen_elevation.png
import json, os
from PIL import Image, ImageDraw, ImageFont

H = os.path.dirname(os.path.abspath(__file__)) + '/'
SRC = Image.open(H + 'src/plan.png').convert('RGB')
S, OX, OY = 165.2, 118, 128
RED, INK, MUTED, BLUE, FILL, GREEN, GFILL, ORANGE = (210, 20, 20), (0, 0, 0), (90, 90, 90), (25, 40, 95), (222, 230, 245), (30, 130, 50), (214, 240, 214), (220, 150, 0)
BOLD, REG = '/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf'
F = lambda sz, b=False: ImageFont.truetype(BOLD if b else REG, sz)
APT = json.load(open(H + 'app/apartment.json')); KIT = json.load(open(H + 'app/kitchen.json'))['B']; SEG = KIT['seg']


class Sheet:
    def __init__(self, box_m, scale, title, sub, footer=()):
        x0, y0, x1, y1 = box_m; self.x0, self.y0, self.k = x0, y0, scale            # scale = output px per metre
        crop = (int(x0 * S + OX), int(y0 * S + OY), int(x1 * S + OX), int(y1 * S + OY))
        plan = SRC.crop(crop).resize((int((x1 - x0) * scale), int((y1 - y0) * scale)), Image.LANCZOS)
        plan = Image.blend(plan, Image.new('RGB', plan.size, 'white'), 0.45)
        self.top = 110; fh = 34 * len(footer) + 30 if footer else 0
        self.img = Image.new('RGB', (plan.width, plan.height + self.top + fh), 'white'); self.img.paste(plan, (0, self.top))
        self.d = ImageDraw.Draw(self.img)
        self.d.text((24, 16), title, font=F(34, True), fill=INK); self.d.text((24, 62), sub, font=F(20), fill=MUTED)
        y = plan.height + self.top + 16
        for line in footer:
            if isinstance(line, tuple):
                k, txt, col = line; self.d.text((30, y), k, font=F(22, True), fill=col); self.d.text((95, y), txt, font=F(22), fill=INK)
            else: self.d.text((30, y), line, font=F(22), fill=INK)
            y += 34

    def P(self, x, y): return ((x - self.x0) * self.k, (y - self.y0) * self.k + self.top)
    def rect(self, x0, y0, x1, y1, fill=FILL, out=BLUE, w=3): self.d.rectangle([*self.P(x0, y0), *self.P(x1, y1)], fill=fill, outline=out, width=w)
    def line(self, a, b, col=RED, w=3): self.d.line([self.P(*a), self.P(*b)], fill=col, width=w)
    def tick(self, x, y):
        cx, cy = self.P(x, y); self.d.line([cx - 8, cy + 8, cx + 8, cy - 8], fill=RED, width=4)
    def label(self, x, y, text, col=RED, sz=24, box=True):
        cx, cy = self.P(x, y); l, t, r, b = self.d.textbbox((0, 0), text, font=F(sz, True)); w, h = r - l, b - t
        if box: self.d.rectangle([cx - w / 2 - 5, cy - h / 2 - 5, cx + w / 2 + 5, cy + h / 2 + 5], fill='white', outline=col, width=1)
        self.d.text((cx - w / 2 - l, cy - h / 2 - t), text, font=F(sz, True), fill=col)
    def chain_h(self, y, xs, labels=None):
        self.line((xs[0], y), (xs[-1], y))
        for x in xs: self.tick(x, y)
        for i, (a, b) in enumerate(zip(xs, xs[1:])): self.label((a + b) / 2, y, labels[i] if labels else '%.2f' % (b - a))
    def chain_v(self, x, ys, labels=None):
        self.line((x, ys[0]), (x, ys[-1]))
        for y in ys: self.tick(x, y)
        for i, (a, b) in enumerate(zip(ys, ys[1:])): self.label(x, (a + b) / 2, labels[i] if labels else '%.2f' % (b - a))
    def save(self, p): self.img.save(p); print('saved', p, self.img.size)


# ---------- 1. room dimensions
r = Sheet((-0.6, -0.6, 13.45, 9.6), 120, 'Ukázkový byt - rozměry místností (světlé, zeď-zeď)',
          'Změřeno z prodejního PDF (měřítko 0-5 m, 1 px = 6 mm), přesnost cca ±3 cm. Ne pro výrobu - ověřit na místě.',
          [('1', 'Vstupní hala 3.70 × 1.54 m (list: 6.2 m²)', INK), ('2', 'WC 1.59 × 1.54 m, šachta v rohu (list: 2.2 m²)', INK),
           ('3', 'Obývací pokoj + kk 5.60 × 4.28 m = 24.0 m²; list uvádí 27.2 m² - započítává i nik se skříní za posuvnými dveřmi', INK),
           ('4', 'Pokoj 5.18 × 2.94 m + nika se skříní 1.29 × 2.37 m (list: 15.0 m²)', INK), ('5', 'Koupelna 1.79 × 2.79 m (list: 5.0 m²)', INK),
           ('O', 'Okna: obývák 3.53 m na jih (francouzské dveře 0.87 m), pokoj 1.93 m na východ (franc. dveře 0.85 m); zábradlí, ne balkon', INK)])
r.chain_h(0.45, [7.361, 11.065]); r.chain_v(10.6, [0.0, 1.538])
r.chain_h(1.2, [11.229, 12.815]); r.chain_v(11.55, [0.0, 1.538])
r.chain_h(2.6, [7.361, 12.966]); r.chain_v(8.6, [1.707, 5.987])
r.chain_h(6.75, [8.916, 12.446], ['okno 3.53'])
r.chain_h(8.6, [1.949, 7.125]); r.chain_v(5.95, [6.223, 9.165])
r.chain_h(4.2, [5.932, 7.222]); r.chain_v(6.1, [3.85, 6.223])
r.chain_v(7.95, [7.064, 8.989], ['okno 1.93'])
r.chain_h(8.75, [0.0, 1.786]); r.chain_v(1.35, [6.368, 9.159])
r.label(12.0, 7.6, 'DVŮR (jih)', MUTED, 26, False); r.label(9.8, 9.0, 'DVŮR (východ)', MUTED, 26, False)
r.save(H + 'out/byt_rooms.png')

# ---------- 2. kitchen plan
WALL, Y0, YE = 12.966, 1.707, SEG['end'][1]
XC = WALL - 0.596
units = [('filler', None, ''), ('fridge', '1', ''), ('sink', '2', ''), ('dw', '3', 'DW'), ('hob', '4', ''), ('drawers', '5', ''), ('end', '6', '')]
k = Sheet((5.4, 1.2, 13.45, 6.75), 170, 'Ukázkový byt - kuchyň, půdorys (návrh)',
          'Standardní moduly napasované na změřený prostor (±3 cm). Finální návrh po zaměření na místě.',
          [('1', 'Lednice s mrazákem, vysoká skříň 60 s nástavcem; u zdi lišta 5 cm, aby šly dveře otevřít', BLUE),
           ('2', 'Dřez 60 - nad ním skříňka s odkapávačem', BLUE), ('3', 'Myčka 60, vestavná - nad ní hlavní pracovní plocha', BLUE),
           ('4', 'Indukční deska 60, trouba pod ní - digestoř ve skříňce nad deskou', BLUE),
           ('5', 'Zásuvky 60 (3 šuplíky) - mikrovlnka v horní skříňce nad nimi', BLUE),
           ('6', 'Koncová skříňka 0.25 se zaobleným rohem R 0.25, horní skříňka zaoblená stejně', GREEN),
           ('- -', 'Horní skříňky hloubky 35 cm od 1.50 m + nástavce; vše končí ve 2.70 (5 cm pod stropem)', BLUE),
           ('LED', 'Oranžově: LED pásky na přední hraně nahoře (natočené 30° do místnosti) + LED pod horními skříňkami; jeden vypínač', ORANGE),
           ('D', 'Francouzské dveře: otevřené křídlo končí cca 0.37 m od zaobleného konce linky', (200, 0, 140)),
           ('!', 'Jiné pořadí než v prodejním plánku (lednice | M | dřez | deska): deska není na konci linky, myčka je u dřezu', RED)])
for n, num, txt in units:
    a, b = SEG[n]
    if n == 'end':
        k.rect(XC + 0.25, a, WALL, b, GFILL, GREEN); cx, cy = k.P(XC + 0.25, a); rr = 0.25 * k.k
        k.d.pieslice([cx - rr, cy - rr, cx + rr, cy + rr], 90, 180, fill=GFILL, outline=GREEN, width=3); k.label(WALL - 0.17, (a + b) / 2, 'R 0.25', GREEN, 16, False)
    elif n == 'filler': k.rect(XC, a, WALL, b, (200, 200, 200), BLUE, 2)
    else: k.rect(XC, a, WALL, b, (190, 205, 230) if n == 'fridge' else FILL)
    if n == 'sink': k.d.rounded_rectangle([*k.P(XC + 0.08, a + 0.06), *k.P(WALL - 0.08, b - 0.06)], radius=10, outline=BLUE, width=2)
    if n == 'hob':
        for dx, dy in ((0.16, 0.15), (0.16, 0.44), (0.42, 0.15), (0.42, 0.44)):
            cx, cy = k.P(XC + dx, a + dy); k.d.ellipse([cx - 15, cy - 15, cx + 15, cy + 15], outline=BLUE, width=2)
    if txt: k.label((XC + WALL) / 2, (a + b) / 2, txt, BLUE, 22, False)
    if num:
        cx, cy = k.P(XC - 0.32, (a + b) / 2); k.d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], outline=GREEN if n == 'end' else BLUE, width=2, fill='white')
        l, t, rr_, bb = k.d.textbbox((0, 0), num, font=F(18, True)); k.d.text((cx - (rr_ - l) / 2 - l, cy - (bb - t) / 2 - t), num, font=F(18, True), fill=GREEN if n == 'end' else BLUE)
k.line((WALL - 0.35, SEG['sink'][0]), (WALL - 0.35, SEG['end'][0]), BLUE, 2)          # wall cabinet front (dashed look)
for y in [SEG['sink'][0] + i * 0.1 for i in range(int((SEG['end'][0] - SEG['sink'][0]) / 0.1))]:
    k.line((WALL - 0.355, y), (WALL - 0.355, y + 0.05), 'white', 4)
k.line((XC + 0.03, SEG['fridge'][0]), (XC + 0.03, SEG['fridge'][1]), ORANGE, 4); k.line((WALL - 0.32, SEG['sink'][0]), (WALL - 0.32, SEG['end'][0]), ORANGE, 4)   # LED strips at the front edges
xs = [Y0] + [SEG[n][1] for n, _, _ in units]
k.chain_v(XC - 0.75, xs, ['.05', '0.60', '0.60', '0.60', '0.60', '0.60', '.25'])
k.chain_v(XC - 1.25, [Y0, YE], ['3.30'])
k.chain_v(WALL - 0.3, [YE, 5.987], ['%.2f' % (5.987 - YE)])
k.chain_h(1.45, [XC, WALL], ['0.60'])
hx, hy = 12.35, 6.26                                                                    # french door: hinge, open leaf toward the kitchen
k.line((hx, hy), (hx, hy - 0.88), (200, 0, 140), 5); cx, cy = k.P(hx, hy); rr = 0.88 * k.k
k.d.arc([cx - rr, cy - rr, cx + rr, cy + rr], 180, 270, fill=(200, 0, 140), width=3)
k.save(H + 'out/byt_kitchen_plan.png')

# ---------- 3. kitchen elevation (east wall seen from the living room: north on the left, window wall on the right)
E = 260; X0, Z0 = 330, 880                                                              # px per metre, origin (plan y = Y0, z = 0)
W_ = int(X0 + (5.987 - Y0) * E + 260); img = Image.new('RGB', (W_, 1290), 'white'); d = ImageDraw.Draw(img)
P = lambda y, z: (X0 + (y - Y0) * E, Z0 - z * E)
def R(y0, y1, z0, z1, fill=FILL, out=BLUE, w=3): d.rectangle([*P(y0, z1), *P(y1, z0)], fill=fill, outline=out, width=w)
def T(y, z, s, col=BLUE, sz=20, b=True):
    cx, cy = P(y, z); l, t, r_, bb = d.textbbox((0, 0), s, font=F(sz, b)); d.text((cx - (r_ - l) / 2 - l, cy - (bb - t) / 2 - t), s, font=F(sz, b), fill=col)
def sock(y, z, n=1):
    for i in range(n):
        cx, cy = P(y + (i - (n - 1) / 2) * 0.07, z); d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], outline=RED, width=3); d.ellipse([cx - 4, cy - 2, cx - 1, cy + 1], fill=RED); d.ellipse([cx + 1, cy - 2, cx + 4, cy + 1], fill=RED)
d.text((24, 16), 'Ukázkový byt - kuchyň, pohled na stěnu linky (návrh)', font=F(34, True), fill=INK)
d.text((24, 62), 'Pohled z obýváku na východní stěnu: vlevo stěna haly (sever), vpravo okno (jih). Schéma, standardní moduly; ±3 cm.', font=F(20), fill=MUTED)
d.line([*P(Y0 - 0.15, 0), *P(5.987 + 0.2, 0)], fill=INK, width=4); d.line([*P(Y0, 0), *P(Y0, 2.75)], fill=INK, width=5)
d.line([*P(5.987, 0), *P(5.987, 2.75)], fill=INK, width=5); T(5.987 - 0.0, 2.85, 'okenní stěna', MUTED, 18, False)
for y in [Y0 + i * 0.12 for i in range(int((5.987 - Y0) / 0.12) + 1)]: d.line([*P(y, 2.75), *P(min(y + 0.06, 5.987), 2.75)], fill=MUTED, width=2)
T(Y0 + 0.5, 2.85, 'strop 2.75', MUTED, 18, False)
a, b = SEG['filler']; R(a, b, 0.15, 2.695, (200, 200, 200), BLUE, 2); R(a, b, 0, 0.15, (90, 90, 90), (90, 90, 90), 1)
a, b = SEG['fridge']; R(a, b, 0, 0.15, (90, 90, 90), (90, 90, 90), 1)
for z0, z1, s in ((0.155, 0.95, 'mrazák'), (0.953, 1.93, 'lednice'), (1.933, 2.40, ''), (2.403, 2.695, 'nástavec')):
    R(a, b, z0, z1, (190, 205, 230)); T((a + b) / 2, (z0 + z1) / 2, s, BLUE, 18)
sock((a + b) / 2, 2.15)
R(SEG['sink'][0], YE, 0, 0.15, (90, 90, 90), (90, 90, 90), 1)
for n, s in (('sink', 'dřez'), ('dw', 'myčka'), ('hob', ''), ('drawers', '')):
    a, b = SEG[n]
    if n == 'hob':
        R(a, b, 0.155, 0.265); R(a, b, 0.27, 0.86, (200, 200, 205)); T((a + b) / 2, 0.55, 'trouba', BLUE, 18); d.line([*P(a + 0.05, 0.92), *P(b - 0.05, 0.92)], fill=INK, width=6)
        T((a + b) / 2, 0.98, 'indukce', INK, 16); d.rectangle([*P(a + 0.2, 0.52), *P(b - 0.2, 0.45)], outline=RED, width=2); T((a + b) / 2, 0.36, '400 V', RED, 14)
    elif n == 'drawers':
        for z0, z1 in ((0.155, 0.40), (0.403, 0.63), (0.633, 0.865)): R(a, b, z0, z1)
        T((a + b) / 2, 0.28, 'šuplíky', BLUE, 18)
    else:
        R(a, b, 0.155, 0.865); T((a + b) / 2, 0.6, s, BLUE, 18)
        if n == 'sink': d.line([*P((a + b) / 2, 0.155), *P((a + b) / 2, 0.865)], fill=BLUE, width=2); sock(a + 0.15, 0.35)
        if n == 'dw': sock(a + 0.3, 0.35)
a, b = SEG['end']; R(a, b, 0.155, 0.865, GFILL, GREEN); R(a, b, 0, 0.15, (150, 190, 150), GREEN, 1); T((a + b) / 2, 0.5, 'R 0.25', GREEN, 15)
R(SEG['sink'][0], YE, 0.87, 0.91, (60, 60, 60), (60, 60, 60), 1)                           # worktop
T(SEG['hob'][0] - 0.3, 1.2, '', RED); sock(SEG['dw'][0] + 0.3, 1.15, 2); sock(SEG['drawers'][0] + 0.3, 1.15, 2)
for n, s in (('sink', 'odkapávač'), ('dw', ''), ('hob', 'digestoř uvnitř'), ('drawers', '')):
    a, b = SEG[n]
    if n == 'hob': R(a, b, 1.553, 2.40); R(a, b, 1.50, 1.553, (200, 200, 200), BLUE, 1); T((a + b) / 2, 1.9, s, (110, 40, 150), 17); sock((a + b) / 2, 2.2)
    elif n == 'drawers': R(a, b, 1.52, 1.90, (230, 215, 245), (110, 40, 150)); T((a + b) / 2, 1.71, 'mikrovlnka', (110, 40, 150), 17); R(a, b, 1.903, 2.40); sock((a + b) / 2, 2.2)
    else: R(a, b, 1.50, 2.40); T((a + b) / 2, 1.95, s, BLUE, 18)
    R(a, b, 2.403, 2.695); T((a + b) / 2, 2.55, 'nástavec', BLUE, 15)
a, b = SEG['end']; R(a, b, 1.50, 2.40, GFILL, GREEN); R(a, b, 2.403, 2.695, GFILL, GREEN)
d.line([*P(SEG['fridge'][0], 2.71), *P(YE, 2.71)], fill=ORANGE, width=6); T(YE + 0.45, 2.62, 'LED pásek nahoře', ORANGE, 18); T(YE + 0.45, 2.52, 'přední hrana, 30° do místnosti', ORANGE, 14, False)
d.line([*P(SEG['sink'][0], 1.485), *P(SEG['end'][0], 1.485)], fill=ORANGE, width=6); T(YE + 0.45, 1.45, 'LED pod skříňkami', ORANGE, 18); T(YE + 0.45, 1.35, 'stejný vypínač', ORANGE, 14, False)
d.rectangle([*P(5.987 - 0.06, 2.40), *P(5.987, 0.0)], fill=(225, 238, 248), outline=BLUE, width=2)
def ch(xs, z, labels):
    d.line([*P(xs[0], z), *P(xs[-1], z)], fill=RED, width=3)
    for x in xs: cx, cy = P(x, z); d.line([cx - 8, cy + 8, cx + 8, cy - 8], fill=RED, width=4)
    for i, (a, b) in enumerate(zip(xs, xs[1:])):
        cx, cy = P((a + b) / 2, z); l, t, r_, bb = d.textbbox((0, 0), labels[i], font=F(20, True)); w, h = r_ - l, bb - t
        d.rectangle([cx - w / 2 - 4, cy - h / 2 - 4, cx + w / 2 + 4, cy + h / 2 + 4], fill='white'); d.text((cx - w / 2 - l, cy - h / 2 - t), labels[i], font=F(20, True), fill=RED)
ch([Y0] + [SEG[n][1] for n, _, _ in units], -0.18, ['.05', '0.60', '0.60', '0.60', '0.60', '0.60', '.25']); ch([YE, 5.987], -0.18, ['%.2f' % (5.987 - YE)])
for z, s in ((0.15, '0.15'), (0.91, '0.91 pracovní deska'), (1.50, '1.50'), (2.40, '2.40'), (2.75, '2.75')):
    cx, cy = P(Y0 - 0.25, z); d.line([cx - 8, cy + 8, cx + 8, cy - 8], fill=RED, width=4); l, t, r_, bb = d.textbbox((0, 0), s, font=F(18, True)); d.text((cx - 14 - (r_ - l), cy - (bb - t) / 2 - t), s, font=F(18, True), fill=RED)
d.line([*P(Y0 - 0.25, 0), *P(Y0 - 0.25, 2.75)], fill=RED, width=2)
y = Z0 + 110
for s in ('Výšky: pracovní deska 0.91 (podle výšky loktů minus 10-15 cm); horní skříňky od 1.50 (min. 0.55 nad deskou), dvířka do 2.40, nástavce do 2.70.',
          'LED: skříňky končí 5 cm pod stropem 2.75; pásek na přední hraně nahoře (30° do místnosti) svítí na strop, pásek pod horními skříňkami na desku; jeden vypínač.',
          'Digestoř: recirkulační s uhlíkovým filtrem, pokud developer nepotvrdí odtah. Dodržet min. výšku nad deskou dle výrobce.',
          'Červená kolečka = zásuvky: dvojité nad deskou, jednoduché ve skříňkách (myčka, trouba, digestoř, mikrovlnka, lednice). Obdélník = přípojka 400 V.'):
    d.text((24, y), s, font=F(21), fill=INK); y += 34
img.save(H + 'out/byt_kitchen_elevation.png'); print('saved elevation', img.size)
