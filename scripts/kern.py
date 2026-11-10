#!/usr/bin/env python3
"""
Derive kerning by measuring the whitespace between outlines.

    python3 scripts/kern.py . build-dir

The sources ship with an empty `kerningLTR`, so the family has no kerning at
all. This does not invent pairs. For every pair it samples the right profile
of the left glyph and the left profile of the right one, measures the band of
white between them, and compares that against the same measurement taken
from control pairs the design already spaces well (nn, oo, HH, no, on). Where
a pair is measurably looser or tighter than the design's own norm, the
difference is corrected.

Three deliberate restraints, because a bad kern is worse than none:

  * the gap is the mean of the tighter 45% of the overlap band, and the
    correction is weighted by how much the two glyphs overlap vertically.
    That weighting, not the size of the gap, is what separates a pair that
    needs kerning from one that does not: T and o are loose over the whole of
    the o, while C and a hyphen look just as loose but only across the
    hyphen's narrow band, and closing that would drive the hyphen into the C.
  * only 55% of the measured correction is applied. Kerning that fully
    equalises reads mechanical; this leaves the design's own rhythm showing.
  * corrections below 22 units are dropped, because sidebearings already
    handle the general case and kerning should correct exceptions, not
    re-space the font. Everything is clamped to 90.
  * only tightening is emitted. The metric under-reads round pairs -- it
    asked to open up `oo` -- and loosening is the sidebearings' job.

It is a floor, not a substitute for kerning by eye.
"""
import glob, os, re, sys, unicodedata
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen

SAMPLES = 48
TIGHT = 0.45      # share of the overlap band that decides the pair
FULLOVL = 0.40    # overlap at which a pair is judged at full strength
MINOVL = 0.10     # below this there is nothing to judge
DAMP = 0.55
MIN_EMIT = 22
CLAMP = 90

LETTERS = ([chr(c) for c in range(ord("A"), ord("Z") + 1)] +
           [chr(c) for c in range(ord("a"), ord("z") + 1)])
PUNCT = [".", ",", ":", ";", "!", "?", "'", '"', "-", ")", "(", "/"]
def cat(ch):
    if ch.isupper():
        return "U"
    if ch.islower():
        return "L"
    return "P"


def outlines(f, name):
    gs = f.getGlyphSet()
    p = DecomposingRecordingPen(gs)
    gs[name].draw(p)
    cs, cur = [], []
    for op, a in p.value:
        if op == "moveTo":
            cur = [a[0]]
        elif op == "lineTo":
            cur.append(a[0])
        elif op in ("qCurveTo", "curveTo"):
            cur.extend(a)
        elif op == "closePath":
            if cur:
                cs.append(cur)
                cur = []
    return cs


def profiles(cs, y0, y1):
    """Rightmost and leftmost ink at each sampled height; None where blank."""
    rt, lf = [], []
    for i in range(SAMPLES):
        y = y0 + (y1 - y0) * i / (SAMPLES - 1.0)
        xs = []
        for c in cs:
            n = len(c)
            for j in range(n):
                xa, ya = c[j]
                xb, yb = c[(j + 1) % n]
                if (ya <= y < yb) or (yb <= y < ya):
                    xs.append(xa + (xb - xa) * (y - ya) / (yb - ya))
        if xs:
            rt.append(max(xs)); lf.append(min(xs))
        else:
            rt.append(None); lf.append(None)
    return rt, lf


def gap(left, right, advance):
    """White between two adjacent glyphs, and how much they overlap vertically.

    The mean of the tighter 45% of the overlap band -- a raw minimum is
    dominated by a single pinch point, which is what jams diagonal pairs.

    The overlap fraction is returned with it because it, not the size of the
    gap, is what separates a pair that needs kerning from one that does not.
    T and o are loose over the whole of the o's height and want closing up. C
    and a hyphen look just as loose, but only across the hyphen's narrow
    band; closing that would drive the hyphen into the C. Judging on gap
    alone gets both wrong."""
    vals = []
    for i in range(SAMPLES):
        if left[0][i] is None or right[1][i] is None:
            continue
        vals.append(advance - left[0][i] + right[1][i])
    if len(vals) < SAMPLES * MINOVL:
        return None, 0.0
    vals.sort()
    k = max(1, int(len(vals) * TIGHT))
    return sum(vals[:k]) / k, len(vals) / float(SAMPLES)


# Letters with a stroke have no canonical decomposition, so they are not
# reached by the rule below, but their silhouettes are their base's: the bar
# or slash crosses the stem rather than redefining the outer profile. Thorn
# is deliberately absent -- its bowl sits at mid-height, where P's does not.
STRUCK = {"Lslash": "L", "lslash": "l", "Oslash": "O", "oslash": "o",
          "Dcroat": "D", "dcroat": "d", "Eth": "D",
          "Hbar": "H", "hbar": "h"}


