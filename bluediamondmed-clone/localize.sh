#!/usr/bin/env bash
#
# Make the Blue Diamond clone 100% self-contained.
#
# Downloads every remaining asset still referenced from a remote host
# (CSS, JS, fonts, and any CSS-referenced images) into local folders, then
# rewrites those references to local paths. Inline <img> images already live
# in img/ and are left alone.
#
# What each pass does:
#   Pass 1  bluediamondmed.com assets linked from the .html pages (fixes the
#           11 inner pages, which still pull ~60 combined css/js each).
#   Pass 2  assets referenced by url() inside the CSS downloaded in pass 1
#           (icon fonts, sprite images), from both absolute and root-relative
#           refs.
#   Pass 3  Google fonts (Playfair Display / Roboto / Plus Jakarta Sans) that
#           the home page's CSS pulls from infindigital.net.
#   Pass 4  puts the icon-font / sprite files the home page's CSS asks for by
#           relative path (../webfonts/, ../fonts/, ../images/, ../img/, and
#           same-folder names) into those sibling folders, by matching the
#           files downloaded in passes 1-2. This is why Font Awesome, eicons,
#           etc. render without touching the CSS.
#   Report  prints, and writes to localize-report.txt, everything that was
#           fetched and anything that could NOT be resolved, so the remaining
#           gaps (if any) are explicit.
#
# Run from anywhere that can reach bluediamondmed.com and infindigital.net:
#     cd bluediamondmed-clone && bash localize.sh
# Then serve from this folder (paths are root-relative):
#     python3 -m http.server 8000   # http://localhost:8000
#
# Safe to re-run: files already present are skipped, so a second run only
# fills gaps.
#
set -uo pipefail
cd "$(dirname "$0")"
BASE="https://bluediamondmed.com"
HOST="bluediamondmed.com"
FONTHOST="infindigital.net"
EXT='css|js|woff2?|ttf|eot|otf|png|jpe?g|gif|svg|webp|avif|ico|mp4|webm'
FONT_EXT='woff2?|ttf|eot|otf'

: > .report_got
: > .report_failed

dl() {  # dl <url> : download <url> to its local (host-mirrored) path, query stripped
  local url="$1" rel path
  rel="${url#https://$HOST/}"; rel="${rel%%\?*}"
  path="./$rel"
  [ -f "$path" ] && return 0
  mkdir -p "$(dirname "$path")"
  if curl -fsSL --max-time 90 "$url" -o "$path"; then
    echo "  got $rel"; echo "$rel" >> .report_got
  else
    rm -f "$path"; echo "  FAILED $url"; echo "$url" >> .report_failed
  fi
}

dlto() {  # dlto <url> <destpath> : download <url> to an explicit local path
  local url="$1" path="$2"
  [ -f "$path" ] && return 0
  mkdir -p "$(dirname "$path")"
  if curl -fsSL --max-time 90 "$url" -o "$path"; then
    echo "  got $path"; echo "$path" >> .report_got
  else
    rm -f "$path"; echo "  FAILED $url"; echo "$url" >> .report_failed
  fi
}

echo "==> Pass 1: bluediamondmed.com assets referenced by the HTML pages (css, js)..."
grep -ohE "$BASE/[^\"')> ]+\.($EXT)(\?[^\"')> ]*)?" ./*.html | sort -u > .urls1
while read -r u; do [ -n "$u" ] && dl "$u"; done < .urls1

echo "==> Pass 2: assets referenced inside downloaded CSS (fonts, images)..."
: > .urls2
find wp-content wp-includes -name '*.css' 2>/dev/null -print0 | while IFS= read -r -d '' f; do
  grep -ohE "url\(([^)]*)\)" "$f" | sed -E "s/url\(['\"]?//; s/['\"]?\).*//" | while read -r ref; do
    case "$ref" in
      "$BASE"/*)                 echo "${ref%%\?*}" ;;              # absolute
      /wp-content/*|/wp-includes/*) echo "$BASE${ref%%\?*}" ;;      # root-relative
    esac
  done
done | sort -u > .urls2
while read -r u; do [ -n "$u" ] && dl "$u"; done < .urls2

echo "==> Rewriting bluediamondmed.com asset URLs to local root-relative paths..."
python3 - "$HOST" "$EXT" <<'PY'
import re, sys, glob, os
host, ext = sys.argv[1], sys.argv[2]
pat = re.compile(r'https://' + re.escape(host) +
                 r'(/[^"\'()> ]+?\.(?:' + ext + r'))(\?[^"\'()> ]*)?')
targets = glob.glob("*.html")
for root in ("wp-content", "wp-includes"):
    for dp, _, fns in os.walk(root):
        targets += [os.path.join(dp, fn) for fn in fns if fn.endswith(".css")]
for fp in targets:
    t = open(fp, encoding="utf-8", errors="replace").read()
    n = pat.sub(lambda m: m.group(1), t)
    if n != t:
        open(fp, "w", encoding="utf-8").write(n)
        print("  rewrote", fp)
PY

echo "==> Pass 3: Google fonts pulled from $FONTHOST by the home page CSS..."
mkdir -p assets/google-fonts
grep -rhoE "https://$FONTHOST/[^)\"' ]+\.($FONT_EXT)(\?[^)\"' ]*)?" assets/*.css 2>/dev/null \
  | sed -E 's/\?.*//' | sort -u > .urls3
