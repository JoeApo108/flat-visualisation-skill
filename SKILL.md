---
name: flat-visualisation
description: Turn a flat's floor plan (vector PDF or old scan) into a local web configurator (one HTML file), a Blender walk-through, a date/time sun simulation, sun-hours charts and a floor sun plan, a contact sheet, room and kitchen drawings, and a 360° tour that mixes rendered light layers. Use when asked to visualise, model or configure an apartment from its floor plan, check its sunlight, or time how long such a build takes.
---

# Flat visualisation

- **Kit:** `${CLAUDE_SKILL_DIR}/kit/` holds working scripts, set up for an example flat (2+kk, 4th floor, courtyard).
- **Method:** [playbook.md](playbook.md) has the pitfalls, real timings, acceptance checks (section 6) and timing sheet (section 9). Read the playbook step you are on before you change its script.

## Rules

- Work in a copy, never in the skill folder: `cp -R "${CLAUDE_SKILL_DIR}/kit" <project>/` and run everything from `<project>/kit`.
- If the user is timing the build, write start and end times per step into the timing sheet.
- After each step, look at its check image or output before going on. Most errors are visible (walls off the plan lines, a "desk" outside the window, black faces).
- Coordinates are plan metres: x east, y south, z up. Blender uses (x, −y, z). Keep the room role ids 1 hall, 2 living + kitchen, 3 bathroom, 4 bedroom, 5 WC, so a configuration code means the same thing in every flat.
- Every script keeps its run command in its header comment.

## Step 0: tools (always first)

1. Run `bash "${CLAUDE_SKILL_DIR}/tools.sh" check`. It lists blender, python3, Pillow, ImageMagick (`magick`), poppler (`pdftoppm`) and the optional Chrome as OK or MISSING, then a PLAN of install commands.
2. If anything is MISSING, show the user the MISSING and PLAN lines and ask whether to install them. Install nothing without a yes. Lines marked NEEDS are commands the user runs themselves, because they ask for a password (Homebrew installer, `sudo`); in Claude Code they can type `! <command>`.
3. After a yes, run `bash "${CLAUDE_SKILL_DIR}/tools.sh" install`. It installs only what is missing, never upgrades what is already there, then checks again. If something is still MISSING, stop and report it.
4. The install part works on macOS with Homebrew only. On other systems show the MISSING list and stop.

## Inputs (not in the repo, supply them)

| Put in `kit/` | What |
|---|---|
| `src/plan.png` | The flat's plan at 300 dpi, cropped to the flat. |
| `oresi/texsq/<code>.jpg`, `oresi/texsq/FLOOR.jpg`, `oresi/tex/FLOOR2.jpg` | Decor and floor textures for Blender, square (we used 876 px). |
| `web/tex/<code>.jpg`, `web/tex/FLOOR.jpg` | The same textures for the web, 512 px. |
| `oresi/catalog_clean.json`, `web/catalog_clean.json` | Decor list: `[{"code": "F01", "title": "…", "desc": "…", "maker": "…", "section": "…"}]`. `F..` are fronts, `W..` are worktops. |
| `site/osm.json` | OpenStreetMap buildings around the flat, fetched with the command below. |

```sh
LL=50.0875,14.4213   # flat lat,lon
curl -s -A "flat-visualisation/1.0" https://overpass-api.de/api/interpreter -o kit/site/osm.json --data-urlencode \
 "data=[out:json][timeout:60];(way[\"building\"](around:400,$LL);relation[\"building\"](around:400,$LL);way[\"landuse\"~\"^(grass|village_green)$\"](around:400,$LL);way[\"leisure\"=\"park\"](around:400,$LL););out geom;"
```

Overpass returns HTTP 406 without a User-Agent (`-A`).

## Pipeline

`C` is the configuration code, e.g. `C='1:P1·F22 2:P9·B·F11·W02 3:P1·T2 4:P1·F16 5:P1·T1'`.

