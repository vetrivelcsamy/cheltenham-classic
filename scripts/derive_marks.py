#!/usr/bin/env python3
"""
Build the marks that can honestly be derived from shapes already in the font.

These are not constructed geometry. Each references an existing glyph as a
component, so they inherit the typeface's own modulation and terminals, and
they follow if that glyph is later redrawn:

  dotaccentcomb      period
  dieresiscomb       period, twice, parted by 0.92 of its width
  cedillacomb        comma, below the baseline
  commaaccentcomb    comma
  macroncomb         a bar, measured off the o and the period

The other nine - acute, grave, circumflex, caron, tilde, breve, ogonek,
hungarumlaut and ring - are left empty on purpose. The first eight are
modulated strokes whose terminals carry the design's voice. The ring was
tried as a scaled-down o and rejected on sight: it rendered as a miniature
letter, complete with serif modulation, where a ring wants an even-weight
circle. Drawing, not derivation.

Mark convention: the `_top` anchor sits at the origin and the shape sits above
it, so the gap between letter and accent is baked into the mark rather than
repeated across 145 composites.
"""
import os, re, sys, glob
from fontTools.ttLib import TTFont

DERIVED = ("dotaccentcomb", "dieresiscomb", "cedillacomb",
           "commaaccentcomb", "macroncomb")
GAP = 70          # letter top to accent bottom, in units
BELOW = {"cedillacomb", "commaaccentcomb"}


def file_for(name):
    return "".join(c + "_" if c.isupper() else c for c in name) + ".glyph"


def layer_id(pkg):
    return re.search(r'id = "([^"]+)";', open(f"{pkg}/fontinfo.plist").read()).group(1)


# Spacing twins of the derived marks, at their own legacy codepoints. A mark
# with no advance width trips base_has_width; an empty slot trips contour_count.
SPACING = {"dotaccentcomb": ("dotaccent", 0x02D9), "dieresiscomb": ("dieresis", 0x00A8),
           "macroncomb": ("macron", 0x00AF), "cedillacomb": ("cedilla", 0x00B8)}


def spacing(pkg, lid, comb, x0, x1, sb):
    name, uni = SPACING[comb]
    body = ("{\nglyphname = %s;\nlayers = (\n{\nlayerId = \"%s\";\nshapes = (\n"
            "{\npos = (%d,0);\nref = %s;\n},\n);\nwidth = %d;\n}\n);\n"
            "unicode = %d;\n}\n" % (name, lid, round(sb - x0), comb,
                                     round((x1 - x0) + 2 * sb), uni))
    open(f"{pkg}/glyphs/{file_for(name)}", "w").write(body)


def glyph(name, lid, shapes, width, uni, anchor="_top"):
    body = "{\nglyphname = %s;\nlayers = (\n{\nanchors = (\n{\nname = %s;\npos = (0,0);\n},\n);\nlayerId = \"%s\";\nshapes = (\n" % (name, anchor, lid)
    for s in shapes:
        body += "{\n"
        if "scale" in s:
            body += "scale = (%.3f,%.3f);\n" % s["scale"]
        body += "pos = (%d,%d);\nref = %s;\n},\n" % (s["pos"][0], s["pos"][1], s["ref"])
    body += ");\nwidth = %d;\n}\n);\nunicode = %d;\n}\n" % (width, uni)
    return body


def path_glyph(name, lid, contour, width, uni):
    nodes = "".join("(%d,%d,l),\n" % p for p in contour)
    return ("{\nglyphname = %s;\nlayers = (\n{\nanchors = (\n{\nname = _top;\npos = (0,0);\n},\n);\n"
            "layerId = \"%s\";\nshapes = (\n{\nclosed = 1;\nnodes = (\n%s);\n},\n);\nwidth = %d;\n}\n);\n"
            "unicode = %d;\n}\n" % (name, lid, nodes, width, uni))


