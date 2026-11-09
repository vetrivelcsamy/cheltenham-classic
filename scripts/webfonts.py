#!/usr/bin/env python3
"""TTF -> WOFF and WOFF2, for the specimen site and release assets.

Kept separate from gf_fixup.py: Google Fonts only ever wants the TTFs, so web
formats are a packaging concern rather than part of the font build.
"""
import sys, os, glob
from fontTools.ttLib import TTFont

def main(src, dst):
    os.makedirs(dst, exist_ok=True)
    for p in sorted(glob.glob(os.path.join(src, "*.ttf"))):
        stem = os.path.splitext(os.path.basename(p))[0]
        for flavor in ("woff", "woff2"):
            f = TTFont(p)
            f.flavor = flavor
            out = os.path.join(dst, f"{stem}.{flavor}")
            f.save(out)
            f.close()
            print(f"  {os.path.basename(out)}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
