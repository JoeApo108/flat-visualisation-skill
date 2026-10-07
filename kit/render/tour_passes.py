# Example flat 360 tour light layers (copy of render/tour_passes.py for the first flat, plus sun layers): each panorama as linear layers the tour mixes live:
#   sky (sky only, at the SUN time), sun_<k> (sun only, at SUN_POS[k]; rooms with windows), night (lit windows outside), lamps, led.
# A south / east flat gets direct sun, which a single daylight layer cannot follow; the tour picks the sun layer nearest to the configurator's sun.
# Run: SUN="2026-10-06 13:00" blender -b -P render/tour_passes.py -- "<code>" <outprefix> <views> <samples> [scale%]
import bpy, json, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'   # kit root
HEAD = 4.0                  # stops of headroom in the 16-bit PNG layers (tour_layers.sh log-encodes them to JPEG)
ROOM_LIGHTS = ('lamp', 'ceil')
SUN_POS = [('2026-12-21', '10:00'), ('2026-12-21', '12:00'), ('2026-03-21', '08:30'), ('2026-03-21', '10:30'),
           ('2026-03-21', '12:30'), ('2026-06-21', '09:00'), ('2026-06-21', '11:30'), ('2026-06-21', '13:30')]
SUN_VIEWS = ('p_living', 'p_kitchen', 'p_window', 'p_bed', 'p_robe')        # viewpoints that see a window


def _emission(m):
    n = next((n for n in m.node_tree.nodes if n.type == 'EMISSION'), None)
    return n.inputs['Strength'] if n else m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']


def _layers(v):
    scn = bpy.context.scene
    eye = 2 ** solar.EYE_STOPS
    sky = scn.world.node_tree.nodes['Background'].inputs['Strength']
    sun = scn.objects['sun'].data
    lights = [o.data for o in scn.objects if o.type == 'LIGHT' and o.name != 'sun']
    mats = {n: bpy.data.materials[n] for n in ('bulb', 'led', 'win_lit', 'led_cove') if n in bpy.data.materials}
    keep = (sky.default_value, sun.energy, [l.energy for l in lights], {n: _emission(m).default_value for n, m in mats.items()})
    expo, view, samples = scn.view_settings.exposure, scn.view_settings.view_transform, scn.cycles.samples

    def kind(l): return l.name.split('.')[0]

    def setup(skyon, sunon, room, led, night):
        sky.default_value = keep[0] if skyon else 0.0
        if not sunon: sun.energy = 0.0
        for l in lights:
            k = kind(l)
            on = (room and k in ROOM_LIGHTS) or (led and k == 'cove')
            l.energy = l['base_energy'] * solar.NIGHT_LAMPS / eye if on and 'base_energy' in l else 0.0
        for n, m in mats.items():
            on = (room and n in ('bulb', 'led')) or (led and n == 'led_cove') or (night and n == 'win_lit')
            _emission(m).default_value = m.get('base_strength', keep[3][n]) / eye if on else 0.0

    def shot(name, half=False):
        if os.path.exists(f'{OUT}_{v}_{name}.png'): print('SKIP', v, name, flush=True); return   # resume: keep finished layers
        scn.render.resolution_percentage = 50 if half else 100
        if half: scn.cycles.samples = max(64, samples // 2)
        elif not name.startswith('sun'): scn.cycles.samples = samples
        scn.render.filepath = f'{OUT}_{v}_{name}.png'
        bpy.ops.render.render(write_still=True)
        print('LAYER', scn.render.filepath, flush=True)

    scn.view_settings.view_transform = 'Standard'; scn.view_settings.look = 'None'
    scn.view_settings.exposure = expo - HEAD
    scn.render.image_settings.file_format = 'PNG'; scn.render.image_settings.color_depth = '16'; scn.render.image_settings.compression = 15
    for name, flags, half in (('sky', (1, 0, 0, 0, 0), False), ('night', (0, 0, 0, 0, 1), True), ('lamps', (0, 0, 1, 0, 0), False), ('led', (0, 0, 0, 1, 0), True)):
        setup(*flags); shot(name, half)
    if v in SUN_VIEWS:
        for k, (d, t) in enumerate(SUN_POS):
            solar.apply_sun(d, t, scn, cycles=True); setup(0, 1, 0, 0, 0); scn.cycles.samples = int(samples * 0.6); shot('sun%d' % k)   # direct sun: less noise
        solar.apply_sun(*SUN.split(), scn, cycles=True)
    scn.render.resolution_percentage, scn.cycles.samples = 100, samples
    sky.default_value, sun.energy = keep[0], keep[1]                     # back to the scene as built
    for l, e in zip(lights, keep[2]): l.energy = e
    for n, m in mats.items(): _emission(m).default_value = keep[3][n]
    scn.view_settings.view_transform, scn.view_settings.exposure = view, expo
    if v == 'p_living' and not os.path.exists(f'{OUT}_{v}_agxref.jpg'):  # AgX reference (sky + sun at the SUN time) to check the tour's tone curve
        scn.view_settings.look = 'AgX - Medium High Contrast'
        scn.render.image_settings.file_format = 'JPEG'; scn.render.filepath = f'{OUT}_{v}_agxref.jpg'
        bpy.ops.render.render(write_still=True)


import os
SUN = os.environ['SUN']
src = open(HERE + 'render/apartment.py').read()
assert src.count('bpy.ops.render.render(write_still=True)') == 1
exec(compile(src.replace('bpy.ops.render.render(write_still=True)', '_layers(v)'), 'apartment.py', 'exec'))
pos = [dict(zip(('date', 'time'), p), **{k: round(solar.sun_local(*p)[k], 2) for k in ('elevation', 'azimuth')}) for p in SUN_POS]
json.dump({'sun': pos, 'sky': {k: round(solar.sun_local(*SUN.split())[k], 2) for k in ('elevation', 'azimuth')}, 'sun_views': SUN_VIEWS}, open(OUT + '_meta.json', 'w'))
print('META', pos, flush=True)
