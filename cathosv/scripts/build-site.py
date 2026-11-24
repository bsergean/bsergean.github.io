#!/usr/bin/env python3
"""Render the original editorial snapshots without paraphrasing.

Requires beautifulsoup4 and lxml. The build checks every source text block before
writing HTML. Image previews are maintained separately by build-galleries.py.
"""
from pathlib import Path
from hashlib import sha256
from html import escape
from urllib.parse import urlsplit,unquote,urljoin
from collections import Counter
from bs4 import BeautifulSoup,Tag,Comment
import json,re,posixpath,urllib.request

ROOT=Path(__file__).resolve().parents[1]
content=json.loads((ROOT/'migration/original-content.json').read_text())
media=json.loads((ROOT/'migration/image-manifest.json').read_text())
assert not content['failures'] and len(content['pages'])==138
PAGES=content['pages']
ASSETS={a['key']:a for a in media['assets']}

def norm(s):return re.sub(r'\s+',' ',s).strip()
def canonical(url):return unquote(urlsplit(url).path).rstrip('/') or '/'
ROUTES={canonical(p['url']):p['local_path'] for p in PAGES}
assert len(set(ROUTES.values()))==len(PAGES)
BY_PATH={p['local_path']:p for p in PAGES}
CSS=sha256((ROOT/'style.css').read_bytes()).hexdigest()[:12]
JS=sha256((ROOT/'script.js').read_bytes()).hexdigest()[:12]
AUDIT=[]
EMITTED={}

def relative(target,current):
    return posixpath.relpath(target,posixpath.dirname(current) or '.')
def link(href,current,origin):
    if not href:return ''
    full=urljoin(origin,href);u=urlsplit(full)
    if u.scheme in ['javascript','data']:return ''
    if u.hostname in ['www.cathosv.org','cathosv.org']:
        path=canonical(full)
        if path in ROUTES:target=ROUTES[path]
        elif path=='/donner':target='donner.html'
        elif path.startswith('/blog/hashtags/') or path.startswith('/profile/'):target='blog.html'
        else:return href
        result=relative(target,current)
        if u.fragment:result+='#'+u.fragment
        return result
    return href

ALLOWED={'div','span','p','br','hr','h1','h2','h3','h4','h5','h6','ul','ol','li','a','strong','b','em','i','u','s','sup','sub','blockquote','table','thead','tbody','tr','th','td','figure','figcaption','section','img'}
def cleaned(fragment,current,origin):
    soup=BeautifulSoup(fragment,'lxml')
    for comment in soup.find_all(string=lambda s:isinstance(s,Comment)):comment.extract()
    for tag in list(soup.find_all()):
        if not tag.name or not tag.parent:continue
        if tag.name in ['html','body']:continue
        if tag.name in ['script','style','svg','noscript']:tag.decompose();continue
        if tag.name not in ALLOWED:tag.unwrap();continue
        attrs=tag.attrs.copy();style=attrs.get('style','')
        keep={k:v for k,v in attrs.items() if k in ['id','title','colspan','rowspan','scope','start','type']}
        if tag.name=='a':
            href=link(attrs.get('href',''),current,origin)
            if href:keep['href']=href
            if attrs.get('target')=='_blank':keep.update(target='_blank',rel='noopener noreferrer')
        if tag.name=='img':
            match=re.search(r'https://static\.wixstatic\.com/media/([^/]+)',attrs.get('src',''))
            assert match and match[1] in ASSETS,('Unmapped inline image',attrs.get('src'))
            asset=ASSETS[match[1]]
            keep.update(src=relative(asset['display'],current),alt=attrs.get('alt',''),width=str(asset['width']),height=str(asset['height']),loading='lazy')
        if tag.name=='p' and not tag.get_text().strip('\u200b\ufeff \n\t\r'):keep['class']='source-spacer'
        tag.attrs=keep
        if tag.name=='h1':tag.name='h2'
        if tag.name=='span':
            if re.search(r'font-weight\s*:\s*(bold|[6-9]00)',style):tag.name='strong'
            elif re.search(r'font-style\s*:\s*italic',style):tag.name='em'
            elif not tag.get('id'):tag.unwrap()
    return ''.join(str(child) for child in soup.body.contents)

def anchors(block,emitted):
    out=''
    for id_ in block.get('anchors',[]):
        if id_ and id_ not in emitted:
            emitted.add(id_);out+='<span class="source-anchor" id="'+escape(id_,quote=True)+'"></span>'
    return out

