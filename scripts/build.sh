#!/usr/bin/env bash
# Build Cheltenham Classic for Google Fonts, end to end.
#
#   pip install -r requirements.txt
#   ./scripts/build.sh
#
# Two passes, because the marks are generated from the design's own
# measurements and you cannot measure a font you have not built yet:
#
#   1. build the sources as they stand, purely to measure stems, hairlines,
#      x-height and slant off real outlines
#   2. regenerate the marks from those measurements, then build for real
#
# Components are flattened in the final pass. The marks are deliberately
# composites of other glyphs so they track their donors in the source, but
# a composite pointing at a composite fails nested_components in the binary.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=gf-submission
TMP=.build-measure
FLATTEN="ufo2ft.filters.flattenComponents::FlattenComponentsFilter"

rm -rf "$TMP"; mkdir -p "$TMP" "$OUT"

echo "pass 1 - measuring build"
for g in sources/*.glyphspackage; do
  fontmake -g "$g" -o ttf --output-dir "$TMP" >/dev/null
done

echo
echo "regenerating marks from the measured design"
python3 scripts/derive_marks.py . "$TMP"
python3 scripts/draw_marks.py . "$TMP"
python3 scripts/latin_core.py . "$TMP"
# after latin_core, which builds these three from ellipses and would
# otherwise overwrite them
python3 scripts/borrow_bowls.py . "$TMP"
python3 scripts/draw_eszett.py . "$TMP"
# after latin_core, which regenerates glyph files and would otherwise wipe
# the kerning groups written onto them
python3 scripts/kern.py . "$TMP"

echo
echo "pass 2 - final build"
for g in sources/*.glyphspackage; do
  echo "building $(basename "$g")"
  fontmake -g "$g" -o ttf --output-dir "$OUT" --filter "$FLATTEN" >/dev/null
done

python3 scripts/gf_fixup.py "$OUT"

# METADATA.pb pins the revision these binaries came from, so it has to be
# rewritten whenever they are. Left to drift it points Google Fonts' tooling
# at the wrong commit, which is worse than no pin at all.
python3 scripts/pin_commit.py "$OUT/METADATA.pb"
echo
python3 scripts/check_marks_drawn.py "$OUT"

# The layout Google Fonts expects upstream: fonts/ttf, fonts/otf and
# fonts/webfonts beside sources/. Their builder produces these by default,
# so a submission that does not carry them does not look like one of theirs.
echo
echo "laying out fonts/ for upstream"
rm -rf fonts; mkdir -p fonts/ttf fonts/webfonts
cp "$OUT"/*.ttf fonts/ttf/
python3 scripts/webfonts.py "$OUT" fonts/webfonts 2>/dev/null || true
# OTF needs fontforge, which CI has and a local checkout may not.
if command -v fontforge >/dev/null; then
  mkdir -p fonts/otf
  for t in "$OUT"/*.ttf; do
    b=$(basename "$t" .ttf)
    fontforge -lang=ff -c 'Open($1); Generate($2)' "$t" "fonts/otf/$b.otf" >/dev/null 2>&1 || true
  done
else
  echo "  (fontforge absent; fonts/otf left to CI)"
fi
printf "  ttf %s  otf %s  webfonts %s\n" \
  "$(ls fonts/ttf 2>/dev/null | wc -l | tr -d ' ')" \
  "$(ls fonts/otf 2>/dev/null | wc -l | tr -d ' ')" \
  "$(ls fonts/webfonts 2>/dev/null | wc -l | tr -d ' ')"
echo
fontbakery check-googlefonts --succinct "$OUT"/*.ttf || true
