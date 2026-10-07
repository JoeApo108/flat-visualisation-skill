import base64, json, os
H = os.path.dirname(os.path.abspath(__file__)) + '/'   # app/
WEB = H + '../web/'
cat = [{k: o[k] for k in ('code', 'title', 'desc', 'maker', 'section')} for o in json.load(open(WEB + 'catalog_clean.json'))]
tex = {c: 'data:image/jpeg;base64,' + base64.b64encode(open(WEB + f'tex/{c}.jpg', 'rb').read()).decode() for c in [o['code'] for o in cat] + ['FLOOR']}
s = open(H + 'template.html', encoding='utf-8').read()
s = s.replace('/*__APT__*/null', open(H + 'apartment.json', encoding='utf-8').read())
s = s.replace('/*__KIT__*/null', open(H + 'kitchen.json').read())
s = s.replace('/*__CAT__*/null', json.dumps(cat, ensure_ascii=False, separators=(',', ':')))
s = s.replace('/*__TEX__*/null', json.dumps(tex, separators=(',', ':')))
s = s.replace('/*__SITE__*/null', open(H + 'site.json', encoding='utf-8').read())
open(H + 'byt.html', 'w', encoding='utf-8').write(s)
open(H + 'index.html', 'w', encoding='utf-8').write('<!doctype html>\n<html lang="cs"><meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<style>html,body{margin:0}[hidden]{display:none!important}</style>\n' + s)
print(round(len(s.encode()) / 1e6, 2), 'MB')
