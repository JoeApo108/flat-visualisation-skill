# Step 1: build byt.blend (kitchen layout B) for live walk-through in Blender's EEVEE viewport.
# Run: blender -b -P render/build_blend.py -- "<code>"
import bpy, sys, re, math, json, os
from mathutils import Vector
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'   # kit root
code = sys.argv[sys.argv.index('--') + 1]
code = re.sub(r'(2:[^·.]+[·.])C([·.])', r'\1B\2', code)   # layout B only
sys.argv = [sys.argv[0], '--', code, HERE + 'fotky/foto', 'none', '128']
exec(compile(open(HERE + 'render/apartment.py').read(), 'apartment.py', 'exec'))
scn = bpy.context.scene
scn['byt_code'] = code

# ---- EEVEE real-time settings (viewport + quick renders); Cycles settings from apartment.py stay for photos
scn.render.engine = 'BLENDER_EEVEE'
ee = scn.eevee
ee.use_raytracing = True
ee.ray_tracing_method = 'SCREEN'
ee.use_fast_gi = True
ee.fast_gi_method = 'GLOBAL_ILLUMINATION'
ee.use_shadows = True
ee.shadow_ray_count = 2
ee.taa_samples = 256          # viewport keeps refining while standing still (16 left visible grain on dim ceilings and in shadows)
scn.render.preview_pixel_size = '2'   # half-res viewport on Retina: samples 4x cheaper, converges in a few seconds
ee.taa_render_samples = 64
ee.gi_diffuse_bounces = 3
scn.view_settings.exposure = 0.3

# window glass: thin, blended, no shadows (Cycles' shadow-ray trick does not apply in EEVEE)
g = bpy.data.materials['glass']
nt = g.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
p = nt.nodes.new('ShaderNodeBsdfPrincipled')
p.inputs['Base Color'].default_value = (0.55, 0.6, 0.62, 1); p.inputs['Roughness'].default_value = 0.02; p.inputs['Alpha'].default_value = 0.05
nt.links.new(p.outputs['BSDF'], nt.nodes['Material Output'].inputs['Surface'])
g.surface_render_method = 'BLENDED'
for ob in scn.objects:
    if ob.type == 'MESH' and ob.data.materials and ob.data.materials[0] == g:
        ob.visible_shadow = False

# the plan-view backdrop would hide the street in the walk-through
bpy.data.objects.remove(bpy.data.objects['groundplane'])

# volume light probe over the whole flat for bounce light
R = [r for room in json.load(open(HERE + 'app/apartment.json', encoding='utf-8'))['rooms'] for r in room['rects']]
x0, y0, x1, y1 = min(r[0] for r in R), min(r[1] for r in R), max(r[2] for r in R), max(r[3] for r in R)
pd = bpy.data.lightprobes.new('flat_gi', 'VOLUME')
pr = bpy.data.objects.new('flat_gi', pd); scn.collection.objects.link(pr)
pr.location = ((x0 + x1) / 2, -(y0 + y1) / 2, 1.4); pr.scale = ((x1 - x0) / 2 + 0.1, (y1 - y0) / 2 + 0.1, 1.45)   # whole flat
pd.resolution_x, pd.resolution_y, pd.resolution_z = max(4, round((x1 - x0) * 2.5)), max(4, round((y1 - y0) * 2.5)), 6

# viewpoint cameras (same spots and headings as the 360° tour, app/tour.html), eye height 1.6
VIEW = {
    'Obývací pokoj': ((8.30, 2.70), 115), 'Kuchyň': ((11.20, 3.90), 75), 'U okna': ((11.00, 5.40), 215), 'Vstupní hala': ((9.30, 0.98), 200),
    'WC': ((11.65, 1.00), 90), 'Šatní kout': ((6.60, 5.20), 180), 'Pokoj': ((6.30, 7.80), 250), 'Koupelna': ((1.20, 8.00), 270),
}
for name, ((x, y), h) in VIEW.items():
    cd = bpy.data.cameras.new('V ' + name); cd.lens = 16; cd.clip_start = 0.05
    co = bpy.data.objects.new('V ' + name, cd); scn.collection.objects.link(co)
    co.location = (x, -y, 1.6)
    hr = math.radians(h)   # heading: clockwise from north (plan -y = Blender +Y)
    d = Vector((math.sin(hr), math.cos(hr), -0.05))
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
scn.camera = bpy.data.objects['V Obývací pokoj']

try:
    bpy.ops.object.lightprobe_cache_bake(subset='ALL')
    print('PROBE BAKED')
except Exception as ex:
    print('PROBE BAKE SKIPPED', ex)
bpy.ops.wm.save_as_mainfile(filepath=HERE + 'byt.blend')
print('SAVED', HERE + 'byt.blend')