def text_block(page,index,block,current,emitted,footer=False):
    html=cleaned(block['html'],current,page['url'])
    result=BeautifulSoup(html,'lxml').get_text('',strip=False)
    assert norm(result)==norm(block['text']),(page['url'],index,'Text changed during sanitization')
    token=('footer-' if footer else '')+str(index)
    marker=f'{page["local_path"]}:{token}'
    AUDIT.append({'page':current,'source':page['url'],'block':token,'sha256':sha256(norm(result).encode()).hexdigest()})
    # Preserve source anchors once; IDs in nested original rich text stay local.
    inner=BeautifulSoup(html,'lxml')
    for tag in inner.find_all(id=True):
        if tag['id'] in emitted:del tag['id']
        else:emitted.add(tag['id'])
    html=''.join(str(child) for child in inner.body.contents)
    return ('<span id="evenements"></span>' if current=='index.html' and not footer and norm(block['text'])=='Les événements CathoSV' else '')+anchors(block,emitted)+f'<div class="source-text" data-source-page="{escape(page["local_path"],quote=True)}" data-source-block="{token}">'+html+'</div>'

def image_grid(page,group,current,emitted,document=False):
    items=[];prefix=''
    for index,block in group:
        asset=ASSETS.get(block['key'])
        assert asset,('Image absent from transfer inventory',page['url'],block['key'])
        alt=block.get('alt','');caption=alt or page['title']
        cls='photo-tile portrait' if asset['height']>asset['width']*1.05 else 'photo-tile'
        imagepath=asset['display'] if document or len(group)==1 else asset['thumbnail']
        prefix+=anchors(block,emitted)
        original_link=block.get('href')
        href=link(original_link,current,page['url']) if original_link else relative(asset['path'],current)
        attrs='' if original_link else ' data-photo'
        if original_link and block.get('target')=='_blank':attrs+=' target="_blank" rel="noopener noreferrer"'
        image_label=caption if original_link else 'Agrandir : '+caption
        items.append(f'<a class="{cls}" href="{escape(href,quote=True)}"{attrs} data-caption="{escape(caption,quote=True)}" data-source-image="{escape(block["key"],quote=True)}" aria-label="{escape(image_label,quote=True)}"><img src="{relative(imagepath,current)}" width="{asset["width"]}" height="{asset["height"]}" alt="{escape(alt,quote=True)}" loading="lazy" decoding="async"></a>')
    return prefix+'<div class="photo-grid source-gallery'+(' source-documents' if document else '')+'" data-count="'+str(len(group))+'">'+''.join(items)+'</div>'

def render_blocks(page,current,selected=None,footer=False):
    blocks=page['footer'] if footer else page['blocks']
    indices=list(range(len(blocks))) if selected is None else selected
    emitted=EMITTED.setdefault(current,set());out=[];image_run=[]
    def flush():
        if image_run:
            out.append(image_grid(page,image_run,current,emitted,document=page['kind']=='post'))
            image_run.clear()
    for index in indices:
        block=blocks[index]
        if block['kind']=='image':image_run.append((index,block));continue
        flush()
        if block['kind']=='text':out.append(text_block(page,index,block,current,emitted,footer))
        elif block['kind']=='video' and block.get('src'):
            src=block['src'];video_path='assets/videos/'+sha256(src.encode()).hexdigest()[:20]+'.mp4'
            destination=ROOT/video_path;destination.parent.mkdir(exist_ok=True)
            if not destination.exists():destination.write_bytes(urllib.request.urlopen(src,timeout=60).read())
            out.append(f'<video class="source-video" controls preload="metadata" src="{relative(video_path,current)}"></video>')
        elif block['kind']=='embed' and block.get('src'):
            src=block['src'];title=block.get('title') or page['title']
            out.append(f'<iframe class="source-embed" src="{escape(src,quote=True)}" title="{escape(title,quote=True)}" loading="lazy" allowfullscreen></iframe>')
    flush()
    return ''.join(out)

