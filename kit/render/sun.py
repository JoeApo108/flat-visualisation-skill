# Sun position for the flat (location from app/site.json) + Blender lighting from it.
# Solar math: NOAA solar calculator equations. Azimuth clockwise from north. Times are Europe/Prague local (CET/CEST).
# Pure Python; bpy is imported only inside apply_sun().
import json, math, os
from datetime import date as _date, datetime, timedelta

# site location + facade orientation: one source for Blender and web (app/site.json, from site.py)
_SITE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app', 'site.json'), encoding='utf-8'))
LAT, LON, FACADE_AZ = _SITE['lat'], _SITE['lon'], _SITE['facade_az']   # FACADE_AZ: azimuth of the model's +Y (street facade normal)


# ---------- Europe/Prague time zone (EU rule: CEST from last Sunday of March 01:00 UTC to last Sunday of October 01:00 UTC)
def _last_sunday(y, m):
    d = _date(y, m, 31)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def is_dst(utc):
    a, b = _last_sunday(utc.year, 3), _last_sunday(utc.year, 10)
    return datetime(a.year, a.month, a.day, 1) <= utc < datetime(b.year, b.month, b.day, 1)


def utc_to_local(utc):
    off = 2 if is_dst(utc) else 1
    return utc + timedelta(hours=off), off


def local_to_utc(local):
    off = 2 if is_dst(local - timedelta(hours=1)) else 1   # skipped/doubled hour at the switch resolves to one valid instant
    return local - timedelta(hours=off), off


