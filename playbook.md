# Flat visualisation from a floor plan: playbook and timing test

**Goal:** find out how long it takes to turn an existing floor plan, including an old or scanned one, into:

1. **A local web configurator**: one self-contained `.html` file. You open it in a browser and get a 3D plan view of the flat, a 3D view of each room, and buttons to change wall colours, tiles, kitchen fronts and worktop.
2. **An interactive Blender walk-through**: a `.blend` file. You walk through the flat in real time (W A S D + mouse), change finishes in a side panel, and render a photorealistic photo with one button.
3. **A sun simulation in both**: pick a date and time, and see the real sun position, shadows and daylight; lights switch on after dusk.
4. **A sun analysis**: hours of direct sun per window for every month, and a sun plan showing where sun lands on the floor.
5. **A contact sheet**: the same views at several dates and times, all with the same exposure.
6. **Drawings**: room dimensions, kitchen plan and kitchen elevation.
7. **A 360° tour that mixes light layers**. It takes the time, light switches and **colour scheme** from the configurator. As a demonstration, three colour schemes with randomly picked decor textures are rendered.

Everything runs locally. No web deployment or hosting is needed. Only the 360° tour needs a tiny local server, started with one command (see Step 12).

This playbook is based on a real run on two flats in one building: the first built from scratch, the second (the example in `kit/`) adapted from it, done with Claude Code, Blender 5 and three.js. It records what worked, what went wrong, and how long each step took. **Write down your own times in the timing sheet (section 9).**

The scripts from that run are in `kit/`; [SKILL.md](SKILL.md) lists the command and the per-flat edits for every step. Decide up front what you measure: adapting the kit to a new plan, or building the pipeline from scratch with this playbook only.

---

## 1. What you need

