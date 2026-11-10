#!/usr/bin/env python3
"""
Draw the nine combining marks that cannot be derived from existing glyphs.

Unlike derive_marks.py, which assembles marks from shapes the font already
contains, these are constructed. Nothing here is a fixed number: every
dimension is a ratio applied to values measured off each style's own built
TTF, so the Bold's accents carry the Bold's weight and contrast and the
italics' are sheared to the italics' own slant.

  gravecomb acutecomb         a tapered wedge, cut horizontally
  hungarumlautcomb            two of the above
  circumflexcomb caroncomb    a chevron, right arm heavier than the left
  tildecomb                   a stroked sine wave, thin at both ends
  brevecomb                   the band between two half-ellipses
  ringcomb                    the band between two ellipses
  ogonekcomb                  a stroked hook, below the baseline

This is construction, not revival: the marks are consistent with the
typeface's measurements but they are not drawn by its designer. Treat them as
a working default to refine in Glyphs, not as finished outlines.
"""
import glob, math, os, re, sys
from fontTools.ttLib import TTFont

GAP = 70          # letter top to accent bottom, matching derive_marks.py
K = 0.5522847498  # circle-to-cubic


# ── emitting ──────────────────────────────────────────────────────────────
def poly(pts):
    return "".join("(%d,%d,l),\n" % (round(x), round(y)) for x, y in pts)


def arc(cx, cy, rx, ry, a0, a1):
    """A quarter-ellipse as one cubic, given in degrees. Returns the two
    offcurves and the endpoint; the caller supplies the start."""
    s, e = math.radians(a0), math.radians(a1)
    x0, y0 = cx + rx * math.cos(s), cy + ry * math.sin(s)
    x1, y1 = cx + rx * math.cos(e), cy + ry * math.sin(e)
    # tangents, scaled by kappa and the sweep direction
    d = 1 if a1 > a0 else -1
    t0x, t0y = -rx * math.sin(s) * d, ry * math.cos(s) * d
    t1x, t1y = -rx * math.sin(e) * d, ry * math.cos(e) * d
    return [(x0 + t0x * K, y0 + t0y * K, "o"),
            (x1 - t1x * K, y1 - t1y * K, "o"),
            (x1, y1, "cs")]


def nodes(seq):
    return "".join("(%d,%d,%s),\n" % (round(x), round(y), t) for x, y, t in seq)


def shape(body):
    return "{\nclosed = 1;\nnodes = (\n%s);\n},\n" % body


def fname(name):
    return "".join(c + "_" if c.isupper() else c for c in name) + ".glyph"


def write(pkg, name, lid, shapes, uni, anchor="_top", width=0):
    anc = ("anchors = (\n{\nname = %s;\npos = (0,0);\n},\n);\n" % anchor) if anchor else ""
    s = ("{\nglyphname = %s;\nlayers = (\n{\n%slayerId = \"%s\";\nshapes = (\n%s"
         ");\nwidth = %d;\n}\n);\n%s}\n"
         % (name, anc, lid, "".join(shapes), width,
            "" if uni is None else "unicode = %d;\n" % uni))
    open(f"{pkg}/glyphs/{fname(name)}", "w").write(s)


def composite(pkg, name, lid, refs, uni, width):
    """refs: list of (glyphname, dx, dy)."""
    sh = "".join("{\npos = (%d,%d);\nref = %s;\n},\n" % (round(dx), round(dy), r)
                 for r, dx, dy in refs)
    s = ("{\nglyphname = %s;\nlayers = (\n{\nlayerId = \"%s\";\nshapes = (\n%s"
         ");\nwidth = %d;\n}\n);\n%s}\n"
         % (name, lid, sh, round(width), "" if uni is None else "unicode = %d;\n" % uni))
    open(f"{pkg}/glyphs/{fname(name)}", "w").write(s)


# The spacing (legacy) accents at their own codepoints. They are the combining
# mark re-centred inside a real advance width -- without a width they trip
# base_has_width, and without an outline they trip contour_count.
SPACING = {"gravecomb": ("grave", 0x0060), "acutecomb": ("acute", 0x00B4),
           "circumflexcomb": ("circumflex", 0x02C6), "caroncomb": ("caron", 0x02C7),
           "tildecomb": ("tilde", 0x02DC), "brevecomb": ("breve", 0x02D8),
           "ringcomb": ("ring", 0x02DA), "hungarumlautcomb": ("hungarumlaut", 0x02DD),
           "ogonekcomb": ("ogonek", 0x02DB), "dotaccentcomb": ("dotaccent", 0x02D9),
           "dieresiscomb": ("dieresis", 0x00A8), "macroncomb": ("macron", 0x00AF),
           "cedillacomb": ("cedilla", 0x00B8)}


