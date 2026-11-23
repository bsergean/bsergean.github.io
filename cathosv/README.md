# CathoSV redesign preview

Live preview: https://bsergean.github.io/cathosv/

This is a responsive design prototype, published as an isolated folder in the existing personal GitHub Pages repository. It leaves the personal homepage and the official CathoSV website untouched.

## What is implemented

- French homepage with Mass times, directions, agenda, welcome information, and activities.
- Responsive desktop and phone layouts, mobile navigation, accessible native disclosure controls, keyboard focus states, and reduced-motion support.
- Agenda category filtering and automatic hiding of past entries, using the America/Los_Angeles calendar date. Without JavaScript all sample announcements remain visible.
- Real links to the official site, email, maps, and Instagram. Newsletter and event registrations use the current site; no subscriber information is collected here.
- Local optimized images and system fonts; no runtime CDN, third-party JavaScript, cookies, database, or build dependency.

## Preview locally

From this repository checkout:

```sh
python3 -m http.server 8765
```

Open http://localhost:8765/cathosv/ . To check from an iPhone on the same Wi-Fi, use the computer's LAN IP instead of localhost and allow the server through the local firewall if needed.

The deployed HTTPS address is the easiest iPhone preview and works outside the local network.

## Publishing

The repository currently uses GitHub Pages' built-in branch deployment from `master`, repository root (verified November 23, 2026), rather than a custom Actions workflow. Commit changes under `cathosv/` and push to that branch; GitHub's Pages build publishes the folder. No additional hosting provider or build configuration is needed for this prototype.

Before publishing another change, verify current Pages settings and remote branch state. Avoid replacing the repository's root index.html or publishing configuration.

## Recommended production setup

The deciding factor is who will maintain the site after handoff.

- **If there is an occasional technical maintainer:** Astro static output + Pages CMS + GitHub Pages. Keep Mass schedules, activities, and announcements as structured content, with required fields and end dates. Pages CMS provides an editing interface; volunteers should not have to edit HTML, CSS, Git, or Actions. Configure automatic publishing on content changes and a daily build if expired announcements are removed at build time. Preserve content and photos in Git for recovery and portability.
- **If nobody will own the technical setup:** redesign within the existing Wix site. This avoids a migration and gives volunteers an existing visual editing workflow. A custom framework still needs somebody to manage access, upgrades, and occasional build problems.

For this kind of information site, a server application or custom database would add ongoing work without a clear benefit. Astro is a good production framework for reusable page templates and structured content; it is intentionally not required just to run this design prototype.

Official references:

- https://docs.astro.build/en/guides/content-collections/
- https://docs.astro.build/en/guides/deploy/github/
- https://pagescms.org/docs/

### Volunteer workflow to implement next

1. Sign into the configured CMS using an authorized account.
2. Edit a labeled form: title, summary, date, location, image, registration link.
3. Preview and publish; deployment runs automatically.
4. Hand the role to another volunteer by updating repository/CMS access.

CMS installation, permissions, content schemas, full page migration, redirects, and a volunteer usability check are **not implemented in this prototype**. Do those before moving the official domain. Keep newsletter signups and donations with their current providers unless the organization requests a separate migration.

## Content and images

The prototype uses a selection of public information from https://www.cathosv.org/, reviewed November 23, 2026. It is not a complete migration or an authoritative schedule. Footer and preview banner label it as a mockup; search indexing is discouraged by a robots meta tag.

Sources:

- Home and announcements: https://www.cathosv.org/
- Mass times: https://www.cathosv.org/messe-en-fran%C3%A7ais
- Newcomers: https://www.cathosv.org/bienvenue-aux-nouveaux-dans-la-baie
- Donations: https://www.cathosv.org/donner-pour-cathosv-1

The source homepage and Mass page disagree on Pittsburg's start time (16:30 vs 16:40); no exact Pittsburg time is shown here. The homepage also lists conflicting December 5 diocesan venues; the preview directs readers to confirm the program rather than choosing one.

`assets/bay.jpg`: Golden Gate Bridge photograph used on the current homepage, credited there to Antonio Gabola. Original source: `https://static.wixstatic.com/media/nsplsh_456f767845447a4e4e4e41~mv2_d_3000_2000_s_2.jpg`.

`assets/community.jpg`: CathoSV community photograph used on the current homepage. Original source: `https://static.wixstatic.com/media/f0c182_1b883215458d490391cb6c66511875ed~mv2.jpeg`.

Images are reused for this CathoSV design proposal; no ownership or broader reuse license is asserted. Confirm publishing permissions with the organization for the final official website.
