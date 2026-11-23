#!/usr/bin/env python3
"""Inventory public CathoSV sitemap images and copy their original files locally.

Run with Python 3.10+: python3 cathosv/scripts/migrate-images.py
Downloads are cached. A manifest records every source page and image URL.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets' / 'migrated'
REPORT = ROOT / 'migration' / 'image-manifest.json'
NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
PATTERN = re.compile(r'(?:https://static\.wixstatic\.com/media/|wix:image://v1/)([\w.%~+-]+\.(?:jpe?g|png|gif|webp|avif|svg|ico))', re.I)

def fetch(url):
    url=quote(url,safe=':/?=&%~+@,')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CathoSV-design-migration/1.0'}),timeout=35) as response:
                return response.read()
        except Exception:
            if attempt==2: raise
            time.sleep(attempt+1)

class Page(HTMLParser):
    def __init__(self,html):
        super().__init__();self.images=[];self.title='';self.in_title=False;self.feed(html)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='title':self.in_title=True
        if tag=='img':
            src=attrs.get('src','')
            match=PATTERN.search(src)
            if match:self.images.append({'key':match.group(1),'alt':attrs.get('alt',''),'width':attrs.get('width'),'height':attrs.get('height')})
    def handle_endtag(self,tag):
        if tag=='title':self.in_title=False
    def handle_data(self,text):
        if self.in_title:self.title+=text

def sitemap(url):
    tree=ET.fromstring(fetch(url))
    if tree.tag.endswith('sitemapindex'):
        urls=[]
        for el in tree.findall('s:sitemap/s:loc',NS):urls.extend(sitemap(el.text))
        return urls
    return [el.text for el in tree.findall('s:url/s:loc',NS)]

def inspect(url):
    html=fetch(url).decode('utf-8').replace('\\/','/')
    page=Page(html)
    keys=list(dict.fromkeys(PATTERN.findall(unescape(html)) + re.findall(r'[a-zA-Z0-9]+_[a-f0-9]{32}(?:~mv2)?\.(?:jpe?g|png|gif|webp|avif|svg|ico)', re.sub(r'https?://[^\s"<>]+', '', html), re.I)))
    return {'url':url,'title':page.title,'images':page.images,'assets':keys}

def download(key):
    path=ASSETS/unquote(key)
    if not path.exists():path.write_bytes(fetch('https://static.wixstatic.com/media/'+key))
    data=path.read_bytes()
    if not data:raise ValueError('Empty image '+key)
    return {'key':key,'source':'https://static.wixstatic.com/media/'+key,'path':str(path.relative_to(ROOT)),'bytes':len(data),'sha256':sha256(data).hexdigest()}

def main():
    ASSETS.mkdir(parents=True,exist_ok=True);REPORT.parent.mkdir(exist_ok=True)
    urls=list(dict.fromkeys(sitemap('https://www.cathosv.org/sitemap.xml')))
    pages=[];failures=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs={pool.submit(inspect,url):url for url in urls}
        for job in as_completed(jobs):
            try:pages.append(job.result())
            except Exception as exc:failures.append({'page':jobs[job],'error':str(exc)})
    pages.sort(key=lambda page:page['url'])
    keys=sorted(set(key for page in pages for key in page['assets']))
    print(f'Inventoried {len(pages)}/{len(urls)} public pages; {len(keys)} unique image assets; {len(failures)} page failures.',flush=True)
    assets=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs={pool.submit(download,key):key for key in keys}
        for index,job in enumerate(as_completed(jobs),1):
            try:assets.append(job.result())
            except Exception as exc:failures.append({'asset':jobs[job],'error':str(exc)})
            if index%50==0:print(f'Copied {index}/{len(keys)} images.',flush=True)
    assets.sort(key=lambda asset:asset['key'])
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'scope':'All image references in HTML and Wix image metadata of the public sitemap pages and blog posts. Private/unlisted content and non-image video files are excluded.','sitemap_pages':len(urls),'pages':pages,'assets':assets,'failures':failures}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'Finished: {len(assets)} images, {sum(a["bytes"] for a in assets)/1024/1024:.1f} MiB, {len(failures)} failures.',flush=True)
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
