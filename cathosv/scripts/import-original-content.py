#!/usr/bin/env python3
"""Capture original editorial HTML without rewriting any text.

Requires beautifulsoup4 and lxml. Raw source downloads are cached outside the
published repository when CATHOSV_SOURCE_CACHE is set.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from bs4 import BeautifulSoup, Tag, NavigableString
import json, os, re, time, urllib.request, unicodedata

ROOT=Path(__file__).resolve().parents[1]
CACHE=Path(os.environ.get('CATHOSV_SOURCE_CACHE',str(ROOT.parent.parent/'qa/source-html')))
CACHE.mkdir(parents=True,exist_ok=True)
images=json.loads((ROOT/'migration/image-manifest.json').read_text())
PATTERN=re.compile(r'https://static\.wixstatic\.com/media/([^/]+)')

def norm(s):return re.sub(r'\s+',' ',s).strip()
def slug(s):
    s=unicodedata.normalize('NFKD',unquote(s)).encode('ascii','ignore').decode().lower()
    return re.sub('[^a-z0-9]+','-',s).strip('-')
def canonical(url):
    p=urlsplit(url);return unquote(p.path).rstrip('/') or '/'
DIRECT={'/':'index.html','/marche-des-hommes-époux-et-pères':'marches.html','/messe-en-français':'messes.html','/bienvenue-aux-nouveaux-dans-la-baie':'bienvenue.html','/donner-pour-cathosv-1':'donner.html','/calendrier':'agenda.html','/blog':'blog.html'}
def local(url):
    path=canonical(url)
    if path in DIRECT:return DIRECT[path]
    if path.startswith('/post/'):return 'blog/'+slug(path[6:])+'.html'
    return 'pages/'+slug(path)+'.html'

def fetch(url):
    path=CACHE/(sha256(url.encode()).hexdigest()+'.html')
    if not path.exists():
        for attempt in range(3):
            try:
                data=urllib.request.urlopen(quote(url,safe=':/?=&%~+@,'),timeout=30).read();path.write_bytes(data);break
            except Exception:
                if attempt==2:raise
                time.sleep(attempt+1)
    return path.read_bytes()

def extract(scope,blog=False):
    blocks=[]
    def add(kind,node,**more):
        ancestors=[]
        for parent in [node]+list(node.parents):
            if parent is scope:break
            if isinstance(parent,Tag) and parent.get('id'):ancestors.append(parent['id'])
        record={'kind':kind,'source_id':node.get('id','') if isinstance(node,Tag) else '', 'anchors':list(reversed(ancestors)),**more}
        if kind=='text':
            record.update(html=str(node),text=node.get_text('',strip=False))
            record['sha256']=sha256(norm(record['text']).encode()).hexdigest()
            if not record['text'].strip('\u200b\ufeff \n\t\r'):return
        blocks.append(record)
    def walk(node):
        if not isinstance(node,Tag):
            if blog and isinstance(node,NavigableString) and node.strip():
                tag=BeautifulSoup('<p></p>','lxml').p;tag.append(str(node));add('text',tag)
            return
        if node.name in ['script','style','svg','noscript']:return
        classes=node.get('class',[])
        if 'wixui-rich-text' in classes or node.get('data-testid')=='richTextElement':add('text',node);return
        if blog and node.name in ['h1','h2','h3','h4','h5','h6','p','ul','ol','blockquote','table','figcaption']:
            add('text',node);return
        if node.name=='img':
            match=PATTERN.search(node.get('src',''))
            if match:
                parent_link=node.find_parent('a',href=True)
                add('image',node,key=match[1],alt=node.get('alt',''),href=parent_link.get('href') if parent_link else None,target=parent_link.get('target') if parent_link else None)
            return
        if node.name=='video':
            add('video',node,src=node.get('src',''),poster=node.get('poster',''));return
        if node.name=='iframe':
            add('embed',node,src=node.get('src',''),title=node.get('title',''));return
        if node.name=='a' and node.get_text(strip=True) and not node.select('.wixui-rich-text'):
            add('text',node);return
        for child in node.children:walk(child)
    for child in scope.children:walk(child)
    return blocks

def inspect(page):
    raw=fetch(page['url']);soup=BeautifulSoup(raw,'lxml');main=soup.find('main')
    if main is None:raise ValueError('No main content: '+page['url'])
    isblog=canonical(page['url']).startswith('/post/')
    if isblog:
        content=main.select_one('[data-hook="post-description"]')
        title=main.select_one('h1[data-hook="post-title"]')
        author=main.select_one('[data-hook="user-name"]')
        date=main.select_one('[data-hook="time-ago"]')
        if content is None:raise ValueError('No post description: '+page['url'])
        blocks=extract(content,blog=True)
        post_title=title.get_text('',strip=False) if title else soup.title.get_text().split('|')[0].strip()
    else:
        blocks=extract(main)
        post_title=soup.title.get_text().split('|')[0].strip() if soup.title else page['title']
        author=date=None
    footer=soup.find('footer',id='SITE_FOOTER')
    header=soup.find('header',id='SITE_HEADER') or soup.find('header')
    nav=[]
    if header:
        nav=[{'label':a.get_text(' ',strip=True),'url':a.get('href')} for a in header.find_all('a') if a.get('href') and a.get_text(strip=True)]
    return {'url':page['url'],'local_path':local(page['url']),'title':post_title,'kind':'post' if isblog else 'page','source_html_sha256':sha256(raw).hexdigest(),'author':author.get_text('',strip=False) if author else None,'date':date.get_text('',strip=False) if date else None,'blocks':blocks,'footer':extract(footer) if footer else [],'navigation':nav}

def main():
    pages=[];failures=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs={pool.submit(inspect,page):page for page in images['pages']}
        for job in as_completed(jobs):
            try:pages.append(job.result())
            except Exception as exc:failures.append({'url':jobs[job]['url'],'error':str(exc)})
    pages.sort(key=lambda p:p['url'])
    result={'imported_at':datetime.now(timezone.utc).isoformat(),'policy':'Preserve original editorial HTML and Unicode text. Layout, whitespace, link destinations, and image presentation may change; authored words, punctuation, dates, names, and mistakes may not.','pages':pages,'failures':failures}
    (ROOT/'migration/original-content.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Imported',len(pages),'pages:',sum(p['kind']=='post' for p in pages),'posts;',sum(b['kind']=='text' for p in pages for b in p['blocks']),'original text blocks;',len(failures),'failures.',flush=True)
    if failures:print(failures);raise SystemExit(1)
if __name__=='__main__':main()
