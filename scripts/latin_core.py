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

    return made


def main(repo, built):
    for pkg in sorted(glob.glob(f"{repo}/src/*.glyphspackage")):
        stem_ = os.path.basename(pkg).replace(".glyphspackage", "")
        style = stem_.replace("CheltenhamClassic", "") or "Regular"
        ttf = f"{built}/CheltenhamClassic-{style}.ttf"
        if not os.path.exists(ttf):
            print(f"  skip {stem_}"); continue
        lid = layer_id(pkg)
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
        print(f"  {stem_:34} {len(new)} new, {len(fixed)} recomposed onto dotless{note}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