# Labels and grouping follow the original site's main navigation.
GROUPS=[
 ('Accueil',[('Accueil','/'),('Bienvenue aux nouveaux dans la baie','/bienvenue-aux-nouveaux-dans-la-baie'),('Qui sommes-nous?','/qui-sommes-nous')]),
 ('Calendrier',[('Calendrier','/calendrier'),('Messes en français','/messe-en-français')]),
 ('Blog',[('Blog','/blog'),("L'Actu Aumônerie",'/about-5')]),
 ('Adultes',[('Préparation des messes','/organisation-des-messes'),('Veillées de prière','/veillées-de-prière'),('Jeunes Pros','/copy-of-communauté-de-l-emmanuel'),('Prière des mères','/prière-des-mères'),('MARCHES : des femmes, des hommes,','/marche-des-hommes-époux-et-pères'),('Equipes Notre-Dame (END)','/equipes-notre-dame-end'),("Communauté de l'Emmanuel",'/ecole-de-charité-et-de-mission-ecm')]),
 ('Jeunes',[("Partage d'évangile",'/general-1'),('Catéchisme','/catéchisme'),('Aumônerie','/aumônerie'),('Scouts en français','/scouts-en-français'),("Servants de messe et d'assemblée",'/servants-de-messe-et-d-assemblée')]),
 ('Sacrements',[('Baptême','/baptême-1'),('Première communion','/première-communion-1'),('Confirmation','/confirmation-1'),('Mariage','/mariage-1'),('Confession et réconciliation','/confession-et-réconciliation-1'),('Sacrement des malades','/sacrement-des-malades')]),
 ('Contacts',[('Prêtres francophones','/prêtres-francophones'),('Peninsula : St Nicholas & St William','/peninsula-st-nicholas-st-wiliam'),('San Francisco : Notre Dame des Victoires','/copy-of-east-bay-st-jarlath'),('East Bay, Oakland : St Jarlath','/east-bay-st-jarlath'),('East Bay, Pittsburg','/general-1-1')]),
]

def header(current):
    nav=[]
    for name,children in GROUPS:
        active=any(ROUTES[path]==current for _,path in children)
        childhtml=''.join(f'<a href="{relative(ROUTES[path],current)}"'+(' aria-current="page"' if ROUTES[path]==current else '')+'>'+escape(label)+'</a>' for label,path in children)
        nav.append(f'<details class="nav-group'+(' current-group' if active else '')+'"><summary>'+escape(name)+'</summary><div class="nav-submenu">'+childhtml+'</div></details>')
    nav.append(f'<a class="button small" href="{relative("donner.html",current)}">Donner à CathoSV</a>')
    return f'''<a class="skip-link" href="#contenu">Aller au contenu</a>
<div class="preview-bar"><span>CathoSV · Maquette</span><a href="https://www.cathosv.org/" target="_blank" rel="noopener noreferrer">Ancien site</a></div>
<header class="header"><a class="brand" href="{relative('index.html',current)}" aria-label="CathoSV, accueil"><svg viewBox="0 0 40 48" aria-hidden="true"><path d="M20 3v40M7 17h26M10 38l10-7"/></svg><span>Catho<span class="brand-sv">SV</span><small>CATHOLIQUES FRANCOPHONES</small></span></a><button class="menu-toggle" aria-expanded="false" aria-controls="navigation" hidden>Menu <span aria-hidden="true">☰</span></button><nav id="navigation" aria-label="Navigation principale">{''.join(nav)}</nav></header>'''

def footer(page,current):
    return '<footer id="contact" class="wrap source-footer"><div class="original-footer">'+render_blocks(page,current,footer=True)+'</div></footer>'

def shell(current,title,body,page,description=''):
    extra_style=('<link rel="stylesheet" href="front.css?v='+sha256((ROOT/'front.css').read_bytes()).hexdigest()[:12]+'">') if current=='index.html' else ''
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#173f35"><meta name="robots" content="noindex, nofollow"><meta name="description" content="{escape(description or title,quote=True)}"><title>{escape(title)} · CathoSV</title><link rel="icon" href="{relative('assets/favicon.svg',current)}" type="image/svg+xml"><link rel="stylesheet" href="{relative('style.css',current)}?v={CSS}">{extra_style}<script src="{relative('script.js',current)}?v={JS}" defer></script></head><body>{header(current)}<main id="contenu">{body}</main>{footer(page,current)}</body></html>'''

def intro(page,current):
    title=escape(page['title']);meta=''
    if page['kind']=='post':
        parts=[page.get('author'),page.get('date')]
        meta='<p class="original-post-meta">'+' · '.join(escape(part) for part in parts if part)+'</p>'
    return '<div class="page-intro"><div class="wrap"><a class="breadcrumb" href="'+relative('index.html',current)+'">Accueil</a><h1>'+title+'</h1>'+meta+'</div></div>'

