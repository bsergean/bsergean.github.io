# CathoSV redesign and faithful content migration

Preview: https://bsergean.github.io/cathosv/

This is a static redesign hosted inside the existing personal GitHub Pages repository. The personal homepage and the official CathoSV domain remain separate.

## Content preservation

The initial mockup used summaries and new headings. Those summaries have been replaced with the original website's authored content.

- All 138 public sitemap URLs are represented: 34 site pages and 104 blog posts.
- `migration/original-content.json` stores the original editorial HTML, Unicode text, page titles, blog authors and dates, source URLs, and source-download hashes.
- The renderer checks all 942 original body text blocks before writing pages. It preserves spelling, punctuation, names, dates, typos, and paragraphs. It does not summarize, translate, correct, or regenerate prose.
- Layout, typography, line wrapping, whitespace, link destinations, and image presentation may differ. Wix-only attributes and empty formatting spacers are removed from presentation.
- Blog bodies have also been independently compared against their original raw HTML, allowing only whitespace and empty Wix formatting characters to differ.
- `migration/text-verification.json` records the content checks performed during rendering.
- The homepage again contains the complete original **Les événements CathoSV** section and announcements. Past announcements remain because they are part of the source content.

The Père Damien article is at `blog/bienvenue-pere-damien.html`. Its authored body consists of six images. They are displayed as readable document images and link to the untouched original files; no OCR or rewritten transcription is substituted.

Original footer wording and the original navigation labels/grouping are retained. **Blog** is in the main menu. **Photos** is not an original menu item and has been removed from that menu. The image audit archive remains available by direct URL at `photos.html`, outside normal site navigation.

`pages.html` is a direct-URL migration directory of public pages and blog articles; it does not add another section to the original menu or footer. Previous mockup entry URLs such as `adultes.html`, `jeunes.html`, and `newsletter.html` continue to work as directories or views of original source content.

## Images and media

All 323 image assets identified across the 138 public sitemap pages and their Wix image metadata were transferred. Original bytes live in `assets/migrated/`; `migration/image-manifest.json` records source-page references, original URLs, file sizes, and SHA-256 checksums. Smaller WebP previews live in `assets/previews/`.

The original Marches page's 23 content images are present alongside its full original text. Blog document images use a single readable column. Ordinary galleries open in a native dialog with previous/next controls and access to originals. Without JavaScript, image links still open the originals directly.

The video embedded in the original introduction to the Lenten course is also copied locally in `assets/videos/`. Existing external services such as payment, registration forms, social networks, and embeds retain their own destinations. Calendar/provider configuration is taken as found in the original site; it is not recreated as a new service.

Private/unlisted pages and account profile areas are outside the sitemap migration. Original image authorship/credits are unchanged; no broader ownership or reuse license is asserted.

## Layout and navigation

The desktop layout uses a wider canvas, readable text columns, and photo grids. The homepage Mass information is in a separate strip below the hero, using the original Mass text. Phone layouts stack vertically and expose the original menu groups through the Menu button.

An explicit **Ancien site** link is at the top of every page. Other internal content links resolve to their local equivalents. Old Wix fragments that do not correspond to portable content anchors are retargeted to the appropriate local page; this changes destinations, not visible wording.

## Local preview

From this repository checkout:

```sh
python3 -m http.server 8765
```

Open http://localhost:8765/cathosv/ . The deployed HTTPS address is the easiest preview on an iPhone.

There is no runtime application server, CMS database, JavaScript framework, or third-party font dependency.

## Maintainer build and migration tools

These tools are for a technical maintainer, not a proposed volunteer editing workflow. Use a Python environment with `beautifulsoup4`, `lxml`, and `Pillow` installed as needed.

```sh
# Capture original images and source metadata.
python3 cathosv/scripts/migrate-images.py
# Build image previews only; this never rewrites page text.
python3 cathosv/scripts/build-galleries.py
# Snapshot the original authored HTML and text.
python3 cathosv/scripts/import-original-content.py
# Render pages and verify wording against the snapshot.
python3 cathosv/scripts/build-site.py
# Independently verify final HTML with the standard-library checker.
python3 cathosv/scripts/verify-content.py
```

The importer caches raw HTML outside the published checkout when `CATHOSV_SOURCE_CACHE` is set. Use a new cache directory, or clear it, when intentionally refreshing the snapshot from the original site. Review a refreshed snapshot against the previous one before publishing: it is the source of truth, not AI-generated copy. `build-site.py` changes presentation only and stops if sanitizing a block changes its text.

Static HTML is committed under `cathosv/`. GitHub Pages currently builds from `master`, repository root, using its configured Pages workflow. Publishing does not replace root `index.html` or the personal site's other pages. CSS and script URLs use content hashes to avoid stale browser assets.

## Production handoff

The volunteer-facing visual editor, access management, redirects for a domain migration, and operational handoff are still separate work. A production Astro + Pages CMS setup remains an option when there is an occasional technical maintainer. If nobody will maintain that setup, redesigning within Wix remains the simpler handoff. Neither option justifies changing the authors' wording during migration.
