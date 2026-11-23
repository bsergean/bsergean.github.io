#!/usr/bin/env python3
"""Build local gallery previews from the image manifest (requires Pillow)."""
from pathlib import Path
from hashlib import sha256
from html import escape
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor
import json
import re
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'migration/image-manifest.json'
manifest=json.loads(REPORT.read_text())
thumbdir=ROOT/'assets/previews';thumbdir.mkdir(exist_ok=True)

def preview(asset):
    key=asset['key'];path=ROOT/asset['path'];token=sha256(key.encode()).hexdigest()[:18]
    if path.suffix.lower()=='.svg':
        return key,{'thumbnail':asset['path'],'display':asset['path'],'width':600,'height':450}
    with Image.open(path) as source:
        image=ImageOps.exif_transpose(source)
        width,height=image.size
        for edge,label in [(600,'thumb'),(1400,'display')]:
            out=thumbdir/f'{token}-{label}.webp'
            if not out.exists():
                resized=image.copy();resized.thumbnail((edge,edge))
                if resized.mode not in ('RGB','RGBA'):resized=resized.convert('RGBA' if 'transparency' in resized.info else 'RGB')
                resized.save(out,'WEBP',quality=82,method=4)
        return key,{'thumbnail':f'assets/previews/{token}-thumb.webp','display':f'assets/previews/{token}-display.webp','width':width,'height':height}

assets={asset['key']:asset for asset in manifest['assets']}
with ThreadPoolExecutor(max_workers=4) as pool:
    for key,derived in pool.map(preview,manifest['assets']):assets[key].update(derived)
REPORT.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')

def albumid(page):return 'album-'+sha256(page['url'].encode()).hexdigest()[:12]
def title(page):return page['title'].split('|')[0].strip() or 'CathoSV'
def sourcepart(part):return next(p for p in manifest['pages'] if unquote(p['url']).rstrip('/').endswith(part))
def contentkeys(page):
    return list(dict.fromkeys(i['key'] for i in page['images'] if max(int(i.get('width') or 0),int(i.get('height') or 0))>90))
def grid(keys,label,limit=None):
    keys=list(dict.fromkeys(keys))
    if limit:keys=keys[:limit]
    tiles=[]
    for index,key in enumerate(keys,1):
        a=assets[key];caption=f'{label} · Image {index}';tileclass='photo-tile portrait' if a['height']>a['width']*1.05 else 'photo-tile'
        tiles.append(f'<a class="{tileclass}" href="{escape(a["path"],quote=True)}" data-photo data-caption="{escape(caption,quote=True)}" aria-label="Agrandir : {escape(caption,quote=True)}"><img src="{a["thumbnail"]}" width="{a["width"]}" height="{a["height"]}" loading="lazy" decoding="async" alt="{escape(caption,quote=True)}"></a>')
    return '<div class="photo-grid">\n'+'\n'.join(tiles)+'\n</div>'
def insert_section(path,html):
    s=path.read_text()
    s=re.sub(r'\n<!-- migrated-gallery -->.*?<!-- /migrated-gallery -->\n','\n',s,flags=re.S)
    if path.name=='index.html':s=s.replace('</main>', '\n<!-- migrated-gallery -->\n'+html+'\n<!-- /migrated-gallery -->\n</main>')
    else:s=s.replace('</article><aside', '\n<!-- migrated-gallery -->\n'+html+'\n<!-- /migrated-gallery -->\n</article><aside')
    path.write_text(s)