def post_list(current):
    posts=[p for p in PAGES if p['kind']=='post']
    # Original titles and author names are used without generated descriptions.
    return '<div class="original-post-list">'+''.join('<article><h2><a href="'+relative(p['local_path'],current)+'">'+escape(p['title'])+'</a></h2><p>'+escape(p.get('author') or '')+'</p></article>' for p in posts)+'</div>'

def front_page(page,current):
    """Arrange the complete original homepage into readable, expandable sections."""
    assert len(page['blocks'])==156, 'Review homepage layout against the updated source snapshot.'
    used=Counter()
    def take(indices):
        indices=list(indices);used.update(indices)
        return render_blocks(page,current,indices)
    def soup_html(html):
        soup=BeautifulSoup(html,'lxml')
        return soup
    def body_html(soup):return ''.join(str(child) for child in soup.body.contents)
    def linked_heading(index,href,button=False):
        soup=soup_html(take([index]))
        heading=soup.find(re.compile('^h[1-6]$'))
        assert heading is not None,(index,'Expected an original heading')
        for existing in list(heading.find_all('a')):existing.unwrap()
        a=soup.new_tag('a',href=href)
        if button:a['class']='button'
        for child in list(heading.contents):a.append(child.extract())
        heading.append(a)
        return body_html(soup)

    # Original welcome wording; only the typography and semantic heading change.
    welcome=soup_html(take([2]))
    paragraphs=welcome.select('.source-text p')
    assert len(paragraphs)==2
    paragraphs[0]['class']='front-eyebrow'
    paragraphs[1].name='h1'
    welcome_html=body_html(welcome)
    jump=linked_heading(3,'#evenements',button=True)
    portrait=take([1])
    hero='<section class="front-hero"><div class="wrap front-hero-grid"><div class="front-welcome">'+welcome_html+'<div class="front-hero-jump">'+jump+'</div></div><div class="front-hero-visual">'+portrait+'</div></div></section>'

    # Preserve each city's full original sentence, with a useful local destination.
    mass_title=take([4])
    masses=soup_html(take([5]))
    container=masses.select_one('.source-text > div')
    assert container is not None
    container['class']='front-mass-grid'
    destinations=[('Los Altos','messes.html'),('San Francisco',ROUTES['/copy-of-east-bay-st-jarlath']),('Pittsburg',ROUTES['/general-1-1']),('Oakland',ROUTES['/east-bay-st-jarlath'])]
    cities=[]
    for paragraph in container.find_all('p',recursive=False):
        text=norm(paragraph.get_text())
        if not text.strip('\u200b\ufeff '):continue
        name,target=next((name,target) for name,target in destinations if text.startswith(name))
        original_text=paragraph.get_text('',strip=False)
        label=re.match(r'(\s*'+re.escape(name)+r'\s*:?[ \u00a0]*)',original_text)
        assert label is not None
        paragraph.clear()
        anchor=masses.new_tag('a',href=relative(target,current))
        strong=masses.new_tag('strong');strong.string=label[1]
        anchor.append(strong);anchor.append(original_text[label.end():])
        paragraph.append(anchor);paragraph['class']='front-mass-city';cities.append(name)
    assert len(cities)==4
    mass='<section class="front-masses"><div class="wrap">'+mass_title+body_html(masses)+'</div></section>'

    # Source teasers are paired with their complete original announcements.
    teasers=[
        (16,17,37,41),(18,19,54,58),(20,21,62,66),(22,23,45,49),
        (24,25,58,62),(26,27,83,86),(28,29,49,54),(30,31,41,45),
        (32,33,79,83),(34,35,66,70),
    ]
    def summary_content(indices):
        soup=soup_html(take(indices))
        # The whole native summary opens the announcement; avoid nested links.
        for br in list(soup.find_all('br')):br.decompose()
        for a in list(soup.find_all('a')):
            if a.get('data-source-image'):
                image=a.find('img');image['data-source-image']=a['data-source-image']
            a.unwrap()
        return body_html(soup)
    cards=[]
    for image,title,start,end in teasers:
        summary=summary_content([image,title])
        story=take(range(start,end))
        cards.append(f'<details class="front-event-card" id="front-story-{start}"><summary><div class="front-card-summary">'+summary+'</div></summary><div class="front-story-content">'+story+'</div></details>')

    other_ranges=[(72,76),(76,79),(86,89),(89,93),(93,102),(102,125),(125,130),(130,134),(134,138)]
    more=[]
    for start,end in other_ranges:
        summary=summary_content([start]);story=take(range(start+1,end))
        more.append(f'<details class="front-story-row" id="front-story-{start}"><summary>'+summary+'</summary><div class="front-story-content">'+story+'</div></details>')

    # Original newsletter, support, social and Monday information become an aside.
    newsletter=linked_heading(9,'newsletter.html')+take([13])
    support=soup_html(take([10,11,12]))
    for a in support.select('[data-source-block="12"] a'):a['class']='button'
    social=take([6,7,8])
    mondays=take([70,71])
    sidebar='<aside class="front-sidebar"><section class="front-sidebar-card front-newsletter">'+newsletter+'</section><section class="front-sidebar-card front-support">'+body_html(support)+'</section><section class="front-sidebar-card front-social">'+social+'</section><section class="front-sidebar-note">'+mondays+'</section></aside>'

    event_heading=take([14]);event_instruction=take([15]);agenda_link=linked_heading(36,'agenda.html',button=True)
    events='<div class="wrap front-content-grid"><section class="front-events"><div class="front-events-heading"><div>'+event_heading+event_instruction+'</div><div class="front-agenda-link">'+agenda_link+'</div></div><div class="front-event-grid">'+''.join(cards)+'</div></section>'+sidebar+'</div><section class="wrap front-more-section"><details class="front-more"><summary>Autres annonces <span>'+str(len(more))+'</span></summary><div class="front-story-list">'+''.join(more)+'</div></details></section>'

    # Preserve all original Blog highlights without showing Wix's duplicate slides.
    blog_heading=take([138]);blog_cards=[]
    for indices,title_index in [([139,140,141],141),([142,143,144],144),([145,146,147,148],148)]:
        soup=soup_html(take(indices))
        matches=[p for p in PAGES if p['kind']=='post' and norm(p['title'])==norm(page['blocks'][title_index]['text'])]
        assert len(matches)==1,('Blog highlight target',title_index)
        href=relative(matches[0]['local_path'],current)
        seen=set()
        for tile in list(soup.select('[data-source-image]')):
            identity=(tile['data-source-image'],tile.get('href'))
            if identity in seen:tile.decompose();continue
            seen.add(identity)
            tile['href']=href;tile.attrs.pop('data-photo',None)
        heading=soup.select_one(f'[data-source-block="{title_index}"]')
        if not heading.find('a'):
            tag=heading.find(re.compile('^h[1-6]$'))
            a=soup.new_tag('a',href=href)
            for child in list(tag.contents):a.append(child.extract())
            tag.append(a)
        blog_cards.append('<article class="front-blog-card">'+body_html(soup)+'</article>')
    blog='<section class="front-blog"><div class="wrap">'+blog_heading+'<div class="front-blog-grid">'+''.join(blog_cards)+'</div></div></section>'

    # Retain the original calendar block without exposing its setup panel by default.
    calendar='<section class="wrap front-calendar"><details class="front-story-row"><summary>'+summary_content([149])+'</summary><div class="front-story-content">'+take(range(150,156))+'</div></details></section>'
    used.update([0]);bridge=page['blocks'][0];asset=ASSETS[bridge['key']]
    scenery='<div class="wrap front-scenery"><figure data-source-image="'+escape(bridge['key'],quote=True)+'"><img src="'+asset['display']+'" width="'+str(asset['width'])+'" height="'+str(asset['height'])+'" alt="'+escape(bridge.get('alt',''),quote=True)+'" loading="lazy"><figcaption>'+escape(bridge.get('alt',''))+'</figcaption></figure></div>'
    assert used==Counter(range(len(page['blocks']))),('Homepage blocks omitted or duplicated',used-Counter(range(len(page['blocks']))),Counter(range(len(page['blocks'])))-used)
    return '<div class="front-page">'+hero+mass+events+blog+calendar+scenery+'</div>'

