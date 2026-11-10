#!/usr/bin/env python3
"""
Fill the rest of the Google Fonts Latin Core set from shapes already in the
font, plus a few constructed strokes measured off the design.

Run after derive_marks.py and draw_marks.py, from a built directory:

    python3 scripts/latin_core.py . build-dir

What it makes, and from what:

  dotlessi dotlessj     i and j with the dot contour removed, and every
                        accented i/j recomposed onto them -- the scaffold had
                        stacked accents on the dotted forms, so a dieresis on
                        an i produced three dots
  Tcommaaccent etc.     T and t over the existing commaaccentcomb
  Dcroat Eth Hbar       base letter plus a crossbar at the measured thin weight
  Lslash Oslash         base letter plus a diagonal at the same weight
  cent yen              c and Y with the same strokes through them
  guillemets            chevrons, built to the design's own stroke weight
  ordfeminine etc.      a, o, T, M, C, R reduced -- these characters are
                        literally smaller letters, so reduction is the
                        construction, not a shortcut around one
  (repair)              any glyph carrying a layer id that is not its
                        master's. glyphsLib silently drops those, which is why
                        the Italic shipped with no semicolon: the outlines
                        were drawn all along, under another master's id

Not here, because they are real drawing: AE, OE, eszett, thorn, eth lowercase,
section and pilcrow. See src/DRAWING.md.
"""
import glob, math, os, re, sys
from fontTools.ttLib import TTFont

# ── source .glyph plumbing ────────────────────────────────────────────────
def fname(n):
    return "".join(c + "_" if c.isupper() else c for c in n) + ".glyph"


def layer_id(pkg):
    return re.search(r'id = "([^"]+)";', open(f"{pkg}/fontinfo.plist").read()).group(1)


def contours(pkg, glyphname):
    """The raw text of each closed contour in a source glyph, with its bbox."""
    p = f"{pkg}/glyphs/{fname(glyphname)}"
    if not os.path.exists(p):
        return []
    txt = open(p).read()
    out = []
    # the last contour in a shapes list has no trailing comma, so it must be
    # optional here -- requiring it silently returned only the first contour
    for m in re.finditer(r"\{\nclosed = 1;\nnodes = \(\n(.*?)\n\);\n\},?", txt, re.S):
        pts = [(int(a), int(b)) for a, b, _ in
               re.findall(r"\((-?\d+),(-?\d+),(\w+)\)", m.group(1))]
        if pts:
            out.append((m.group(0), min(p[1] for p in pts), max(p[1] for p in pts),
                        min(p[0] for p in pts), max(p[0] for p in pts)))
    return out


def width_of(pkg, glyphname):
    p = f"{pkg}/glyphs/{fname(glyphname)}"
    m = re.search(r"width = (\d+);", open(p).read()) if os.path.exists(p) else None
    return int(m.group(1)) if m else 0


def put_outline(pkg, name, lid, shapes_text, width, uni):
    body = ("{\nglyphname = %s;\nlayers = (\n{\nlayerId = \"%s\";\nshapes = (\n%s\n);\n"
            "width = %d;\n}\n);\n%s}\n"
            % (name, lid, "\n".join(shapes_text), width,
               "" if uni is None else "unicode = %d;\n" % uni))
    open(f"{pkg}/glyphs/{fname(name)}", "w").write(body)


def put_composite(pkg, name, lid, refs, width, uni):
    sh = "".join("{\n%spos = (%d,%d);\nref = %s;\n},\n"
                 % (("scale = (%.4f,%.4f);\n" % sc) if sc else "", round(dx), round(dy), r)
                 for r, dx, dy, sc in refs)
    body = ("{\nglyphname = %s;\nlayers = (\n{\nlayerId = \"%s\";\nshapes = (\n%s);\n"
            "width = %d;\n}\n);\n%s}\n"
            % (name, lid, sh, round(width), "" if uni is None else "unicode = %d;\n" % uni))
    open(f"{pkg}/glyphs/{fname(name)}", "w").write(body)


def bar(x0, y0, x1, y1):
    """A filled rectangle as a source contour, counterclockwise."""
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return "{\nclosed = 1;\nnodes = (\n%s\n);\n}," % ",\n".join(
        "(%d,%d,l)" % (round(x), round(y)) for x, y in pts)


def quad(pts):
    return "{\nclosed = 1;\nnodes = (\n%s\n);\n}," % ",\n".join(
        "(%d,%d,l)" % (round(x), round(y)) for x, y in pts)


