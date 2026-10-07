# Blender: the whole example flat (courtyard side) from app/*.json, styled by a configuration code. Copy of render/apartment.py (first flat).
# Plan coords: x east (bathroom west wall face = 0), y south (hall north wall face = 0), z up. Blender: (x, -y, z).
# SITE=app/site_<n>np.json selects the surroundings for the same flat on another floor (python3 site.py <n>).
# Run: blender -b -P apartment.py -- "<code>" OUTPREFIX views samples [scale%]
# Optional real sun: SUN="YYYY-MM-DD HH:MM" (Prague local time) blender ...; unset = the fixed default light.
import bpy, bmesh, sys, json, math, re, os
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'   # kit root
argv = sys.argv[sys.argv.index('--') + 1:]
CODE = argv[0]
OUT = argv[1]
VIEWS = argv[2].split(',')
SAMPLES = int(argv[3])
SCALE = int(argv[4]) if len(argv) > 4 else 100

APT = json.load(open(HERE + 'app/apartment.json'))
KIT = json.load(open(HERE + 'app/kitchen.json'))
SQ = HERE + 'oresi/texsq/'
PAINTS = {'P1': '#f1f0eb', 'P2': '#ede5d7', 'P3': '#d6d7d3', 'P4': '#c9bfb0', 'P5': '#b3bea9', 'P6': '#a7b9c4', 'P7': '#e0c9c0', 'P8': '#8a8867', 'P9': '#3c4a5f', 'P10': '#55585c'}
TILES = {'T1': '#efefeb', 'T2': '#cdcdc9', 'T3': '#d5c8b2', 'T4': '#a49d93', 'T5': '#47494c'}

# ---- parse code: 1:P10·F01 2:P9·B·F02·W02 3:P7·T5 4:P5·F11 5:P9·T4
cfg = {'paint': {}, 'tile': {}}
for part in re.split(r'\s+', CODE.strip()):
    rid, rest = part.split(':')
    v = re.split(r'[·.]', rest)
    rid = int(rid)
    cfg['paint'][rid] = v[0]
    if rid == 1: cfg['hallrobe'] = v[1]
    if rid == 2: cfg['layout'], cfg['front'], cfg['work'] = v[1], v[2], v[3]
    if rid in (3, 5): cfg['tile'][rid] = v[1]
    if rid == 4: cfg['bedrobe'] = v[1]
print('CONFIG', cfg)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
B = lambda x, y, z=0.0: (x, -y, z)


def lin(h):
    h = h.lstrip('#')
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(f(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


# ---------------- materials ----------------
MATS = {}
def principled(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1); p.inputs['Roughness'].default_value = rough; p.inputs['Metallic'].default_value = metal
    for k, v in kw.items():
        p.inputs[k].default_value = v if not isinstance(v, tuple) else (*v, 1)
    MATS[name] = m
    return m


def tex_box(name, path, size, rough=0.45, rot=0):
    m = principled(name, rough=rough); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    tc, mp, im = nt.nodes.new('ShaderNodeTexCoord'), nt.nodes.new('ShaderNodeMapping'), nt.nodes.new('ShaderNodeTexImage')
    im.image = bpy.data.images.load(path, check_existing=True); im.projection = 'BOX'; im.projection_blend = 0.15; im.extension = 'MIRROR'
    mp.inputs['Scale'].default_value = (1 / size,) * 3; mp.inputs['Rotation'].default_value = (0, 0, math.radians(rot))
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], im.inputs['Vector']); nt.links.new(im.outputs['Color'], p.inputs['Base Color'])
    return m


