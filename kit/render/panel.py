# Step 2: "Byt" sidebar panel for byt.blend — live colours/decors, viewpoints, walk, Cycles photo.
# Started by Byt.command: Blender byt.blend --python render/panel.py
import bpy, json, re, os, subprocess, time, sys, importlib, datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'   # kit root
sys.path.insert(0, HERE + 'render')
import sun as solar
importlib.reload(solar)
SQ = HERE + 'oresi/texsq/'
CAT = json.load(open(HERE + 'oresi/catalog_clean.json'))
PAINTS = [('P1', 'Bílá', '#f1f0eb'), ('P2', 'Teplá bílá', '#ede5d7'), ('P3', 'Světle šedá', '#d6d7d3'), ('P4', 'Greige', '#c9bfb0'), ('P5', 'Šalvěj', '#b3bea9'),
          ('P6', 'Holubí modrá', '#a7b9c4'), ('P7', 'Pudrová', '#e0c9c0'), ('P8', 'Olivová', '#8a8867'), ('P9', 'Námořní', '#3c4a5f'), ('P10', 'Grafit', '#55585c')]
TILES = [('T1', 'Bílá', '#efefeb'), ('T2', 'Světle šedá', '#cdcdc9'), ('T3', 'Béžová', '#d5c8b2'), ('T4', 'Šedobéžová', '#a49d93'), ('T5', 'Antracit', '#47494c')]
ROOMS = {r['id']: r['name'] for r in json.load(open(HERE + 'app/apartment.json', encoding='utf-8'))['rooms']}