def groups(pkg, f):
    """Point every accented glyph at its base for kerning.

    145 glyphs decompose to a base already in the font, and none of them were
    kerned: `Avatar` closed up but `Avatar` with an accent on the A did not.
    Rather than emit a pair for every combination, each accented glyph joins
    its base's kerning group, and the pairs are written against the groups.
    """
    cm = f.getBestCmap()
    rev = {v: k for k, v in cm.items()}
    n = 0
    for gname in f.getGlyphOrder():
        u = rev.get(gname)
        if u is None:
            continue
        d = unicodedata.decomposition(chr(u))
        if not d or d.startswith("<"):
            continue
        base = int(d.split()[0], 16)
        bn = cm.get(base)
        if not bn:
            continue
        path = f"{pkg}/glyphs/{fname(gname)}"
        if not os.path.exists(path):
            continue
        t = open(path).read()
        if "kernLeft" in t:
            continue
        t = t.replace("glyphname = %s;\n" % gname,
                      "glyphname = %s;\nkernLeft = %s;\nkernRight = %s;\n" % (gname, bn, bn),
                      1)
        open(path, "w").write(t)
        n += 1
    for gname, bn in STRUCK.items():
        path = f"{pkg}/glyphs/{fname(gname)}"
        if not os.path.exists(path) or bn not in f.getGlyphOrder():
            continue
        t = open(path).read()
        if "kernLeft" in t:
            continue
        t = t.replace("glyphname = %s;\n" % gname,
                      "glyphname = %s;\nkernLeft = %s;\nkernRight = %s;\n" % (gname, bn, bn), 1)
        open(path, "w").write(t)
        n += 1

    # the bases themselves must be in their own group or the pairs miss them
    for bn in set(cm.values()):
        path = f"{pkg}/glyphs/{fname(bn)}"
        if not os.path.exists(path):
            continue
        t = open(path).read()
        if "kernLeft" in t:
            continue
        t = t.replace("glyphname = %s;\n" % bn,
                      "glyphname = %s;\nkernLeft = %s;\nkernRight = %s;\n" % (bn, bn, bn), 1)
        open(path, "w").write(t)
    return n


def fname(n):
    return "".join(c + "_" if c.isupper() else c for c in n) + ".glyph"


def main(repo, built):
    for pkg in sorted(glob.glob(f"{repo}/src/*.glyphspackage")):
        stem = os.path.basename(pkg).replace(".glyphspackage", "")
        style = stem.replace("CheltenhamClassic", "") or "Regular"
        ttf = f"{built}/CheltenhamClassic-{style}.ttf"
        if not os.path.exists(ttf):
            print(f"  skip {stem}"); continue
        f = TTFont(ttf)
        cm, hm, glyf = f.getBestCmap(), f["hmtx"], f["glyf"]
        y0, y1 = -60, glyf[cm[ord("H")]].yMax

        prof, adv, gname = {}, {}, {}
        for ch in LETTERS + PUNCT:
            n = cm.get(ord(ch))
            if not n:
                continue
            gname[ch] = n
            prof[ch] = profiles(outlines(f, n), y0, y1)
            adv[ch] = hm[n][0]

        # One target cannot serve the whole font: H beside H leaves far more
        # white than o beside o, because flat-sided and round shapes are
        # spaced differently on purpose. Normalising everything to a single
        # number re-spaces the font instead of kerning it -- it asked to open
        # up oo and left To alone, which is backwards. So each category pair
        # (cap-cap, cap-lower, lower-punctuation and so on) gets its own
        # norm, taken from the median of that category's own measurements,
        # and only the outliers within a category are corrected.
        chars = [c for c in LETTERS + PUNCT if c in prof]
        meas = {}
        for a_ in chars:
            for b_ in chars:
                g, ovl = gap(prof[a_], prof[b_], adv[a_])
                if g is not None:
                    meas[(a_, b_)] = (g, ovl)
        norms = {}
        for (a_, b_), (g, _) in meas.items():
            norms.setdefault(cat(a_) + cat(b_), []).append(g)
        for k_ in norms:
            v = sorted(norms[k_])
            norms[k_] = v[len(v) // 2]

        pairs = {}
        for (a_, b_), (g, ovl) in meas.items():
            target = norms[cat(a_) + cat(b_)]
            weight = min(1.0, ovl / FULLOVL)
            k = int(round((target - g) * DAMP * weight))
            # Tightening only. A horizontal-gap metric systematically
            # under-reads round pairs -- it wanted to open up `oo`, which no
            # one would ask for -- and loosening is the sidebearings' job
            # anyway. Dropping positives removes that whole class of error.
            if k < 0 and abs(k) >= MIN_EMIT:
                pairs.setdefault(gname[a_], {})[gname[b_]] = max(-CLAMP, min(CLAMP, k))
        shown = ", ".join(f"{k_}:{v:.0f}" for k_, v in sorted(norms.items()))
        ng = groups(pkg, f)
        write(pkg, pairs)
        n = sum(len(v) for v in pairs.values())
        print(f"  {stem:30} {n:5} pairs, {ng} accented glyphs grouped")
        f.close()


def write(pkg, pairs):
    fi = f"{pkg}/fontinfo.plist"
    t = open(fi).read()
    lid = re.search(r'id = "([^"]+)";', t).group(1)
    body = "".join(
        '"@MMK_L_%s" = {\n%s};\n' % (a, "".join('"@MMK_R_%s" = %d;\n' % (b, v)
                                                 for b, v in sorted(pairs[a].items())))
        for a in sorted(pairs))
    block = 'kerningLTR = {\n"%s" = {\n%s};\n};\n' % (lid, body)
    # Brace-matched, not a regex. A non-greedy pattern stops at the first
    # "};" -- the inner master dict -- and replacing that span leaves the
    # outer close behind as junk, which fails the plist parse.
    i = t.index("kerningLTR = {")
    j = i + len("kerningLTR = {")
    depth = 1
    while depth:
        if t[j] == "{":
            depth += 1
        elif t[j] == "}":
            depth -= 1
        j += 1
    while j < len(t) and t[j] in ";\n":
        j += 1
    open(fi, "w").write(t[:i] + block + t[j:])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