def tile_mat(name, hexc, row_h, rough=0.18):
    m = principled(name, rough=rough, **{'Coat Weight': 0.3}); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    tc, br = nt.nodes.new('ShaderNodeTexCoord'), nt.nodes.new('ShaderNodeTexBrick')
    br.offset = 0.0
    c = lin(hexc)
    br.inputs['Color1'].default_value = (*c, 1); br.inputs['Color2'].default_value = (*[v * 0.94 for v in c], 1)
    g = [min(1, v * 0.75 + 0.06) for v in c]
    br.inputs['Mortar'].default_value = (*g, 1); br.inputs['Scale'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = 0.0025; br.inputs['Brick Width'].default_value = 0.6; br.inputs['Row Height'].default_value = row_h
    nt.links.new(tc.outputs['UV'], br.inputs['Vector']); nt.links.new(br.outputs['Color'], p.inputs['Base Color'])
    return m


def fabric(name, hexc):
    m = principled(name, lin(hexc), 0.95, **{'Sheen Weight': 0.4}); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    nz, bm = nt.nodes.new('ShaderNodeTexNoise'), nt.nodes.new('ShaderNodeBump')
    nz.inputs['Scale'].default_value = 400; bm.inputs['Strength'].default_value = 0.15
    nt.links.new(nz.outputs['Fac'], bm.inputs['Height']); nt.links.new(bm.outputs['Normal'], p.inputs['Normal'])
    return m


def emit(name, hexc, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (*lin(hexc), 1); e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs['Emission'], nt.nodes['Material Output'].inputs['Surface'])
    MATS[name] = m; return m


def window_glass():
    m = bpy.data.materials.new('glass'); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    g, t, mix, lp = nt.nodes.new('ShaderNodeBsdfGlass'), nt.nodes.new('ShaderNodeBsdfTransparent'), nt.nodes.new('ShaderNodeMixShader'), nt.nodes.new('ShaderNodeLightPath')
    g.inputs['Roughness'].default_value = 0.0
    nt.links.new(lp.outputs['Is Shadow Ray'], mix.inputs['Fac']); nt.links.new(g.outputs['BSDF'], mix.inputs[1]); nt.links.new(t.outputs['BSDF'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], nt.nodes['Material Output'].inputs['Surface'])
    m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    MATS['glass'] = m; return m


for rid in (1, 2, 3, 4, 5):
    principled(f'paint:{rid}', lin(PAINTS[cfg['paint'][rid]]), 0.88)
for rid in (3, 5):
    tile_mat(f'tile:{rid}', TILES[cfg['tile'][rid]], 0.3)
    tile_mat(f'tilefloor:{rid}', TILES[cfg['tile'][rid]], 0.6, 0.3)
principled('ext', lin('#e4e2dc'), 0.9); principled('wallcore', lin('#2b2c2e'), 0.9); principled('ceiling', lin('#f4f4f2'), 0.95)
principled('skirt', lin('#f4f4f1'), 0.5)
tex_box('front', SQ + cfg['front'] + '.jpg', 0.6, 0.42)
tex_box('worktop', SQ + cfg['work'] + '.jpg', 0.9, 0.3, rot=90)
tex_box('splash', SQ + cfg['work'] + '.jpg', 1.2, 0.3)
tex_box('hallrobe', SQ + cfg['hallrobe'] + '.jpg', 0.6, 0.42)
tex_box('bedrobe', SQ + cfg['bedrobe'] + '.jpg', 0.6, 0.42)
tex_box('oak', SQ + 'W13.jpg', 0.9, 0.5); MATS['chairwood'] = MATS['oak']; MATS['table'] = MATS['oak']
principled('carcass', lin('#dededb'), 0.6); principled('plinth', lin('#1f1f1f'), 0.6)
principled('black_metal', lin('#141414'), 0.35, 1.0); principled('black', lin('#1b1b1b'), 0.45, 0.3)
principled('steel', lin('#b9b9b9'), 0.25, 1.0); principled('chrome', lin('#d6d6d6'), 0.08, 1.0)
principled('black_glass', lin('#060606'), 0.05, **{'Coat Weight': 1.0}); principled('screen', lin('#0a0a0b'), 0.12, **{'Coat Weight': 1.0})
principled('sink_granite', lin('#1c1c1c'), 0.45); principled('hob_ring', lin('#4a4a4a'), 0.25)
principled('door_white', lin('#f1f1ee'), 0.4); principled('window_frame', lin('#3b3e42'), 0.4); principled('entrydoor', lin('#5b5e62'), 0.5)
principled('white', lin('#f6f6f4'), 0.15, **{'Coat Weight': 0.5}); principled('mirror', lin('#e8ecef'), 0.02, 1.0)
principled('darkgrey', lin('#3d3f42'), 0.6); principled('pot', lin('#c9c4bb'), 0.85); principled('leaf', lin('#3f5a33'), 0.7)
fabric('fabric', '#bdb8af'); fabric('fabric2', '#7d8a7f'); fabric('fabric3', '#9c968d'); fabric('accent', '#c08a6a')
fabric('linen', '#f1f0ec'); fabric('duvet', '#e9e6df'); fabric('blanket', '#c9b9a0'); fabric('curtain', '#ece7dc')
fabric('rug', '#d8d0c2'); fabric('rug2', '#cfcac1'); fabric('bathmat', '#e4e1da'); fabric('doormat', '#4c4a46')
emit('led', '#ffd9b0', 6); emit('led_cove', '#ffd9b0', 8); emit('bulb', '#ffd2a0', 30)
m = bpy.data.materials.new('lampshade'); m.use_nodes = True; nt = m.node_tree   # fabric shade: the bulb inside shines through it
nt.nodes.remove(nt.nodes['Principled BSDF'])
d, t, mx = nt.nodes.new('ShaderNodeBsdfDiffuse'), nt.nodes.new('ShaderNodeBsdfTranslucent'), nt.nodes.new('ShaderNodeMixShader')
d.inputs['Color'].default_value = (*lin('#efe6d6'), 1); t.inputs['Color'].default_value = (*lin('#ffe2b8'), 1); mx.inputs['Fac'].default_value = 0.6
nt.links.new(d.outputs[0], mx.inputs[1]); nt.links.new(t.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
MATS['lampshade'] = m
principled('shade_in', lin('#f4f1ea'), 0.8)
LED = os.environ.get('LED', '1') == '1'          # LED cove strips on top of the tall units (walk-through / web switch them)
scn['led_cove'] = int(LED)
MATS['led_cove']['base_strength'] = MATS['led_cove'].node_tree.nodes['Emission'].inputs['Strength'].default_value
MATS['led_cove'].node_tree.nodes['Emission'].inputs['Strength'].default_value *= LED


def cove_light(x0, y0, x1, y1, z, d=(0, 0, 1)):   # Blender coords: area light along an LED strip emitting along d (up, tilted, or down), 60 W/m (default look)
    L = max(x1 - x0, y1 - y0)
    ld = bpy.data.lights.new('cove', 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = .03, L
    ld.energy = 60 * L * LED; ld.color = (1.0, 0.86, 0.68); ld['base_energy'] = 60 * L
    lo = bpy.data.objects.new('cove', ld); scn.collection.objects.link(lo); lo.location = ((x0 + x1) / 2, (y0 + y1) / 2, z + (.005 if d[2] >= 0 else -.003))
    zl = -Vector(d).normalized(); yl = Vector((1, 0, 0) if x1 - x0 >= y1 - y0 else (0, 1, 0)); yl = (yl - yl.dot(zl) * zl).normalized(); xl = yl.cross(zl)
    lo.rotation_euler = Matrix((xl, yl, zl)).transposed().to_euler()      # area lights emit along local -Z; local Y along the strip


window_glass()
fl = tex_box('vinyl', HERE + 'oresi/tex/FLOOR2.jpg', 1, 0.42)
for n in list(fl.node_tree.nodes):   # planks use explicit UVs instead of box projection
    if n.type in ('TEX_COORD', 'MAPPING'): fl.node_tree.nodes.remove(n)
im = [n for n in fl.node_tree.nodes if n.type == 'TEX_IMAGE'][0]; im.projection = 'FLAT'; im.extension = 'EXTEND'
uvn = fl.node_tree.nodes.new('ShaderNodeUVMap'); fl.node_tree.links.new(uvn.outputs['UV'], im.inputs['Vector'])
tile_mat('deck', '#a9aaa6', 0.4, 0.85); MATS['deck'].node_tree.nodes['Brick Texture'].inputs['Brick Width'].default_value = 0.4


# ---------------- geometry helpers ----------------
def mesh_obj(name, verts, faces, mat, uvs=None, smooth=False):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    if uvs is not None:
        uv = me.uv_layers.new(name='UVMap')
        k = 0
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[k]; k += 1
    if smooth:
        for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); scn.collection.objects.link(ob)
    ob.data.materials.append(MATS[mat] if isinstance(mat, str) else mat)
    return ob


def box(x0, y0, x1, y1, z0, z1, mat, bevel=0.0, name='box'):
    xa, xb = sorted((x0, x1)); ya, yb = sorted((y0, y1)); za, zb = sorted((z0, z1))
    v = [B(xa, ya, za), B(xb, ya, za), B(xb, yb, za), B(xa, yb, za), B(xa, ya, zb), B(xb, ya, zb), B(xb, yb, zb), B(xa, yb, zb)]
    f = [tuple(reversed(t)) for t in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
    ob = mesh_obj(name, v, f, mat)
    b = min(bevel, (xb - xa) / 2 - 0.001, (yb - ya) / 2 - 0.001, (zb - za) / 2 - 0.001)
    if b > 0.002:
        md = ob.modifiers.new('bevel', 'BEVEL'); md.width = b; md.segments = 3; md.limit_method = 'NONE'
    return ob


def arc_obj(name, c, r0, r1, a0, a1, z0, z1, mat, seg=16):
    """ring sector (r0 = 0: pie slice) from z0 to z1; centre c and angles a0..a1 (degrees) in Blender XY"""
    ang = [math.radians(a0 + (a1 - a0) * i / seg) for i in range(seg + 1)]
    pts = [(c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a)) for a in ang]
    pts += [(c[0] + r0 * math.cos(a), c[1] + r0 * math.sin(a)) for a in reversed(ang)] if r0 > 0 else [tuple(c)]
    n = len(pts)
    v = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    f = [tuple(range(n))[::-1], tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    ob = mesh_obj(name, v, f, mat)
    for i, p in enumerate(ob.data.polygons[2:]): p.use_smooth = i < seg or (r0 > 0 and seg < i <= 2 * seg)   # curved sides only
    return ob


def cyl(x, y, z0, z1, r0, r1, mat, seg=32, name='cyl', open_top=False):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=not open_top, cap_tris=False, segments=seg, radius1=r0, radius2=r1, depth=z1 - z0)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(B(x, y, (z0 + z1) / 2)))
    for f in bm.faces: f.smooth = len(f.verts) == 4
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scn.collection.objects.link(ob); ob.data.materials.append(MATS[mat]); return ob


def quads_obj(name, quads, mat):   # quads: list of (4 points (plan x,y,z), 4 uvs)
    if not quads: return None
    verts, faces, uvs = [], [], []
    for P, U in quads:
        i = len(verts); verts += [B(*p) for p in P]; faces.append((i, i + 1, i + 2, i + 3)); uvs += U
    return mesh_obj(name, verts, faces, mat, uvs)


def room_at(x, y):
    for r in APT['rooms']:
        for x0, y0, x1, y1 in r['rects']:
            if x0 - 0.001 <= x <= x1 + 0.001 and y0 - 0.001 <= y <= y1 + 0.001: return r['id']
    return 0
ROOMS = {r['id']: r for r in APT['rooms']}
H = 2.75

# ---------------- walls with per-room finishes ----------------
FIN = {}
def add_q(key, P, U): FIN.setdefault(key, []).append((P, U))
def wall(x0, y0, x1, y1, zb, zt):
    box(x0, y0, x1, y1, zb, zt, 'wallcore', name='wall')
    e, off = 0.03, 0.0015
    def runs(L, sample):
        n = max(1, round(L / 0.04)); out = []; cur = None
        for i in range(n):
            t0, t1 = i / n * L, (i + 1) / n * L; rid = sample((t0 + t1) / 2)
            if cur and cur[0] == rid: cur[2] = t1
            else: cur = [rid, t0, t1]; out.append(cur)
        return out
    sides = [
        (x1 - x0, lambda t: room_at(x0 + t, y0 - e), lambda t, z, o: (x0 + t, y0 - o, z)),
        (x1 - x0, lambda t: room_at(x0 + t, y1 + e), lambda t, z, o: (x0 + t, y1 + o, z)),
        (y1 - y0, lambda t: room_at(x0 - e, y0 + t), lambda t, z, o: (x0 - o, y0 + t, z)),
        (y1 - y0, lambda t: room_at(x1 + e, y0 + t), lambda t, z, o: (x1 + o, y0 + t, z)),
    ]
    for L, sample, mk in sides:
        for rid, a, b in runs(L, sample):
            r = ROOMS.get(rid)
            key = f'paint:{rid}' if 1 <= rid <= 5 else 'ext'
            spans = [(zb, min(zt, r['tileH']), f'tile:{rid}'), (min(zt, r['tileH']), zt, key)] if r and r.get('tileH') and zb < r['tileH'] else [(zb, zt, key)]
            for z0, z1, k in spans:
                if z1 - z0 > 0.001:
                    add_q(k, [mk(a, z0, off), mk(b, z0, off), mk(b, z1, off), mk(a, z1, off)], [(a, z0), (b, z0), (b, z1), (a, z1)])
            if zb == 0 and r and r['floor'] == 'vinyl':
                add_q('skirt', [mk(a, 0, 0.012), mk(b, 0, 0.012), mk(b, 0.06, 0.012), mk(a, 0.06, 0.012)], [(0, 0), (1, 0), (1, 1), (0, 1)])
                add_q('skirt', [mk(a, 0.06, off), mk(b, 0.06, off), mk(b, 0.06, 0.012), mk(a, 0.06, 0.012)], [(0, 0), (1, 0), (1, 1), (0, 1)])

for w in APT['walls']: wall(*w, 0, H)
for o in APT['openings']:
    x0, y0, x1, y1 = o['rect']; head = 2.02 if o['kind'] == 'door' else 2.4
    wall(x0, y0, x1, y1, head, H)
    if o['kind'] == 'door' and not o.get('entry'):
        vert, e = (x1 - x0) < (y1 - y0), 0.02
        if vert: box(x0 - e, y0, x1 + e, y0 + 0.05, 0, head, 'door_white'); box(x0 - e, y1 - 0.05, x1 + e, y1, 0, head, 'door_white'); box(x0 - e, y0, x1 + e, y1, head - 0.05, head, 'door_white')
        else: box(x0, y0 - e, x0 + 0.05, y1 + e, 0, head, 'door_white'); box(x1 - 0.05, y0 - e, x1, y1 + e, 0, head, 'door_white'); box(x0, y0 - e, x1, y1 + e, head - 0.05, head, 'door_white')
    if o['kind'] == 'window':
        g, along_x = o['glass'], o['n'][1] != 0
        a0, a1 = (x0, x1) if along_x else (y0, y1)
        Q = (lambda a, b, d, z0, z1, m, name='box': box(a, g - d, b, g + d, z0, z1, m, name=name)) if along_x else (lambda a, b, d, z0, z1, m, name='box': box(g - d, a, g + d, b, z0, z1, m, name=name))
        Q(a0, a1, 0.008, 0.04, head - 0.06, 'glass', 'glass')
        mull = o['door'][1] if abs(o['door'][0] - a0) < 0.2 else o['door'][0]          # mullion at the french door's inner edge
        for aa in (a0, mull, a1 - 0.06): Q(aa, aa + 0.06, 0.04, 0, head, 'window_frame')
        Q(a0, a1, 0.04, head - 0.06, head, 'window_frame'); Q(a0, a1, 0.04, 0, 0.04, 'window_frame')
for k, q in FIN.items(): quads_obj('fin_' + k, q, k)

# ---------------- floors and ceilings ----------------
def h1(i): return abs(math.sin(i * 12.9898) * 43758.5453) % 1
def planks(rects, name):
    quads = []
    for x0, y0, x1, y1 in rects:
        c = math.floor(x0 / 0.2)
        while c * 0.2 < x1:
            off = h1(c + 101) * 0.8; cx0 = c * 0.2
            k = math.floor((y0 - off) / 0.8)
            while k * 0.8 + off < y1:
                py0 = k * 0.8 + off; pid = c * 1000 + k
                ax, bx, ay, by = max(cx0, x0) + 0.001, min(cx0 + 0.2, x1) - 0.001, max(py0, y0) + 0.001, min(py0 + 0.8, y1) - 0.001
                if bx > ax and by > ay:
                    su, fl = (0.5 if h1(pid) > 0.5 else 0) + 0.01, h1(pid + 7) > 0.5
                    U = lambda x, y: (su + 0.48 * (x - cx0) / 0.2, 1 - (y - py0) / 0.8 if fl else (y - py0) / 0.8)
                    quads.append(([(ax, ay, 0), (bx, ay, 0), (bx, by, 0), (ax, by, 0)], [U(ax, ay), U(bx, ay), U(bx, by), U(ax, by)]))
                k += 1
            c += 1
    ob = quads_obj(name, quads, 'vinyl')
    for p in ob.data.polygons: p.flip()   # mirrored Y -> keep normals up
    return ob
for r in ((7.119, -0.34, 13.2, 6.447), (-0.39, 5.981, 7.585, 9.38), (5.521, 3.65, 7.119, 5.981)): box(*r, -0.06, -0.003, 'plinth', name='subfloor')   # flat outline (L-shaped)
box(-6, -6, 19, 15, -0.5, -0.45, 'ext', name='groundplane').hide_render = True   # plan-view backdrop only (the plan view shows it)
for r in APT['rooms']:
    if r['floor'] == 'vinyl': planks(r['rects'], f'floor{r["id"]}')
    else:
        key = f'tilefloor:{r["id"]}' if r['floor'] == 'tile' else 'deck'
        ob = quads_obj(f'floor{r["id"]}', [([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]) for x0, y0, x1, y1 in r['rects']], key)
        for p in ob.data.polygons: p.flip()
    if r['ceil']:
        for x0, y0, x1, y1 in r['rects']:
            c = box(x0 - 0.02, y0 - 0.02, x1 + 0.02, y1 + 0.02, r['ceil'], r['ceil'] + 0.05, 'ceiling', name='ceiling')
planks([o['rect'] for o in APT['openings'] if o['kind'] == 'door' and not o.get('entry')], 'thresholds')

# ---------------- furniture ----------------
SIDE = {'+x': (1, 0), '-x': (-1, 0), '+y': (0, 1), '-y': (0, -1)}
OPP = {'+x': '-x', '-x': '+x', '+y': '-y', '-y': '+y'}
LAMPS = []
def furniture(f):
    x0, y0, x1, y1 = f['r']; z0, z1 = f['z']; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; k = f['kind']; m = f['m']
    def along(side, d):
        return {'+x': (x1 - d, y0, x1, y1), '-x': (x0, y0, x0 + d, y1), '+y': (x0, y1 - d, x1, y1), '-y': (x0, y0, x1, y0 + d)}[side]
    if k == 'box': box(x0, y0, x1, y1, z0, z1, m)
    elif k == 'rug': box(x0, y0, x1, y1, 0.001, z1, m, 0.004)
    elif k == 'tvunit':
        for lx, ly in ((x0 + .06, y0 + .06), (x0 + .06, y1 - .06), (x1 - .06, y0 + .06), (x1 - .06, y1 - .06)): cyl(lx, ly, 0, .12, .012, .012, 'black_metal', 10)
        box(x0, y0, x1, y1, .12, z1, 'oak', .01); box(x0 + .08, cy - .4, x1 - .06, cy + .4, z1, z1 + .06, 'black', .02)
    elif k == 'tv': box(x0, y0, x1 + .02, y1, z0, z1, 'black', .008); box(x1 + .02, y0 + .01, x1 + .021, y1 - .01, z0 + .01, z1 - .01, 'screen')
    elif k == 'sofa':
        dx = SIDE[f['back']][0]
        for lx, ly in ((x0 + .06, y0 + .06), (x0 + .06, y1 - .06), (x1 - .06, y0 + .06), (x1 - .06, y1 - .06)): cyl(lx, ly, 0, .1, .02, .015, 'oak', 12)
        box(x0, y0, x1, y1, .1, .3, m, .04)
        bk = along(f['back'], .2); box(*bk, .3, .72, m, .06)
        box(x0, y0, x1, y0 + .15, .3, .62, m, .06); box(x0, y1 - .15, x1, y1, .3, .62, m, .06)
        mid = (y0 + y1) / 2; sx0, sx1 = (x0 + .02, x1 - .2) if dx > 0 else (x0 + .22, x1 - .02)
        box(sx0, y0 + .15, sx1, mid - .005, .3, .45, m, .07); box(sx0, mid + .005, sx1, y1 - .15, .3, .45, m, .07)
        bx0 = x1 - .36 if dx > 0 else x0 + .2
        box(bx0, y0 + .15, bx0 + .16, mid - .005, .45, .82, m, .07); box(bx0, mid + .005, bx0 + .16, y1 - .15, .45, .82, m, .07)
        box(bx0 - .1, y0 + .2, bx0 + .02, y0 + .6, .45, .83, 'accent', .06); box(bx0 - .1, y1 - .6, bx0 + .02, y1 - .2, .45, .83, 'fabric2', .06)
    elif k == 'armchair':
        s = (x1 - x0) / 2; parts = []
        for lx, ly in ((-s + .06, -s + .06), (s - .06, -s + .06), (-s + .06, s - .06), (s - .06, s - .06)): parts.append(cyl(lx, ly, 0, .14, .018, .012, 'oak', 10))
        parts += [box(-s, -s, s, s, .14, .3, m, .05), box(-s + .1, -s + .14, s - .1, s - .02, .3, .44, m, .06), box(-s, -s, s, -s + .15, .3, .8, m, .07),
                  box(-s, -s, -s + .11, s, .3, .6, m, .05), box(s - .11, -s, s, s, .3, .6, m, .05)]
        emp = bpy.data.objects.new('armchair', None); scn.collection.objects.link(emp); emp.location = B(cx, cy, 0); emp.rotation_euler = (0, 0, math.radians(f.get('yaw', 0)))
        for p in parts: p.parent = emp
    elif k == 'coffeetable':
        r = (x1 - x0) / 2; cyl(cx, cy, z1 - .025, z1, r, r, 'oak', 64)
        for i in range(3):
            a = i * 2.094; cyl(cx + math.cos(a) * r * .6, cy + math.sin(a) * r * .6, 0, z1 - .025, .018, .012, 'black_metal', 10)
        if z1 < .5: box(cx - .14, cy - .1, cx + .12, cy + .08, z1, z1 + .04, 'accent', .005); cyl(cx + .15, cy + .12, z1, z1 + .12, .05, .04, 'white', 20)
    elif k == 'floorlamp':
        cyl(cx, cy, 0, .02, .13, .13, 'black', 32); cyl(cx, cy, .02, z1 - .3, .012, .012, 'black', 8)
        cyl(cx, cy, z1 - .32, z1, .18, .14, 'lampshade', 32, open_top=True); LAMPS.append((cx, cy, z1 - .25, 25))
    elif k == 'plant':
        r = (x1 - x0) / 2; ph = min(.35, z1 * .3); cyl(cx, cy, 0, ph, r, r * .75, 'pot', 24)
        seed = cx * 13.1 + cy * 7.7
        for i in range(9):
            a, rad = seed + i * 2.4, .05 + (i % 3) * .06; hh = ph + .15 + (i / 9) * (z1 - ph - .2)
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=.11 + (i % 4) * .03, location=B(cx + math.cos(a) * rad, cy + math.sin(a) * rad, hh))
            o = bpy.context.active_object; o.scale = (1, 1, .7); o.rotation_euler = (a, a * .7, 0); o.data.materials.append(MATS['leaf'])
    elif k == 'table':
        box(x0, y0, x1, y1, z1 - .035, z1, 'oak', .008)
        for lx, ly in ((x0 + .07, y0 + .07), (x1 - .07, y0 + .07), (x0 + .07, y1 - .07), (x1 - .07, y1 - .07)): cyl(lx, ly, 0, z1 - .035, .025, .018, 'oak', 12)
        cyl(cx, cy, z1, z1 + .18, .06, .05, 'pot', 20)
    elif k == 'chair':
        dx, dy = SIDE[f['face']]
        for lx, ly in ((x0 + .04, y0 + .04), (x1 - .04, y0 + .04), (x0 + .04, y1 - .04), (x1 - .04, y1 - .04)): cyl(lx, ly, 0, .44, .014, .011, 'oak', 10)
        box(x0, y0, x1, y1, .43, .47, m, .02); bk = along(OPP[f['face']], .04); box(*bk, .6, z1, m, .015)
        for px, py in ([(bk[0], y0 + .03), (bk[0], y1 - .05)] if dx else [(x0 + .03, bk[1]), (x1 - .05, bk[1])]): box(px, py, px + .02, py + .02, .47, .6, 'oak')
    elif k == 'pendant':
        cyl(cx, cy, z0 + .22, 2.75, .003, .003, 'black', 6); cyl(cx, cy, z0, z0 + .22, .2, .04, 'black', 40, open_top=True)
        cyl(cx, cy, z0 + .003, z0 + .217, .196, .037, 'shade_in', 40, open_top=True)          # matte white inside, lit by the bulb
        bpy.ops.mesh.primitive_uv_sphere_add(radius=.045, location=B(cx, cy, z0 + .06)); b = bpy.context.active_object
        b.data.materials.append(MATS['bulb']); b.visible_shadow = False                         # the light sits inside the bulb
        LAMPS.append((cx, cy, z0 + .06, 200))      # inside the shade: lit opening and a cone of light on the table
    elif k == 'curtain':
        ax = x1 - x0 >= y1 - y0; n, w = 60, (x1 - x0 if ax else y1 - y0); folds = max(4, round(w / .1)); verts, faces = [], []
        for i in range(n + 1):
            t = i / n; o = math.sin(t * folds * math.pi * 2) * .03
            px_, py_ = (x0 + t * w, cy + o) if ax else (cx + o, y0 + t * w)
            verts += [B(px_, py_, z0), B(px_, py_, z1)]
            if i < n: a = i * 2; faces.append((a, a + 2, a + 3, a + 1))
        ob = mesh_obj('curtain', verts, faces, 'curtain', smooth=True); sol = ob.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = .004
        if ax: box(x0 - .05, cy - .01, x1 + .05, cy + .01, z1, z1 + .02, 'black')
        else: box(cx - .01, y0 - .05, cx + .01, y1 + .05, z1, z1 + .02, 'black')
    elif k == 'bed' and f['head'] == '-y':
        box(x0, y0, x1, y1, .06, .32, m, .03); box(*along('-y', .1), .06, z1, m, .05)
        box(x0 + .03, y0 + .1, x1 - .03, y1 - .02, .32, .52, 'linen', .06)
        box(x0 - .02, y0 + .55, x1 + .02, y1 + .01, .45, .6, 'duvet', .06)
        box(x0 - .025, y1 - .485, x1 + .025, y1 + .015, .47, .615, 'blanket', .04)
        mid = (x0 + x1) / 2
        for a, b in ((x0 + .1, mid - .03), (mid + .03, x1 - .1)): box(a, y0 + .12, b, y0 + .54, .52, .68, 'linen', .06)
        box(mid - .25, y0 + .56, mid + .25, y0 + .69, .55, .78, 'accent', .05)
    elif k == 'bed':
        hx = SIDE[f['head']][0]
        box(x0, y0, x1, y1, .06, .32, m, .03); box(*along(f['head'], .1), .06, z1, m, .05)
        mx0, mx1 = (x0 + .02, x1 - .1) if hx > 0 else (x0 + .1, x1 - .02); box(mx0, y0 + .03, mx1, y1 - .03, .32, .52, 'linen', .06)
        dx0, dx1 = (x0 - .01, x1 - .55) if hx > 0 else (x0 + .55, x1 + .01); box(dx0, y0 - .02, dx1, y1 + .02, .45, .6, 'duvet', .06)
        tx0 = x0 - .015 if hx > 0 else x1 - .5; box(tx0, y0 - .025, tx0 + .5, y1 + .025, .47, .615, 'blanket', .04)
        px0, mid = (x1 - .55 if hx > 0 else x0 + .12), (y0 + y1) / 2
        for a, b in ((y0 + .1, mid - .03), (mid + .03, y1 - .1)): box(px0, a, px0 + .42, b, .52, .68, 'linen', .06)
        box(px0 - .15, mid - .25, px0 - .02, mid + .25, .55, .78, 'accent', .05)
    elif k == 'nightstand':
        box(x0, y0, x1, y1, .12, z1, 'oak', .015)
        for lx, ly in ((x0 + .04, y0 + .04), (x0 + .04, y1 - .04), (x1 - .04, y0 + .04), (x1 - .04, y1 - .04)): cyl(lx, ly, 0, .12, .01, .01, 'black_metal', 8)
        cyl(cx, cy, z1, z1 + .03, .06, .06, 'pot', 20); cyl(cx, cy, z1 + .03, z1 + .3, .008, .008, 'black', 8)
        cyl(cx, cy, z1 + .25, z1 + .42, .11, .09, 'lampshade', 28, open_top=True); LAMPS.append((cx, cy, z1 + .32, 8))
    elif k == 'desk':
        box(x0, y0, x1, y1, z1 - .03, z1, 'oak', .006)
        for yy in (y0 + .05, y1 - .07): box(x0 + .04, yy, x1 - .04, yy + .02, 0, .02, 'black_metal'); box(cx - .01, yy, cx + .01, yy + .02, 0, z1 - .03, 'black_metal')
        box(cx - .12, cy - .17, cx + .12, cy + .17, z1, z1 + .015, 'darkgrey', .005)
    elif k == 'officechair':
        for i in range(5):
            a = i * 1.2566; box(cx + math.cos(a) * .15 - .02, cy + math.sin(a) * .15 - .02, cx + math.cos(a) * .15 + .02, cy + math.sin(a) * .15 + .02, .04, .07, 'black_metal')
        cyl(cx, cy, .06, .42, .025, .025, 'chrome', 12); box(cx - .24, cy - .24, cx + .24, cy + .24, .42, .5, m, .04); box(cx + .2, cy - .22, cx + .26, cy + .22, .55, 1.0, m, .03)
    elif k == 'robe':
        dx, dy = SIDE[f['face']]; fr = along(f['face'], .02); body = along(OPP[f['face']], (x1 - x0 if dx else y1 - y0) - .02)
        box(*body, 0, z1, 'carcass'); L = y1 - y0 if dx else x1 - x0; n = max(1, round(L / .55))
        zt = 2.4 if z1 > 2.45 else z1       # up to the ceiling: doors to 2.4 m + a row of top boxes (as the kitchen units)
        for i in range(n):
            a, b = i / n, (i + 1) / n
            r = (fr[0], y0 + a * L + .002, fr[2], y0 + b * L - .002) if dx else (x0 + a * L + .002, fr[1], x0 + b * L - .002, fr[3])
            box(*r, .08, zt - .002, m)
            if zt < z1: box(*r, zt + .001, z1 - .002, m)
            hx = (fr[2] + .025 if dx > 0 else fr[0] - .025) if dx else (r[0] + .05 if i % 2 else r[2] - .05)
            hy = (r[1] + .05 if i % 2 else r[3] - .05) if dx else (fr[3] + .025 if dy > 0 else fr[1] - .025)
            box(hx - .006, hy - .006, hx + .006, hy + .006, .85, 1.55, 'black_metal')
        box(*fr, 0, .08, 'plinth')
        if zt < z1:                         # LED strip on top at the front edge, tilted 30° toward the room (as the kitchen units)
            bx0, by0, bx1, by1 = body
            if dx: fx = bx1 - .032 if dx > 0 else bx0 + .02; sx0, sy0, sx1, sy1 = fx, by0 + .03, fx + .012, by1 - .03
            else: fy = by1 - .032 if dy > 0 else by0 + .02; sx0, sy0, sx1, sy1 = bx0 + .03, fy, bx1 - .03, fy + .012
            box(sx0, sy0, sx1, sy1, z1, z1 + .006, 'led_cove', name='cove_robe')
            a, b = B(sx0, sy0, 0), B(sx1, sy1, 0); t = math.radians(30)
            cove_light(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), z1 + .006, (math.sin(t) * dx, -math.sin(t) * dy, math.cos(t)))
    elif k == 'bath':
        ob = box(x0, y0, x1, y1, 0, z1, 'white', .02, name='vana'); c = box(x0 + .07, y0 + .07, x1 - .07, y1 - .07, .15, z1 + .1, 'white', name='vana_cut')
        c.hide_render = True; c.hide_viewport = True; md = ob.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = c
        cyl(x1 - .12, y0 + .035, z1, z1 + .1, .015, .015, 'chrome', 12); box(x1 - .127, y0 + .035, x1 - .113, y0 + .16, z1 + .085, z1 + .1, 'chrome')
    elif k == 'washer' and SIDE[f['face']][0]:
        box(x0, y0, x1, y1, 0, z1, 'white', .02); xx = x1 + .01 if SIDE[f['face']][0] > 0 else x0 - .01
        bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=.19, depth=.02, location=B(xx, cy, .42), rotation=(0, math.pi / 2, 0)); bpy.context.active_object.data.materials.append(MATS['black_glass'])
    elif k == 'washer':
        box(x0, y0, x1, y1, 0, z1, 'white', .02); s = 1 if SIDE[f['face']][1] > 0 else -1; yy = y1 if s > 0 else y0
        cyl(cx, yy + s * .01, .25, .59, .19, .19, 'chrome', 40).rotation_euler = (0, 0, 0)
        ob = bpy.data.objects[-1] if False else None
        bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=.19, depth=.02, location=B(cx, yy + s * .01, .42), rotation=(math.pi / 2, 0, 0)); bpy.context.active_object.data.materials.append(MATS['black_glass'])
    elif k == 'toilet':
        dx, dy = SIDE[f['face']]; panel = along(OPP[f['face']], .14); box(*panel, 0, 1.1, 'white')
        bowl = along(f['face'], (x1 - x0 if dx else y1 - y0) - .14); sx, sy = (.03 if dy else 0), (.03 if dx else 0)
        box(bowl[0] + sx, bowl[1] + sy, bowl[2] - sx, bowl[3] - sy, z0, z1, 'white', .08); box(bowl[0] + sx, bowl[1] + sy, bowl[2] - sx, bowl[3] - sy, z1, z1 + .02, 'white', .05)
    elif k == 'vanity' and SIDE[f['face']][0]:
        box(x0, y0, x1, y1, z0, z1 - .06, 'oak', .01); box(x0 - .005, y0 - .005, x1 + .005, y1 + .005, z1 - .06, z1, 'white', .015)
        dx = SIDE[f['face']][0]; wx = x0 + .05 if dx > 0 else x1 - .05; cyl(wx, cy, z1, z1 + .16, .014, .014, 'chrome', 12)
        box(min(wx, wx + dx * .14), cy - .012, max(wx, wx + dx * .14), cy + .012, z1 + .14, z1 + .165, 'chrome')
    elif k == 'vanity':
        box(x0, y0, x1, y1, z0, z1 - .06, 'oak', .01); box(x0 - .005, y0 - .005, x1 + .005, y1 + .005, z1 - .06, z1, 'white', .015)
        dy = SIDE[f['face']][1]; wy = y1 - .05 if dy < 0 else y0 + .05; cyl(cx, wy, z1, z1 + .16, .014, .014, 'chrome', 12)
        box(cx - .012, min(wy, wy - dy * .14), cx + .012, max(wy, wy - dy * .14), z1 + .14, z1 + .165, 'chrome')
    elif k == 'mirror' and SIDE[f['face']][0]:
        box(x0, y0, x1, y1, z0, z1, 'mirror'); fx = x1 if SIDE[f['face']][0] > 0 else x0 - .004; box(fx, y0, fx + .004, y1, z0 - .01, z0, 'led')
    elif k == 'mirror':
        box(x0, y0, x1, y1, z0, z1, 'mirror'); fy = y0 - .004 if SIDE[f['face']][1] < 0 else y1; box(x0, fy, x1, fy + .004, z0 - .01, z0, 'led')
    elif k == 'basin':
        box(x0, y0, x1, y1, z0, z1, 'white', .03); wy = y1 - .03 if SIDE[f['face']][1] < 0 else y0 + .03; cyl(cx, wy, z1, z1 + .12, .01, .01, 'chrome', 10)
    elif k == 'shower':
        box(x0 + .003, y0 + .003, x1 - .003, y1 - .003, 0, .035, 'white'); gx0, gy0, gx1, gy1 = f['glass']
        box(gx0, gy0, gx1, gy1, .035, z1, 'glass', name='glass'); box(gx0 - .004, gy0, gx1 + .004, gy0 + .02, .035, z1, 'chrome')
        hx, hy = x1 - .02, y1 - .45; box(hx - .015, hy - .015, hx, hy + .015, 1.0, z1 + .05, 'chrome'); box(hx - .32, hy - .01, hx, hy + .01, z1 + .03, z1 + .05, 'chrome')
        cyl(hx - .32, hy, z1 + .01, z1 + .03, .13, .13, 'chrome', 40)
    elif k == 'towelrail':
        for yy in (y0, y1 - .025): box(x0, yy, x1, yy + .025, z0, z1, 'chrome')
        z = z0 + .06
        while z < z1 - .03: box(x0 + .005, y0, x1 - .005, y1, z, z + .018, 'chrome'); z += .11
    elif k == 'entrydoor': box(x0, y0, x1, y1, z0, z1, m)
