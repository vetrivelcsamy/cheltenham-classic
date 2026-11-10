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
for g in src/*.glyphspackage; do
  fontmake -g "$g" -o ttf --output-dir "$TMP" >/dev/null
done

echo
echo "regenerating marks from the measured design"
python3 scripts/derive_marks.py . "$TMP"
python3 scripts/draw_marks.py . "$TMP"
python3 scripts/latin_core.py . "$TMP"
python3 scripts/draw_eszett.py . "$TMP"
# after latin_core, which regenerates glyph files and would otherwise wipe
# the kerning groups written onto them
python3 scripts/kern.py . "$TMP"

echo
echo "pass 2 - final build"
for g in src/*.glyphspackage; do
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
echo
fontbakery check-googlefonts --succinct "$OUT"/*.ttf || true
