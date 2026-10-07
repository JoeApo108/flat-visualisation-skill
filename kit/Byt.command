#!/bin/zsh
# Opens the walk-through: Blender with byt.blend and the "Byt" side panel (macOS; elsewhere run the same blender command from this folder).
cd "${0:A:h}"
exec /Applications/Blender.app/Contents/MacOS/Blender byt.blend --python render/panel.py
