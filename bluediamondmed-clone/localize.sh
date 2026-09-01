#!/usr/bin/env bash
#
# Make the Blue Diamond clone 100% self-contained.
#
# Downloads every remaining asset still referenced from bluediamondmed.com
# (CSS, JS, fonts, and any CSS-referenced images) into local folders that
# mirror the site's paths, then rewrites all those references to root-relative
# local paths. Inline <img> images already live in img/ and are left alone.
#
# Run from anywhere that can reach bluediamondmed.com:
#     cd bluediamondmed-clone && bash localize.sh
# Then serve from this folder (paths are root-relative):
#     python3 -m http.server 8000   # http://localhost:8000
#
set -uo pipefail
cd "$(dirname "$0")"
BASE="https://bluediamondmed.com"
HOST="bluediamondmed.com"
EXT='css|js|woff2?|ttf|eot|otf|png|jpe?g|gif|svg|webp|avif|ico|mp4|webm'

dl() {  # dl <url> : download <url> to its local path (query stripped)
  local url="$1" rel path
  rel="${url#https://$HOST/}"; rel="${rel%%\?*}"
  path="./$rel"
  [ -f "$path" ] && return 0
  mkdir -p "$(dirname "$path")"
  curl -fsSL "$url" -o "$path" && echo "  got $rel" || echo "  FAILED $url"
}

echo "==> Pass 1: assets referenced by the HTML pages (css, js)..."
grep -ohE "$BASE/[^\"')> ]+\.($EXT)(\?[^\"')> ]*)?" ./*.html | sort -u > .urls1
while read -r u; do [ -n "$u" ] && dl "$u"; done < .urls1

echo "==> Pass 2: assets referenced inside downloaded CSS (fonts, images)..."
: > .urls2
find wp-content wp-includes -name '*.css' 2>/dev/null -print0 | while IFS= read -r -d '' f; do
  grep -ohE "url\(([^)]*)\)" "$f" | sed -E "s/url\(['\"]?//; s/['\"]?\).*//" \
    | grep -E "^$BASE/" | sed -E 's/\?.*//'
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

rm -f .urls1 .urls2
echo "==> Done. The clone is now fully self-contained."