while read -r u; do
  [ -z "$u" ] && continue
  dlto "$u" "assets/google-fonts/$(basename "$u")"
done < .urls3
python3 - "$FONTHOST" "$FONT_EXT" <<'PY'
import re, sys, glob, os
host, fext = sys.argv[1], sys.argv[2]
# https://infindigital.net/.../fonts/NAME.woff2  ->  google-fonts/NAME.woff2
pat = re.compile(r'https://' + re.escape(host) +
                 r'/[^)"\' ]+?/([^/)"\' ?]+\.(?:' + fext + r'))(\?[^)"\' ]*)?')
for fp in glob.glob("assets/*.css"):
    t = open(fp, encoding="utf-8", errors="replace").read()
    n = pat.sub(lambda m: "google-fonts/" + m.group(1), t)
    if n != t:
        open(fp, "w", encoding="utf-8").write(n)
        print("  rewrote", fp)
PY

echo "==> Pass 4: place icon fonts / sprites where the home page CSS expects them..."
python3 - <<'PY'
import re, glob, os, shutil
# Relative refs in the home page's local CSS resolve to sibling folders of the
# clone root (assets/foo.css -> ../webfonts/, ../fonts/, ../images/, ../img/)
# and to the CSS's own folder for bare names (assets/NAME.ext). Collect them.
need = set()  # (target_dir, basename)
folder_re = re.compile(
    r'url\(\s*[\'"]?(?:\.\./)?(webfonts|fonts|images|img)/'
    r'([^)\'"?#]+\.(?:woff2?|ttf|eot|otf|svg|png|jpe?g|gif|webp))')
bare_re = re.compile(
    r'url\(\s*[\'"]?([A-Za-z0-9_-]+\.(?:woff2?|ttf|eot|otf|svg))(?:[?#][^)\'"]*)?[\'"]?\s*\)')
for fp in glob.glob("assets/*.css"):
    t = open(fp, encoding="utf-8", errors="replace").read()
    for m in folder_re.finditer(t):
        need.add((m.group(1), os.path.basename(m.group(2))))
    for m in bare_re.finditer(t):
        need.add(("assets", m.group(1)))

# Index every file downloaded in passes 1-2 by basename.
index = {}
for root in ("wp-content", "wp-includes"):
    for dp, _, fns in os.walk(root):
        for fn in fns:
            index.setdefault(fn, os.path.join(dp, fn))

placed, missing = [], []
for folder, bn in sorted(need):
    dest = "assets/" + bn if folder == "assets" else folder + "/" + bn
    if os.path.exists(dest):
        continue
    src = index.get(bn)
    if src:
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        shutil.copy2(src, dest)
        placed.append(dest + "  <-  " + src)
        print("  placed", dest)
    else:
        missing.append(folder + "/" + bn)
with open(".report_placed", "w") as fh:
    fh.write("\n".join(placed))
with open(".report_missing", "w") as fh:
    fh.write("\n".join(missing))
PY

echo "==> Writing localize-report.txt ..."
{
  echo "Blue Diamond clone localization report"
  echo "generated: $(date -u '+%Y-%m-%d %H:%M:%SZ')"
  echo
  echo "Downloaded ($(grep -c . .report_got 2>/dev/null)):"
  sort -u .report_got 2>/dev/null | sed 's/^/  /'
  echo
  echo "Placed into sibling folders:"
  sed 's/^/  /' .report_placed 2>/dev/null
  echo
  echo "COULD NOT resolve locally (still need these files) :"
  if [ -s .report_failed ] || [ -s .report_missing ]; then
    sort -u .report_failed 2>/dev/null | sed 's/^/  download-failed: /'
    sed 's/^/  no-source-found: /' .report_missing 2>/dev/null
  else
    echo "  (none - clone is fully self-contained)"
  fi
} | tee localize-report.txt

rm -f .urls1 .urls2 .urls3 .report_got .report_failed .report_placed .report_missing
echo
echo "==> Done. Review localize-report.txt, then commit the new files."
echo "    Verify locally with:  python3 -m http.server 8000"
