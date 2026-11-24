#!/usr/bin/env python3
"""Build image previews only (requires Pillow). Never edits page text."""
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

print(f"Built previews for {len(assets)} original images. Page text is rendered by build-site.py.")
