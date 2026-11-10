#!/usr/bin/env python3
"""
Rebuild Thorn, thorn and the pilcrow from the font's own P and b bowls.

latin_core.py builds these three from half-ellipses, on the stated grounds
that "in P and b the stem and bowl are one contour, so the bowl cannot be
lifted out". That is true of a component reference, which can only move a
whole glyph. It is not true of the geometry.

Intersect P with the half-plane to the right of its stem and above its foot
serif and the bowl falls out as two contours -- the outer curve and its
counter. Both are the designer's own drawing: the stroke thins into the join
the way P's does, and the counter is the shape P's counter is, not an oval.
That is exactly what sources/DRAWING.md section 2a said these glyphs were
missing.

The stem the bowl is re-hung on is the font's own I or l, so the serifs come
along too, and stem and bowl are unioned into a single contour rather than
left as overlapping pieces -- an outline a designer would recognise as drawn
rather than assembled.

Italic styles shear every cut by the master's own angle, so the cut follows
the stem instead of slicing across it.

Run after latin_core.py (which would otherwise overwrite these glyphs) and
before kern.py (which writes kerning groups onto the glyph files).
"""
import glob
import math
import os
import re
import sys

from booleanOperations.booleanGlyph import BooleanGlyph
from fontTools.pens.boundsPen import ControlBoundsPen
from fontTools.pens.pointPen import SegmentToPointPen
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

BIG = 4000          # far enough outside any glyph to act as "infinity"


# ── glyph objects booleanOperations will accept ───────────────────────────
class Shape:
    """The minimum surface BooleanGlyph wants from a glyph."""
    name = "shape"
    unicodes = ()
    width = 0
    note = None

    def __init__(self, rec=None):
        self.rec = rec or RecordingPen()
        self.lib = {}

    def draw(self, pen):
        self.rec.replay(pen)

    def drawPoints(self, pointPen):
        self.rec.replay(SegmentToPointPen(pointPen))


def outline(glyphset, name):
    """A glyph's outline as cubics; booleanOperations cannot take quadratics."""
    rec = RecordingPen()
    glyphset[name].draw(Qu2CuPen(rec, max_err=0.4, all_cubic=True))
    return Shape(rec)


def region(x0, y0, x1, y1, slant=0.0):
    """A rectangle, sheared by the master's italic angle about the baseline."""
    t = math.tan(math.radians(slant))
    rec = RecordingPen()
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    rec.moveTo((pts[0][0] + pts[0][1] * t, pts[0][1]))
    for x, y in pts[1:]:
        rec.lineTo((x + y * t, y))
    rec.closePath()
    return Shape(rec)


def bounds(shape):
    pen = ControlBoundsPen(None)
    shape.draw(pen)
    return pen.bounds


def spans(bg, lo, hi, horizontal=True, slant=0.0):
    """Ink runs through a thin slice: x-runs across a row, or y-runs up a column."""
    slab = (region(-BIG, lo, BIG, hi, slant) if horizontal
            else region(lo, -BIG, hi, BIG, slant))
    cut = BooleanGlyph(bg).intersection(BooleanGlyph(slab))
    out = []
    for contour in cut.contours:
        pen = ControlBoundsPen(None)
        contour.draw(pen)
        if pen.bounds:
            x0, y0, x1, y1 = pen.bounds
            out.append((x0, x1) if horizontal else (y0, y1))
    return sorted(out)


def stem_edges(bg, probes, slant=0.0):
    """The left and right edge of the upright stem, read where it stands alone.

    Probed at several heights and intersected, so a height that happens to
    cut through the bowl as well does not widen the answer.
    """
    tan = math.tan(math.radians(slant))
    best = None
    for y in probes:
        runs = spans(bg, y, y + 6, True, slant)
        if not runs:
            continue
        # A slanted stem sits at a different x at every height, so each
        # reading is pulled back to the baseline before the readings are
        # intersected. Comparing them where they were taken reports the
        # stem as far narrower than it is, and the bowl is then cut and
        # re-hung off a stem edge that was never there.
        left = (runs[0][0] - y * tan, runs[0][1] - y * tan)
        best = left if best is None else (max(best[0], left[0]),
                                          min(best[1], left[1]))
    return best


