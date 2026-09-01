#!/usr/bin/env python3
"""Build a fully-local index.html from the browser-saved home page (webpage/s.html
+ webpage/s_files). Move the saved assets into assets/, repoint everything to
local files (CSS/JS from assets/, images from img/ or assets/), fix nav links,
and hide the logged-in admin bar. Fonts weren't captured by the save, so any
font url() stays pointing at the live site (browsers fall back otherwise)."""
import re, os, shutil, html as ihtml

CLONE = "bluediamondmed-clone"
SRC_HTML = f"{CLONE}/webpage/s.html"
SRC_FILES = f"{CLONE}/webpage/s_files"
ASSETS = f"{CLONE}/assets"
IMGDIR = f"{CLONE}/img"
HOST = "https://bluediamondmed.com"

PAGES = {
    "": "index.html", "about-us": "about-us.html", "services": "services.html",
    "healthcare-staffing-services-page": "healthcare-staffing-services-page.html",
    "school-staffing": "school-staffing.html",
    "healthcare-professionals": "healthcare-professionals.html",
    "teachers-substitute-educators": "teachers-substitute-educators.html",
    "cpr-emergency-training-certification": "cpr-emergency-training-certification.html",
    "teach-in-the-u-s-a-with-blue-diamond-school-staffing": "teach-in-the-u-s-a-with-blue-diamond-school-staffing.html",
    "healthcare-staffing": "healthcare-staffing.html",
    "teaching-jobs": "teaching-jobs.html", "contact-us": "contact-us.html",
}
IMG_EXT = "png|jpe?g|gif|svg|webp|avif|ico"
SIZE = re.compile(r'-\d+x\d+(?=\.\w+$)')

# 1. Move saved assets into assets/
os.makedirs(ASSETS, exist_ok=True)
for fn in os.listdir(SRC_FILES):
    shutil.copy2(os.path.join(SRC_FILES, fn), os.path.join(ASSETS, fn))
img_have = set(os.listdir(IMGDIR))
asset_have = set(os.listdir(ASSETS))


def local_image(url_path, from_css):
    """Map a live image path to a local path, or None to leave as-is."""
    fn = os.path.basename(url_path)
    base = SIZE.sub('', fn)
    if base.startswith('cropped-') and 'BLUE-DIAMOND' in base:
        base = 'BLUE-DIAMOND-MEDICAL-STAFFING.png'
    if base in img_have:
        return ("../img/" if from_css else "img/") + base
    if fn in asset_have:
        return ("" if from_css else "assets/") + fn
    if base in asset_have:
        return ("" if from_css else "assets/") + base
    return None


def rewrite_live_images(text, from_css):
    pat = re.compile(re.escape(HOST) + r'(/[^"\'()> ]+?\.(?:' + IMG_EXT + r'))(\?[^"\'()> ]*)?')
    def repl(m):
        loc = local_image(m.group(1), from_css)
        return loc if loc else m.group(0)
    return pat.sub(repl, text)


# 2. Rewrite image url() inside the moved CSS files
for fn in os.listdir(ASSETS):
    if fn.endswith(".css"):
        p = os.path.join(ASSETS, fn)
        t = open(p, encoding="utf-8", errors="replace").read()
        n = rewrite_live_images(t, from_css=True)
        if n != t:
            open(p, "w", encoding="utf-8").write(n)

# 3. Build index.html from the saved page
h = open(SRC_HTML, encoding="utf-8", errors="replace").read()
h = h.replace("./s_files/", "assets/").replace('"s_files/', '"assets/')
h = rewrite_live_images(h, from_css=False)
# nav links -> local pages
def nav(m):
    q, slug = m.group(1), m.group(2).strip("/")
    return f'href={q}{PAGES[slug]}{q}' if slug in PAGES else m.group(0)
h = re.sub(r'href=(["\'])' + re.escape(HOST) + r'/([a-z0-9\-/]*)/?\1', nav, h)
# hide the logged-in admin bar and its offset
h = h.replace("</head>",
              "<style>#wpadminbar{display:none!important}"
              "html{margin-top:0!important}</style></head>", 1)

open(f"{CLONE}/index.html", "w", encoding="utf-8").write(h)

# report
live_left = len(re.findall(re.escape(HOST), h))
print("assets/ files:", len(os.listdir(ASSETS)))
print("index.html written; residual live bluediamondmed refs:", live_left)
