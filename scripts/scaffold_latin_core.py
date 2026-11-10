#!/usr/bin/env python3
"""
Lay out the Google Fonts Latin Core expansion so only the drawing is left.

Writes into every sources/*.glyphspackage:

  1. `top` and `bottom` anchors on each base letter that will carry an accent,
     positioned from that glyph's own outline rather than a shared constant.
     The sources currently have no anchors at all, so without this every one
     of the ~145 accented glyphs would need its mark placed by hand.
  2. Empty slots for the combining marks, each with a `_top` or `_bottom`
     attachment anchor at the origin. Draw the mark around that anchor and
     every composite that uses it lands correctly.
  3. The accented glyphs themselves, as composites of base + mark.
  4. Spacing accent characters, which Latin Core requires alongside the
     combining ones.

Idempotent: re-running updates in place rather than duplicating.

IMPORTANT: until the marks in (2) are actually drawn, the composites render
as the bare base letter. This branch is scaffolding, not releasable.
"""
import os, re, sys, glob, unicodedata
from fontTools.ttLib import TTFont
from fontTools import agl

# Marks needed by Latin Core, as combining-mark glyph names.
MARKS = {
    "gravecomb": 0x0300, "acutecomb": 0x0301, "circumflexcomb": 0x0302,
    "tildecomb": 0x0303, "macroncomb": 0x0304, "brevecomb": 0x0306,
    "dotaccentcomb": 0x0307, "dieresiscomb": 0x0308, "ringcomb": 0x030A,
    "hungarumlautcomb": 0x030B, "caroncomb": 0x030C,
    "cedillacomb": 0x0327, "ogonekcomb": 0x0328, "commaaccentcomb": 0x0326,
}
BELOW = {"cedillacomb", "ogonekcomb", "commaaccentcomb"}

# Spacing forms Latin Core also wants in their own right.
SPACING = {
    "grave": 0x0060, "acute": 0x00B4, "circumflex": 0x02C6, "tilde": 0x02DC,
    "macron": 0x00AF, "breve": 0x02D8, "dotaccent": 0x02D9,
    "dieresis": 0x00A8, "ring": 0x02DA, "hungarumlaut": 0x02DD,
    "caron": 0x02C7, "cedilla": 0x00B8, "ogonek": 0x02DB,
}


def layer_id(pkg):
    m = re.search(r'id = "([^"]+)";', open(f"{pkg}/fontinfo.plist").read())
    return m.group(1)


def read_glyph(path):
    return open(path).read() if os.path.exists(path) else None


def set_anchors(src, anchors):
    """Insert or replace the layer's anchors block."""
    block = "anchors = (\n" + "".join(
        "{\nname = %s;\npos = (%d,%d);\n},\n" % (n, x, y) for n, (x, y) in anchors.items()
    ) + ");\n"
    if "anchors = (" in src:
        return re.sub(r"anchors = \(.*?\);\n", block, src, count=1, flags=re.S)
    return src.replace("layerId = ", block + "layerId = ", 1)


def write_mark(pkg, lid, name, uni):
    """An empty mark with its attachment anchor at the origin."""
    anchor = "_bottom" if name in BELOW else "_top"
    body = (
        "{\nglyphname = %s;\nlayers = (\n{\n"
        "anchors = (\n{\nname = %s;\npos = (0,0);\n},\n);\n"
        "layerId = \"%s\";\nshapes = (\n);\nwidth = 0;\n}\n);\n"
        "unicode = %d;\n}\n" % (name, anchor, lid, uni)
    )
    open(f"{pkg}/glyphs/{file_for(name)}", "w").write(body)


def write_composite(pkg, lid, name, base, mark, width, uni, mx, my):
    """base + mark. The mark's own `_top` sits at its origin, so offsetting the
    component by the base's anchor is what aligns them."""
    body = (
        "{\nglyphname = %s;\nlayers = (\n{\nlayerId = \"%s\";\nshapes = (\n"
        "{\nref = %s;\n},\n{\npos = (%d,%d);\nref = %s;\n},\n);\n"
        "width = %d;\n}\n);\nunicode = %d;\n}\n"
        % (name, lid, base, mx, my, mark, width, uni)
    )
    open(f"{pkg}/glyphs/{file_for(name)}", "w").write(body)


def file_for(name):
    """Glyphs escapes uppercase with a trailing underscore: A -> A_.glyph"""
    return "".join(c + "_" if c.isupper() else c for c in name) + ".glyph"


def main(repo, core_file, built_dir):
    # Latin Core: codepoint -> nice glyph name
    core = {}
    for line in open(core_file):
        n = line.strip()
        if n and not n.startswith("#"):
            u = agl.toUnicode(n)
            if len(u) == 1:
                core[ord(u)] = n

    pkgs = sorted(glob.glob(f"{repo}/sources/*.glyphspackage"))
    for pkg in pkgs:
        stem = os.path.basename(pkg).replace(".glyphspackage", "")
        style = stem.replace("LibreCheltenham", "") or "Regular"
        ttf = f"{built_dir}/LibreCheltenham-{style}.ttf"
        if not os.path.exists(ttf):
            print(f"  skip {stem}: no built {os.path.basename(ttf)}"); continue

        font = TTFont(ttf, lazy=True)
        cmap, glyf, hmtx = font.getBestCmap(), font["glyf"], font["hmtx"]
        have = set(cmap)
        lid = layer_id(pkg)

        # Which accented glyphs can be built from what already exists?
        composites, bases = {}, {}
        for cp, name in sorted(core.items()):
            if cp in have:
                continue
            d = unicodedata.normalize("NFD", chr(cp))
            if len(d) != 2:
                continue
            b, m = ord(d[0]), ord(d[1])
            mark = next((k for k, v in MARKS.items() if v == m), None)
            if not mark or b not in have:
                continue
            composites[name] = (cmap[b], mark, cp)
            bases.setdefault(cmap[b], b)

        # 1. anchors on the bases, from each glyph's own outline
        for gname in bases:
            g = glyf[gname]
            if not g.numberOfContours:
                continue
            p = f"{pkg}/glyphs/{file_for(gname)}"
            src = read_glyph(p)
            if src is None:
                continue
            cx = (g.xMin + g.xMax) // 2
            open(p, "w").write(set_anchors(src, {"top": (cx, g.yMax),
                                                 "bottom": (cx, min(0, g.yMin))}))

        # 2. the marks, empty, anchored at the origin
        for name, uni in MARKS.items():
            write_mark(pkg, lid, name, uni)
        for name, uni in SPACING.items():
            if uni not in have:
                write_mark(pkg, lid, name, uni)

        # 3. the composites
        for name, (base, mark, cp) in composites.items():
            g = glyf[base]
            cx = (g.xMin + g.xMax) // 2
            y = min(0, g.yMin) if mark in BELOW else g.yMax
            write_composite(pkg, lid, name, base, mark, hmtx[base][0], cp, cx, y)

        # 4. keep order.plist in step so Glyphs shows the new slots
        order = open(f"{pkg}/order.plist").read().rstrip()
        assert order.endswith(")")
        known = set(re.findall(r"[\w.]+", order))
        added = [n for n in list(MARKS) + list(SPACING) + list(composites)
                 if n not in known]
        if added:
            open(f"{pkg}/order.plist", "w").write(
                order[:-1].rstrip().rstrip(",") + ",\n" + ",\n".join(added) + "\n)\n")

        print(f"  {stem:34} anchors on {len(bases):3}  marks {len(MARKS)}  "
              f"composites {len(composites):3}  order +{len(added)}")
        font.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