def parse_local(day, local_time):
    """day: 'YYYY-MM-DD' | date | (y, m, d); local_time: 'HH:MM' | hours (float). Day past month end is clamped."""
    if isinstance(day, str): y, m, d = (int(v) for v in day.split('-'))
    elif isinstance(day, tuple): y, m, d = day
    else: y, m, d = day.year, day.month, day.day
    last = ((_date(y + m // 12, m % 12 + 1, 1)) - timedelta(days=1)).day
    if isinstance(local_time, str):
        hh, mm = local_time.split(':'); local_time = int(hh) + int(mm) / 60
    return datetime(y, m, min(d, last)) + timedelta(hours=float(local_time))


# ---------- solar position
def _solar(utc, lat, lon):
    """-> (geometric elevation, azimuth, equation of time [min]) in degrees"""
    jd = (utc - datetime(1970, 1, 1)).total_seconds() / 86400 + 2440587.5
    t = (jd - 2451545) / 36525
    L0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    M = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    r = math.radians
    C = math.sin(r(M)) * (1.914602 - t * (0.004817 + 0.000014 * t)) + math.sin(r(2 * M)) * (0.019993 - 0.000101 * t) + math.sin(r(3 * M)) * 0.000289
    om = 125.04 - 1934.136 * t
    lam = L0 + C - 0.00569 - 0.00478 * math.sin(r(om))
    eps = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60 + 0.00256 * math.cos(r(om))
    decl = math.asin(math.sin(r(eps)) * math.sin(r(lam)))
    y = math.tan(r(eps) / 2) ** 2
    eot = 4 * math.degrees(y * math.sin(2 * r(L0)) - 2 * e * math.sin(r(M)) + 4 * e * y * math.sin(r(M)) * math.cos(2 * r(L0))
                           - 0.5 * y * y * math.sin(4 * r(L0)) - 1.25 * e * e * math.sin(2 * r(M)))
    minutes = utc.hour * 60 + utc.minute + utc.second / 60 + utc.microsecond / 6e7
    ha = r(((minutes + eot + 4 * lon) % 1440) / 4 - 180)
    phi = r(lat)
    el = math.asin(max(-1, min(1, math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.cos(ha))))
    az = (math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(phi) - math.tan(decl) * math.cos(phi))) + 180) % 360
    return math.degrees(el), az, eot


def _refraction(el):   # NOAA approximation, degrees
    if el > 85: return 0.0
    te = math.tan(math.radians(el))
    if el > 5: s = 58.1 / te - 0.07 / te ** 3 + 0.000086 / te ** 5
    elif el > -0.575: s = 1735 + el * (-518.2 + el * (103.4 + el * (-12.79 + el * 0.711)))
    else: s = -20.774 / te
    return s / 3600


def sun_position(utc, lat=LAT, lon=LON):
    """utc: naive UTC datetime -> (apparent elevation, azimuth) in degrees, azimuth clockwise from north"""
    el, az, _ = _solar(utc, lat, lon)
    return el + _refraction(el), az


def sun_times(day, lat=LAT, lon=LON):
    """local sunrise / solar noon / sunset (sun centre at -0.833° geometric) -> dict of (local datetime, azimuth)"""
    base = parse_local(day, 0)
    f = lambda m: _solar(local_to_utc(base + timedelta(minutes=m))[0], lat, lon)[0] + 0.833
    out, prev = {}, f(0)
    for m in range(1, 1441):
        cur = f(m)
        if (prev < 0) != (cur < 0):
            t = m - 1 + prev / (prev - cur)
            out['sunrise' if cur > 0 else 'sunset'] = t
        prev = cur
    noon = max(range(0, 1440), key=lambda m: f(m))
    out['noon'] = noon
    res = {}
    for k, m in out.items():
        loc = base + timedelta(minutes=m)
        res[k] = (loc, sun_position(local_to_utc(loc)[0], lat, lon)[1])
    return res


def sun_local(day, local_time, lat=LAT, lon=LON):
    loc = parse_local(day, local_time)
    utc, off = local_to_utc(loc)
    el, az = sun_position(utc, lat, lon)
    return {'local': loc, 'utc': utc, 'offset': off, 'zone': 'SELČ' if off == 2 else 'SEČ', 'elevation': el, 'azimuth': az}


# ---------- lighting model (shared with the web version)
def _smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# Daylight: IES (1984) clear-sky daylight availability model (Gillette et al. 1984):
#   direct normal  E_dn = 127.5 klx * exp(-0.21 m)          (m = air mass, Kasten-Young 1989, valid down to the horizon)
#   sky, horizontal E_d = 0.8 + 15.5 * sin(h)^0.5 klx       (clear sky: A 0.8, B 15.5, C 0.5)
# Twilight (h < 0): log-linear from E_d(0) = 0.8 klx to 3.4 lx at -6° (end of civil twilight) and 0.002 lx at -18° (moonless night).
TWILIGHT = ((0.0, 0.8), (-6.0, 0.0034), (-18.0, 0.000002))   # (elevation, klx)
H_REF = 60.0                                                # calibration: Blender sky strength 0.55 (default look) = clear sky at 60°


def air_mass(el):
    e = max(el, 0.0)
    return 1 / (math.sin(math.radians(e)) + 0.50572 * (e + 6.07995) ** -1.6364)


def direct_klx(el):
    if el <= -0.5: return 0.0
    return 127.5 * math.exp(-0.21 * air_mass(el)) * min(1.0, (el + 0.5) / 1.5)   # last factor: sun disc sinking below the horizon


def sky_klx(el):
    if el >= 0: return 0.8 + 15.5 * math.sqrt(math.sin(math.radians(el)))
    for (h0, e0), (h1, e1) in zip(TWILIGHT, TWILIGHT[1:]):
        if el >= h1: return 10 ** (math.log10(e0) + (math.log10(e1) - math.log10(e0)) * (el - h0) / (h1 - h0))
    return TWILIGHT[-1][1]


def lights_on(el):
    """interior lights: off in daylight, on after dusk (sun below about -6°)"""
    return 1 - _smooth(-7, -5, el)


SUN_RAMP = ((-1, (1.0, 0.35, 0.12)), (0, (1.0, 0.42, 0.16)), (3, (1.0, 0.58, 0.32)), (8, (1.0, 0.75, 0.52)),
            (15, (1.0, 0.86, 0.70)), (30, (1.0, 0.94, 0.86)), (50, (1.0, 0.97, 0.93)))


def sun_color(el):
    if el <= SUN_RAMP[0][0]: return SUN_RAMP[0][1]
    for (a, ca), (b, cb) in zip(SUN_RAMP, SUN_RAMP[1:]):
        if el <= b:
            t = (el - a) / (b - a); return tuple(x + (y - x) * t for x, y in zip(ca, cb))
    return SUN_RAMP[-1][1]


def sky(el):
    """-> (sky brightness relative to the clear sky at H_REF (IES model), sky colour)"""
    c = (0.72, 0.82, 1.0)
    tw = max(0.0, 1 - abs(el - 1) / 7) * 0.45                                    # warm horizon around sunrise/sunset
    c = tuple(x + (y - x) * tw for x, y in zip(c, (1.0, 0.72, 0.55)))
    nt = 1 - _smooth(-10, 0, el)                                               # deep blue at night
    c = tuple(x + (y - x) * nt for x, y in zip(c, (0.32, 0.38, 0.6)))
    return sky_klx(el) / sky_klx(H_REF), c


def note_cs(info):
    """one-line Czech hint about direct sun through the north windows"""
    el, az = info['elevation'], info['azimuth']
    if el <= 0: return 'Slunce je pod obzorem (noc).'
    if 90 < (az - FACADE_AZ) % 360 < 270: return 'Slunce je za domem (jih), okna na sever přímé slunce nedostanou.'
    return 'Slunce je na severní straně: nízké světlo může dopadnout přímo do oken.'


# ---------- Blender
SKY_STRENGTH = 0.55                          # world strength of the default look = clear sky at H_REF
# same units for the sun lamp: a uniform world of strength S and colour c lights the ground with pi*S*c W/m²
W_PER_KLX = math.pi * SKY_STRENGTH * (0.72 + 0.82 + 1.0) / 3 / sky_klx(H_REF)
# Cycles (photos, apartment.py with SUN): physical - sky and sun through the glass only, no fill lights, camera exposure + EYE_STOPS
# (an eye adapted to the room; lamps scaled down by the same stops so the night looks as before).
# EEVEE (walk-through): same sky and sun, plus window fill lights calibrated against the Cycles daylight-only renders.
# An extra interior sun x 2**EYE_STOPS overshot Cycles by 0.2-0.3 mean (EEVEE GI already carries the sun patch's bounce), so none.
EYE_STOPS = 3.5
FILL_REF = 0.43                              # EEVEE window fill x base 260 W at H_REF (render/suntest/calibrate_fill.py)
NIGHT_LAMPS = 0.1                            # ceiling lights and lamps after dusk x default level
EEVEE_LAMPS = 1.5                            # EEVEE carries less lamp bounce than Cycles: x1.5 matches the 23:00 mean (calibrate_fill.py)


def apply_sun(day, local_time, scene=None, cycles=False):
    """Drive the sun, sky (world), window fill lights and lamps from the real sun position and the IES clear-sky model.
    Blender +Y = street facade normal (azimuth FACADE_AZ, ~north), +X = along the facade (~east).
    cycles=False (EEVEE): physical sky + sun, window fills at the eye-adapted scale.
    cycles=True: physical light only; the caller adds EYE_STOPS to the camera exposure of interior views."""
    import bpy
    from mathutils import Vector
    scn = scene or bpy.context.scene
    info = sun_local(day, local_time)
    el, az = info['elevation'], info['azimuth']
    e, a = math.radians(el), math.radians(az - FACADE_AZ)
    to_sun = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    k, col = sky(el)
    night = lights_on(el)
    on = night if scn.get('lamps', -1) < 0 else float(scn['lamps'])   # lamps: automatic at night, or switched (walk-through key L)
    if scn.world and scn.world.use_nodes:
        bg = scn.world.node_tree.nodes.get('Background')
        if bg:
            bg.inputs['Color'].default_value = (*col, 1)
            bg.inputs['Strength'].default_value = SKY_STRENGTH * k
    mx, eye = max(col), 2 ** EYE_STOPS
    for o in scn.objects:
        if o.type != 'LIGHT': continue
        kind, ld = o.name.split('.')[0], o.data
        if kind not in ('win', 'ceil', 'lamp', 'cove'): continue
        if 'base_energy' not in ld:
            ld['base_energy'] = ld.energy; ld['base_color'] = list(ld.color)
        if kind == 'win':      # daylight through the windows
            ld.energy = 0.0 if cycles else ld['base_energy'] * FILL_REF * k
            ld.color = tuple(0.5 * b + 0.5 * c / mx for b, c in zip(ld['base_color'], col))
        else:                  # ceiling lights and lamps: off by day, on after dusk; LED cove strips: switched (scene 'led_cove')
            sw = scn.get('led_cove', 1) if kind == 'cove' else on
            ld.energy = ld['base_energy'] * NIGHT_LAMPS * sw * (1 / eye if cycles else EEVEE_LAMPS)
    for name in ('bulb', 'led', 'win_lit'):   # bulbs, mirror LED and lit windows opposite follow the lamps (shades are fabric lit by the bulb)
        m = bpy.data.materials.get(name)
        if not (m and m.node_tree): continue
        n = next((n for n in m.node_tree.nodes if n.type == 'EMISSION'), None)
        s = n.inputs['Strength'] if n else m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
        if 'base_strength' not in m: m['base_strength'] = s.default_value
        s.default_value = m['base_strength'] * (night if name == 'win_lit' else on) / (eye if cycles else 1)
    m = bpy.data.materials.get('led_cove')
    if m and 'base_strength' in m:
        m.node_tree.nodes['Emission'].inputs['Strength'].default_value = m['base_strength'] * scn.get('led_cove', 1) / (eye if cycles else 1)
    old = bpy.data.objects.get('sun_in')     # interior sun left by an older build
    if old: bpy.data.objects.remove(old)
    sun = bpy.data.objects.get('sun')
    if sun:
        sun.rotation_mode = 'XYZ'
        sun.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()
        sun.data.energy = W_PER_KLX * direct_klx(el)
        sun.data.color = sun_color(el)
    scn['sun_time'] = info['local'].strftime('%Y-%m-%d %H:%M')
    return info


if __name__ == '__main__':
    for d, t in (('2026-06-21', '13:12'), ('2026-12-21', '12:00'), ('2026-06-21', '20:30')):
        i = sun_local(d, t); print(d, t, i['zone'], round(i['elevation'], 2), round(i['azimuth'], 2))
    for k, (loc, az) in sun_times('2026-06-21').items(): print(k, loc.strftime('%H:%M'), round(az, 1))