def lin(h):
    h = h.lstrip('#')
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(f(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


PAINT_ITEMS = [(c, f'{c} {n}', '') for c, n, _ in PAINTS]
TILE_ITEMS = [(c, f'{c} {n}', '') for c, n, _ in TILES]
FRONT_ITEMS = [(o['code'], f"{o['code']} {o['title']}", o['desc']) for o in CAT if o['code'].startswith('F')]
WORK_ITEMS = [(o['code'], f"{o['code']} {o['title']}", o['desc']) for o in CAT if o['code'].startswith('W')]
VIEW_ITEMS = [(o.name, o.name[2:], '') for o in sorted(bpy.data.objects, key=lambda o: o.name) if o.name.startswith('V ')] or [('none', '-', '')]


def mat(name):
    return bpy.data.materials.get(name)


def set_paint(rid, code):
    m = mat(f'paint:{rid}')
    if m: m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*lin(dict((c, h) for c, _, h in PAINTS)[code]), 1)


def set_tile(rid, code):
    c = lin(dict((k, h) for k, _, h in TILES)[code])
    for name in (f'tile:{rid}', f'tilefloor:{rid}'):
        m = mat(name)
        if not m: continue
        br = m.node_tree.nodes['Brick Texture']
        br.inputs['Color1'].default_value = (*c, 1); br.inputs['Color2'].default_value = (*[v * 0.94 for v in c], 1)
        br.inputs['Mortar'].default_value = (*[min(1, v * 0.75 + 0.06) for v in c], 1)


def set_decor(names, code):
    img = bpy.data.images.load(SQ + code + '.jpg', check_existing=True)
    for name in names:
        m = mat(name)
        if m:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE': n.image = img


def code_text(p):
    return f'1:{p.paint_1}·{p.hallrobe}  2:{p.paint_2}·B·{p.front}·{p.worktop}  3:{p.paint_3}·{p.tile_3}  4:{p.paint_4}·{p.bedrobe}  5:{p.paint_5}·{p.tile_5}'


def upd(fn):
    def _u(self, ctx):
        fn(self)
        ctx.scene['byt_code'] = code_text(self)
    return _u


def go_view(self, ctx):
    cam = bpy.data.objects.get(self.view)
    if not cam: return
    ctx.scene.camera = cam
    for area in ctx.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'


SUN_PRESETS = (('Ráno', 8.0), ('Poledne', 13.0), ('Odpoledne', 16.0), ('Večer', 19.5))
SUN_INFO, SUN_BUSY = {}, [False]
hm = lambda h: '%d:%02d' % divmod(round(h * 60) % 1440, 60)


def _rebake():   # the volume probe keeps the bounce light of its last bake (e.g. daylight at night): re-bake as a background job
    wins = bpy.context.window_manager.windows
    if wins:
        with bpy.context.temp_override(window=wins[0]):
            bpy.ops.object.lightprobe_cache_bake('INVOKE_DEFAULT', subset='ALL')


def sun_apply(p, scene=None, bake=True):
    if SUN_BUSY[0]: return
    info = solar.apply_sun((p.sun_year, p.sun_month, p.sun_day), p.sun_time, scene or p.id_data)
    SUN_INFO.clear(); SUN_INFO.update(info, times=solar.sun_times(info['local'].date()))
    if bake:   # once the time stops changing for 1 s
        if bpy.app.timers.is_registered(_rebake): bpy.app.timers.unregister(_rebake)
        bpy.app.timers.register(_rebake, first_interval=1.0)


def sun_now(p):
    loc, _ = solar.utc_to_local(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    SUN_BUSY[0] = True
    try:
        p.sun_year, p.sun_month, p.sun_day = loc.year, loc.month, loc.day
        p.sun_time = loc.hour + loc.minute / 60
    finally:
        SUN_BUSY[0] = False
    sun_apply(p)


def _sun_upd(self, ctx): sun_apply(self, ctx.scene)


def _led_upd(self, ctx):   # LED strips on top of the tall units (sun.apply_sun reads scene['led_cove'])
    ctx.scene['led_cove'] = int(self.led); sun_apply(self, ctx.scene)
def _get_t(self): return self.get('sun_t', 13.0)
def _set_t(self, v): self['sun_t'] = min(24.0, max(0.0, round(v * 4) / 4))   # 15-minute steps


class BytProps(bpy.types.PropertyGroup):
    paint_1: bpy.props.EnumProperty(name='Zádveří', items=PAINT_ITEMS, update=upd(lambda p: set_paint(1, p.paint_1)))
    paint_2: bpy.props.EnumProperty(name='Obývací pokoj', items=PAINT_ITEMS, update=upd(lambda p: set_paint(2, p.paint_2)))
    paint_3: bpy.props.EnumProperty(name='Koupelna', items=PAINT_ITEMS, update=upd(lambda p: set_paint(3, p.paint_3)))
    paint_4: bpy.props.EnumProperty(name='Pokoj', items=PAINT_ITEMS, update=upd(lambda p: set_paint(4, p.paint_4)))
    paint_5: bpy.props.EnumProperty(name='WC', items=PAINT_ITEMS, update=upd(lambda p: set_paint(5, p.paint_5)))
    tile_3: bpy.props.EnumProperty(name='Obklad koupelna', items=TILE_ITEMS, update=upd(lambda p: set_tile(3, p.tile_3)))
    tile_5: bpy.props.EnumProperty(name='Obklad WC', items=TILE_ITEMS, update=upd(lambda p: set_tile(5, p.tile_5)))
    front: bpy.props.EnumProperty(name='Dvířka kuchyně', items=FRONT_ITEMS, update=upd(lambda p: set_decor(['front'], p.front)))
    worktop: bpy.props.EnumProperty(name='Pracovní deska', items=WORK_ITEMS, update=upd(lambda p: set_decor(['worktop', 'splash'], p.worktop)))
    hallrobe: bpy.props.EnumProperty(name='Skříň v zádveří', items=FRONT_ITEMS, update=upd(lambda p: set_decor(['hallrobe'], p.hallrobe)))
    bedrobe: bpy.props.EnumProperty(name='Skříně v pokoji', items=FRONT_ITEMS, update=upd(lambda p: set_decor(['bedrobe'], p.bedrobe)))
    view: bpy.props.EnumProperty(name='Místo', items=VIEW_ITEMS, update=go_view)
    sun_day: bpy.props.IntProperty(name='Den', min=1, max=31, default=21, update=_sun_upd)
    sun_month: bpy.props.IntProperty(name='Měsíc', min=1, max=12, default=6, update=_sun_upd)
    sun_year: bpy.props.IntProperty(name='Rok', min=2000, max=2100, default=2026, update=_sun_upd)
    sun_time: bpy.props.FloatProperty(name='Čas', description='Místní čas (SEČ / SELČ), po 15 minutách', min=0, max=24, precision=2, step=25,
                                      get=_get_t, set=_set_t, update=_sun_upd)
    led: bpy.props.BoolProperty(name='LED nad skříněmi', default=True, update=_led_upd)


def toggle_lights(scene):   # L: lamps + LED strips on / off together (sun.apply_sun reads scene 'lamps' and 'led_cove')
    p = scene.byt
    lamps = scene.get('lamps', -1)
    lit = p.led or (lamps == 1 if lamps >= 0 else solar.lights_on(SUN_INFO.get('elevation', 90)) > 0.5)
    scene['lamps'] = int(not lit); scene['led_cove'] = int(not lit)
    p['led'] = not lit                  # set without the update callback, then apply once
    sun_apply(p, scene)


def toggle_door(cam):   # E: swing the door leaf nearest to the camera (in front, within 2.2 m) open / closed
    from mathutils import Vector
    fwd = cam.matrix_world.to_3x3() @ Vector((0, 0, -1)); fwd.z = 0
    best = None
    for o in bpy.data.objects:
        if 'door_close' not in o: continue
        d = o.matrix_world @ (sum((Vector(c) for c in o.bound_box), Vector()) / 8) - cam.location; d.z = 0
        if d.length > 2.2: continue
        score = d.length - (fwd.normalized().dot(d.normalized()) if d.length > 1e-3 and fwd.length > 1e-3 else 0)
        if best is None or score < best[0]: best = (score, o)
    if not best: return
    o = best[1]; a0 = o.rotation_euler.z; a1 = 0.0 if abs(a0) > abs(o['door_close']) / 2 else o['door_close']; t0 = time.time()

    def step():
        u = min(1.0, (time.time() - t0) / 0.4); u = u * u * (3 - 2 * u)
        o.rotation_euler.z = a0 + (a1 - a0) * u
        for w in bpy.context.window_manager.windows:
            for ar in w.screen.areas:
                if ar.type == 'VIEW_3D': ar.tag_redraw()
        return None if u >= 1 else 1 / 60
    bpy.app.timers.register(step)


class BYT_OT_nav(bpy.types.Operator):
    """Always-on navigation in the 3D view: W A S D / arrows walk, drag to look, R/F up/down, E door, Shift faster, wheel = zoom"""
    bl_idname = 'byt.nav'; bl_label = 'Pohyb'
    KEYS = {'W', 'A', 'S', 'D', 'R', 'F', 'UP_ARROW', 'DOWN_ARROW', 'LEFT_ARROW', 'RIGHT_ARROW', 'LEFT_SHIFT', 'RIGHT_SHIFT'}

    def invoke(self, ctx, event):
        self.area = ctx.area
        self.win = next(r for r in self.area.regions if r.type == 'WINDOW')
        self.ui = next(r for r in self.area.regions if r.type == 'UI')
        self.cam = None; self.down = set(); self.drag = None; self.last = time.time()
        self.timer = ctx.window_manager.event_timer_add(1 / 60, window=ctx.window)
        ctx.window_manager.modal_handler_add(self)
        print('NAV START', flush=True)
        return {'RUNNING_MODAL'}

    def sync(self, ctx):   # (re)read yaw/pitch when the active camera changes (e.g. "Skočit na místo")
        import math
        from mathutils import Vector
        self.cam = ctx.scene.camera
        d = self.cam.matrix_world.to_3x3() @ Vector((0, 0, -1))
        self.yaw, self.pitch = math.atan2(-d.x, d.y), math.asin(max(-1, min(1, d.z)))

    def apply(self):
        import math
        self.cam.rotation_mode = 'XYZ'
        self.cam.rotation_euler = (math.pi / 2 + self.pitch, 0, self.yaw)
        self.win.tag_redraw()

    def over_view(self, event):
        x, y, u = event.mouse_x, event.mouse_y, self.ui
        in_ui = u.width > 1 and u.x <= x < u.x + u.width and u.y <= y < u.y + u.height
        w = self.win
        return not in_ui and w.x <= x < w.x + w.width and w.y <= y < w.y + w.height

    def modal(self, ctx, event):
        import math
        if ctx.scene.camera is not self.cam:
            self.sync(ctx)
        t, v = event.type, event.value
        if t in self.KEYS and v == 'RELEASE':
            self.down.discard(t); return {'PASS_THROUGH'}
        if t == 'TIMER':
            now = time.time(); dt = min(0.1, now - self.last); self.last = now
            k = self.down
            fw = (('W' in k) or ('UP_ARROW' in k)) - (('S' in k) or ('DOWN_ARROW' in k))
            rt = (('D' in k) or ('RIGHT_ARROW' in k)) - (('A' in k) or ('LEFT_ARROW' in k))
            up = ('R' in k) - ('F' in k)
            if fw or rt or up:
                sp = (3.0 if (k & {'LEFT_SHIFT', 'RIGHT_SHIFT'}) else 1.3) * dt
                sy, cy = math.sin(self.yaw), math.cos(self.yaw)
                loc = self.cam.location
                loc.x = max(-0.3, min(8.0, loc.x + (-sy * fw + cy * rt) * sp))
                loc.y = max(-8.1, min(1.85, loc.y + (cy * fw + sy * rt) * sp))   # stay inside the flat / on the balcony
                loc.z = max(0.3, min(2.6, loc.z + up * sp * 0.6))
                self.win.tag_redraw()
            return {'PASS_THROUGH'}
        if not self.over_view(event):
            if t in ('LEFTMOUSE', 'RIGHTMOUSE') and v == 'RELEASE':
                self.drag = None
            return {'PASS_THROUGH'}          # side panel and everything else keep working normally
        if t == 'E' and v == 'PRESS':
            toggle_door(self.cam); return {'RUNNING_MODAL'}
        if t == 'L' and v == 'PRESS':
            toggle_lights(ctx.scene); return {'RUNNING_MODAL'}
        if t in self.KEYS and v == 'PRESS':
            self.down.add(t); return {'RUNNING_MODAL'}
        if t in ('LEFTMOUSE', 'RIGHTMOUSE'):
            self.drag = (event.mouse_x, event.mouse_y) if v == 'PRESS' else None
            return {'RUNNING_MODAL'}
        if t == 'MOUSEMOVE' and self.drag:
            dx, dy = event.mouse_x - self.drag[0], event.mouse_y - self.drag[1]
            self.drag = (event.mouse_x, event.mouse_y)
            self.yaw -= dx * 0.004
            self.pitch = max(-1.3, min(1.3, self.pitch + dy * 0.004))
            self.apply()
            return {'RUNNING_MODAL'}
        if t in ('WHEELUPMOUSE', 'WHEELDOWNMOUSE'):
            self.cam.data.lens = max(10, min(35, self.cam.data.lens + (1 if t == 'WHEELUPMOUSE' else -1)))
            self.win.tag_redraw()
            return {'RUNNING_MODAL'}
        if t in ('TRACKPADPAN', 'TRACKPADZOOM', 'MOUSEROTATE', 'MIDDLEMOUSE'):
            return {'RUNNING_MODAL'}         # block Blender's own orbit/pan so the view stays inside the camera
        return {'PASS_THROUGH'}


class BYT_OT_photo(bpy.types.Operator):
    bl_idname = 'byt.photo'; bl_label = 'Fotka (Cycles, ~40 s)'
    bl_description = 'Vyrenderuje aktuální pohled kamery v plné kvalitě a otevře ho v Náhledu'
    def execute(self, ctx):
        s = ctx.scene
        prev = s.render.engine, s.view_settings.exposure
        s.render.engine = 'CYCLES'; s.cycles.samples = 128
        s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1800, 1200, 100
        s.view_settings.exposure = 0.2
        p = s.byt
        if SUN_INFO:   # Cycles with the simulated sun: physical sky and sun only (no window fill lights), eye-adapted exposure
            solar.apply_sun((p.sun_year, p.sun_month, p.sun_day), p.sun_time, s, cycles=True)
            if s.camera.location.y < 0: s.view_settings.exposure += solar.EYE_STOPS   # inside the flat only, the balcony is outdoors
        os.makedirs(HERE + 'fotky', exist_ok=True)
        path = HERE + 'fotky/' + time.strftime('%Y-%m-%d_%H%M%S') + '_' + s.camera.name[2:].replace(' ', '_') + '.jpg'
        s.render.filepath = path
        bpy.ops.render.render(write_still=True)
        s.render.engine, s.view_settings.exposure = prev
        if SUN_INFO: sun_apply(p, s, bake=False)   # back to the EEVEE lighting (the probe bake is still valid)
        subprocess.Popen(['open', path])
        self.report({'INFO'}, 'Uloženo: ' + path)
        return {'FINISHED'}


class BYT_OT_copy(bpy.types.Operator):
    bl_idname = 'byt.copy'; bl_label = 'Kopírovat kód'
    def execute(self, ctx):
        ctx.window_manager.clipboard = code_text(ctx.scene.byt)
        self.report({'INFO'}, 'Kód zkopírován')
        return {'FINISHED'}


class BYT_OT_light(bpy.types.Operator):
    bl_idname = 'byt.light'; bl_label = 'Přepočítat odražené světlo'
    bl_description = 'Po větší změně barev přepočítá odrazy světla (pár sekund)'
    def execute(self, ctx):
        return bpy.ops.object.lightprobe_cache_bake('INVOKE_DEFAULT', subset='ALL')


class BYT_OT_sun(bpy.types.Operator):
    bl_idname = 'byt.sun'; bl_label = 'Čas slunce'
    bl_description = 'Nastaví čas simulace slunce (Teď = aktuální datum a čas)'
    hour: bpy.props.FloatProperty(default=-1)
    def execute(self, ctx):
        p = ctx.scene.byt
        if self.hour < 0: sun_now(p)
        else: p.sun_time = self.hour
        return {'FINISHED'}


def draw_sun(L, p):
    b = L.box(); b.label(text='Slunce', icon='LIGHT_SUN')
    r = b.row(align=True); r.prop(p, 'sun_day', text='Den'); r.prop(p, 'sun_month', text='Měsíc'); r.prop(p, 'sun_year', text='Rok')
    b.prop(p, 'sun_time', text='Čas ' + hm(p.sun_time), slider=True)
    b.prop(p, 'led', text='LED nad skříněmi', icon='LIGHT_AREA', toggle=True)
    g = b.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
    for name, h in SUN_PRESETS:
        g.operator('byt.sun', text=f'{name} {hm(h)}', depress=abs(p.sun_time - h) < 1e-6).hour = h
    b.operator('byt.sun', text='Teď', icon='TIME').hour = -1
    i = SUN_INFO or solar.sun_local((p.sun_year, p.sun_month, p.sun_day), p.sun_time)
    c = b.column(align=True)
    c.label(text=f"Azimut {i['azimuth']:.0f}° · výška {i['elevation']:.1f}° · {i['zone']}")
    t = i.get('times', {})
    tm = lambda d: hm(d.hour + d.minute / 60 + d.second / 3600)
    if 'sunrise' in t and 'sunset' in t: c.label(text=f"Východ {tm(t['sunrise'][0])} · západ {tm(t['sunset'][0])}")
    c.label(text=solar.note_cs(i), icon='INFO')


class BYT_PT_main(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = 'Item'; bl_label = 'Byt'; bl_order = 0
    def draw(self, ctx):
        p, L = ctx.scene.byt, self.layout
        h = L.box().column(align=True)
        h.label(text='Pohyb (myš nad bytem):', icon='MOD_DYNAMICPAINT')
        for t in ('W A S D nebo šipky = chůze', 'táhni myší = rozhlížení', 'E = otevřít / zavřít dveře', 'L = lampy + LED', 'R / F = nahoru / dolů', 'Shift = rychleji', 'kolečko = širší / užší záběr'): h.label(text=t)
        col = L.column(align=True); col.label(text='Skočit na místo'); col.prop(p, 'view', text='')
        row = L.row(); row.scale_y = 1.4; row.operator('byt.photo', icon='RENDER_STILL')
        draw_sun(L, p)
        b = L.box(); b.label(text='Barva stěn', icon='BRUSH_DATA')
        for i in range(1, 6): b.prop(p, f'paint_{i}')
        b = L.box(); b.label(text='Obklady a dlažba', icon='MESH_GRID')
        b.prop(p, 'tile_3'); b.prop(p, 'tile_5')
        b = L.box(); b.label(text='Kuchyně (rozložení B)', icon='HOME')
        b.prop(p, 'front'); b.prop(p, 'worktop')
        b = L.box(); b.label(text='Skříně', icon='SNAP_FACE')
        b.prop(p, 'hallrobe'); b.prop(p, 'bedrobe')
        b = L.box(); b.label(text='Kód nastavení', icon='COPYDOWN')
        for part in code_text(p).split('  '): b.label(text=part)
        b.operator('byt.copy'); L.operator('byt.light', icon='LIGHT_SUN')


CLASSES = (BytProps, BYT_OT_nav, BYT_OT_photo, BYT_OT_copy, BYT_OT_light, BYT_OT_sun, BYT_PT_main)
for c in CLASSES:
    bpy.utils.register_class(c)
bpy.types.Scene.byt = bpy.props.PointerProperty(type=BytProps)


def init_from_code():
    s = bpy.context.scene; p = s.byt
    code = s.get('byt_code', '')
    for part in re.split(r'\s+', code.strip()):
        if ':' not in part: continue
        rid, rest = part.split(':'); v = re.split(r'[·.]', rest); rid = int(rid)
        setattr(p, f'paint_{rid}', v[0])
        if rid == 1: p.hallrobe = v[1]
        if rid == 2: p.front, p.worktop = v[2], v[3]
        if rid in (3, 5): setattr(p, f'tile_{rid}', v[1])
        if rid == 4: p.bedrobe = v[1]
    if s.camera: p.view = s.camera.name


def setup_ui():
    try:
        sun_now(bpy.context.scene.byt)    # the sun starts at the current date and time
    except Exception as ex:
        print('Byt sun:', ex)
    try:
        init_from_code()
        vl = bpy.context.view_layer
        for o in bpy.data.objects:
            o.hide_select = True          # clicks cannot select or move anything
        vl.objects.active = None
        win = bpy.context.window_manager.windows[0]
        area = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width * a.height)
        with bpy.context.temp_override(window=win, area=area):
            bpy.ops.screen.screen_full_area()   # only the 3D view, no timeline / outliner / properties
        area = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width * a.height)
        sp = area.spaces.active
        sp.shading.type = 'RENDERED'; sp.overlay.show_overlays = False; sp.show_gizmo = False
        sp.show_region_ui = True; sp.show_region_toolbar = False; sp.show_region_tool_header = False; sp.show_region_header = False
        sp.region_3d.view_perspective = 'CAMERA'
        bpy.context.scene.camera.data.passepartout_alpha = 1.0
        region = next(r for r in area.regions if r.type == 'WINDOW')
        with bpy.context.temp_override(window=win, area=area, region=region):
            bpy.ops.view3d.view_center_camera()
        with bpy.context.temp_override(window=win, area=area, region=region):
            bpy.ops.byt.nav('INVOKE_DEFAULT')   # navigation is always on, no start button needed
    except Exception as ex:
        print('Byt setup:', ex)
    return None


bpy.app.timers.register(setup_ui, first_interval=1.0)
_tab_tries = [0]


def set_tab():   # the sidebar tab can only be switched once the region has been drawn: retry until it sticks
    _tab_tries[0] += 1
    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    for r in area.regions:
                        if r.type == 'UI':
                            r.active_panel_category = 'Item'
                            if r.active_panel_category == 'Item':
                                print('TAB OK', flush=True)
                                return None
    except Exception:
        pass
    return 0.5 if _tab_tries[0] < 40 else None


bpy.app.timers.register(set_tab, first_interval=2.0)