# Restore every Marches content image in the same section order as the source page.
walkpage=sourcepart('/marche-des-hommes-époux-et-pères')
keys=contentkeys(walkpage)
assert len(keys)==23, f'Review source section boundaries: expected 23 Marches images, found {len(keys)}'
p=ROOT/'marches.html';s=p.read_text()
s=s.replace('class="wrap page-layout"','class="wrap page-layout gallery-layout"')
s=re.sub(r'<figure class="walk-photo">.*?</figure>','',s,flags=re.S)
s=re.sub(r'<!-- walk-gallery-[^>]+ -->.*?<!-- /walk-gallery -->','',s,flags=re.S)
for section,group,label in [('hommes-2026',keys[:4],'Marche des hommes 2026'),('femmes-2026',keys[4:11],'Marche des femmes 2026')]:
    pattern=rf'(<section id="{section}">)(.*?)(</section>)'
    s=re.sub(pattern,lambda m:m[1]+m[2]+'<!-- walk-gallery-'+section+' -->'+grid(group,label)+'<!-- /walk-gallery -->'+m[3],s,flags=re.S)
# Separate the two historical collections so all twelve archive photos remain visible.
archive='''<h2>D’autres chemins parcourus</h2><h3>Les hommes à Angel Island · 2025</h3><p>Les 26 et 27 avril, seize hommes se sont retrouvés pour marcher, prier et échanger sur leur chemin de foi.</p>'''+grid(keys[11:17],'Marche des hommes 2025')+'''<h3>Les femmes à Point Reyes · 2024</h3><p>Un week-end de retraite accompagné par les Pères Johannes et David, avec des randonnées, des messes et des temps de partage.</p>'''+grid(keys[17:],'Marche des femmes 2024')
s=re.sub(r'(<section id="souvenirs">).*?(</section>)',lambda m:m[1]+archive+m[2],s,flags=re.S)
p.write_text(s)

# Restore photographs on the matching pages, including youth and community sections.
page_sources={
 'jeunes.html':['/catéchisme','/aumônerie','/scouts-en-français'],
 'adultes.html':['/prière-des-mères','/equipes-notre-dame-end'],
 'bienvenue.html':['/bienvenue-aux-nouveaux-dans-la-baie','/qui-sommes-nous'],
 'messes.html':['/messe-en-français','/peninsula-st-nicholas-st-wiliam'],
 'donner.html':['/donner-pour-cathosv-1'],
}
for filename,sources in page_sources.items():
    pages=[sourcepart(part) for part in sources]
    merged=list(dict.fromkeys(key for page in pages for key in contentkeys(page)))
    if not merged:continue
    html='<section class="restored-gallery"><h2>En images</h2><p>Les images de ces activités, conservées depuis les pages de la communauté. Sélectionnez une image pour l’agrandir.</p>'+grid(merged,'CathoSV')+'<a href="photos.html#'+albumid(pages[0])+'">Parcourir les albums de la communauté</a></section>'
    insert_section(ROOT/filename,html)

home=sourcepart('www.cathosv.org')
# Community snapshots from later in the original homepage; the full set stays in the archive.
homekeys=contentkeys(home)
communitykeys=[k for k in homekeys if k.lower().endswith(('.jpg','.jpeg')) and not k.startswith('nsplsh')]
html='<section class="section wrap home-photos"><div class="section-heading"><div><p class="eyebrow">DES VISAGES ET DES SOUVENIRS</p><h2>La communauté en images</h2></div><a class="underlined" href="photos.html">Tous les albums photos</a></div>'+grid(communitykeys[-4:],'Vie de la communauté')+'</section>'
insert_section(ROOT/'index.html',html)

# Build a complete, browsable image archive, including references from Wix metadata.
base=(ROOT/'newsletter.html').read_text()
base=base.replace('Les nouvelles de CathoSV','Les photos de la communauté').replace('GARDONS LE LIEN','LA VIE EN IMAGES')
base=base.replace('Les annonces de messe, les prochaines rencontres et les occasions de participer à la vie de la communauté.','Les albums, affiches et souvenirs de la communauté, conservés depuis le site d’origine.')
base=base.replace('class="wrap page-layout"','class="wrap page-layout gallery-layout"')
select='<label class="album-picker" for="album-picker">Retrouver un album</label><select id="album-picker"><option value="">Choisir une page ou un article</option>'
body=f'<section><h2>Tous les albums</h2><p>{len(manifest["assets"])} images conservées depuis les {len(manifest["pages"])} pages et articles publics du site d’origine. Les fichiers originaux sont disponibles en ouvrant les images. Certains albums incluent aussi les affiches et illustrations de la page.</p>'
for blog,label in [(False,'Pages de la communauté'),(True,'Articles du blog')]:
    select+=f'<optgroup label="{label}">'
    for page in manifest['pages']:
        if ('/post/' in page['url'])!=blog:continue
        select+=f'<option value="{albumid(page)}">{escape(title(page))}</option>'
    select+='</optgroup>'