| Item | Notes |
|---|---|
| Floor plan | Vector PDF (best), or a scan or photo of an old plan. It needs a scale bar or at least one dimension you can trust. |
| Room areas from the seller or architect | Used to check your scale (areas should match within about 2–3 %). |
| Blender 4.x or 5.x | Cycles on GPU for photos; EEVEE for the real-time walk-through. Run headless with `blender -b -P script.py -- args`. |
| Python 3 with Pillow (and ImageMagick) | Turns the plan image into data, draws sheets, builds the HTML. `pdftoppm` (poppler) renders PDFs. |
| A browser | The HTML loads three.js r147 from a CDN. If you must work offline, download `three.min.js` plus the addons (OrbitControls, RoomEnvironment, RoundedBoxGeometry, BufferGeometryUtils, RectAreaLightUniformsLib) and inline them. |
| Decor photos (optional) | Square photos of kitchen and wardrobe fronts and worktops, used as textures. We used 80 Oresi samples. For the colour-scheme demo in Step 12, any 10–20 wood and stone textures will do. |
| Location of the flat | Latitude and longitude, and the facade direction (the azimuth the plan's "up" points to). From a map or the building's key plan. Needed for the sun (Steps 8–9). |
| Surroundings (optional but recommended for the sun) | Building footprints and storey counts from OpenStreetMap (Overpass API), and your own building's outline from the developer's key plan. Without them the sun shines in at hours when a neighbouring wing would block it. |
| Claude Code or similar (optional) | Everything here was written by an AI agent from short instructions. Suggested prompts are under each step. |

---

## 2. Pipeline overview

```
plan PDF / scan
   │  render at 300 dpi, measure the scale bar
   ▼
wall mask (black walls + grey shafts, thin lines removed)  ──►  walls.json (rectangles in metres)
   │  + rooms, doors, windows, furniture read off the plan
   ▼
apartment.json  (+ kitchen.json, optional site.json for surroundings)
   │                                   │
   ▼                                   ▼
template.html + build.py           apartment.py (Blender scene from the JSON)
   │  inline JSON + textures         │  build_blend.py: EEVEE settings, light probes, cameras
   ▼                                   │  panel.py: side panel, walk mode, photo button
index.html (single file, ~4 MB)    byt.blend + launcher (.command / .bat)
   │                                   │
   │  sun.py / same JS: sun position + daylight (Step 8)
   │                                   ├─ sun_hours.py, sun_plan.py  → chart + CSV + floor heat map (Step 9)
   │                                   ├─ contact.py                 → contact sheet (Step 10)
   │                                   ├─ drawings.py                → dimension + kitchen sheets (Step 11)
   │                                   └─ tour_passes.py             → 360 light layers, 3 colour schemes (Step 12)
   ▼                                                                     │ encode (log JPEG)
"Prohlídka 360°" button  ── ?t=&el=&az=&sun=&lamps=&led=&code= ──►  tour/index.html (mixes layers live)
```

**Key decision: one data model, two viewers.** The web and Blender both read the same `apartment.json` and `kitchen.json`, so a change in the plan data reaches both. Keep one coordinate frame: plan metres, x to the right (east), y down (south), z up. Blender uses (x, −y, z); three.js uses (x, z, y).

---

## 3. Step by step: core (Steps 1–7)

### Step 1: Plan image and scale (≈10–20 min)

1. Render the PDF at 300 dpi: `pdftoppm -r 300 -png plan.pdf plan`. For a scan, straighten (deskew) it and crop it to the flat.
2. **Measure the scale bar in pixels**, segment by segment. In our case 5 segments of 165 px each gave 826 px for 5 m, so 165.2 px/m.
   - Old plans without a scale bar: use a written dimension, a standard door leaf (0.80 m) or a known wall length.
3. **Check the scale with areas.** Sum the measured room rectangles and compare with the official areas. We got 54.5 m² measured against 55.6 m² on the sheet.
   - Watch for differences in how rooms are counted. The developer counted a 2.9 m² wardrobe niche as part of the living room, although it opens onto the bedroom.

> Prompt: *"Render this PDF at 300 dpi, find the 0–5 m scale bar and measure px/m from its segments. Then crop the flat and save plan.png."*

### Step 2: Walls (≈15–30 min)

1. Make a mask from dark pixels (walls are solid black; installation shafts are grey). **Remove thin lines with a morphological opening.** We used a minimum filter, then a maximum filter, both 11 px (about 6–7 cm at 300 dpi). This removes door swings, window frames and furniture lines while keeping walls 8 cm and thicker.
2. Turn the mask into rectangles: go row by row, find runs of wall pixels, and merge identical runs on consecutive rows into one rectangle. This gave about 40–65 rectangles per flat. Convert pixels to metres with an origin at a clean interior wall face.
3. Overlay the rectangles on the plan in a check image and look at it. Fix single cases by hand, e.g. a sliding-door pocket that the opening step splits apart.

Old or scanned plans need extra care:
- **Hatched walls:** threshold on darkness plus texture, or trace them by hand.
- **Coloured plans:** threshold per channel.
- **Handwritten notes:** remove them first.
- **Thin partitions** may be thinner than the opening filter. Lower it to 7–9 px or add them by hand.

### Step 3: Rooms, openings, doors, furniture (≈20–40 min)

Write `data.py`, which outputs `apartment.json`. Read coordinates off the plan image (a preview with a pixel grid helps).

- **rooms:** id, name, official area, floor type (vinyl or tile), ceiling height, tile height, rects (one or more rectangles per room), options (paint, tiles, kitchen, wardrobe).
  - **Keep fixed role ids** (1 hall, 2 living + kitchen, 3 bathroom, 4 bedroom, 5 WC). Then a configuration code such as `1:P1·F22 2:P9·B·F11·W02 …` means the same thing in every flat.
- **openings:** the gap rectangle in the wall.
  - Doors: lintel at 2.02 m. Mark the entrance door separately (it gets no frame or threshold).
  - Windows: head at 2.40 m, plus the **position of the glass and the outward normal**, so windows can face any direction. Note any French-door part.
- **doors:** hinge point, opening direction and leaf width, as drawn.
- **furniture:** a kind (sofa, bed, table, chair, wardrobe, toilet, bath, …), a rectangle, a height and the side it faces. Take the furniture drawn on the plan; old plans often have none, so place a few pieces sensibly.

Check: draw the walls, rooms, openings, furniture rectangles and door leaves over the plan and look at it before going on.

> Prompt: *"From plan.png (165.2 px/m), write data.py that produces apartment.json: walls from the mask, rooms with these ids …, doors and windows (glass position + outward normal), furniture as drawn. Then draw a check overlay."*

### Step 4: Kitchen (≈15–30 min, optional)

`kitchen.py` writes `kitchen.json`, a list of boxes (carcass, front, worktop, plinth, handles, appliances) plus cylinders (hob zones, tap) and arcs (rounded end). Build it from a module list along one wall:

`filler 5 | fridge 60 | sink 60 | dishwasher 60 | hob 60 | drawers 60 | rounded end 25`

Heights we used:
- worktop 0.91
- wall cabinets 1.50–2.40, plus top boxes up to 2.70
- tall units up to 2.70, i.e. 5 cm under a 2.75 ceiling
- LED strip on the front edge on top, tilted 30° toward the room, plus an LED strip under the wall cabinets

### Step 5: Blender scene (≈30–60 min)

`apartment.py` builds the whole flat from the JSON. Usage: `blender -b -P apartment.py -- "<code>" <outprefix> <views> <samples> [scale%]`.

What it builds:
- **Materials:** paints, tiles (procedural bricks), decor textures (box-projected), oak, fabrics, glass, emissive LED.
- **Walls:** each side of a wall gets the finish of the room it faces (sample a point just outside the face, look up its room), tiles up to the room's tile height, skirting boards.
- **Floors:** planks with UVs from one floor photo, tiles, ceilings.
- **Furniture, doors and kitchen** from the JSON.
- **Lights:**
  - sun + sky (world)
  - ceiling area lights per room
  - lamp point lights
  - LED area lights
  - window portals (Cycles) to reduce noise in dark corners
- **Cameras:** a few interior views plus a top-down plan view without ceilings.

Pitfalls we hit:
- **Area lights emit along their local −Z.** For a strip or window facing any direction, build the rotation from vectors: emit direction, strip axis, cross product. Don't guess Euler angles.
- **Hide helper objects in normal renders**, e.g. a backdrop plane used only for the plan view. Otherwise it shows up as a big "desk" outside the windows.
- **Two identical faces in the same place render black.** We had a duplicated slab.
- **Surroundings:** OpenStreetMap footprints extruded to their storey count, the street from a map screenshot, your own building from the developer's key plan. They change the light a lot, but are optional for a timing test.

### Step 6: Blender walk-through (≈30–60 min)

1. `build_blend.py` runs `apartment.py`, switches to EEVEE with real-time GI, adds light probes and viewpoint cameras, bakes the probe, and saves `byt.blend`.
2. `panel.py` is a sidebar panel (N-panel tab) with:
   - wall colour per room, tiles, kitchen fronts and worktop, wardrobe fronts
   - "jump to viewpoint"
   - **walk mode** that is always on: W A S D / arrows, drag to look, R/F up/down, Shift faster, E opens the nearest door, L lights
   - **Photo** button: renders the current view in Cycles and saves it
   - the configuration code
3. A launcher (`.command` on macOS, `.bat` on Windows) opens Blender with `byt.blend` and the panel.

Known limit: **the EEVEE viewport is grainy right after you move** and clears over 1–2 s; settings can't remove this. Mitigations: viewport pixel size ×2 and 256 TAA samples. For a clean image, use the Photo button.

> Prompt: *"Write build_blend.py (EEVEE, probes, cameras) and panel.py (side panel with paint/tile/decor pickers, WASD walk mode, E doors, Cycles photo button), plus a launcher."*

### Step 7: Local web configurator (≈60–120 min first time, ≈30–45 min when adapting an existing one)

1. `template.html` is a single page:
   - three.js scene built from the inlined JSON: the same walls, finishes per room side, floors, furniture, kitchen, doors
   - orthographic plan view with room labels; clicking a room opens a perspective dollhouse view of it, with the walls on the camera side cut away
   - side panel with paints, tiles, decor grids and the configuration code (the same code Blender takes)
2. `build.py` replaces placeholders in the template with `apartment.json`, `kitchen.json`, the decor catalogue and **base64 textures** and writes **one `index.html`** (about 4 MB). Double-click it to open it locally. No server is needed, apart from the CDN (see section 1).

Pitfalls we hit:
- **Camera far plane:** at 100 m, buildings across a courtyard were cut into white wedges. Use 1500 m.
- **No ceiling in a dollhouse view:** light aimed at the ceiling (LED coves) has no effect unless you fake the reflection, e.g. with a soft down-facing area light at ceiling height.
- **The web has no bounced light**, so its brightness must be calibrated against Blender (Step 8, point 6). Keep a separate even "colour picking" light mode.
- **Testing:** headless Chrome screenshots (`--headless=new --use-angle=swiftshader --screenshot=…`). Chrome 154 does not exit after the screenshot, so poll for the PNG, then kill that Chrome.

---

## 4. Step by step: sun, sheets and 360° tour (Steps 8–12)

### Step 8: Sun simulation, date and time, in the web and in Blender (≈1–2 h)

1. **Site data** (`site.json`): latitude, longitude, facade azimuth, street level relative to your floor, and the surroundings (extruded building footprints, your own building's outline). Plan coordinates stay as before.
2. **Sun position**: write `sun.py` with the NOAA solar-position equations (elevation, azimuth, refraction; local time with summer and winter time, which in the EU switches on the last Sunday of March and October). **Port the same code to JavaScript** for the web page and add a test that both give the same numbers. Ours agree to 1e-9°.
3. **Daylight model** (IES clear sky):
   - direct sun = 127.5 klx × exp(−0.21 × air mass)
   - sky = 0.8 + 15.5 × sin(elevation)^0.5 klx
   - twilight fades to about 3 lx at −6° and to night at −18°
   - sun colour shifts from orange to white with elevation
4. **Blender**: `apply_sun(date, time)` rotates the sun lamp, sets its strength and the sky (world) strength and colour, and switches lamps on after dusk (sun below −6°). Keep the camera exposure **fixed for all times**, plus a few stops for an eye adapted to the room (we used +3.5). That way you see real differences between morning, noon and night.
   - The Blender panel gets "Sun": day, month, time slider, a "now" button.
5. **Web**: a directional sun light with a shadow box of ±30 m (a smaller box cut the shadows on the ground into hard wedges). There is also a narrow spot light from the sun's direction with tight shadows for sharp sun patches indoors.
   - Window light = sky brightness × window strength.
   - Which windows the sun reaches: cast 12 rays from each window toward the sun against the buildings, so a neighbouring wing really blocks it.
   - **Light modes**: "colour picking" (even light, time ignored) and "real light" (sun + time).
   - **Lights**: automatic, i.e. on after dusk, plus one button and the L key cycling off → LED → LED + lamps.
   - Date field, time slider, presets (morning, noon, afternoon, evening, now). "Now" stays highlighted on load.
6. **Calibrate the web against Blender.** The web has no bounced light, so its brightness is a guess until you compare it.
   - Render top-down floor images in Cycles (camera just under the ceiling) at 4–5 dates and times, and the same views in the web.
   - Compare floor brightness in 1 m bands from the window, and tune the window, sky and sun-patch-bounce strengths.
   - In our run the error went from 0.18 to 0.05 (scale 0–1).

> Prompt: *"Add a sun simulation: sun.py with the NOAA equations and an IES clear-sky daylight model, the same in JS; apply_sun() for Blender (sun, sky, lamps after dusk, fixed exposure); web: date/time controls, presets, real-light vs colour-picking mode, automatic lights. Then write floor_cyc.py + web_floor.py to compare floor brightness and tune the web."*

### Step 9: Sun hours and sun plan (≈30 min)

- **Sun hours per window**: points just outside each window's glass, 10 × 6 per window. For every 5 minutes of the 21st of each month, cast rays toward the sun through the scene; glass and glass railings let the sun through. A moment counts as sunny when more than 10 % of the points see the sun.
  - Output a CSV and a chart: months × hours, with sun above the horizon in grey and direct sun in orange.
- **Sun plan**: a 10 cm grid on the floor of the rooms with windows, with loose furniture and curtains hidden and built-in units left out. Use one BVH of all opaque geometry (fast: about 20 s for a year).
  - Output 4 heat maps over the plan: 21 Dec, 21 Mar (≈ 21 Sep), 21 Jun, and the whole year in hours.
  - Use one orange ramp from light to dark.

### Step 10: Contact sheet (≈10 min + about 6 min of rendering)

Render 5–7 views (living room, kitchen, window, bedroom, bedroom window, view out, courtyard or street) at about 11 times. We used:
- 21 Jun: 5:30, 8:00, 13:00, 17:00, 20:30, 23:00
- 21 Mar: 10:00, 15:00
- 21 Dec: 10:00, 12:00, 14:30

Settings: Cycles, 640 × 400, 48 samples, physical sky + sun only, lamps only after dusk, LED off, **one exposure for all tiles**. Put them on one sheet with a label in each tile.

### Step 11: Drawings (≈30–60 min)

PIL drawings over the faded plan image, with red dimension chains:
- **Rooms**: clear dimensions of every room and window, with a table comparing them to the official areas.
- **Kitchen plan**: numbered modules, the wall cabinets dashed, LED shown, clearances (e.g. distance to the window, open door leaf), and a legend.
- **Kitchen elevation**: heights (plinth 0.15, worktop 0.91, wall cabinets 1.50, doors 2.40, top boxes 2.70, ceiling), appliances, sockets, LED.

### Step 12: 360° tour with light layers, configurator handover and three colour schemes (≈1 h of setup + 1–3 h of rendering)

**Viewpoints.** Place 6–8 points in free floor space, at least 0.3 m from furniture and not inside a door swing, at eye height 1.55 m. Render equirectangular images at 4096 × 2048 with the image centre facing north (so headings are compass headings).

**Light layers.** Light adds up, so render each light source alone and mix them live in the browser:

| Layer | What is on | Size / samples |
|---|---|---|
| sky | sky only, at a reference time | full, 256 |
| sun0…sunN | direct sun only, at N sun positions (we used 8: Dec 10:00 and 12:00; Mar 8:30, 10:30 and 12:30; Jun 9:00, 11:30 and 13:30); only for viewpoints that see a window | full, ~150 |
| night | lit windows of the buildings outside | half, 128 |
| lamps | room lamps + ceiling lights | full, 256 |
| led | LED strips | half, 128 |

- Render to **16-bit PNG, linear, 4 stops under** (exposure −4, view transform Standard), so bright sun is not clipped.
- Encode to JPEG with a **log curve** (x = linear/16, v = log(1024x + 1) / log(1025)). Plain 8-bit made dark walls blotchy.
- Make the renderer **resumable** (skip layers that already exist) and keep the Mac awake (`caffeinate -i -w <blender pid>`). A sleeping Mac slowed one image from 2.5 to 34 minutes.

**Tour page** (`tour/index.html`, three.js): an inside-out sphere with a shader that:
- decodes the layers, then adds sky × (sky brightness at the chosen time ÷ at the reference time) + the nearest sun layer (within 25°) × (direct sun at that time ÷ at the layer's time) + night × (darkness) + lamps × (on/off) + LED × (on/off)
- applies an AgX-like tone curve; fit one gain factor so the result matches a Blender AgX render of the same view (RMSE about 0.015)

It also has jump arrows to the next viewpoints, a small plan map with the current position and view cone, drag/wheel/pinch to look around, and the L key.

**Handover from the configurator.** The "Prohlídka 360°" button opens `tour/?t=<date>T<time>&el=<sun elevation>&az=<azimuth>&sun=<1 if the sun reaches a window>&m=<light mode>&lamps=&led=&code=<configuration code>`. The tour's "Configurator" button sends the light settings back.

**Three colour schemes (demonstration of colour pickup).** Every colour combination would mean rendering everything again, so demonstrate the function with three presets:
1. Make three configuration codes: for example **light** (warm white walls), **warm** (greige walls, olive bedroom) and **dark** (navy living room, charcoal hall). Fill the kitchen fronts, worktop and wardrobe fronts with **randomly picked decor textures** from the catalogue, with a fixed random seed so the result is repeatable.
2. Render the layers once per scheme into `layers/<scheme>/…`. To keep the test short, render the schemes for 2–3 viewpoints with only the sky + lamps layers: 3 schemes × 3 viewpoints × 2 layers = 18 renders, about 45 min.
3. In the tour: if the `code` from the configurator matches a scheme, show it. Otherwise pick the **nearest scheme**: compare the wall colours of the code with each scheme's colours (sum of colour distances per room). Show the scheme's name and a small switcher with the three schemes.
4. The configurator gets a hint next to the button: "the tour shows the nearest of 3 rendered schemes".

Advanced, not needed for the test: live recolouring of any wall colour without re-rendering. Render a mask layer per room's walls (object index or AOV). In the shader, scale the masked pixels by new colour ÷ rendered colour. This works well for matte walls but ignores colour bleeding.

**Run it locally:** in the folder with `index.html` and `tour/`, run `python3 -m http.server 8000` and open `http://localhost:8000/`. The browser does not load the layer images from a `file://` page. The configurator alone still works by double-click.

**Time:** about viewpoints × (2.5 + 2 + 0.5 + 1 + 1.7 × sun positions) min, plus the schemes. Our example-flat run: 72 layers in 2 h 10 min. First flat: 32 layers in about 2 h, including the sleep slowdown.

> Prompt: *"Add 360 viewpoints to apartment.py, write tour_passes.py that renders the light layers (sky, N sun positions, night, lamps, LED) as 16-bit linear PNGs, resumable, an encode script (log JPEG) and tour/index.html that mixes them for the time and switches passed from the configurator. Render three colour schemes (random decor textures, fixed seed) for 3 viewpoints and let the tour pick the scheme nearest to the configurator's code."*

---

## 5. Real timings from our run (reference)

These are rough, not a clean measurement: they come from a live session with many change requests in between.

| Work | Elapsed time | Context |
|---|---|---|
| First flat: full pipeline (web configurator, Blender renders, walk-through, sun) | spread over about 4 days, 3–6 Oct, many sessions | Built from scratch, with iterations driven by the user's wishes. Not representative of a focused run. |
| Example flat: PDF → measured data → first Blender test renders | about 30–35 min | Reused the first flat's scripts. |
| Example flat: then sun hours, sun plan, contact sheet, drawings | about +30 min | Includes about 6 min of rendering. |
| Example flat: web configurator ported (windows on any side, courtyard, new kitchen) | about 40–60 min | Plus later fixes: lights, far plane, LED. |
| One Cycles photo at 1800 × 1200, 128 samples (Apple GPU) | about 25–30 s | |
| One 360 layer at 4096 × 2048, 256 samples | about 2–3 min | Sun layers at ~150 samples about 1.7 min; half-size layers 0.5–1 min. |
| Example flat, 360 tour: 72 layers (8 viewpoints, 8 sun positions for 5 of them) | 2 h 10 min | Rendering only; encoding and checks about 15 min. |
| Example flat, sun simulation in the web, ported from the first flat | about 1 h | Including the calibration against Cycles. |
| Sun hours + sun plan | about 5 min of compute | After the scripts existed. |

**Expectation for a focused test with an AI agent and an existing pipeline:**

| Part | Estimate |
|---|---|
| Core: plan → local HTML + Blender walk-through (Steps 1–7) | 2–3 h |
| Sun simulation + calibration (Step 8) | 1–2 h |
| Sun hours + sun plan (Step 9) | 30 min |
| Contact sheet (Step 10) | 20 min |
| Drawings (Step 11) | 30–60 min |
| 360° tour setup + three colour schemes (Step 12) | 1–1.5 h of work + 2–3 h of rendering (unattended) |
| **Total** | **about 6–9 h of work + 2–3 h of rendering** |

For a scanned or old plan, add about 1 hour for straightening and wall tracing, more if walls are hatched or the plan has no scale bar. **From scratch, without these scripts,** expect several working days.

---

## 6. Acceptance checks (what "done" means)

- [ ] Measured room areas within ±3 % of the official ones (explain any difference in how rooms are counted).
- [ ] Check overlay: walls, openings, furniture and door leaves sit on the plan lines.
- [ ] `index.html` opens by double-click; the plan view shows labelled rooms; clicking a room shows its 3D view; changing a colour updates the 3D model and the code; no errors in the browser console.
- [ ] `byt.blend` opens through the launcher; W A S D walking works; the panel changes colours; the Photo button saves a Cycles image.
- [ ] The same configuration code gives the same look in the web and in Blender.
- [ ] Sun: Python and JS sun positions agree (test); the sun at a chosen date and time lands in the right place in both viewers; at night the lights switch on; the web's floor brightness is within about 0.05 of Cycles in the calibration.
- [ ] Sun hours chart + CSV and the 4-panel sun plan exist and agree with each other (e.g. no sun in a north room in winter).
- [ ] The contact sheet shows clear differences between times with one exposure.
- [ ] Drawings: dimensions match the measured data; the kitchen sheets match the kitchen in both viewers.
- [ ] 360° tour runs on the local server; the configurator button opens it with the same time, switches and the nearest colour scheme; the scheme switcher and the L key work; no console errors.

---

## 7. Data formats (short)

`apartment.json`:
```json
{
  "rooms": [{"id": 2, "name": "Obývací pokoj + kk", "area": 27.2, "dims": "5.60 × 4.28 m", "ceil": 2.75,
             "rects": [[7.361, 1.707, 12.966, 5.987]], "floor": "vinyl", "opts": ["paint", "kitchen"]}],
  "walls": [[x0, y0, x1, y1], ...],
  "openings": [{"kind": "door", "rect": [x0, y0, x1, y1]},
               {"kind": "door", "rect": [...], "entry": true},
               {"kind": "window", "rect": [...], "glass": 6.22, "n": [0, 1], "door": [11.50, 12.37]}],
  "doors": [{"hinge": [7.95, 1.707], "dir": [0, 1], "w": 0.80}],
  "furniture": [{"kind": "sofa", "r": [x0, y0, x1, y1], "z": [0, 0.82], "m": "fabric", "back": "+x"}]
}
```
`kitchen.json`:
```json
{"B": {"box": [{"n": "f_dw", "m": "front", "a": [x, y, z], "b": [x, y, z]}],
       "cyl": [...], "arc": [...], "cut": [a, b], "bowl": [a, b]}}
```
Kitchen coordinates are in Blender space (y = −plan y). LED boxes carry a `dir` (emission direction).

---

## 8. Suggested order for the test

1. Steps 1–3 (plan → `apartment.json`). Check the overlay.
2. Step 5 with a simple light setup. Render one interior view and the plan view.
3. Step 6, the walk-through.
4. Step 7, the web configurator.
5. Step 4, the kitchen; it also shows in both viewers.
6. Step 8, sun simulation, then Step 9, the sun analysis (needs the surroundings).
7. Steps 10 and 11, contact sheet and drawings.
8. Step 12, the 360° tour. Start the rendering in the evening or over lunch; it runs unattended.

Stop the clock at each checkpoint.

---

## 9. Timing sheet (fill in)

| Step | Start | End | Minutes | Problems / notes |
|---|---|---|---|---|
| 1 Plan image + scale | | | | |
| 2 Walls | | | | |
| 3 Rooms, openings, doors, furniture | | | | |
| 4 Kitchen (optional) | | | | |
| 5 Blender scene | | | | |
| 6 Blender walk-through | | | | |
| 7 Local web configurator | | | | |
| 8 Sun simulation + calibration | | | | |
| 9 Sun hours + sun plan | | | | |
| 10 Contact sheet | | | | |
| 11 Drawings | | | | |
| 12 360° tour: setup | | | | |
| 12 360° tour: rendering (unattended) | | | | |
| 12 Three colour schemes | | | | |
| Checks (section 6) | | | | |
| **Total** | | | | |

Also note: plan type (vector PDF, scan or photo), plan quality, whether scripts were reused, and the tools and models used.
