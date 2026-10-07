# Example flat sun test sheet (as the first flat's render/suntest/contact_sheet.jpg, but Cycles): the views of apartment.py at several dates/times,
# physical sky + sun only, lamps automatic after dusk, LED strips off, same exposure at every time (eye adapted to the room: EYE_STOPS).
# Run: blender -b -P render/apartment.py -P render/contact.py -- "<code>" out/x none 48
import bpy, json, os, subprocess, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'   # kit root
sys.path.insert(0, HERE + 'render'); import sun as solar
FLOOR = json.load(open(HERE + os.environ.get('SITE', 'app/site.json')))['floor']
OUTD = HERE + 'out/contact_%dnp/' % FLOOR; os.makedirs(OUTD, exist_ok=True)
TIMES = [('2026-06-21', '05:30'), ('2026-06-21', '08:00'), ('2026-06-21', '13:00'), ('2026-06-21', '17:00'), ('2026-06-21', '20:30'),
         ('2026-06-21', '23:00'), ('2026-03-21', '10:00'), ('2026-03-21', '15:00'), ('2026-12-21', '10:00'), ('2026-12-21', '12:00'), ('2026-12-21', '14:30')]
VIEWS = [('r_liv', 'Obývák'), ('r_kit', 'Kuchyň'), ('r_win', 'Obývák okno'), ('r_bed', 'Pokoj'), ('r_bedwin', 'Pokoj okno'), ('r_view', 'Výhled'), ('r_court', 'Dvůr')]
scn = bpy.context.scene
scn.cycles.samples = int(sys.argv[sys.argv.index('--') + 4]); scn.render.resolution_x, scn.render.resolution_y = 640, 400
scn['led_cove'] = 0; scn['lamps'] = -1
for d, t in TIMES:
    solar.apply_sun(d, t, scn, cycles=True)
    for v, _ in VIEWS:
        co = scn.objects['cam_' + v]; scn.camera = co
        scn.view_settings.exposure = co['expo'] + (0 if co['outdoor'] else solar.EYE_STOPS)
        scn.render.filepath = OUTD + '%s_%s_%s.jpg' % (d, t.replace(':', ''), v)
        bpy.ops.render.render(write_still=True); print('RENDERED', scn.render.filepath, flush=True)
# sheet: rows = times, columns = views, label in each tile (system python with PIL)
script = '''
import sys
from PIL import Image, ImageDraw, ImageFont
outd, floor, times, views = sys.argv[1], sys.argv[2], [t.split('|') for t in sys.argv[3].split(',')], [v.split('|') for v in sys.argv[4].split(',')]
f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 15)
W, H = 320, 200
sheet = Image.new('RGB', (W * len(views), H * len(times) + 40), 'white'); d = ImageDraw.Draw(sheet)
d.text((10, 10), 'Ukazkovy byt (%s.NP, dvur/jih+vychod) - jasna obloha, slunce + obloha, lampy jen po setmeni, stejna expozice' % floor, font=f, fill='black')
for r, (day, t) in enumerate(times):
    for c, (v, lab) in enumerate(views):
        im = Image.open('%s%s_%s_%s.jpg' % (outd, day, t.replace(':', ''), v)).resize((W, H))
        sheet.paste(im, (c * W, 40 + r * H)); txt = '%d.%d. %s  %s' % (int(day[8:]), int(day[5:7]), t, lab)
        w = d.textlength(txt, font=f); d.rectangle([c * W + 4, 40 + r * H + 4, c * W + 12 + w, 40 + r * H + 24], fill='black'); d.text((c * W + 8, 40 + r * H + 6), txt, font=f, fill='white')
sheet.save(outd + 'contact_sheet.jpg', quality=90); print('SHEET', sheet.size)
'''
print(subprocess.run([os.environ.get('PYTHON', 'python3'), '-c', script, OUTD, str(FLOOR), ','.join('%s|%s' % x for x in TIMES), ','.join('%s|%s' % x for x in VIEWS)],
                     capture_output=True, text=True).stdout, flush=True)
