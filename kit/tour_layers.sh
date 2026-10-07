#!/bin/zsh
# Example flat tour: rendered light layers (16-bit PNG, sRGB, 4 stops under; night + LED already half size) -> log-encoded JPEG
# v = log(1024 x + 1) / log(1025), x = linear / 16 (as for the first flat); plan render -> tour map; tour page.
cd "${0:A:h}"
D=out/tour; mkdir -p $D/layers
for f in out/layers/L_p_*_{sky,night,lamps,led,sun?}.png(N); do
  n=$(basename $f .png); n=${n#L_}
  magick $f -colorspace RGB -evaluate Log 1024 -set colorspace sRGB -quality 90 -sampling-factor 4:4:4 $D/layers/$n.jpg
done
magick out/tourmap_plan.jpg -resize 1000x -quality 85 $D/plan.jpg
cp app/tour.html $D/index.html; cp app/index.html out/index.html   # serve out/: python3 -m http.server -d out
ls $D/layers | wc -l; du -sh $D/layers