K = 0.5522847498
BELOW = ("cedillacomb", "ogonekcomb", "commaaccentcomb")


def ellipse(cx, cy, rx, ry, cw=False):
    """A full ellipse as four cubics, in source-node text."""
    seq, ang = [], [0, -90, -180, -270, -360] if cw else [0, 90, 180, 270, 360]
    seq.append((cx + rx, cy, "c"))
    for a0, a1 in zip(ang, ang[1:]):
        s, e = math.radians(a0), math.radians(a1)
        d = 1 if a1 > a0 else -1
        x0, y0 = cx + rx * math.cos(s), cy + ry * math.sin(s)
        x1, y1 = cx + rx * math.cos(e), cy + ry * math.sin(e)
        t0 = (-rx * math.sin(s) * d, ry * math.cos(s) * d)
        t1 = (-rx * math.sin(e) * d, ry * math.cos(e) * d)
        seq += [(x0 + t0[0] * K, y0 + t0[1] * K, "o"),
                (x1 - t1[0] * K, y1 - t1[1] * K, "o"), (x1, y1, "cs")]
    seq = seq[:-1]
    return "{\nclosed = 1;\nnodes = (\n%s\n);\n}," % ",\n".join(
        "(%d,%d,%s)" % (round(x), round(y), t) for x, y, t in seq)


def diagonal(x0, y0, x1, y1, w):
    """A stroke from one point to another, cut square at both ends."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    return quad([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                 (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)])


def chevron(cx, cy, h, w, t, left=True):
    """A guillemet arm: a V on its side."""
    s = -1 if left else 1
    tip, back = cx - s * w / 2, cx + s * w / 2
    return quad([(tip, cy), (back, cy + h / 2), (back - s * t * 1.5, cy + h / 2),
                 (tip + s * t * 1.15, cy), (back - s * t * 1.5, cy - h / 2),
                 (back, cy - h / 2)])


def half_arc(cx, cy, rx, ry, a0, a1):
    """One quarter-ellipse as a cubic, as (x,y,type) nodes after the start."""
    s_, e_ = math.radians(a0), math.radians(a1)
    d = 1 if a1 > a0 else -1
    x0, y0 = cx + rx * math.cos(s_), cy + ry * math.sin(s_)
    x1, y1 = cx + rx * math.cos(e_), cy + ry * math.sin(e_)
    t0 = (-rx * math.sin(s_) * d, ry * math.cos(s_) * d)
    t1 = (-rx * math.sin(e_) * d, ry * math.cos(e_) * d)
    return [(x0 + t0[0] * K, y0 + t0[1] * K, "o"),
            (x1 - t1[0] * K, y1 - t1[1] * K, "o"), (x1, y1, "cs")]


def nodes_text(seq):
    return "{\nclosed = 1;\nnodes = (\n%s\n);\n}," % ",\n".join(
        "(%d,%d,%s)" % (round(x), round(y), t) for x, y, t in seq)


def dbowl(x, x_in, y0, y1, reach, w_side, w_horiz):
    """The bowl of a thorn: a solid D springing rightward from a stem, with
    its counter punched as a separate contour. Returns both.

    Tracing outer-then-inner as ONE contour does not work here: the two
    ellipses need different centres (the counter must stop at the stem's
    right edge, `x_in`, or it eats a hole through the stem) and ellipses with
    different centres and aspect ratios diverge instead of staying parallel.
    The bowl came out a wedge -- thick at the stem, thin at the outside,
    which is backwards. As two contours each one can be sized on its own.
    """
    # Counter-clockwise, matching bar() and the font's own outer contours.
    # Traced the other way it subtracts, and the bowl cut a slot out of the
    # stem instead of joining it.
    cy, ry = (y0 + y1) / 2.0, (y1 - y0) / 2.0
    solid = [(x, cy - ry, "l")]
    solid += half_arc(x, cy, reach, ry, -90, 0) + half_arc(x, cy, reach, ry, 0, 90)
    outer = nodes_text(solid)

    x_right = (x + reach) - w_side
    rxi = (x_right - x_in) / 2.0
    ryi = ry - w_horiz
    counter = ellipse(x_in + rxi, cy, rxi, ryi, cw=True)
    return outer + "\n" + counter


def disc(x, y0, y1, reach, left=False):
    """A solid half-disc springing from a stem at x. The pilcrow's bowl."""
    cy, ry = (y0 + y1) / 2.0, (y1 - y0) / 2.0
    seq = [(x, cy + ry, "l")]
    if left:
        seq += half_arc(x, cy, reach, ry, 90, 180) + half_arc(x, cy, reach, ry, 180, 270)
    else:
        seq += half_arc(x, cy, reach, ry, 90, 0) + half_arc(x, cy, reach, ry, 0, -90)
    return nodes_text(seq)


