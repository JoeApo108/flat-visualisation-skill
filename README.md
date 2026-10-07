# Flat visualisation from a floor plan

Turns a flat's floor plan (vector PDF or an old scan) into:

- **a web configurator**: one `index.html` with a 3D plan, room views, colour/tile/decor pickers, sun by date and time, automatic night lights;
- **a Blender walk-through**: `byt.blend` with W A S D walking, a finishes panel and a Cycles photo button;
- **a sun analysis**: direct-sun hours per window per month, and a sun plan of the floor;
- **a contact sheet** (views × times of day, one exposure), **drawings** (room sizes, kitchen plan and elevation);
- **a 360° tour** that mixes rendered light layers live and takes time, lights and colours from the configurator.

Everything runs locally; nothing is deployed.

## Contents

| Path | What |
|---|---|
| `SKILL.md` | Claude Code skill: how an agent runs and adapts the kit for a new plan |
| `playbook.md` | The method step by step, pitfalls, real timings, acceptance checks, timing sheet |
| `tools.sh` | Checks the required tools and installs missing ones (macOS, Homebrew) |
| `kit/` | Working scripts, set up for an example flat; inputs not included |

## Install

In Claude Code, say:

> Install the skill https://github.com/JoeApo108/flat-visualisation-skill into ~/.claude/skills/flat-visualisation

or run in a terminal:

```sh
git clone https://github.com/JoeApo108/flat-visualisation-skill.git ~/.claude/skills/flat-visualisation
```

Start a new Claude Code session and type `/flat-visualisation path/to/plan.pdf`. The skill first checks Blender, Python + Pillow, ImageMagick and poppler. It asks before it installs anything missing (macOS, Homebrew), and at the end it tells you how to check each result.

## Requirements

Blender 4.x/5.x (`blender` on PATH; tested with Blender 5 on macOS, Apple GPU), Python 3 with Pillow, ImageMagick (`magick`), poppler (`pdftoppm`), Google Chrome (only for `render/web_floor.py`). `bash tools.sh check` lists what is missing; `bash tools.sh install` installs it (macOS, Homebrew). The web page loads three.js r147 from a CDN.

## Quick start

The repo has code only: no floor plan, textures or map data. Put your inputs into `kit/` as listed in [SKILL.md](SKILL.md#inputs-not-in-the-repo-supply-them). Then run the steps of the pipeline table there, from `kit/`:

```sh
cd kit
C='1:P1·F22 2:P9·B·F11·W02 3:P1·T2 4:P1·F16 5:P1·T1'      # configuration code
python3 wallmask.py src/plan.png src/wallmask.png        # plan -> wall mask
python3 data.py && python3 kitchen.py && python3 site.py # -> app/apartment.json, kitchen.json, site.json
python3 app/build.py                                    # -> app/index.html (open it by double-click)
blender -b -P render/build_blend.py -- "$C"              # -> byt.blend; open it with ./Byt.command
```

The scripts carry the example flat's measurements, so they are a worked example: adapt the per-flat values listed in SKILL.md.

## Data sources

- Map data you fetch: © OpenStreetMap contributors, ODbL.
- The example flat's coordinates in `data.py` were measured from the developer's sales plan (not included).