_pre = set(scn.objects)
for f in APT['furniture']: furniture(f)
for d in APT['doors']:
    (hx, hy), (dx, dy), w, t = d['hinge'], d['dir'], d['w'], .04
    r = (hx, hy - t / 2, hx + dx * w, hy + t / 2) if dx else (hx - t / 2, hy, hx + t / 2, hy + dy * w)
    ob = box(min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3]), .01, 1.98, 'door_white', .006, name='door')
    # pivot at the hinge; 'door_close' = z rotation from the built (open) position to closed in its opening (walk-through: E)
    ox0, oy0, ox1, oy1 = next(o['rect'] for o in APT['openings'] if o['kind'] == 'door' and o['rect'][0] - .1 <= hx <= o['rect'][2] + .1 and o['rect'][1] - .1 <= hy <= o['rect'][3] + .1)
    cx_, cy_ = ((1 if (ox0 + ox1) / 2 > hx else -1), 0) if ox1 - ox0 > oy1 - oy0 else (0, (1 if (oy0 + oy1) / 2 > hy else -1))
    hp = Vector(B(hx, hy, 0)); ob.data.transform(Matrix.Translation(-hp)); ob.location = hp
    ob['door_close'] = math.atan2(dx * -cy_ - (-dy) * cx_, dx * cx_ + dy * cy_)