def measure_slant(l_shape, xh):
    """The master's own slant, read off l's stem.

    post.italicAngle is still zero at this point -- gf_fixup.py sets it after
    the final build -- but the italic outlines are already sheared, so the
    angle has to come from the geometry, the same way latin_core.py reads it.
    A cut taken as upright through a slanted stem leaves a sliver behind.
    """
    lo = spans(l_shape, xh * 0.25, xh * 0.25 + 4, True, 0.0)
    hi = spans(l_shape, xh * 0.95, xh * 0.95 + 4, True, 0.0)
    if not lo or not hi:
        return 0.0
    deg = math.degrees(math.atan2(hi[0][0] - lo[0][0], xh * 0.70))
    return 0.0 if abs(deg) < 1.5 else deg


def bowl_of(bg, stem_right, y_floor, slant=0.0):
    """P's bowl, cut away from its stem and its foot serif."""
    return BooleanGlyph(bg).intersection(
        BooleanGlyph(region(stem_right, y_floor, BIG, BIG, slant)))


def shifted(shape, dx, dy):
    rec = RecordingPen()

    class Mover:
        def moveTo(self, p): rec.moveTo((p[0] + dx, p[1] + dy))
        def lineTo(self, p): rec.lineTo((p[0] + dx, p[1] + dy))
        def curveTo(self, *p): rec.curveTo(*[(q[0] + dx, q[1] + dy) for q in p])
        def qCurveTo(self, *p): rec.qCurveTo(*[(q[0] + dx, q[1] + dy) for q in p])
        def closePath(self): rec.closePath()
        def endPath(self): rec.endPath()
        def addComponent(self, *a, **k): pass

    shape.draw(Mover())
    return Shape(rec)


def mirrored(shape, axis_x):
    """Reflected left-to-right about a vertical line. The pilcrow's bowl hangs
    the other way from P's, and a reflection keeps the modulation honest --
    heavy on the outside of the curve, which is now the left."""
    rec = RecordingPen()
    f = lambda p: (2 * axis_x - p[0], p[1])

    class Flip:
        def moveTo(self, p): rec.moveTo(f(p))
        def lineTo(self, p): rec.lineTo(f(p))
        # reflection reverses winding, so the points are replayed in reverse
        def curveTo(self, *p): rec.curveTo(*[f(q) for q in p])
        def qCurveTo(self, *p): rec.qCurveTo(*[f(q) for q in p])
        def closePath(self): rec.closePath()
        def endPath(self): rec.endPath()
        def addComponent(self, *a, **k): pass

    shape.draw(Flip())
    out = Shape(rec)
    # a mirror flips every contour's direction; put them back
    return Shape(reverse(out))


def reverse(shape):
    """Re-wind every contour the other way."""
    from fontTools.pens.reverseContourPen import ReverseContourPen
    rec = RecordingPen()
    shape.draw(ReverseContourPen(rec))
    return rec


# ── writing geometry back out as Glyphs source nodes ──────────────────────
def nodes_of(shape):
    """Contours as Glyphs node text: offcurves `o`, curve points `cs`, lines `l`.

    Glyphs lists a closed contour's nodes in order with the offcurves ahead of
    the point they belong to, so the segment that closes the contour has its
    offcurves at the end of the list and its endpoint is the first node. The
    first node's type therefore records how the contour closes, not how it
    opens.
    """
    rec = RecordingPen()
    shape.draw(rec)
    out, segs, start = [], [], None

    def flush():
        if start is None or not segs:
            return
        closes_curved = segs[-1][0] == "curveTo" and _same(segs[-1][1][-1], start)
        nodes = [(start[0], start[1], "cs" if closes_curved else "l")]
        for i, (op, pts) in enumerate(segs):
            last = i == len(segs) - 1
            if op == "lineTo":
                if last and _same(pts[-1], start):
                    continue
                nodes.append((pts[-1][0], pts[-1][1], "l"))
            else:
                nodes.append((pts[0][0], pts[0][1], "o"))
                nodes.append((pts[1][0], pts[1][1], "o"))
                if not (last and _same(pts[-1], start)):
                    nodes.append((pts[-1][0], pts[-1][1], "cs"))
        out.append("{\nclosed = 1;\nnodes = (\n%s\n);\n}," % ",\n".join(
            "(%d,%d,%s)" % (round(x), round(y), t) for x, y, t in nodes))

    for op, pts in rec.value:
        if op == "moveTo":
            flush()
            segs, start = [], pts[0]
        elif op in ("lineTo", "curveTo"):
            segs.append((op, pts))
        elif op == "closePath":
            flush()
            segs, start = [], None
    flush()
    return out


