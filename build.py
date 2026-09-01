#!/usr/bin/env python3
"""Build the static Blue Diamond mirror from raw fetched HTML.

Phase 1: copy rendered HTML into the clone folder, rewrite internal page
navigation to local .html files, keep all asset (css/js/img/font) URLs
pointing at the live CDN so the pages render identically.
"""
import re, glob, os

SRC = "site-raw"
OUT = "bluediamondmed-clone"
BASE = "https://bluediamondmed.com"

# slug (no slashes) -> local file
PAGES = {
    "": "index.html",
    "about-us": "about-us.html",
    "services": "services.html",
    "healthcare-staffing-services-page": "healthcare-staffing-services-page.html",
    "school-staffing": "school-staffing.html",
    "healthcare-professionals": "healthcare-professionals.html",
    "teachers-substitute-educators": "teachers-substitute-educators.html",
    "cpr-emergency-training-certification": "cpr-emergency-training-certification.html",
    "teach-in-the-u-s-a-with-blue-diamond-school-staffing": "teach-in-the-u-s-a-with-blue-diamond-school-staffing.html",
    "healthcare-staffing": "healthcare-staffing.html",
    "teaching-jobs": "teaching-jobs.html",
    "contact-us": "contact-us.html",
}

os.makedirs(OUT, exist_ok=True)

IMG_EXT = "png|jpe?g|gif|svg|webp|avif|ico"
IMG_RE = re.compile(
    r'https://bluediamondmed\.com/([^"\'\s,)]+?\.(?:' + IMG_EXT + r'))(\?[^"\'\s,)]*)?')
SIZE_SUFFIX = re.compile(r'-\d+x\d+(?=\.\w+$)')  # e.g. Testi1-300x300.jpg -> Testi1.jpg
IMGDIR = "img"  # local folder holding the actual image files
IMAGES = set()  # base filenames referenced across the pages


def localize_images(html):
    """Point every <img>/srcset/favicon image at the local img/ folder. WordPress
    generates size variants (name-300x300.jpg) from one upload; we only have the
    base files, so collapse every variant to its base filename."""
    def repl(m):
        fn = os.path.basename(m.group(1))
        base = SIZE_SUFFIX.sub('', fn)
        # Favicon uses cropped-* variants we don't have; fall back to the logo.
        if base.startswith('cropped-') and 'BLUE-DIAMOND-MEDICAL-STAFFING' in base:
            base = 'BLUE-DIAMOND-MEDICAL-STAFFING.png'
        IMAGES.add(base)
        return f'{IMGDIR}/{base}'
    return IMG_RE.sub(repl, html)


def fix_lazy_backgrounds(html):
    """Elementor lazy-loads section background images: an injected <style> sets
    `background-image:none !important` on parent containers until its JS adds the
    `e-lazyloaded` class on scroll. In a static snapshot that suppresses most
    section backgrounds. Remove the gating <style> and mark every container as
    loaded so all backgrounds render immediately."""
    # Drop the injected style block that suppresses lazy backgrounds.
    html = re.sub(
        r'<style>[^<]*background-image:\s*none\s*!important[^<]*</style>',
        '', html, flags=re.DOTALL)
    # Ensure every Elementor container (.e-con) also carries .e-lazyloaded.
    def add_class(m):
        cls = m.group(1)
        if 'e-con' in cls and 'e-lazyloaded' not in cls:
            cls = cls + ' e-lazyloaded'
        return f'class="{cls}"'
    html = re.sub(r'class="([^"]*\be-con\b[^"]*)"', add_class, html)
    # Elementor hides entrance-animated elements with `elementor-invisible`
    # (opacity:0) until its JS runs. In a static mirror that can leave images
    # and content blank, so strip the class to show everything immediately.
    html = re.sub(r'\s*\belementor-invisible\b', '', html)
    return html


def rewrite_nav(html):
    # href="https://bluediamondmed.com/slug/" or without trailing slash -> local file
    def repl(m):
        quote = m.group(1)
        slug = m.group(2).strip("/")
        if slug in PAGES:
            return f'href={quote}{PAGES[slug]}{quote}'
        return m.group(0)  # leave other internal links absolute

    # match href="https://bluediamondmed.com/....." (page-like, no file extension, no query)
    pattern = r'href=(["\'])' + re.escape(BASE) + r'/([a-z0-9\-/]*)/?\1'
    html = re.sub(pattern, repl, html)
    return html


import json
BG_MAP = json.load(open(f"{SRC}/bg-map.json")) if os.path.exists(f"{SRC}/bg-map.json") else {}


def add_section_backgrounds(html, name):
    """Inject an inline <style> that sets each Elementor section's background to
    the matching local img/ file. url() in an inline <style> resolves relative to
    the page, so img/<file> works the same as the inline <img> tags."""
    rules = BG_MAP.get(name)
    if not rules:
        return html
    css = "".join(
        f'.elementor-element-{eid}{{background-image:url({IMGDIR}/{img})!important;'
        f'background-position:center center;background-size:cover}}'
        for eid, img in rules.items())
    style = f'<style id="local-section-bg">{css}</style>'
    return html.replace('</head>', style + '</head>', 1)


def main():
    count = 0
    for f in sorted(glob.glob(f"{SRC}/*.html")):
        name = os.path.basename(f)
        # index.html is built separately from the browser-saved, fully-local
        # home page (see localize_home.py); don't overwrite it here.
        if name == "index.html":
            continue
        html = open(f, encoding="utf-8", errors="replace").read()
        html = fix_lazy_backgrounds(html)
        html = localize_images(html)
        html = rewrite_nav(html)
        html = add_section_backgrounds(html, name)
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(html)
        count += 1
        print("built", name)

    # Report which referenced <img> files are present in the local img/ folder.
    have = set(os.listdir(os.path.join(OUT, IMGDIR))) if os.path.isdir(
        os.path.join(OUT, IMGDIR)) else set()
    missing = sorted(b for b in IMAGES if b not in have)
    print(f"\n{count} pages written to {OUT}/")
    print(f"{len(IMAGES)} distinct <img> files referenced; "
          f"{len(IMAGES) - len(missing)} present in {IMGDIR}/, {len(missing)} missing.")
    for m in missing:
        print("  MISSING:", m)


if __name__ == "__main__":
    main()