def measure(ttf):
    f = TTFont(ttf); cm = f.getBestCmap(); g = f["glyf"]; hm = f["hmtx"]
    m = dict(xh=g[cm[0x78]].yMax, cap=g[cm[0x48]].yMax, asc=g[cm[0x62]].yMax,
             ow=g[cm[0x6F]].xMax - g[cm[0x6F]].xMin)
    # measured, not estimated: the n's left stem at mid x-height, and the
    # o's bowl at its horizontal centre
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    def outline(n):
        gs = f.getGlyphSet(); pen = DecomposingRecordingPen(gs); gs[n].draw(pen)
        cs, cur = [], []
        for op, a in pen.value:
            if op == "moveTo": cur = [a[0]]
            elif op == "lineTo": cur.append(a[0])
            elif op in ("qCurveTo", "curveTo"): cur.extend(a)
            elif op == "closePath":
                if cur: cs.append(cur); cur = []
        return cs
    def hits(cs, v, horiz=True):
        out = []
        for c in cs:
            for i in range(len(c)):
                a, b = c[i], c[(i + 1) % len(c)]
                p, q = (a[1], b[1]) if horiz else (a[0], b[0])
                if (p <= v < q) or (q <= v < p):
                    t = (v - p) / (q - p)
                    out.append((a[0] + (b[0] - a[0]) * t) if horiz
                               else (a[1] + (b[1] - a[1]) * t))
        return sorted(out)
    nn = hits(outline(cm[0x6E]), m["xh"] * 0.5)
    m["stem"] = int(nn[1] - nn[0]) if len(nn) >= 2 else 90
    og = g[cm[0x6F]]
    oo = hits(outline(cm[0x6F]), (og.xMin + og.xMax) / 2, horiz=False)
    m["thin"] = int(oo[-1] - oo[-2]) if len(oo) >= 2 else int(m["stem"] * 0.5)
    a = hits(outline(cm[0x6C]), m["xh"] * 0.25)
    b = hits(outline(cm[0x6C]), m["xh"] * 0.95)
    sl = math.degrees(math.atan2(b[0] - a[0], m["xh"] * 0.70)) if a and b else 0.0
    m["slant"] = 0.0 if abs(sl) < 1.5 else sl
    m["stemx"] = {}
    for ch, yy in (("I", m["cap"] * 0.5), ("l", m["xh"] * 0.5)):
        h_ = hits(outline(cm[ord(ch)]), yy)
        if len(h_) >= 2:
            m["stemx"][ch] = (h_[0], h_[1])
    m["box"] = {chr(u): (g[n].xMin, g[n].yMin, g[n].xMax, g[n].yMax, hm[n][0])
                for u, n in cm.items() if 0x20 < u < 0x7F}
    f.close()
    return m


def put_mixed(pkg, name, lid, shapes, width, uni):
    """shapes: contour text, or ('ref', glyphname, dx, dy, scale|None)."""
    out = []
    for s in shapes:
        if isinstance(s, tuple):
            _, r, dx, dy, sc = s
            out.append("{\n%spos = (%d,%d);\nref = %s;\n}," %
                       (("scale = (%.4f,%.4f);\n" % sc) if sc else "", round(dx), round(dy), r))
        else:
            out.append(s)
    put_outline(pkg, name, lid, out, width, uni)


ABOVE_MARKS = ("gravecomb acutecomb circumflexcomb tildecomb macroncomb "
               "brevecomb dotaccentcomb dieresiscomb ringcomb "
               "hungarumlautcomb caroncomb")


