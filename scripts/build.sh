#!/usr/bin/env bash
# Build Cheltenham Classic for Google Fonts, end to end.
#
#   pip install fontmake "fontbakery[googlefonts]"
#   ./scripts/build.sh
#
# fontmake reads the .glyphspackage sources directly and already emits GF
# filenames. gf_fixup.py then applies the metadata the sources do not carry.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=gf-submission
mkdir -p "$OUT"
for g in src/*.glyphspackage; do
  echo "building $(basename "$g")"
  fontmake -g "$g" -o ttf --output-dir "$OUT" >/dev/null
done
python3 scripts/gf_fixup.py "$OUT"
echo
fontbakery check-googlefonts --succinct "$OUT"/*.ttf || true