def spacing_from(pkg, lid, comb, pts, sb):
    """Write the spacing twin of a combining mark whose points are `pts`."""
    if comb not in SPACING or not pts:
        return None
    name, uni = SPACING[comb]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    composite(pkg, name, lid, [(comb, sb - x0, 0)], uni, (x1 - x0) + 2 * sb)
    return name


# ── stroking a centreline, for the shapes that are not arcs ───────────────
def stroke(pts, widths, taper_start=False, taper_end=False):
    """Offset a sampled centreline by half of `widths` either side."""
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        px = pts[min(i + 1, n - 1)]; qx = pts[max(i - 1, 0)]
        dx, dy = px[0] - qx[0], px[1] - qx[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        h = widths[i] / 2.0
        left.append((x + nx * h, y + ny * h))
        right.append((x - nx * h, y - ny * h))
    ring = left + list(reversed(right))
    if taper_end:                      # collapse the far cap to a point
        # the tip has to sit between the two sides, not after them, or the
        # contour closes through it and the stroke reads as a filled blade
        ring = left[:-1] + [pts[-1]] + list(reversed(right[:-1]))
    if taper_start:
        ring = [pts[0]] + left[1:] + list(reversed(right[1:]))
    return ring


def sample(f, n):
    return [f(i / (n - 1.0)) for i in range(n)]


# ── measuring the design ──────────────────────────────────────────────────
def outline(f, name):
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    gs = f.getGlyphSet(); p = DecomposingRecordingPen(gs); gs[name].draw(p)
    cs, cur = [], []
    for op, a in p.value:
        if op == "moveTo": cur = [a[0]]
        elif op in ("lineTo",): cur.append(a[0])
        elif op in ("qCurveTo", "curveTo"): cur.extend(a)
        elif op == "closePath":
            if cur: cs.append(cur); cur = []
    return cs


def cross_x(cs, y):
    xs = []
    for c in cs:
        for i in range(len(c)):
            x1, y1 = c[i]; x2, y2 = c[(i + 1) % len(c)]
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (x2 - x1) * (y - y1) / (y2 - y1))
    return sorted(xs)


def cross_y(cs, x):
    ys = []
    for c in cs:
        for i in range(len(c)):
            x1, y1 = c[i]; x2, y2 = c[(i + 1) % len(c)]
            if (x1 <= x < x2) or (x2 <= x < x1):
                ys.append(y1 + (y2 - y1) * (x - x1) / (x2 - x1))
    return sorted(ys)


def measure(ttf):
    f = TTFont(ttf); cm = f.getBestCmap(); glyf = f["glyf"]
    xh = glyf[cm[0x78]].yMax
    o, n, l = outline(f, cm[0x6F]), outline(f, cm[0x6E]), outline(f, cm[0x6C])
    sp = cross_x(n, xh * 0.5); stem = sp[1] - sp[0]
    og = glyf[cm[0x6F]]; ox = (og.xMin + og.xMax) / 2
    ys = cross_y(o, ox); thin = ys[-1] - ys[-2]
    # slant, off the l's stem at two heights
    a = cross_x(l, xh * 0.25); b = cross_x(l, xh * 0.95)
    slant = math.degrees(math.atan2((b[0] - a[0]), (xh * 0.70))) if a and b else 0.0
    f.close()
    return dict(xh=xh, stem=stem, thin=thin, ow=og.xMax - og.xMin,
                asc=glyf[cm[0x62]].yMax, cap=glyf[cm[0x48]].yMax,
                slant=0.0 if abs(slant) < 1.5 else slant)


def shear(pts, deg, pivot):
    if not deg: return pts
    t = math.tan(math.radians(deg))
    return [(x + (y - pivot) * t, y) for x, y in pts]


def shear_n(seq, deg, pivot):
    if not deg: return seq
    t = math.tan(math.radians(deg))
    return [(x + (y - pivot) * t, y, k) for x, y, k in seq]