# ---------------- kitchen (Blender coords already) ----------------
G = KIT[cfg['layout']]
def kb(a, b, m, name='kit'):
    return box(a[0], -b[1], b[0], -a[1], a[2], b[2], m if m in MATS else 'carcass', name=name)
c0, c1 = G['cut']
cut = kb(c0, c1, 'carcass', 'sink_cut'); cut.hide_render = True; cut.hide_viewport = True
for o in G['box']:
    ob = kb(o['a'], o['b'], o['m'], o['n'])
    if o['n'] in ('worktop_long', 'base_carcass'):
        md = ob.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cut
for o in G.get('arc', []): arc_obj(o['n'], o['c'], o['r0'], o['r1'], o['a0'], o['a1'], o['z0'], o['z1'], o['m'] if o['m'] in MATS else 'carcass')
for o in G['box']:
    if o['m'] == 'led_cove': d = o.get('dir', (0, 0, 1)); cove_light(o['a'][0], o['a'][1], o['b'][0], o['b'][1], o['b'][2] if d[2] >= 0 else o['a'][2], d)
w0, w1 = G['bowl']; t = .01
for a, b in ((w0, (w1[0], w1[1], w0[2] + t)), (w0, (w0[0] + t, w1[1], w1[2])), ((w1[0] - t, w0[1], w0[2]), w1), (w0, (w1[0], w0[1] + t, w1[2])), ((w0[0], w1[1] - t, w0[2]), w1)):
    kb(a, b, 'sink_granite')