for page in PAGES:
    current=page['local_path'];outpath=ROOT/current;outpath.parent.mkdir(exist_ok=True)
    if current=='index.html':
        body=front_page(page,current)
    else:
        body=intro(page,current)+'<div class="wrap original-content'+(' original-post' if page['kind']=='post' else '')+'">'+render_blocks(page,current)+'</div>'
        if current=='blog.html':body+='<section class="wrap section"><h2>Blog</h2>'+post_list(current)+'</section>'
    outpath.write_text(shell(current,page['title'],body,page))

# Keep existing mockup entry URLs functional, without retaining invented prose.
home=BY_PATH['index.html']
for filename,group in [('adultes.html','Adultes'),('jeunes.html','Jeunes')]:
    children=next(children for name,children in GROUPS if name==group)
    entries=[]
    aliases={'Catéchisme':'catechisme','Scouts en français':'scouts','Prière des mères':'priere','MARCHES : des femmes, des hommes,':'marches'}
    for label,path in children:
        id_=aliases.get(label,'')
        entries.append('<li'+(' id="'+id_+'"' if id_ else '')+'><a href="'+relative(ROUTES[path],filename)+'">'+escape(label)+'</a></li>')
    body='<div class="page-intro"><div class="wrap"><h1>'+group+'</h1></div></div><div class="wrap section"><ul class="section-directory">'+''.join(entries)+'</ul></div>'
    (ROOT/filename).write_text(shell(filename,group,body,home))

