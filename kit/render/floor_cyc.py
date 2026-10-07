# Example flat light check, Cycles side: top-down ortho frames of the living-room and bedroom floor (camera under the ceiling), physical sky + sun,
# lamps + LED after dusk (as the web's automatic lights), same exposure as the interior views (0.2 + EYE_STOPS). Copy of the first flat's floor_cyc.py.
# Run: blender -b -P render/apartment.py -P render/floor_cyc.py -- "<code>" x none 64   -> out/floor/cyc_<date>_<time>_<room>.png
import bpy, sys, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'   # kit root
sys.path.insert(0, HERE + 'render'); import sun as solar
from mathutils import Vector
scn = bpy.context.scene
import os
LED_ONLY = os.environ.get('LIGHTS') == 'led'   # LIGHTS=led: night, LED strips only (lamps off) -> cyc_..._<room>_led.png
TIMES = [('2026-10-06', '23:00')] if LED_ONLY else [('2026-10-06', '13:00'), ('2026-10-06', '16:00'), ('2026-12-21', '12:00'), ('2026-06-21', '13:00'), ('2026-10-06', '21:00')]
ROOMS = {'Obyvak': (7.40, 1.75, 12.30, 5.95), 'Pokoj': (3.20, 6.25, 7.10, 9.14)}   # plan rects without built-in units
scn.cycles.samples = int(sys.argv[sys.argv.index('--') + 4])
for d, t in TIMES:
    scn['lamps'] = 0 if LED_ONLY else -1; info = solar.apply_sun(d, t, scn, cycles=True); scn['led_cove'] = 1 if LED_ONLY else int(solar.lights_on(info['elevation']) > 0.5)
    solar.apply_sun(d, t, scn, cycles=True)
    for name, (x0, y0, x1, y1) in ROOMS.items():
        cd = bpy.data.cameras.new('top'); cd.type = 'ORTHO'; cd.ortho_scale = max(x1 - x0, y1 - y0); cd.clip_start = 0.01
        co = bpy.data.objects.new('top', cd); scn.collection.objects.link(co); co.location = ((x0 + x1) / 2, -(y0 + y1) / 2, 2.5)
        scn.render.resolution_x, scn.render.resolution_y = (240, round(240 * (y1 - y0) / (x1 - x0))) if x1 - x0 >= y1 - y0 else (round(240 * (x1 - x0) / (y1 - y0)), 240)
        scn.view_settings.exposure = 0.2 + solar.EYE_STOPS
        scn.render.image_settings.file_format = 'PNG'; scn.camera = co
        scn.render.filepath = HERE + 'out/floor/cyc_%s_%s_%s%s.png' % (d, t.replace(':', ''), name, '_led' if LED_ONLY else '')
        bpy.ops.render.render(write_still=True); print('FLOOR', scn.render.filepath, flush=True)