for o in G['cyl']:
    e = [o['b'][i] - o['a'][i] for i in range(3)]; c = [(o['a'][i] + o['b'][i]) / 2 for i in range(3)]
    ax = 2
    if abs(e[1] - e[2]) < 1e-3 and abs(e[0] - e[1]) > 1e-3: ax = 0
    elif abs(e[0] - e[2]) < 1e-3 and abs(e[1] - e[0]) > 1e-3: ax = 1
    r = e[(ax + 1) % 3] / 2
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=r, depth=e[ax], location=c, rotation=((math.pi / 2, 0, 0) if ax == 1 else (0, math.pi / 2, 0) if ax == 0 else (0, 0, 0)))
    bpy.context.active_object.data.materials.append(MATS.get(o['m'], MATS['carcass']))


for ob in set(scn.objects) - _pre: ob['furn'] = 1

# ---------------- surroundings: street, buildings opposite, trees (flat is on 4.NP, street ~9.4 m below) ----------------
STREET = -9.4
before = set(scn.objects)
principled('asphalt', lin('#3a3c3f'), 0.92); principled('sidewalk', lin('#b8b6b0'), 0.9); principled('curb', lin('#9b9994'), 0.85)
principled('grass', lin('#5d7745'), 0.95); principled('linemark', lin('#e9e9e4'), 0.7); principled('bark', lin('#4a3b2e'), 0.9)
principled('win', lin('#1f262c'), 0.06, 0.25, **{'Coat Weight': 1.0}); principled('win_lit', lin('#f3e2c2'), 0.5, **{'Emission Color': lin('#ffd9a0'), 'Emission Strength': 1.5})
principled('lampgrey', lin('#4a4d50'), 0.4, 0.6)
for i, c in enumerate(('#e8e2d6', '#c9b49a', '#d9dcdc', '#a7a29a', '#e3d3bd', '#bfc6c9')): principled(f'facade{i}', lin(c), 0.88)
for i, c in enumerate(('#4c6b3a', '#5a7a40', '#476236')):
    m = principled(f'crown{i}', lin(c), 0.85); nt = m.node_tree        # leafy look: coarse noise bump + colour variation
    nz, bm_, mix = nt.nodes.new('ShaderNodeTexNoise'), nt.nodes.new('ShaderNodeBump'), nt.nodes.new('ShaderNodeMix')
    nz.inputs['Scale'].default_value = 6; nz.inputs['Detail'].default_value = 8; bm_.inputs['Strength'].default_value = 0.6
    mix.data_type = 'RGBA'; mix.inputs['A'].default_value = (*lin(c), 1); mix.inputs['B'].default_value = (*[v * 0.55 for v in lin(c)], 1)
    nt.links.new(nz.outputs['Fac'], bm_.inputs['Height']); nt.links.new(bm_.outputs['Normal'], nt.nodes['Principled BSDF'].inputs['Normal'])
    nt.links.new(nz.outputs['Fac'], mix.inputs['Factor']); nt.links.new(mix.outputs['Result'], nt.nodes['Principled BSDF'].inputs['Base Color'])