| # | Step | Command (from `kit/`) | Edit per flat |
|---|---|---|---|
| 1 | Plan + scale | `pdftoppm -r 300 -png plan.pdf src/hi`, crop the flat to `src/plan.png`, measure the scale bar in px/m | – |
| 2 | Walls | `python3 wallmask.py src/plan.png src/wallmask.png` | `T`, `K` for scans and hatched walls |
| 3 | Flat data | `python3 data.py` → `app/apartment.json` + area check | `S, OX, OY`, preview factor, rooms, openings (glass + outward normal), doors, furniture |
| 4 | Kitchen | `python3 kitchen.py` → `app/kitchen.json` | `WALL, Y0`, module list |
| 5 | Surroundings | `python3 site.py [floor]` → `app/site.json` | everything: `PIN` (lat, lon), facade azimuth, own building, `site/osm.json` (Overpass, radius 350 m). Minimum: location + facade azimuth + OSM footprints. |
| 6 | Blender test | `blender -b -P render/apartment.py -- "$C" $PWD/out/test plan,r_liv 64` | `CAMS`, plan `ortho_scale`, `PANOS` in `render/apartment.py` |
| 7 | Walk-through | `blender -b -P render/build_blend.py -- "$C"` → `byt.blend`; open with `./Byt.command` | `VIEW` in `render/build_blend.py` |
| 8 | Web | `python3 app/build.py` → `app/index.html` | `app/template.html`: title, `ROOMVIEW`, `PLAN`, default `state`, `STORE`, `FILES` |
| 8b | Calibrate web light | `SUN="2026-10-06 13:00" blender -b -P render/apartment.py -P render/floor_cyc.py -- "$C" x none 64`, then `python3 render/web_floor.py` | `ROOMS` rects in both scripts, `TIMES` |
| 9 | Sun hours | `blender -b -P render/apartment.py -P render/sun_hours.py -- "$C" $PWD/out/x none 1` | – (windows come from `apartment.json`) |
| 9b | Sun plan | `blender -b -P render/apartment.py -P render/sun_plan.py -- "$C" $PWD/out/x none 1` | plan image, crop |
| 10 | Contact sheet | `blender -b -P render/apartment.py -P render/contact.py -- "$C" $PWD/out/x none 48` | `VIEWS`, `TIMES` |
| 11 | Drawings | `python3 drawings.py` | `S, OX, OY`, plan image, labels |
| 11b | Photos + downloads | `SUN="2026-10-06 11:00" LED=0 blender -b -P render/apartment.py -- "$C" $PWD/out/foto_1006_1100 r_liv,r_kit,r_bed,r_view,r_court 128`, then `zsh files.sh` | names in `files.sh` = `FILES` in the template |
| 12 | 360° tour | `SUN="2026-10-06 13:00" caffeinate -i blender -b -P render/tour_passes.py -- "$C" $PWD/out/layers/L <viewpoints> 256 100`; map: `blender -b -P render/apartment.py -- "$C" $PWD/out/tourmap plan 64`; `zsh tour_layers.sh`; `python3 -m http.server -d out` | `SUN_VIEWS`, `SUN_POS` (tour_passes.py); viewpoints, `PLAN`, `CODE` (app/tour.html) |

Step 12 renders for 1–3 h. The renderer resumes: it skips layers that already exist. Keep the Mac awake, because sleep slowed one layer from 2.5 to 34 min. The tour needs the local server, because browsers block the layer images on `file://`.

## Not in the kit

- **Three colour schemes in the tour** (playbook, Step 12): render the layers per scheme into `layers/<scheme>/`, and let the tour show the scheme nearest to the configurator's code. Build it from the playbook description.
- **Deployment**: none. All outputs are local files.

## Done when

Section 6 of the playbook passes. Report the measured times per step, the plan type (vector, scan or photo), and what had to be done by hand.

## Final message: how to check the result

End with this list, in the user's language, with full paths, and only for the parts that were built:

- **Web configurator:** double-click `<project>/kit/app/index.html`. The plan shows labelled rooms. Clicking a room opens its 3D view. Changing a wall colour changes the model and the configuration code. In "Skutečné světlo", the time slider moves the sun; after dusk the lights switch on.
- **Blender walk-through:** run `<project>/kit/Byt.command`, or `blender byt.blend --python render/panel.py` from `kit/`. Press N for the "Byt" tab, walk with W A S D and the mouse, pick a viewpoint, and press "Fotka" to save a Cycles photo to `kit/fotky/`.
- **Sun:** `kit/out/sun_hours_<floor>np.png` (+ `.csv`) and `kit/out/sun_plan_<floor>np.png`. Sanity check: a north window gets no direct sun in winter.
- **Contact sheet and drawings:** `kit/out/contact_<floor>np/contact_sheet.jpg`, `kit/out/byt_*.png`.
- **360° tour:** run `cd <project>/kit && python3 -m http.server -d out 8000`, open http://localhost:8000/, and press "Prohlídka 360°".
- **Checklist and times:** `playbook.md` section 6 and the timing sheet in section 9.
