#!/bin/zsh
# Outputs -> out/soubory/ (+ 360x240 thumbnails in nahled/) for the configurator's "Ke stažení" panel; names = FILES in app/template.html.
cd "${0:A:h}"; D=out/soubory; mkdir -p $D/nahled
cp out/byt_rooms.png $D/byt_rozmery_mistnosti.png
cp out/byt_kitchen_plan.png $D/byt_kuchyn_pudorys.png
cp out/byt_kitchen_elevation.png $D/byt_kuchyn_pohled_na_linku.png
cp out/sun_hours_4np.png $D/byt_slunce_hodiny_4NP.png
cp out/sun_plan_4np.png $D/byt_slunecni_plan_4NP.png
for v n in r_liv obyvak r_kit kuchyn r_bed pokoj r_view vyhled r_court dvur; do cp out/foto_1006_1100_$v.jpg $D/byt_foto_2026-10-06_1100_$n.jpg; done
cp out/contact_4np/contact_sheet.jpg $D/byt_kontaktni_list_4NP.jpg
for f in $D/*.*; do magick $f -resize 360x240^ -gravity center -extent 360x240 -quality 82 $D/nahled/${${f:t}:r}.jpg; done
ls $D | wc -l