for i, c in enumerate(('#9aa3ab', '#2c3e50', '#7a1f1f', '#e6e6e6', '#3d4a3a')): principled(f'car{i}', lin(c), 0.25, 0.6, **{'Coat Weight': 1.0})
import random
rnd = random.Random(7)

def windows_quads(x_ranges, y_face, floors, step=3.0, w=1.5, h=1.7, sill=0.9, facing=-1, lit=0.12):
    """window panes on a facade at plan y=y_face; facing -1 = looks north (toward -y), +1 = south"""
    dark, warm = [], []
    for zf in floors:
        for xa, xb in x_ranges:
            x = xa + 0.8
            while x + w <= xb - 0.5:
                y = y_face + facing * 0.012
                P = [(x, y, zf + sill), (x + w, y, zf + sill), (x + w, y, zf + sill + h), (x, y, zf + sill + h)]
                (warm if rnd.random() < lit else dark).append((P, [(0, 0), (1, 0), (1, 1), (0, 1)]))
                x += step
    for name, q, m in (('okna', dark, 'win'), ('okna_svetla', warm, 'win_lit')):
        ob = quads_obj(name, q, m)
        if ob and facing > 0:
            for poly in ob.data.polygons: poly.flip()

# real layout around the plot, generated by site.py from OpenStreetMap + the street map
SITE = json.load(open(HERE + os.environ.get('SITE', 'app/site.json')))
STREET = SITE['street']

