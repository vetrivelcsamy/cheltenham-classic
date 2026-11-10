#!/usr/bin/env python3
"""
Draw the eszett, as one continuous stroke.

    python3 scripts/draw_eszett.py . build-dir

`ß` and `ẞ` were the last two characters missing from the Google Fonts Latin
Core set, and seven attempts to assemble them from pieces all failed the same
way. Each built the stem, the upper bowl and the lower bowl separately and
then had to join them, and every failure was at a join: welded shut, cut
through, collapsed to a slit, or read as a `B` with a tail.

This draws the letter as a single skeleton instead -- up the stem, round the
upper bowl, back to the waist, round the lower bowl, out to the terminal --
and strokes it with a width that varies along the way. There are no joins to
get wrong, because the joins are the path. The counters form where the
stroke encloses white, and overlap removal resolves them.

Weights come from the style's own stem and hairline, so the bold's eszett is
the bold's weight. Italics are sheared to the angle measured off their `l`.

It is a drawing, not a derivation, and like the nine constructed marks it is
a working default rather than a finished outline -- see src/DRAWING.md.
"""
import glob, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import latin_core as L

PER = 26          # samples per skeleton segment


def bez(p, t):
    a, b, c, d = p
    v = 1 - t
    return (v**3 * a[0] + 3 * v * v * t * b[0] + 3 * v * t * t * c[0] + t**3 * d[0],
            v**3 * a[1] + 3 * v * v * t * b[1] + 3 * v * t * t * c[1] + t**3 * d[1])


def sample(segs):
    pts = []
    for i, s in enumerate(segs):
        rng = range(PER) if i == 0 else range(1, PER)
        pts += [bez(s, j / (PER - 1.0)) for j in rng]
    return pts


def stroke(pts, widths):
    """Offset the skeleton either side, tapering the last point to a tip."""
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        nx = pts[min(i + 1, n - 1)]
        px = pts[max(i - 1, 0)]
        dx, dy = nx[0] - px[0], nx[1] - px[1]
        ln = math.hypot(dx, dy) or 1.0
        ux, uy = -dy / ln, dx / ln
        h = widths[i] / 2.0
        left.append((x + ux * h, y + uy * h))
        right.append((x - ux * h, y - uy * h))
    return left[:-1] + [pts[-1]] + list(reversed(right[:-1]))


def skeleton(cx, T, W, waist):
    """Stem, upper bowl, waist, lower bowl, terminal -- one path."""
    return [
        [(cx, 0), (cx, T * 0.45), (cx, T * 0.78), (cx + 28 * W, T * 0.92)],
        [(cx + 28 * W, T * 0.92), (cx + 150 * W, T * 1.00),
         (cx + 330 * W, T * 0.95), (cx + 330 * W, T * (waist + 0.22))],
        [(cx + 330 * W, T * (waist + 0.22)), (cx + 330 * W, T * (waist + 0.065)),
         (cx + 180 * W, T * (waist + 0.01)), (cx + 40 * W, T * waist)],
        [(cx + 40 * W, T * waist), (cx + 210 * W, T * (waist - 0.01)),
         (cx + 390 * W, T * (waist - 0.095)), (cx + 390 * W, T * 0.245)],
        [(cx + 390 * W, T * 0.245), (cx + 390 * W, T * 0.085),
         (cx + 230 * W, T * 0.015), (cx + 120 * W, T * 0.055)],
    ]


def widths(n, stem, thin):
    """Stem weight on the upright, hairline at the tops and the waist,
    full weight on the outside of each bowl, tapering into the terminal."""
    per = n / 5.0
    out = []
    for i in range(n):
        k = i / per
        if k < 1.0:
            v = stem - (stem - thin * 1.25) * max(0.0, (k - 0.72) / 0.28)
        elif k < 2.0:
            v = thin * 1.25 + (stem * 0.92 - thin * 1.25) * math.sin(math.pi * (k - 1) * 0.5)
        elif k < 3.0:
            v = stem * 0.92 - (stem * 0.92 - thin * 1.15) * math.sin(math.pi * (k - 2) * 0.5)
        elif k < 4.0:
            v = thin * 1.15 + (stem * 1.02 - thin * 1.15) * math.sin(math.pi * (k - 3) * 0.5)
        else:
            u = min(1.0, k - 4)
            v = stem * 1.02 - (stem * 1.02 - thin * 0.85) * u ** 0.75
        out.append(v)
    return out


def main(repo, built):
    for pkg in sorted(glob.glob(f"{repo}/src/*.glyphspackage")):
        stem_ = os.path.basename(pkg).replace(".glyphspackage", "")
        style = stem_.replace("CheltenhamClassic", "") or "Regular"
        ttf = f"{built}/CheltenhamClassic-{style}.ttf"
        if not os.path.exists(ttf):
            print(f"  skip {stem_}"); continue
        m = L.measure(ttf)
        stem, thin = m["stem"], m["thin"]
        lid = L.layer_id(pkg)
        tan = math.tan(math.radians(m["slant"]))
        made = []
        for top, uni, name, cap in ((m["asc"], 0x00DF, "germandbls", False),
                                    (m["cap"], 0x1E9E, "uni1E9E", True)):
            cx = 32 + stem / 2.0
            Wf = 1.16 if cap else 1.0
            waist = 0.500 if cap else 0.535
            pts = sample(skeleton(cx, top, Wf, waist))
            poly = stroke(pts, widths(len(pts), stem, thin))
            if tan:
                mid = top * 0.5
                poly = [(x + (y - mid) * tan, y) for x, y in poly]
            adv = int(cx + 390 * Wf + m["ow"] * 0.11)
            L.put_mixed(pkg, name, lid, [L.quad(poly)], adv, uni)
            made.append(name)
        order = f"{pkg}/order.plist"
        if os.path.exists(order):
            t = open(order).read()
            add = [n for n in made if n not in t]
            if add:
                open(order, "w").write(t.rstrip().rstrip(")").rstrip()
                                       + ",\n" + ",\n".join(add) + "\n)\n")
        print(f"  {stem_:34} eszett drawn  (stem {stem}, thin {thin}, "
              f"slant {m['slant']:.1f}deg)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
