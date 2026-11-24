#!/usr/bin/env python3
"""Independently check rendered original wording using only Python's standard library."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
import json,re

ROOT=Path(__file__).resolve().parents[1]
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

def norm(text):return re.sub(r'\s+',' ',text).strip()

class Page(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True)
        self.stack=[];self.captures=[];self.blocks={};self.refs=[];self.ids=set();self.images=[];self.nav_labels=[];self.nav_link=None
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids,('Duplicate HTML id',attrs['id'])
            self.ids.add(attrs['id'])
        if tag in {'a','img','script','link','video'}:
            ref=attrs.get('href') or attrs.get('src')
            if ref:self.refs.append(ref)
        if attrs.get('data-source-image'):self.images.append(attrs['data-source-image'])
        if tag not in VOID:self.stack.append(tag)
        if tag=='a' and 'nav' in self.stack:self.nav_link={'depth':len(self.stack),'text':[]}
        if 'data-source-page' in attrs:
            self.captures.append({'key':(attrs['data-source-page'],attrs['data-source-block']),'depth':len(self.stack),'text':[]})
    def handle_data(self,text):
        if self.nav_link is not None:self.nav_link['text'].append(text)
        for capture in self.captures:capture['text'].append(text)
    def handle_endtag(self,tag):
        if tag not in self.stack:return
        depth=len(self.stack)-list(reversed(self.stack)).index(tag)
        if self.nav_link is not None and self.nav_link['depth']>=depth:
            self.nav_labels.append(norm(''.join(self.nav_link['text'])))
            self.nav_link=None
        completed=[capture for capture in self.captures if capture['depth']>=depth]
        for capture in completed:
            self.blocks.setdefault(capture['key'],[]).append(''.join(capture['text']))
            self.captures.remove(capture)
        del self.stack[depth-1:]

source=json.loads((ROOT/'migration/original-content.json').read_text())
documents={path:Page(path.read_text()) for path in ROOT.rglob('*.html')}
body_count=footer_count=0
expected_menu=[norm(item['label']) for item in next(p for p in source['pages'] if p['local_path']=='index.html')['navigation']]
for path,document in documents.items():assert document.nav_labels==expected_menu,(path,'Original navigation changed')
for entry in source['pages']:
    document=documents[ROOT/entry['local_path']]
    for field,prefix in [('blocks',''),('footer','footer-')]:
        for i,block in enumerate(entry[field]):
            if block['kind']!='text':continue
            key=(entry['local_path'],prefix+str(i));copies=document.blocks.get(key,[])
            assert len(copies)==1,(entry['local_path'],key,'Missing or duplicated original text')
            assert norm(copies[0])==norm(block['text']),(entry['local_path'],key,'Original wording changed')
            if field=='blocks':body_count+=1
            else:footer_count+=1
    for block in entry['blocks']:
        if block['kind']=='image':assert block['key'] in document.images,(entry['local_path'],'Missing image',block['key'])
for path,document in documents.items():
    for ref in document.refs:
        url=urlsplit(ref)
        if url.scheme or url.netloc:continue
        target=(path.parent/unquote(url.path)).resolve() if url.path else path
        assert target.exists(),(str(path.relative_to(ROOT)),ref,'Missing local destination')
        if url.fragment and target in documents:assert unquote(url.fragment) in documents[target].ids,(str(path.relative_to(ROOT)),ref,'Missing local anchor')
assert len(source['pages'])==138
assert sum(page['kind']=='post' for page in source['pages'])==104
print(f'PASS: {body_count} original body text blocks, {footer_count} original footer text blocks, 138 public source pages / 104 posts, and all local links/assets/anchors.')