def merged_boxes(name, items):   # items: (mat, x0, y0, x1, y1, z0, z1) in plan coords -> one mesh per material
    by = {}
    for m, x0, y0, x1, y1, z0, z1 in items: by.setdefault(m, []).append((x0, y0, x1, y1, z0, z1))
    for m, lst in by.items():
        verts, faces = [], []
        for x0, y0, x1, y1, z0, z1 in lst:
            i = len(verts)
            verts += [B(x0, y0, z0), B(x1, y0, z0), B(x1, y1, z0), B(x0, y1, z0), B(x0, y0, z1), B(x1, y0, z1), B(x1, y1, z1), B(x0, y1, z1)]
            faces += [tuple(i + k for k in reversed(t)) for t in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
        mesh_obj(f'{name}_{m}', verts, faces, m)

def prisms(name, items):   # items: (mat, [(x, y) ...] counter-clockwise, z0, z1) -> extruded footprints, one mesh per material
    by = {}
    for m, pts, z0, z1 in items: by.setdefault(m, []).append((pts, z0, z1))
    for m, lst in by.items():
        me = bpy.data.meshes.new(f'{name}_{m}'); bm = bmesh.new()
        for pts, z0, z1 in lst:
            lo = [bm.verts.new(B(x, y, z0)) for x, y in pts]; hi = [bm.verts.new(B(x, y, z1)) for x, y in pts]
            bm.faces.new(lo); bm.faces.new(hi)
            for i in range(len(pts)): bm.faces.new((lo[i - 1], lo[i], hi[i], hi[i - 1]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(f'{name}_{m}', me); scn.collection.objects.link(ob); ob.data.materials.append(MATS[m])

# our own building (developer's U from site.py): solid mass below and above our floor; on our floor the U minus the flat outline
OWN = SITE['own']; FL, TOP = OWN['fl'], OWN['top']
principled('rail', lin('#2a2c2e'), 0.45, 0.6)
prisms('dum_e2', [('facade0', OWN['poly'], STREET, -0.06), ('facade0', OWN['poly'], 2.80, TOP)])
prisms('patro_e2', [('facade0', OWN['poly'], -0.06, 2.80)])
prisms('byt_cut', [('facade0', OWN['flat'], -0.3, 3.1)])
cut, floor_ob = bpy.data.objects['byt_cut_facade0'], bpy.data.objects['patro_e2_facade0']
cut.hide_render = True; cut.hide_viewport = True
md = floor_ob.modifiers.new('flat', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cut; md.solver = 'EXACT'
for b in SITE['balconies']:   # slab + railing on the three free sides ('wall' = side against the facade)
    x0, y0, x1, y1 = b['r']; rail, t = b['rail'], 0.02
    sides = {'-y': (x0, y0, x1, y0 + t), '+y': (x0, y1 - t, x1, y1), '-x': (x0, y0, x0 + t, y1), '+x': (x1 - t, y0, x1, y1)}
    for zf in b['z']:
        box(x0, y0, x1, y1, zf - 0.2, zf, 'facade3', name='balk')
        for k, r in sides.items():
            if k == b['wall']: continue
            if rail == 'glass': box(*r, zf, zf + 1.05, 'glass', name='glass'); box(*r, zf + 1.02, zf + 1.07, 'black', name='balk')
            else: box(*r, zf + 0.1, zf + 1.05, 'rail', name='balk')
# streets, sidewalks, green strip, tram rails, zebra crossings, signals; ground; green areas
merged_boxes('ulice', [tuple(b) for b in SITE['boxes']])
box(-450, -450, 450, 450, STREET - 0.5, STREET - 0.3, 'sidewalk', name='zem')
for m, z, pts in SITE['polys']: mesh_obj('zelen', [B(x, y, z) for x, y in pts], [tuple(range(len(pts)))[::-1]], m)
# buildings around (OSM footprints) and their window panes
prisms('domy', [(f"facade{b['m']}", b['p'], STREET, STREET + b['h']) for b in SITE['buildings']])
for name, m in (('okna', 'win'), ('okna_svetla', 'win_lit')):
    quads_obj(name, [([(x0, y0, z0), (x0, y0, z1), (x1, y1, z1), (x1, y1, z0)], [(0, 0), (0, 1), (1, 1), (1, 0)])   # outward-facing
                     for k, x0, y0, x1, y1, z0, z1 in SITE['windows'] + SITE['own']['windows'] if (k == 'winLit') == (m == 'win_lit')], m)

def tree(x, y, h):
    cyl(x, y, STREET, STREET + h * 0.55, 0.16, 0.12, 'bark', 10, name='kmen')
    me = bpy.data.meshes.new('koruna'); bm = bmesh.new()
    for i in range(6):
        r = h * (0.16 + rnd.random() * 0.08)
        m = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r)
        off = Vector(B(x + rnd.uniform(-1, 1) * h * 0.12, y + rnd.uniform(-1, 1) * h * 0.12, STREET + h * (0.62 + rnd.random() * 0.25)))
        bmesh.ops.translate(bm, verts=m['verts'], vec=off)
    for f in bm.faces: f.smooth = True
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('koruna', me); scn.collection.objects.link(ob); ob.data.materials.append(MATS[f'crown{rnd.randrange(3)}'])
for x, y, h in SITE['trees']: tree(x, y, h)

def lamp(x, y, toward):
    cyl(x, y, STREET, STREET + 7.0, 0.09, 0.06, 'lampgrey', 12, name='lampa')
    box(x - 0.04, y, x + 0.04, y + toward * 1.3, STREET + 6.9, STREET + 6.98, 'lampgrey', name='lampa')
    box(x - 0.18, y + toward * 1.15, x + 0.18, y + toward * 1.55, STREET + 6.78, STREET + 6.92, 'lampgrey', name='lampa')
for x, y, toward in SITE['lamps']: lamp(x, y, toward)

def car(x, y, along='x', col=0):
    L, W = 4.3, 1.8
    S = (lambda a, b: (a, b)) if along == 'x' else (lambda a, b: (b, a))      # (along, across) -> plan (dx, dy)
    (ax, ay), (bx, by) = S(L / 2, W / 2), S(L * 0.28, W / 2 - 0.08)
    box(x - ax, y - ay, x + ax, y + ay, STREET + 0.3, STREET + 0.95, f'car{col}', 0.12, name='auto')
    (cx0, cy0), (cx1, cy1) = S(-L * 0.28, -(W / 2 - 0.08)), S(L * 0.22, W / 2 - 0.08)
    box(x + cx0, y + cy0, x + cx1, y + cy1, STREET + 0.95, STREET + 1.45, 'win', 0.1, name='auto')
    for da in (-1.35, 1.35):
        for db in (-0.82, 0.82):
            dx, dy = S(da, db)
            bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.33, depth=0.22, location=B(x + dx, y + dy, STREET + 0.33), rotation=((math.pi / 2, 0, 0) if along == 'x' else (0, math.pi / 2, 0)))
            bpy.context.active_object.data.materials.append(MATS['plinth'])
for cx, cy, c, along in SITE['cars']: car(cx, cy, along, c)

# pedestrians on the sidewalks and the forecourt: simple figures, one mesh each (skin / top / trousers / hair / shoes)
for i, c in enumerate(('#e0b89a', '#c68e6b', '#8d5a3b')): principled(f'skin{i}', lin(c), 0.6)
for i, c in enumerate(('#2f4a6d', '#b23a3a', '#e8e4da', '#3f6b4a', '#d9a441', '#5b4b6e', '#222222', '#8fa9c4')): fabric(f'top{i}', c)
for i, c in enumerate(('#2b2f3a', '#4a4036', '#6b7a8f', '#1d1d1d', '#9c8e7a')): fabric(f'pants{i}', c)
for i, c in enumerate(('#2a1d14', '#5a3a22', '#b08a55', '#1a1a1a')): principled(f'hair{i}', lin(c), 0.7)
def person(x, y, yaw, h):
    me = bpy.data.meshes.new('chodec'); bm = bmesh.new(); k = h / 1.75
    def part(fn, mi, off):
        before = set(bm.faces); r = fn()
        bmesh.ops.translate(bm, verts=r['verts'], vec=Vector(off) * k)
        for f in set(bm.faces) - before: f.material_index = mi; f.smooth = True
        return r
    stride = rnd.uniform(-0.14, 0.14)
    for side in (-1, 1):
        part(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.065 * k, radius2=0.075 * k, depth=0.78 * k), 2, (side * stride, side * 0.1, 0.47))
        part(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.06 * k, radius2=0.05 * k, depth=0.08 * k), 4, (side * stride + 0.04, side * 0.1, 0.04))
        part(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.042 * k, radius2=0.05 * k, depth=0.58 * k), 1, (-side * stride * 0.6, side * 0.25, 1.13))
    t = part(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.17 * k, radius2=0.21 * k, depth=0.6 * k), 1, (0, 0, 1.15))
    bmesh.ops.scale(bm, vec=(0.62, 1, 1), verts=t['verts'], space=__import__('mathutils').Matrix.Translation(-Vector((0, 0, 1.15)) * k))
    part(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.045 * k, radius2=0.045 * k, depth=0.1 * k), 0, (0, 0, 1.49))
    part(lambda: bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=10, radius=0.11 * k), 0, (0, 0, 1.62))
    if rnd.random() < 0.85: part(lambda: bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=0.115 * k), 3, (-0.015, 0, 1.655))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__('mathutils').Matrix.Rotation(yaw, 3, 'Z'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(B(x, y, STREET + 0.15)))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('chodec', me); scn.collection.objects.link(ob)
    for mname in (f'skin{rnd.randrange(3)}', f'top{rnd.randrange(8)}', f'pants{rnd.randrange(5)}', f'hair{rnd.randrange(4)}', 'plinth'):
        ob.data.materials.append(MATS[mname])
