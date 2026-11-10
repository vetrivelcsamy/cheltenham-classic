#!/usr/bin/env python3
"""
Fail if a combining mark is encoded but has no outline.

An empty mark is worse than a missing one. The composites that use it still
build, so U+00C1 exists and renders as a bare `A` — a reader sees a plausible
wrong letter instead of a missing-glyph box, and nothing warns them.

FontBakery will not catch this: glyph_coverage counts codepoints, not
outlines, and reports success either way. Hence this check.
"""
import sys, glob, os
from fontTools.ttLib import TTFont

COMBINING = range(0x0300, 0x0370)


def main(d):
    bad = {}
    for p in sorted(glob.glob(os.path.join(d, "*.ttf"))):
        f = TTFont(p, lazy=True)
        cmap, glyf = f.getBestCmap(), f["glyf"]
        empty = [cp for cp in cmap if cp in COMBINING
                 and not glyf[cmap[cp]].numberOfContours]
        if empty:
            bad[os.path.basename(p)] = empty
        f.close()

    if not bad:
        print("marks drawn: every encoded combining mark has an outline")
        return 0

    for name, cps in bad.items():
        print(f"{name}: {len(cps)} combining marks encoded but empty")
        print("   " + " ".join(f"U+{c:04X}" for c in sorted(cps)))
    print("\nThese build into accented glyphs that render as the bare base letter.")
    print("Draw them (see sources/DRAWING.md) before publishing.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "gf-submission"))
