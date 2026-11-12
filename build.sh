#!/bin/sh
# Rebuild everything generated: the development pages, then the stylesheet
# (Tailwind only emits classes it finds in the HTML, so pages come first),
# then stamp the stylesheet's content hash into every page that links it.
set -e
cd "$(dirname "$0")"
python3 build_pages.py
npx tailwindcss@3.4.17 -c tailwind.config.js -i in.css -o assets/tailwind.css --minify
H=$(shasum -a 256 assets/tailwind.css | cut -c1-8)
for f in index.html developments/*/index.html; do
  sed -i '' -E "s#(assets/tailwind\.css)(\?v=[0-9a-f]+)?\"#\1?v=$H\"#" "$f"
done
echo "css -> $H"