for x, y, yaw, h in SITE['people']: person(x, y, yaw, h)
for bx, by in SITE['benches']:   # benches in the forecourt along the green strip
    box(bx, by - 0.45, bx + 1.8, by, STREET + 0.15, STREET + 0.6, 'oak', 0.02, name='lavicka')
    box(bx, by - 0.08, bx + 1.8, by, STREET + 0.6, STREET + 1.0, 'oak', 0.02, name='lavicka')

OKOLI = bpy.data.collections.new('Okolí'); scn.collection.children.link(OKOLI)
for ob in set(scn.objects) - before:
    for c in list(ob.users_collection): c.objects.unlink(ob)
    OKOLI.objects.link(ob)

# ---------------- lights ----------------
world = bpy.data.worlds.new('World'); scn.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.72, 0.82, 1.0, 1); bg.inputs['Strength'].default_value = 0.55
sd = bpy.data.lights.new('sun', 'SUN'); sd.energy = 2.2; sd.angle = math.radians(1.5)
sun = bpy.data.objects.new('sun', sd); scn.collection.objects.link(sun)
sun.rotation_euler = Vector((0.3, 0.6, -0.8)).to_track_quat('-Z', 'Y').to_euler()     # default look: sun in the south-south-west
for o in APT['openings']:
    if o['kind'] != 'window': continue
    x0, y0, x1, y1 = o['rect']; (nx, ny), g = o['n'], o['glass']
    w = x1 - x0 if ny else y1 - y0
    c = ((x0 + x1) / 2, g) if ny else (g, (y0 + y1) / 2)
    rot = Vector(B(-nx, -ny, 0)).to_track_quat('-Z', 'Y').to_euler()                      # area lights emit along local -Z: into the room
    ld = bpy.data.lights.new('win', 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = w, 2.3; ld.energy = 260; ld.color = (0.92, 0.95, 1.0)
    lo = bpy.data.objects.new('win', ld); scn.collection.objects.link(lo); lo.location = B(c[0] + nx * 0.55, c[1] + ny * 0.55, 1.2); lo.rotation_euler = rot
    lo.visible_camera = False; lo.visible_glossy = False; lo.visible_transmission = False   # fill light only (default look); off with SUN
    pd = bpy.data.lights.new('portal', 'AREA'); pd.shape = 'RECTANGLE'; pd.size, pd.size_y = w, 2.3; pd.cycles.is_portal = True
    po = bpy.data.objects.new('portal', pd); scn.collection.objects.link(po); po.location = B(c[0] - nx * .02, c[1] - ny * .02, 1.2); po.rotation_euler = rot
for r in APT['rooms']:
    if not r['ceil']: continue
    for x0, y0, x1, y1 in r['rects']:
        a = (x1 - x0) * (y1 - y0)
        if a < 1.2: continue          # small room parts (kitchen niche, wardrobe bay) would light up inside the units
        ld = bpy.data.lights.new('ceil', 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = (x1 - x0) * 0.5, (y1 - y0) * 0.5
        ld.energy = 18 * a; ld.color = (1.0, 0.93, 0.85)
        lo = bpy.data.objects.new('ceil', ld); scn.collection.objects.link(lo); lo.location = B((x0 + x1) / 2, (y0 + y1) / 2, r['ceil'] - 0.02)
for x, y, z, w in LAMPS:
    ld = bpy.data.lights.new('lamp', 'POINT'); ld.energy = w; ld.color = (1.0, 0.82, 0.62); ld.shadow_soft_size = 0.05
    lo = bpy.data.objects.new('lamp', ld); scn.collection.objects.link(lo); lo.location = B(x, y, z)
if os.environ.get('SUN'):
    sys.path.insert(0, HERE + 'render'); import sun as solar
    print('SUN', solar.apply_sun(*os.environ['SUN'].split(), scn, cycles=True), flush=True)   # physical sky + sun, no fill lights

# ---------------- render ----------------
scn.render.engine = 'CYCLES'
cp = bpy.context.preferences.addons['cycles'].preferences
try:
    cp.compute_device_type = 'METAL'; cp.get_devices()
    for dv in cp.devices: dv.use = True
    scn.cycles.device = 'GPU'
except Exception as ex:
    print('GPU setup failed', ex)
scn.cycles.samples = SAMPLES; scn.cycles.use_denoising = True; scn.cycles.max_bounces = 8
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
scn.render.image_settings.file_format = 'JPEG'; scn.render.image_settings.quality = 92
CAMS = {   # plan coords camera -> target, lens, exposure; outdoor views get no EYE_STOPS with SUN
    'r_liv': ((8.35, 1.95, 1.60), (11.8, 5.6, 1.00), 15, 0.2),        # living room from the hall door: window + kitchen
    'r_kit': ((7.75, 4.30, 1.60), (12.9, 2.9, 1.15), 16, 0.2),        # kitchen run from the TV wall
    'r_win': ((9.75, 2.00, 1.60), (9.6, 6.4, 1.20), 16, 0.2),         # living room toward the window (view to the neighbouring block)
    'r_bed': ((6.75, 6.45, 1.60), (2.5, 8.7, 0.85), 15, 0.2),         # bedroom from the niche
    'r_bedwin': ((3.30, 8.85, 1.60), (7.4, 7.7, 1.15), 15, 0.2),      # bedroom toward its east window
    'r_view': ((10.4, 5.75, 1.55), (5.5, 22.0, 0.0), 18, 0.0, 'out'),  # out of the living-room window, south-west
    'r_court': ((44.0, 52.0, 14.0), (8.0, 4.0, -4.0), 22, 0.0, 'out'),  # courtyard: our corner from the south-east, above
}
PANOS = {   # 360 viewpoints (plan x, y); image centre faces north (plan -y)
    'p_living': (8.30, 2.70), 'p_kitchen': (11.20, 3.90), 'p_window': (11.00, 5.40), 'p_hall': (9.30, 0.98),
    'p_wc': (11.65, 1.00), 'p_bath': (1.20, 8.00), 'p_bed': (6.30, 7.80), 'p_robe': (6.60, 5.20),
}
cam_obs = {}
for v, (c, t, lens, ex, *out) in CAMS.items():
    cd = bpy.data.cameras.new(v); co = bpy.data.objects.new('cam_' + v, cd); scn.collection.objects.link(co)
    cd.lens = lens; cd.clip_start = 0.05; co.location = B(*c)
    co.rotation_euler = (Vector(B(*t)) - Vector(B(*c))).to_track_quat('-Z', 'Y').to_euler()
    co['expo'] = ex; co['outdoor'] = int(bool(out)); cam_obs[v] = co
for v in VIEWS:
    if v not in CAMS and v not in PANOS and v != 'plan':
        continue
    ceilings = [o for o in scn.objects if o.name.startswith('ceiling')]
    for o in ceilings: o.hide_render = v == 'plan'
    OKOLI.hide_render = v == 'plan'
    scn.objects['groundplane'].hide_render = v != 'plan'
    if v in PANOS:
        cd = bpy.data.cameras.new(v); co = bpy.data.objects.new(v, cd); scn.collection.objects.link(co)
        cd.type = 'PANO'; cd.panorama_type = 'EQUIRECTANGULAR'; cd.clip_start = 0.05
        scn.render.resolution_x, scn.render.resolution_y = 4096 * SCALE // 100, 2048 * SCALE // 100
        co.location = B(*PANOS[v], 1.55); co.rotation_euler = (math.pi / 2, 0, 0)
        scn.view_settings.exposure = 0.2 + (solar.EYE_STOPS if os.environ.get('SUN') else 0)
    elif v == 'plan':
        cd = bpy.data.cameras.new(v); co = bpy.data.objects.new(v, cd); scn.collection.objects.link(co)
        cd.type = 'ORTHO'; cd.ortho_scale = 14.2
        scn.render.resolution_x, scn.render.resolution_y = 2000 * SCALE // 100, 1440 * SCALE // 100
        co.location = B(6.4, 4.5, 20); co.rotation_euler = (0, 0, 0)
        scn.view_settings.exposure = 0.0
    else:
        co = cam_obs[v]
        scn.render.resolution_x, scn.render.resolution_y = 1800 * SCALE // 100, 1200 * SCALE // 100
        scn.view_settings.exposure = co['expo'] + (solar.EYE_STOPS if os.environ.get('SUN') and not co['outdoor'] else 0)   # eye adapted to the room
    scn.camera = co
    scn.render.filepath = f'{OUT}_{v}.jpg'
    bpy.ops.render.render(write_still=True)
    print('RENDERED', scn.render.filepath, flush=True)