# ── the marks ─────────────────────────────────────────────────────────────
def build(m):
    xh, stem, thin, ow = m["xh"], m["stem"], m["thin"], m["ow"]
    sl, piv = m["slant"], GAP + 0.42 * xh / 2

    # Accent height follows the x-height, but the italic's x-height is 492
    # against the uprights' 421, which pushed its Agrave to 1018 -- past the
    # 1000 typoAscender, which is what typoascender_exceeds_Agrave catches.
    # Capped so a cap plus gap plus accent stays inside the ascender.
    h = min(0.42 * xh, 985 - m["cap"] - GAP)
    heavy = stem * 0.80           # an accent's thick part
    light = thin * 0.85           # its thin part
    y0, y1 = GAP, GAP + h
    out = {}

    # ── acute: a wedge rising left to right, cut horizontally top and bottom
    w = h * 0.60
    cosang = h / math.hypot(w, h)
    tb, tt = light / cosang, heavy / cosang
    acute = [(-w / 2 - tb / 2, y0), (-w / 2 + tb / 2, y0),
             (w / 2 + tt / 2, y1), (w / 2 - tt / 2, y1)]
    def put(name, uni, pts_list, shapes, anchor="_top"):
        out[name] = (uni, shapes, anchor,
                     [p for g in pts_list for p in g])

    put("acutecomb", 0x0301, [shear(acute, sl, piv)],
        [shape(poly(shear(acute, sl, piv)))])
    grave = [(-x, y) for x, y in acute][::-1]
    put("gravecomb", 0x0300, [shear(grave, sl, piv)], [shape(poly(shear(grave, sl, piv)))])

    # ── hungarumlaut: two of them, a touch narrower, parted by one width
    aw = (w + (tb + tt) / 2)
    sep = aw * 0.62
    for dx, key in ((-sep, 0), (sep, 1)):
        pass
    hl = [shape(poly(shear([(x + d, y) for x, y in acute], sl, piv)))
          for d in (-sep, sep)]
    put("hungarumlautcomb", 0x030B,
        [shear([(x + d, y) for x, y in acute], sl, piv) for d in (-sep, sep)], hl)

    # ── circumflex / caron: a chevron. The right arm is the heavier one,
    #    which is where the stress falls in a face with this contrast.
    W = h * 1.42
    vl, vr = light * 1.55, heavy * 1.45
    vd = (vl + vr) / 2 * 1.08
    circ = [(-W / 2, y0), (0, y1 - vd), (W / 2, y0),
            (W / 2, y0 + vr), (0, y1), (-W / 2, y0 + vl)]
    put("circumflexcomb", 0x0302, [shear(circ, sl, piv)], [shape(poly(shear(circ, sl, piv)))])
    car = [(x, y0 + y1 - y) for x, y in circ][::-1]
    put("caroncomb", 0x030C, [shear(car, sl, piv)], [shape(poly(shear(car, sl, piv)))])

    # ── tilde: a stroked sine, thin at both ends, heaviest through the middle
    # The amplitude has to beat the stroke weight or the wave reads as a bar.
    Wt, A = ow * 0.74, xh * 0.118
    mid = y0 + A + light * 0.85
    cen = sample(lambda t: (-Wt / 2 + Wt * t,
                            mid - A * math.sin(2 * math.pi * t)), 56)
    wid = [light * 0.85 + (heavy * 0.70 - light * 0.85)
           * math.sin(math.pi * (i / 55.0)) ** 0.55 for i in range(56)]
    tl_ = shear(stroke(cen, wid), sl, piv)
    put("tildecomb", 0x0303, [tl_], [shape(poly(tl_))])

    # ── breve: the band between two half-ellipses, so the bottom carries the
    #    weight and the tips come out thin without any taper maths
    rxo, ryo = h * 0.72, h * 0.86
    rxi, ryi = rxo - light * 1.05, ryo - heavy * 1.12
    cy = y0 + ryo
    br = [(-rxo, cy, "l")] + arc(0, cy, rxo, ryo, 180, 270) + arc(0, cy, rxo, ryo, 270, 360)
    br += [(rxi, cy, "l")] + arc(0, cy, rxi, ryi, 360, 270) + arc(0, cy, rxi, ryi, 270, 180)
    br += [(-rxo, cy, "l")]
    put("brevecomb", 0x0306, [[(-rxo, cy), (rxo, cy), (0, cy - ryo)]],
        [shape(nodes(shear_n(br[:-1], sl, piv)))])

    # ── ring: the band between two ellipses, stressed like the o
    R = xh * 0.225
    side, top = stem * 0.58, thin * 0.74
    cy = y0 + R
    o_ = [(R, cy, "c")] + arc(0, cy, R, R, 0, 90) + arc(0, cy, R, R, 90, 180) \
         + arc(0, cy, R, R, 180, 270) + arc(0, cy, R, R, 270, 360)
    ri, rj = R - side, R - top
    i_ = [(ri, cy, "c")] + arc(0, cy, ri, rj, 0, -90) + arc(0, cy, ri, rj, -90, -180) \
         + arc(0, cy, ri, rj, -180, -270) + arc(0, cy, ri, rj, -270, -360)
    put("ringcomb", 0x030A, [[(-R, cy), (R, cy), (0, cy - R), (0, cy + R)]],
        [shape(nodes(shear_n(o_[:-1], sl, piv))),
         shape(nodes(shear_n(i_[:-1], sl, piv)))])

    # ── ogonek: a hook below the baseline, thin where it leaves the letter
    hg, wg = xh * 0.54, ow * 0.34

    def og(t):
        # One open cubic, under 180 degrees of sweep. Anything more and the
        # stroke's two ends meet and the mark closes into a teardrop.
        a, b, c, d = (0.80, 0.00), (0.93, -0.44), (0.70, -0.94), (0.10, -0.90)
        v = 1 - t
        x = v**3*a[0] + 3*v*v*t*b[0] + 3*v*t*t*c[0] + t**3*d[0]
        y = v**3*a[1] + 3*v*v*t*b[1] + 3*v*t*t*c[1] + t**3*d[1]
        # Bite into the letter rather than meeting it. The composite hangs
        # this from the base's lowest point, so starting the centreline at
        # the anchor left the ogonek overlapping `a` by two units -- it read
        # as detached, with white between.
        return (x * wg - wg * 0.45, y * hg + thin * 0.95)

    cen = sample(og, 40)
    # thin where it leaves the letter, weight through the bend, a fine tip
    wid = [light * 0.50 + (heavy * 0.52 - light * 0.50)
           * math.sin(math.pi * (i / 39.0) ** 0.85) ** 0.75 for i in range(40)]
    ogp = stroke(cen, wid, taper_end=True)
    put("ogonekcomb", 0x0328, [ogp], [shape(poly(ogp))], "_bottom")

    # ── the Czech/Slovak caron, as its own shape ──────────────────────────
    # d, l and t have no room overhead, so these four letters take an upright
    # mark at the shoulder instead. FontBakery rejects quoteright, quotesingle,
    # comma and the chevron here on purpose: the convention exists precisely
    # because the mark should NOT read as an apostrophe. So it is drawn --
    # a straight tapered wedge, wider at the top, with no comma's curve.
    ct, cb = heavy * 0.98, light * 0.80
    cy0, cy1 = xh * 1.10, m["asc"] * 1.02
    alt = [(-cb / 2, cy0), (cb / 2, cy0), (ct / 2, cy1), (-ct / 2, cy1)]
    put("caroncomb.alt", None, [shear(alt, sl, (cy0 + cy1) / 2)],
        [shape(poly(shear(alt, sl, (cy0 + cy1) / 2)))])
    return out