select+='</select>'
body+=select+'</section>'
for blog,label in [(False,'Pages de la communauté'),(True,'Archives du blog')]:
    body+=f'<section><h2>{label}</h2>'
    for page in manifest['pages']:
        if ('/post/' in page['url'])!=blog:continue
        body+=f'<details class="album" id="{albumid(page)}"><summary>{escape(title(page))}<span>{len(page["assets"])} images</span></summary>'+grid(page['assets'],title(page))+'</details>'
    body+='</section>'
base=re.sub(r'(<article class="page-content">).*?(</article>)',lambda m:m[1]+body+m[2],base,flags=re.S)
(ROOT/'photos.html').write_text(base)

# Compact page covers make the desktop title area part of the photographic layout.
coverkeys={
 'marches.html':keys[1],
 'bienvenue.html':next((k for k in contentkeys(home) if k.startswith('f0c182_1b883')),communitykeys[0]),
 'jeunes.html':contentkeys(sourcepart('/scouts-en-français'))[0],
}
for filename,key in coverkeys.items():
    p=ROOT/filename;s=p.read_text();asset=assets[key]
    if 'class="page-intro has-cover"' in s:continue
    s=s.replace('class="page-intro"','class="page-intro has-cover"')
    s=re.sub(r'(<div class="page-intro has-cover"><div class="wrap">)(.*?)(</div></div>)',lambda m:m[1]+'<div class="title-block">'+m[2]+'</div><img class="intro-cover" src="'+asset['display']+'" width="'+str(asset['width'])+'" height="'+str(asset['height'])+'" alt="Un moment partagé dans la communauté CathoSV">'+m[3],s,count=1,flags=re.S)
    p.write_text(s)

# Every page has the same top-level navigation; retain the requested old-site link.
links=[('index.html','Accueil'),('messes.html','Messes'),('agenda.html','Agenda'),('bienvenue.html','Communauté'),('jeunes.html','Jeunes'),('adultes.html','Adultes'),('marches.html','Marches'),('photos.html','Photos'),('newsletter.html','Newsletter'),('donner.html','Faire un don')]
for p in ROOT.glob('*.html'):
    s=p.read_text();items=[]
    s=re.sub(r'<div class="preview-bar">.*?</div>', '<div class="preview-bar"><span>CathoSV · Maquette</span><a href="https://www.cathosv.org/" target="_blank" rel="noopener noreferrer">Ancien site</a></div>', s, count=1, flags=re.S)
    css_version=sha256((ROOT/'style.css').read_bytes()).hexdigest()[:12]
    js_version=sha256((ROOT/'script.js').read_bytes()).hexdigest()[:12]
    s=re.sub(r'href="style\.css(?:\?[^"]*)?"', f'href="style.css?v={css_version}"', s)
    s=re.sub(r'src="script\.js(?:\?[^"]*)?"', f'src="script.js?v={js_version}"', s)
    for href,label in links:
        attrs=' class="button small"' if href=='donner.html' else ''
        current=' aria-current="page"' if href==p.name else ''
        items.append(f'    <a{attrs} href="{href}"{current}>{label}</a>')
    nav='<nav id="navigation" aria-label="Navigation principale">\n'+'\n'.join(items)+'\n  </nav>'
    s=re.sub(r'<nav id="navigation".*?</nav>',lambda _:nav,s,flags=re.S)
    p.write_text(s)
print(f'Built {len(assets)} previews; restored all 23 Marches images and matching page galleries; generated complete archive.')
