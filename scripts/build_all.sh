#!/usr/bin/env bash
# Rebuild everything that is generated: blank templates, example zines, README preview images.
# Needs rsvg-convert, pdftoppm + pdfunite (poppler), Ghostscript and Pillow.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 zine.py blank
[ -f examples/photos/14.jpg ] || python3 scripts/fetch_example_photos.py

rm -f docs/images/example_*.png docs/images/hero.png
for style in polaroid fullbleed bilingual specimen duo journal; do
  python3 zine.py make --style "$style" --photos examples/photos --captions examples/captions.txt \
    --by "pocket-zine" --date "Nov 2026" -o "examples/$style.pdf" >/dev/null
  rm -f "examples/$style.svg"   # the .svg embeds every photo; the PDF is enough for an example
  pdftoppm -r 110 -jpeg -jpegopt quality=86 -singlefile "examples/$style.pdf" "docs/images/example_$style"
done
for f in templates/0*.pdf; do
  name=$(basename "$f" .pdf)
  pdftoppm -r 110 -png -singlefile "$f" "docs/images/template_${name#*_}"
done
python3 scripts/contact_sheet.py
# the panel-order diagram from the folding guide, for the README
pdftoppm -r 200 -png -singlefile -x 100 -y 990 -W 1160 -H 650 templates/00_how-to-fold.pdf docs/images/imposition
echo "done: templates/, examples/, docs/images/"