def main(repo, built):
    for pkg in sorted(glob.glob(f"{repo}/sources/*.glyphspackage")):
        stem_ = os.path.basename(pkg).replace(".glyphspackage", "")
        style = stem_.replace("LibreCheltenham", "") or "Regular"
        ttf = f"{built}/LibreCheltenham-{style}.ttf"
        if not os.path.exists(ttf):
            print(f"  skip {stem_}"); continue
        m = measure(ttf)
        lid = re.search(r'id = "([^"]+)";', open(f"{pkg}/fontinfo.plist").read()).group(1)
        made = build(m)
        sb = int(m["ow"] * 0.11)
        extra = []
        for name, (uni, shapes, anchor, pts) in made.items():
            write(pkg, name, lid, shapes, uni, anchor)
            got = spacing_from(pkg, lid, name, pts, sb)
            if got: extra.append(got)

        # d, l, t and cap L take the upright caron at the shoulder.
        f = TTFont(ttf, lazy=True); cm = f.getBestCmap(); glyf = f["glyf"]; hmtx = f["hmtx"]
        ap = made["caroncomb.alt"][3]
        aw = max(p[0] for p in ap) - min(p[0] for p in ap)
        for base, uni, nm in (("d", 0x010F, "dcaron"), ("t", 0x0165, "tcaron"),
                              ("l", 0x013E, "lcaron"), ("L", 0x013D, "Lcaron")):
            bn = cm.get(ord(base))
            if not (bn and os.path.exists(f"{pkg}/glyphs/{fname(nm)}")):
                continue
            bg = glyf[bn]
            dx = bg.xMax + m["ow"] * 0.07 - min(p[0] for p in ap)
            rsb = max(hmtx[bn][0] - bg.xMax, m["ow"] * 0.07)
            composite(pkg, nm, lid, [(base, 0, 0), ("caroncomb.alt", dx, 0)],
                      uni, dx + aw + rsb)
            extra.append(nm)
        f.close()

        order = f"{pkg}/order.plist"
        if os.path.exists(order):
            txt = open(order).read()
            if "caroncomb.alt" not in txt:
                txt = txt.rstrip().rstrip(")").rstrip() + ",\ncaroncomb.alt\n)\n"
                open(order, "w").write(txt)

        print(f"  {stem_:34} 9 marks + {len(extra)} spacing/alt  "
              f"(stem {m['stem']:.0f}, thin {m['thin']:.0f}, slant {m['slant']:.1f}deg)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