def add_ccmp(pkg):
    """A soft-dotted i or j must lose its dot when a mark is stacked on it.

    Precomposed iacute already uses dotlessi, but a decomposed i + U+0301
    sequence has nothing to tell the renderer, so the dot stays and collides
    with the accent. This is the font's first GSUB feature -- the sources
    carried only an empty FontLab stub declaring zero lookups.
    """
    fi = f"{pkg}/fontinfo.plist"
    t = open(fi).read()
    # Rewrite rather than skip. Bailing out when a ccmp block already existed
    # meant later edits to these rules silently never reached the font.
    had = "tag = ccmp;" in t
    t = re.sub(r"features = \(\n\{\ncode = \".*?\";\ntag = ccmp;\n\}\n\);\n", "", t, flags=re.S)
    # just the rules: Glyphs wraps them in feature/endfeature from `tag`,
    # and nesting a feature block inside one is a syntax error
    # A mark below may sit between the letter and the accent above
    # (Lithuanian i-ogonek-grave), so that case needs its own rule.
    below = "cedillacomb ogonekcomb commaaccentcomb"
    # Precomposed iogonek keeps its dot under an accent too, and that cannot
    # be fixed by swapping one glyph for another -- there is no dotless i
    # with an ogonek. It is decomposed instead, in that context only.
    code = ("lookup ccmp_iog {\n"
            "sub iogonek by dotlessi ogonekcomb;\n"
            "} ccmp_iog;\n"
            "sub iogonek' lookup ccmp_iog [%s];\n"
            "sub i' [%s] [%s] by dotlessi;\n"
            "sub j' [%s] [%s] by dotlessj;\n"
            "sub i' [%s] by dotlessi;\n"
            "sub j' [%s] by dotlessj;"
            % (ABOVE_MARKS, below, ABOVE_MARKS, below, ABOVE_MARKS,
               ABOVE_MARKS, ABOVE_MARKS))
    block = 'features = (\n{\ncode = "%s";\ntag = ccmp;\n}\n);\n' % code
    t = re.sub(r"(featurePrefixes = \(.*?\n\);\n)", lambda m: m.group(1) + block, t,
               count=1, flags=re.S)
    open(fi, "w").write(t)
    return not had


def repair_layers(pkg, lid):
    """A glyph whose layerId is not this master's is dropped on build, without
    a warning. The Italic's semicolon was lost that way."""
    fixed = []
    for gp in sorted(glob.glob(f"{pkg}/glyphs/*.glyph")):
        txt = open(gp).read()
        ids = re.findall(r'layerId = "([^"]+)";', txt)
        if not ids or all(i == lid for i in ids):
            continue
        new = re.sub(r'layerId = "[^"]+";', 'layerId = "%s";' % lid, txt)
        new = re.sub(r"\nname = \w+;", "", new)   # the stale master name with it
        open(gp, "w").write(new)
        fixed.append(os.path.basename(gp)[:-6])
    return fixed