welcome=BY_PATH['bienvenue.html']
newsletter_indices=[i for i,b in enumerate(welcome['blocks']) if b['kind']=='text' and 'newsletter' in b['text'].lower()]
body='<div class="page-intro"><div class="wrap"><h1>Recevoir la Newsletter CathoSV</h1></div></div><div class="wrap original-content">'+render_blocks(welcome,'newsletter.html',newsletter_indices)+'<a class="button" href="mailto:info@cathosv.org?subject=Newsletter%20CathoSV">info@cathosv.org</a></div>'
(ROOT/'newsletter.html').write_text(shell('newsletter.html','Recevoir la Newsletter CathoSV',body,home))

# A directory makes every public source page discoverable, without adding menu sections.
body='<div class="page-intro"><div class="wrap"><h1>Toutes les pages</h1></div></div><div class="wrap section"><ul class="section-directory">'
for p in PAGES:
    if p['kind']=='page':body+='<li><a href="'+p['local_path']+'">'+escape(p['title'])+'</a></li>'
body+='</ul><h2>Blog</h2>'+post_list('pages.html')+'</div>'
(ROOT/'pages.html').write_text(shell('pages.html','Toutes les pages',body,home))

# The image audit remains available by direct URL, outside the original public menu.
photos=ROOT/'photos.html'
if photos.exists():
    soup=BeautifulSoup(photos.read_text(),'lxml')
    main=soup.find('main')
    body=str(main).removeprefix('<main id="contenu">').removesuffix('</main>')
    photos.write_text(shell('photos.html','Photos CathoSV',body,home))

# Retarget unknown obsolete Wix section fragments to the local destination page.
# Link destinations are presentation behavior; the visible source words stay intact.
allhtml=list(ROOT.glob('*.html'))+list((ROOT/'pages').glob('*.html'))+list((ROOT/'blog').glob('*.html'))
ids={p:set(re.findall(r'\bid="([^"]+)"',p.read_text())) for p in allhtml}
repaired=[]
for p in allhtml:
    s=p.read_text()
    def fix(match):
        href=match[1];u=urlsplit(href)
        if u.scheme or u.netloc or not u.fragment:return match[0]
        target=(p.parent/unquote(u.path)).resolve() if u.path else p.resolve()
        if target in ids and unquote(u.fragment) not in ids[target]:
            repaired.append({'page':str(p.relative_to(ROOT)),'href':href})
            return 'href="'+escape(u.path or '#contenu',quote=True)+'"'
        return match[0]
    updated=re.sub(r'href="([^"]+)"',fix,s)
    p.write_text('\n'.join(line.rstrip(' \t') for line in updated.splitlines())+'\n')

report={'source_pages':len(PAGES),'source_posts':sum(p['kind']=='post' for p in PAGES),'original_body_text_blocks':sum(b['kind']=='text' for p in PAGES for b in p['blocks']),'checks':AUDIT,'obsolete_link_fragments_retargeted':repaired,'failures':[]}
(ROOT/'migration/text-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(f'Rendered {len(PAGES)} original pages ({report["source_posts"]} blog posts); {report["original_body_text_blocks"]} body text blocks and all rendered footer copies checked without rewriting.')
