# Example flat light check, web side: app/index.html rendered top-down over the same floor rects in headless Chrome, floor brightness per metre from
# the window (living: south edge, bedroom: east edge) vs Cycles (out/floor/cyc_*.png from floor_cyc.py). Copy of the first flat's web_floor.py.
# Run: python3 app/build.py && python3 render/web_floor.py ['[{"win": 3}, {"sunIn": 2}]']
import json, os, re, subprocess, sys, tempfile, time
from PIL import Image
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'   # kit root
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
import os
LED_ONLY = os.environ.get('LIGHTS') == 'led'   # LIGHTS=led: night with LED strips only (state.lights = 1)
TIMES = [('2026-10-06', '23:00')] if LED_ONLY else [('2026-10-06', '13:00'), ('2026-10-06', '16:00'), ('2026-12-21', '12:00'), ('2026-06-21', '13:00'), ('2026-10-06', '21:00')]
ROOMS = {'Obyvak': (7.40, 1.75, 12.30, 5.95), 'Pokoj': (3.20, 6.25, 7.10, 9.14)}
WIN = {'Obyvak': 'S', 'Pokoj': 'E'}
looks = sys.argv[1] if len(sys.argv) > 1 else '[{}]'


def bands(grid, room):   # grid rows (top = north) of luminance -> mean per metre from the window wall, 4 bands
    x0, y0, x1, y1 = ROOMS[room]; H, W = len(grid), len(grid[0])
    if WIN[room] == 'S': lines, depth = [grid[H - 1 - i] for i in range(H)], y1 - y0          # rows from the south edge
    else: lines, depth = [[grid[y][W - 1 - i] for y in range(H)] for i in range(W)], x1 - x0  # columns from the east edge
    n = len(lines); out = []
    for b in range(4):
        a, c = int(b / depth * n), min(n, int((b + 1) / depth * n))
        out.append(sum(sum(l) / len(l) for l in lines[a:c]) / max(1, c - a))
    return out


def cycles(d, t, room):
    im = Image.open(HERE + 'out/floor/cyc_%s_%s_%s%s.png' % (d, t.replace(':', ''), room, '_led' if LED_ONLY else '')).convert('RGB'); W, H = im.size; p = im.load()
    return bands([[(0.2126 * p[x, y][0] + 0.7152 * p[x, y][1] + 0.0722 * p[x, y][2]) / 255 for x in range(W)] for y in range(H)], room)


probe = '''<script>
setTimeout(() => {
  renderer.setAnimationLoop(null); state.room = null; cutaway(); if (OWN_FLOOR) OWN_FLOOR.visible = true;
  const out = {}, gl = renderer.getContext(), base = { ...LOOK };
  for (const [li, lk] of %s.entries()) for (const [d, t] of %s) {
    Object.assign(LOOK, base, lk);
    state.sun = { date: d, min: +t.slice(0, 2) * 60 + +t.slice(3) }; state.lights = %s; applySun();
    for (const [name, [x0, y0, x1, y1]] of Object.entries(%s)) {
      const s = 240 / Math.max(x1 - x0, y1 - y0), W = Math.round((x1 - x0) * s), H = Math.round((y1 - y0) * s);
      renderer.setPixelRatio(1); renderer.setSize(W, H, false);
      const cam = new THREE.OrthographicCamera(-(x1 - x0) / 2, (x1 - x0) / 2, (y1 - y0) / 2, -(y1 - y0) / 2, 0.05, 10);
      cam.position.set((x0 + x1) / 2, 2.5, (y0 + y1) / 2); cam.up.set(0, 0, -1); cam.lookAt((x0 + x1) / 2, 0, (y0 + y1) / 2);
      renderer.render(scene, cam);
      const px = new Uint8Array(W * H * 4); gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, px);
      const rows = [];
      for (let y = H - 1; y >= 0; y--) { const r = []; for (let x = 0; x < W; x++) { const i = (y * W + x) * 4; r.push((0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]) / 255); } rows.push(r); }
      out[li + ' ' + d + ' ' + t + ' ' + name] = rows;
    }
  }
  const pre = document.createElement('pre'); pre.id = 'floorprof'; pre.textContent = JSON.stringify(out); document.body.append(pre);
}, 8000);
</script>''' % (looks, json.dumps(TIMES), "1" if LED_ONLY else "'auto'", json.dumps(ROOMS))
page = open(HERE + 'app/index.html', encoding='utf-8').read() + probe
tmp = tempfile.mkdtemp()
open(tmp + '/probe.html', 'w', encoding='utf-8').write(page)
pr = subprocess.Popen([CHROME, '--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--user-data-dir=' + tmp + '/prof',
                       '--virtual-time-budget=60000', '--window-size=800,600', '--dump-dom', 'file://' + tmp + '/probe.html'],
                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
dom, t0 = '', time.time()
for line in pr.stdout:
    dom += line
    if '</html>' in line or time.time() - t0 > 900: break
pr.kill(); pr.wait()
m = re.search(r'<pre id="floorprof">(.*?)</pre>', dom, re.S)
if not m: sys.exit('no probe output')
res = json.loads(m.group(1).replace('&quot;', '"'))
print('LOOK overrides', looks)
print('%-30s %-26s %-26s' % ('look time room', 'web 0-1 1-2 2-3 3-4 m', 'cycles 0-1 .. 3-4 m'))
err = {}
for key, rows in res.items():
    li, d, t, room = key.split()
    w, c = bands(rows, room), cycles(d, t, room)
    err.setdefault(li, []).extend(abs(a - b) for a, b in zip(w, c))
    print('%-30s %-26s %-26s mean web %.2f cyc %.2f' % (key, ' '.join('%.2f' % v for v in w), ' '.join('%.2f' % v for v in c), sum(w) / 4, sum(c) / 4))
for li, e in err.items(): print('LOOK %s %s: mean |web - cycles| per band %.3f' % (li, json.loads(looks)[int(li)], sum(e) / len(e)))
