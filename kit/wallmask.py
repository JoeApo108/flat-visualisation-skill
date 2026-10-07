# Plan image -> wall mask: dark pixels (black walls, grey shafts) minus thin lines (door swings, frames, furniture) by an 11 px opening.
# Run: python3 wallmask.py src/plan.png src/wallmask.png   (reproduces the example flat's mask exactly; for scans tune T and K)
import sys
from PIL import Image, ImageFilter
T, K = 120, 11   # darkness threshold (0-255), opening size in px (~6-7 cm at 165 px/m)
src, dst = sys.argv[1], sys.argv[2]
m = Image.open(src).convert('L').point(lambda v: 255 if v < T else 0)
m.filter(ImageFilter.MinFilter(K)).filter(ImageFilter.MaxFilter(K)).save(dst)
print('saved', dst)