def build(pkg, lid, m, style):
    B, stem, thin = m["box"], m["stem"], m["thin"], 
    xh, cap, asc, ow = m["xh"], m["cap"], m["asc"], m["ow"]
    made = []

    def R(g, dx=0, dy=0, sc=None): return ("ref", g, dx, dy, sc)

    # ── dotless i and j, and every accent that belongs on them ────────────
    # The scaffold stacked accents on the dotted forms, so a dieresis on an i
    # gave three dots. Swapping the base is only half the fix: the mark's y
    # was measured to the dot's top, so it has to come down to the new one.
    dotless_top = {}
    for base, dot, uni in (("i", "dotlessi", 0x0131), ("j", "dotlessj", 0x0237)):
        cs = contours(pkg, base)
        if not cs:
            continue
        keep = [c for c in cs if c[1] < xh * 1.02]           # drop the dot
        if len(keep) == len(cs):
            continue
        put_outline(pkg, dot, lid, [c[0] for c in keep], width_of(pkg, base), uni)
        dotless_top[base] = max(c[2] for c in keep)
        made.append(dot)

    for gp in sorted(glob.glob(f"{pkg}/glyphs/*.glyph")):
        txt = open(gp).read()
        refs = re.findall(r"ref = ([\w.]+);", txt)
        if not refs:
            continue
        base = refs[0][7:] if refs[0].startswith("dotless") else refs[0]
        if base not in dotless_top or not any(r.endswith("comb") for r in refs[1:]):
            continue
        if all(r in BELOW for r in refs[1:]):                # ogonek keeps the dot
            continue
        new = txt.replace("ref = %s;" % refs[0], "ref = dotless%s;" % base, 1)
        # re-seat every above-mark on the dotless letter's own top
        def reseat(mo):
            return ("{\npos = (%s,%d);\nref = %s;\n}"
                    % (mo.group(1), dotless_top[base], mo.group(3))
                    if mo.group(3) not in BELOW else mo.group(0))
        new = re.sub(r"\{\npos = \((-?\d+),(-?\d+)\);\nref = ([\w.]+comb);\n\}",
                     reseat, new)
        if new != txt:
            open(gp, "w").write(new)
            made.append("~" + os.path.basename(gp)[:-6])

    # ── T and t with comma below: the mark already exists ─────────────────
    for base, name, uni in (("T", "Tcommaaccent", 0x021A), ("t", "tcommaaccent", 0x021B)):
        if base not in B:
            continue
        x0, y0, x1, y1, w = B[base]
        put_mixed(pkg, name, lid, [R(base), R("commaaccentcomb", (x0 + x1) / 2, min(0, y0))],
                  w, uni)
        made.append(name)

    # ── strokes through existing letters ──────────────────────────────────
    t = thin * 1.06
    over = ow * 0.052
    # On a slanted letter the bbox's extremes are at opposite corners, so an
    # x taken from it is wrong by this much at height y.
    tan = math.tan(math.radians(m["slant"]))
    def lean(y): return tan * y
    def hbarat(base, y, left, span, extra=0.0):
        x0, y0, x1, y1, w = B[base]
        a = ((x0 - over) if left else (x1 - span + extra)) + lean(y)
        return bar(a, y - t / 2, a + span, y + t / 2)

    # Capital eth is a D with a crossbar and would be free here, but its
    # lowercase is a wholly different curved form that cannot be constructed.
    # Shipping one half of a case pair breaks case_mapping, which was passing,
    # so Eth waits for eth. See src/DRAWING.md.
    specs = []
    if "D" in B:
        specs += [("Dcroat", 0x0110, "D")]
    for nm, uni, base in specs:
        x0, y0, x1, y1, w = B[base]
        put_mixed(pkg, nm, lid, [R(base), hbarat(base, cap * 0.50, True, stem * 2.0 + over)],
                  w, uni); made.append(nm)
    if "d" in B:
        x0, y0, x1, y1, w = B["d"]
        put_mixed(pkg, "dcroat", lid,
                  [R("d"), bar(x1 - stem * 2.1 + lean(asc * 0.80), asc * 0.80 - t / 2,
                               x1 + over + lean(asc * 0.80), asc * 0.80 + t / 2)],
                  w, 0x0111); made.append("dcroat")
    if "H" in B:
        x0, y0, x1, y1, w = B["H"]
        put_mixed(pkg, "Hbar", lid,
                  [R("H"), bar(x0 - over + lean(cap * 0.80), cap * 0.80 - t / 2,
                               x1 + over + lean(cap * 0.80), cap * 0.80 + t / 2)],
                  w, 0x0126); made.append("Hbar")
    if "h" in B:
        x0, y0, x1, y1, w = B["h"]
        put_mixed(pkg, "hbar", lid,
                  [R("h"), bar(x0 - over + lean(asc * 0.80), asc * 0.80 - t / 2,
                               x0 + stem * 2.1 + lean(asc * 0.80), asc * 0.80 + t / 2)],
                  w, 0x0127); made.append("hbar")
    # The slash has to clear the stem on both sides to read, and it sits
    # shallower than a solidus -- nearer 45 degrees than vertical.
    for base, nm, uni, lo, hi in (("L", "Lslash", 0x0141, 0.30, 0.54),
                                  ("l", "lslash", 0x0142, 0.42, 0.66)):
        if base not in B: continue
        x0, y0, x1, y1, w = B[base]
        cx = x0 + stem / 2 if base == "L" else (x0 + x1) / 2
        r_ = ow * 0.175
        put_mixed(pkg, nm, lid,
                  [R(base), diagonal(cx - r_ + lean(y1 * lo), y1 * lo,
                                    cx + r_ + lean(y1 * hi), y1 * hi, t)],
                  w, uni); made.append(nm)
    for base, nm, uni in (("O", "Oslash", 0x00D8), ("o", "oslash", 0x00F8)):
        if base not in B: continue
        x0, y0, x1, y1, w = B[base]
        p = (y1 - y0) * 0.07
        put_mixed(pkg, nm, lid,
                  [R(base), diagonal(x0 - over * 0.7 + lean(y0), y0 - p,
                                    x1 + over * 0.7 + lean(y1) * 0.55, y1 + p, t * 1.05)],
                  w, uni); made.append(nm)

    # ── currency ──────────────────────────────────────────────────────────
    if "c" in B:
        x0, y0, x1, y1, w = B["c"]
        put_mixed(pkg, "cent", lid,
                  [R("c"), diagonal((x0 + x1) / 2 + lean(y0) * 0.5, y0 - xh * 0.17,
                                    (x0 + x1) / 2 + lean(y1) * 0.9, y1 + xh * 0.17, t)], w, 0x00A2)
        made.append("cent")
    if "Y" in B:
        x0, y0, x1, y1, w = B["Y"]
        cx = (x0 + x1) / 2
        put_mixed(pkg, "yen", lid,
                  [R("Y"), bar(cx - ow * 0.335 + lean(cap * 0.250), cap * 0.250 - t / 2,
                               cx + ow * 0.335 + lean(cap * 0.250), cap * 0.250 + t / 2),
                           bar(cx - ow * 0.335 + lean(cap * 0.400), cap * 0.400 - t / 2,
                               cx + ow * 0.335 + lean(cap * 0.400), cap * 0.400 + t / 2)],
                  w, 0x00A5); made.append("yen")

    # ── guillemets ────────────────────────────────────────────────────────
    gh, gw, gt, gy = xh * 0.56, xh * 0.30, thin * 1.12, xh * 0.42
    sb = int(ow * 0.13)
    for nm, uni, left in (("guilsinglleft", 0x2039, False), ("guilsinglright", 0x203A, True)):
        put_mixed(pkg, nm, lid, [chevron(sb + gw / 2, gy, gh, gw, gt, left)],
                  int(gw + 2 * sb), uni); made.append(nm)
    for nm, uni, left in (("guillemetleft", 0x00AB, False), ("guillemetright", 0x00BB, True)):
        d = gw * 0.92
        put_mixed(pkg, nm, lid,
                  [chevron(sb + gw / 2, gy, gh, gw, gt, left),
                   chevron(sb + gw / 2 + d, gy, gh, gw, gt, left)],
                  int(gw + d + 2 * sb), uni); made.append(nm)

    # ── characters that are literally smaller letters ─────────────────────
    for base, nm, uni, sc, top in (("a", "ordfeminine", 0x00AA, 0.60, 0.98),
                                   ("o", "ordmasculine", 0x00BA, 0.60, 0.98)):
        if base not in B: continue
        x0, y0, x1, y1, w = B[base]
        dy = cap * top - y1 * sc
        put_mixed(pkg, nm, lid, [R(base, -x0 * sc + sb * 0.6, dy, (sc, sc))],
                  int((x1 - x0) * sc + sb * 1.2), uni); made.append(nm)
    if "T" in B and "M" in B:
        sc = 0.40
        tx0, _, tx1, ty1, tw = B["T"]; mx0, _, mx1, my1, mw = B["M"]
        gap = ow * 0.03
        put_mixed(pkg, "trademark", lid,
                  [R("T", -tx0 * sc + sb * 0.4, cap * 0.98 - ty1 * sc, (sc, sc)),
                   R("M", -mx0 * sc + sb * 0.4 + (tx1 - tx0) * sc + gap,
                     cap * 0.98 - my1 * sc, (sc, sc))],
                  int(((tx1 - tx0) + (mx1 - mx0)) * sc + gap + sb * 0.8), 0x2122)
        made.append("trademark")
    for base, nm, uni in (("C", "copyright", 0x00A9), ("R", "registered", 0x00AE)):
        if base not in B: continue
        x0, y0, x1, y1, w = B[base]
        rad = cap * 0.375
        cy, cx = cap * 0.50, sb + rad
        sc = (rad * 2 - thin * 3.4) / max(x1 - x0, y1 - y0)
        put_mixed(pkg, nm, lid,
                  [ellipse(cx, cy, rad, rad),
                   ellipse(cx, cy, rad - thin * 0.92, rad - thin * 0.92, cw=True),
                   R(base, cx - (x0 + x1) / 2 * sc, cy - (y0 + y1) / 2 * sc, (sc, sc))],
                  int(rad * 2 + sb * 2), uni); made.append(nm)

    # ── ligatures: two letters sharing a stroke ───────────────────────────
    # fontmake unions overlapping contours, so setting the second letter so
    # its left edge lands on the first's right stem produces the join. This
    # is the real construction of these four characters, not a trick around
    # one -- but a designer would still want to even out the shared stroke.
    for a_, b_, nm, uni, shrink in (("A", "E", "AE", 0x00C6, 0.96),
                                    ("a", "e", "ae", 0x00E6, 1.0),
                                    ("O", "E", "OE", 0x0152, 1.0),
                                    ("o", "e", "oe", 0x0153, 1.0)):
        if a_ not in B or b_ not in B:
            continue
        ax0, _, ax1, _, aw = B[a_]
        bx0, _, bx1, _, bw = B[b_]
        # The A's right leg is a diagonal and the E's stem is vertical, so
        # they can only truly meet at one height. Overlapping by more than a
        # stem puts that meeting near the middle of the E rather than at its
        # foot, which is where the eye looks for the join.
        join = stem * 2.15 if a_ == "A" else (stem * 1.25 if a_ == "O" else thin * 1.15)
        dx = (ax1 - join) - bx0
        put_mixed(pkg, nm, lid, [R(a_), R(b_, dx, 0)],
                  int(aw + (bw - bx0) - join + (bx0 - 0)), uni)
        made.append(nm)

    # ── lowercase eth: the o's bowl, with a stroked ascender over it ──────
    if "o" in B and "d" in B:
        ox0, oy0, ox1, oy1, owd = B["o"]
        top = asc * 0.96
        x_a, y_a = ox1 - thin * 0.9, oy1 - thin * 0.4
        x_b, y_b = ox0 + (ox1 - ox0) * 0.42, top
        # the bar crosses the ascender, so it is placed ON the stroke at a
        # fraction of its run -- not at an absolute height, which put it
        # floating above the tip
        f_ = 0.68
        bx = x_a + (x_b - x_a) * f_
        by = y_a + (y_b - y_a) * f_
        put_mixed(pkg, "eth", lid,
                  [R("o"), diagonal(x_a, y_a, x_b, y_b, thin * 1.15),
                   diagonal(bx - ow * 0.115, by - thin * 0.30,
                            bx + ow * 0.115, by + thin * 0.30, thin * 0.95)],
                  owd, 0x00F0); made.append("eth")
        # with its lowercase in hand the capital is just a D with a crossbar
        dx0, dy0, dx1, dy1, dw = B["D"]
        put_mixed(pkg, "Eth", lid,
                  [R("D"), hbarat("D", cap * 0.50, True, stem * 2.0 + over)], dw, 0x00D0)
        made.append("Eth")

    # ── section: the S is already a double curve; two of them make this ──
    if "S" in B:
        sx0, sy0, sx1, sy1, sw = B["S"]
        sc = 0.56
        h = (sy1 - sy0) * sc
        put_mixed(pkg, "section", lid,
                  [R("S", -sx0 * sc + sb * 0.5, cap * 0.96 - sy1 * sc, (sc, sc)),
                   R("S", -sx0 * sc + sb * 0.5, cap * 0.96 - sy1 * sc - h * 0.62, (sc, sc))],
                  int((sx1 - sx0) * sc + sb), 0x00A7); made.append("section")
    desc = -cap * 0.255

    # ── dotted circle ────────────────────────────────────────────────────
    # U+25CC is what a renderer shows when a combining mark arrives with no
    # base. A font carrying 14 marks should be able to draw it. Twelve of the
    # font's own periods on a ring, so it matches the dots in the dieresis.
    if "period" in [chr(0x2E)] or True:
        pg = B.get(".")
        if pg:
            p0, p1 = pg[0], pg[2]
            pw_ = p1 - p0
            rad = xh * 0.42
            cy_d = xh * 0.52
            dots = []
            for k in range(12):
                a_ = math.radians(90 - k * 30)
                dots.append(("ref", "period",
                             rad * math.cos(a_) - (p0 + pw_ / 2) + sb + rad,
                             cy_d + rad * math.sin(a_) - (pg[1] + pg[3]) / 2, None))
            # It needs top/bottom anchors or the marks have nothing to
            # attach to, and dotted_circle turns from a WARN into a FAIL.
            sh = "".join("{\npos = (%d,%d);\nref = period;\n},\n"
                         % (round(d[2]), round(d[3])) for d in dots)
            cxd = sb + rad
            body = ("{\nglyphname = uni25CC;\nlayers = (\n{\nanchors = (\n"
                    "{\nname = top;\npos = (%d,%d);\n},\n"
                    "{\nname = bottom;\npos = (%d,%d);\n},\n);\n"
                    "layerId = \"%s\";\nshapes = (\n%s);\nwidth = %d;\n}\n);\n"
                    "unicode = 9676;\n}\n"
                    % (round(cxd), round(cy_d + rad), round(cxd), round(cy_d - rad),
                       lid, sh, round(2 * (rad + sb))))
            open(f"{pkg}/glyphs/{fname('uni25CC')}", "w").write(body)
            made.append("uni25CC")

    # ── thorn, and the pilcrow ────────────────────────────────────────────
    # Borrowing a bowl does not work: in P and b the stem and bowl are one
    # contour, so the bowl cannot be lifted out, and P reduced onto a cap
    # stem still read as a P. The bowl is therefore built -- a D-shaped band
    # between two half-ellipses, modulated like the font's own o: heavy on
    # the outside of the curve, light top and bottom. The stem is the font's
    # own I or l, so it keeps its serifs; a plain bar read as sans-serif
    # beside P.
    if "P" in B and "b" in B and "I" in B and "l" in B:
        px0, _, _, _, pw = B["P"]
        bx0, _, _, _, bw = B["b"]
        w_side, w_horiz = stem * 1.12, thin * 1.10

        ix0, _, _, _, iw = B["I"]
        isl, isr = m["stemx"].get("I", (ix0, ix0 + stem))
        ty0, ty1 = cap * 0.175, cap * 0.815
        reach = (pw - px0) * 0.62
        dxi = px0 - ix0
        put_mixed(pkg, "Thorn", lid,
                  [R("I", dxi, 0),
                   dbowl(isr + dxi - thin * 0.70 + lean((ty0 + ty1) / 2),
                         isr + dxi + lean((ty0 + ty1) / 2),
                         ty0, ty1, reach, w_side, w_horiz)],
                  int(isr + dxi + reach + (pw - px0) * 0.16), 0x00DE)
        made.append("Thorn")

        lx0, _, _, _, lw = B["l"]
        lsl, lsr = m["stemx"].get("l", (lx0, lx0 + stem))
        reachl = (bw - bx0) * 0.60
        dxl = bx0 - lx0
        put_mixed(pkg, "thorn", lid,
                  [R("l", dxl, 0),
                   bar(lsl + dxl + lean(desc), desc, lsr + dxl, 1),
                   dbowl(lsr + dxl - thin * 0.70 + lean(xh / 2),
                         lsr + dxl + lean(xh / 2), 0.0, xh,
                         reachl, w_side, w_horiz)],
                  int(lsr + dxl + reachl + (bw - bx0) * 0.16), 0x00FE)
        made.append("thorn")

    # The pilcrow's bowl is solid and hangs to the LEFT of its stem. Spanning
    # the full width instead gave an arch on two legs.
    W = ow * 1.06
    st = stem * 0.95
    ry = cap * 0.255
    cy_ = cap - ry
    rstem = W - sb * 0.6 - st
    reach_p = rstem - sb * 0.6
    put_mixed(pkg, "paragraph", lid,
              [bar(rstem + lean(desc), desc, rstem + st + lean(cap), cap),
               disc(rstem + lean(cy_), cy_ - ry, cy_ + ry, reach_p, left=True),
               bar(sb * 0.6 + lean(desc), desc, sb * 0.6 + st + lean(cy_), cy_)],
              int(W), 0x00B6); made.append("paragraph")

    return made


def main(repo, built):
    for pkg in sorted(glob.glob(f"{repo}/src/*.glyphspackage")):
        stem_ = os.path.basename(pkg).replace(".glyphspackage", "")
        style = stem_.replace("CheltenhamClassic", "") or "Regular"
        ttf = f"{built}/CheltenhamClassic-{style}.ttf"
        if not os.path.exists(ttf):
            print(f"  skip {stem_}"); continue
        lid = layer_id(pkg)
        ccmp = add_ccmp(pkg)
        relaid = repair_layers(pkg, lid)
        made = build(pkg, lid, measure(ttf), style)
        new = [n for n in made if not n.startswith("~")]
        fixed = [n[1:] for n in made if n.startswith("~")]
        op = f"{pkg}/order.plist"
        if os.path.exists(op):
            txt = open(op).read()
            add = [n for n in new if n not in txt]
            if add:
                open(op, "w").write(txt.rstrip().rstrip(")").rstrip()
                                    + ",\n" + ",\n".join(add) + "\n)\n")
        note = f", relaid {','.join(relaid)}" if relaid else ""
        note += ", +ccmp" if ccmp else ""
        print(f"  {stem_:34} {len(new)} new, {len(fixed)} recomposed onto dotless{note}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