def main(repo, built):
    for pkg in sorted(glob.glob(f"{repo}/sources/*.glyphspackage")):
        stem = os.path.basename(pkg).replace(".glyphspackage", "")
        style = stem.replace("CheltenhamClassic", "") or "Regular"
        ttf = f"{built}/CheltenhamClassic-{style}.ttf"
        if not os.path.exists(ttf):
            print(f"  skip {stem}"); continue
        f = TTFont(ttf, lazy=True)
        cm, glyf, hmtx = f.getBestCmap(), f["glyf"], f["hmtx"]
        lid = layer_id(pkg)

        pn, cn, on = cm.get(0x2E), cm.get(0x2C), cm.get(0x6F)
        pg, og = glyf[pn], glyf[on]
        cg = glyf[cn]
        pw, ph = pg.xMax - pg.xMin, pg.yMax - pg.yMin
        ow = og.xMax - og.xMin
        # The macron has no donor glyph, so its weight is scaled off the
        # period, which in this design is close to the stem. 0.72 of that
        # lands it between stem and hairline, where a macron belongs.
        thin = max(40, int(ph * 0.72))

        out = {}
        # a single dot, lifted clear of the letter
        out["dotaccentcomb"] = glyph("dotaccentcomb", lid,
            [{"ref": pn, "pos": (-(pg.xMin + pw // 2), GAP - pg.yMin)}], 0, 0x0307)
        # two of them, parted by one dot width
        sep = int(pw * 0.92)
        out["dieresiscomb"] = glyph("dieresiscomb", lid,
            [{"ref": pn, "pos": (-(pg.xMin + pw // 2) - sep, GAP - pg.yMin)},
             {"ref": pn, "pos": (-(pg.xMin + pw // 2) + sep, GAP - pg.yMin)}], 0, 0x0308)
        # the comma, hung below the baseline
        # A whole comma hangs 297 units below the baseline, past the descender
        # box. Scaled to 0.82 it reads as a cedilla rather than a comma that
        # wandered, and Ccedilla stops being the deepest glyph in the family.
        cs_ = 0.82
        out["cedillacomb"] = glyph("cedillacomb", lid,
            [{"ref": cn, "scale": (cs_, cs_),
              "pos": (-(cg.xMin + (cg.xMax - cg.xMin) // 2) * cs_, -cg.yMax * cs_ - 8)}],
            0, 0x0327, anchor="_bottom")
        out["commaaccentcomb"] = glyph("commaaccentcomb", lid,
            [{"ref": cn, "pos": (-(cg.xMin + (cg.xMax - cg.xMin) // 2), -cg.yMax - 20)}],
            0, 0x0326, anchor="_bottom")
        # the one mark with no donor glyph: a bar as wide as 0.72 of the o
        half = int(ow * 0.36)
        out["macroncomb"] = path_glyph("macroncomb", lid,
            [(-half, GAP), (half, GAP), (half, GAP + thin), (-half, GAP + thin)], 0, 0x0304)

        # Latvian lowercase g is the one exception: Unicode decomposes it to
        # a cedilla below, but the descender already owns that space, so the
        # mark is turned and set above. Every other comma-accent letter
        # (k l n r, and cap G) keeps it below.
        gp = f"{pkg}/glyphs/gcommaaccent.glyph"
        if os.path.exists(gp):
            gs = open(gp).read()
            top = glyf[cm[0x67]].yMax + GAP
            # the derived cedilla's shape ends 20 units under its origin, so
            # turning it about the origin puts its underside at +20.
            gs = re.sub(r"\{\n(?:scale = \([^)]*\);\n)?pos = \((-?\d+),(-?\d+)\);\nref = cedillacomb;\n\}",
                        lambda m: "{\nscale = (-1,-1);\npos = (%s,%d);\nref = cedillacomb;\n}"
                                  % (m.group(1), top - 20), gs, count=1)
            open(gp, "w").write(gs)

        for name, body in out.items():
            open(f"{pkg}/glyphs/{file_for(name)}", "w").write(body)

        sb = int((og.xMax - og.xMin) * 0.11)
        cw = cg.xMax - cg.xMin
        for comb, x0, x1 in (
                ("dotaccentcomb", -(pw // 2), pw - pw // 2),
                ("dieresiscomb", -(pw // 2) - sep, pw - pw // 2 + sep),
                ("macroncomb", -half, half),
                ("cedillacomb", -(cw // 2) * cs_, (cw - cw // 2) * cs_)):
            spacing(pkg, lid, comb, x0, x1, sb)
        print(f"  {stem:34} derived {len(out)}  (dot {pw}x{ph}, thin {thin})")
        f.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
