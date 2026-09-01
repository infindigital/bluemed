#!/usr/bin/env python3
"""Remove non-rendering WordPress admin/discovery cruft from the clone.

- All pages: strip WP discovery <link> tags (feeds, oEmbed, RSD/EditURI,
  wlwmanifest, shortlink, api.w.org, pingback, dns-prefetch, REST page JSON).
- Home page only: remove the hidden admin-bar markup block, the admin/plugin
  CSS+JS it loaded (admin bar, LiteSpeed panel, Wordfence, Elementor notes /
  dev-tools), and the now-redundant #wpadminbar hide style.
Nothing here renders on the public pages, so the visible UI is unchanged.
Then delete admin asset files no page references any more.
"""
import re, os, glob, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
HOME = os.path.join(ROOT, "index.html")

# --- markers that identify a discovery <link> to drop (case-insensitive) ---
MARKERS = [
    'application/rss+xml', 'application/atom+xml', 'oembed',
    'rel="edituri"', "rel='edituri'",
    'rel="wlwmanifest"', "rel='wlwmanifest'",
    'rel="shortlink"', "rel='shortlink'",
    'rel="https://api.w.org/"', "rel='https://api.w.org/'",
    'rel="pingback"', "rel='pingback'",
    'rel="dns-prefetch"', "rel='dns-prefetch'",
    'wp-json/wp/v2/pages',
]
LINK_RE = re.compile(r'<link\b[^>]*>', re.I)

# --- admin/plugin asset files loaded only by the logged-in home snapshot ---
ADMIN_ASSETS = [
    'admin-bar(1).min.css', 'admin-bar.min.css', 'admin-bar.min.js',
    'admin-toolbar.js', 'admin.ajaxWatcher.1756145765.js', 'admin.css',
    'admin.js', 'dev-tools.min.js', 'elementor-admin-bar.min.js',
    'litespeed.css', 'notes-app-initiator.min.js', 'notes.min.css',
    'notes.min.js', 'wfi18n.1756145765.js', 'wordfenceBox.1756145765.css',
]

def strip_discovery(html):
    def repl(m):
        low = m.group(0).lower()
        return '' if any(mk in low for mk in MARKERS) else m.group(0)
    return LINK_RE.sub(repl, html)

def remove_div_block(html, marker):
    """Remove a <div ...>...</div> block starting at `marker`, matching the
    close by div-depth counting (reliable for well-formed nested markup)."""
    i = html.find(marker)
    if i < 0:
        return html
    tag = re.compile(r'<(/?)div\b[^>]*?(/?)>', re.I)
    depth = 0
    for m in tag.finditer(html, i):
        if m.group(2):            # self-closing <div/>
            continue
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return html[:i] + html[m.end():]
    return html  # unbalanced; leave untouched

def remove_admin_assets(html):
    # drop the admin/plugin stylesheet + script tags (the files are deleted)
    for a in ADMIN_ASSETS:
        esc = re.escape(a)
        html = re.sub(r'<link\b[^>]*assets/' + esc + r'[^>]*>', '', html, flags=re.I)
        html = re.sub(r'<script\b[^>]*assets/' + esc + r'[^>]*>\s*</script>', '', html, flags=re.I)
    # NOTE: intentionally KEEP the injected
    #   <style>#wpadminbar{display:none!important}html{margin-top:0!important}</style>
    # override. It pins html margin-top to 0 exactly as the page renders now;
    # dropping it would re-expose the WP admin-bar's 32px gap. It is ~60 bytes
    # of inert CSS (its target element is gone) and guarantees identical layout.
    return html

def sheet_hrefs(html):
    hrefs = []
    for m in re.finditer(r'<link\b[^>]*rel=["\']stylesheet["\'][^>]*>', html, re.I):
        h = re.search(r'href=["\']([^"\']+)["\']', m.group(0), re.I)
        hrefs.append(h.group(1) if h else m.group(0))
    return hrefs

report = []
for fp in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
    orig = open(fp, encoding="utf-8", errors="replace").read()
    before = sheet_hrefs(orig)
    new = strip_discovery(orig)
    if os.path.abspath(fp) == os.path.abspath(HOME):
        new = remove_div_block(new, '<div id="wpadminbar"')
        new = remove_div_block(new, '<div id="wordfenceBox"')
        new = remove_admin_assets(new)
    after = sheet_hrefs(new)
    # every stylesheet we dropped must be an admin one; front-end sheets untouched
    removed = [h for h in before if h not in after]
    bad = [h for h in removed if not any(a in h for a in ADMIN_ASSETS)]
    assert not bad, f"{fp}: removed non-admin stylesheet(s): {bad}"
    for must in ("</html>", "<body", 'class="elementor'):
        assert must in new, f"{fp}: lost {must!r}!"
    if new != orig:
        open(fp, "w", encoding="utf-8").write(new)
    report.append((os.path.basename(fp), len(orig) - len(new), len(after)))

print("file, bytes_removed, stylesheet_links_kept")
for name, delta, s in report:
    print(f"  {name:52s} -{delta:<7d} sheets={s}")

# delete admin asset files no remaining HTML references
htmls = " ".join(open(f, encoding="utf-8", errors="replace").read()
                  for f in glob.glob(os.path.join(ROOT, "*.html")))
adir = os.path.join(ROOT, "assets")
deleted = []
for a in ADMIN_ASSETS:
    if ("assets/" + a) not in htmls:
        p = os.path.join(adir, a)
        if os.path.exists(p):
            os.remove(p); deleted.append(a)
print("\ndeleted unreferenced admin assets:", len(deleted))
for d in deleted:
    print("  -", d)