def _area(contour):
    pen = ControlBoundsPen(None)
    contour.draw(pen)
    if not pen.bounds:
        return 0
    x0, y0, x1, y1 = pen.bounds
    return (x1 - x0) * (y1 - y0)


def _same(a, b, tol=0.6):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def fname(n):
    return "".join(c + "_" if c.isupper() else c for c in n) + ".glyph"


def layer_id(pkg):
    return re.search(r'id = "([^"]+)";',
                     open(f"{pkg}/fontinfo.plist").read()).group(1)


def put(pkg, name, lid, shapes, width, uni):
    body = ("{\nglyphname = %s;\nlayers = (\n{\nlayerId = \"%s\";\nshapes = (\n%s\n);\n"
            "width = %d;\n}\n);\n%s}\n"
            % (name, lid, "\n".join(shapes), round(width),
               "" if uni is None else "unicode = %d;\n" % uni))
    open(f"{pkg}/glyphs/{fname(name)}", "w").write(body)


# ── the three glyphs ──────────────────────────────────────────────────────
def build_style(pkg, ttf):
    f = TTFont(ttf)
    gs, cm, glyf = f.getGlyphSet(), f.getBestCmap(), f["glyf"]
    lid = layer_id(pkg)
    hmtx = f["hmtx"]

    need = "PbIl"
    if any(ord(c) not in cm for c in need):
        f.close()
        return []
    N = {c: cm[ord(c)] for c in need}

    cap = glyf[N["I"]].yMax
    xh = glyf[cm[ord("o")]].yMax if ord("o") in cm else glyf[N["b"]].yMax * 0.72
    slant = measure_slant(outline(gs, N["l"]), xh)

    made = []

    # ---- P's bowl -------------------------------------------------------
    P = outline(gs, N["P"])
    # heights that sit inside P's counter, where the stem stands alone
    p_stem = stem_edges(P, [cap * 0.60, cap * 0.68, cap * 0.75], slant)
    # the bowl's underside, read just right of the stem; the run that starts
    # at the baseline is the foot serif and is skipped
    runs = [r for r in spans(P, p_stem[1] + 4, p_stem[1] + 10, False, slant)
            if r[0] > cap * 0.12]
    if not (p_stem and runs):
        f.close()
        return []
    p_bowl_bottom = min(r[0] for r in runs)
    p_serif_top = max([r[1] for r in
                       spans(P, p_stem[1] + 4, p_stem[1] + 10, False, slant)
                       if r[0] <= cap * 0.12] or [0])
    y_floor = (p_serif_top + p_bowl_bottom) / 2.0
    Pbowl = bowl_of(P, p_stem[1], y_floor, slant)
    pb = bounds(Pbowl)

    # ---- Thorn: I's stem, P's bowl, hung at mid-height -------------------
    I = outline(gs, N["I"])
    i_stem = stem_edges(I, [cap * 0.45, cap * 0.55], slant)
    # Thorn's bowl is vertically centred on the cap, where P's sits at the top
    want_mid = cap * 0.495
    dy = want_mid - (pb[1] + pb[3]) / 2.0
    dx = i_stem[1] - p_stem[1]
    t = math.tan(math.radians(slant))
    joined = BooleanGlyph(I).union(
        BooleanGlyph(shifted(Pbowl, dx + dy * t, dy)))
    adv = hmtx[N["I"]][0] + (bounds(joined)[2] - bounds(I)[2])
    put(pkg, "Thorn", lid, nodes_of(joined), adv, 0x00DE)
    made.append("Thorn")

    # ---- thorn: l's stem taken below the baseline, b's own bowl ----------
    b = outline(gs, N["b"])
    b_stem = stem_edges(b, [xh * 0.50, xh * 0.62], slant)
    bruns = [r for r in spans(b, b_stem[1] + 4, b_stem[1] + 10, False, slant)]
    if bruns:
        b_low = min(r[0] for r in bruns)
        bbowl = bowl_of(b, b_stem[1], max(b_low - 6, -20), slant)
        l = outline(gs, N["l"])
        l_stem = stem_edges(l, [xh * 0.55, xh * 0.80], slant)
        desc = -round(cap * 0.255)
        # l has a foot serif because l stops at the baseline. A thorn's stem
        # carries on to the descender, so there is no foot for a serif to sit
        # on: cut it away and run the stem straight through. Leaving it gave
        # a stem that stepped out at the baseline and back in below it.
        serif_top = cap * 0.075
        body = BooleanGlyph(l).intersection(
            BooleanGlyph(region(-BIG, serif_top, BIG, BIG, slant)))
        tail = region(l_stem[0], desc, l_stem[1], serif_top + 8, slant)
        dxl = l_stem[1] - b_stem[1]
        stack = BooleanGlyph(body).union(BooleanGlyph(tail))
        stack = stack.union(BooleanGlyph(shifted(bbowl, dxl, 0)))
        advl = hmtx[N["l"]][0] + (bounds(stack)[2] - bounds(l)[2])
        put(pkg, "thorn", lid, nodes_of(stack), advl, 0x00FE)
        made.append("thorn")

    # ---- pilcrow: P's bowl, mirrored and filled, on two stems ----------
    # A pilcrow's bowl is solid -- it has no counter -- so only the outer
    # contour of P's bowl is taken. Mirrored, because the bowl hangs to the
    # LEFT of its stem, which also keeps the weight on the outside of the
    # curve where the design puts it rather than even all the way round.
    # Cutting at the stem's right edge opens the counter, so Pbowl is a
    # C -- correct for Thorn, where the stem closes it again. A pilcrow's
    # bowl is solid, so the cut is taken from P's OUTER contour alone, with
    # P's counter discarded before the knife goes in.
    P_solid = Shape()
    max(BooleanGlyph(P).contours, key=_area).draw(P_solid.rec)
    solid = BooleanGlyph(P_solid).intersection(
        BooleanGlyph(region(p_stem[1], y_floor, BIG, BIG, slant)))
    sb = round(hmtx[N["I"]][0] * 0.09)
    ob = bounds(solid)
    flip = mirrored(solid, (ob[0] + ob[2]) / 2.0)
    fb = bounds(flip)
    stem_w = p_stem[1] - p_stem[0]
    desc = -round(cap * 0.255)
    dy2 = cap - fb[3]
    dx2 = sb - fb[0]
    flip = shifted(flip, dx2 + dy2 * t, dy2)
    fb = bounds(flip)
    # the stem the bowl hangs from, then a bare one a bowl's-width away
    s1x = fb[2] - stem_w
    s2x = fb[2] + round(stem_w * 1.55)
    pil = BooleanGlyph(flip)
    pil = pil.union(BooleanGlyph(region(s1x, desc, fb[2], cap, slant)))
    pil = pil.union(BooleanGlyph(region(s2x, desc, s2x + stem_w, cap, slant)))
    put(pkg, "paragraph", lid, nodes_of(pil), bounds(pil)[2] + sb, 0x00B6)
    made.append("paragraph")

    print("  %-34s P stem %.0f-%.0f  bowl y %.0f-%.0f  slant %.1f  -> %s"
          % (os.path.basename(pkg), p_stem[0], p_stem[1], pb[1], pb[3],
             slant, ", ".join(made)))
    f.close()
    return made


def main(repo, built):
    for pkg in sorted(glob.glob(f"{repo}/sources/*.glyphspackage")):
        stem = os.path.basename(pkg).replace(".glyphspackage", "")
        style = stem.replace("CheltenhamClassic", "") or "Regular"
        ttf = f"{built}/CheltenhamClassic-{style}.ttf"
        if not os.path.exists(ttf):
            print(f"  skip {stem}")
            continue
        build_style(pkg, ttf)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
