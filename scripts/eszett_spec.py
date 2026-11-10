#!/usr/bin/env python3
"""
Measure what a drawn eszett has to match, and write src/DRAWING-ESZETT.md.

    python3 scripts/eszett_spec.py . gf-submission

The eszett is the last thing standing between this family and a Google Fonts
submission, and it cannot be constructed -- five attempts are recorded in
src/DRAWING.md. It has to be drawn. This measures the numbers a drawing has
to agree with, off the built fonts, so whoever draws it starts from the
design's own values instead of guessing, and so the figures cannot drift
away from the font the way a hand-written table would.
"""
import glob, math, os, sys
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen

STYLES = ["Regular", "Italic", "Medium", "MediumItalic", "Bold", "BoldItalic"]


def contours(f, name):
    gs = f.getGlyphSet(); p = DecomposingRecordingPen(gs); gs[name].draw(p)
    cs, cur = [], []
    for op, a in p.value:
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


def bbox(cs):
    xs = [p[0] for c in cs for p in c]; ys = [p[1] for c in cs for p in c]
    return min(xs), min(ys), max(xs), max(ys)


def measure(path):
    f = TTFont(path); cm = f.getBestCmap(); hm = f["hmtx"]; glyf = f["glyf"]
    d = {}
    d["xh"] = glyf[cm[0x78]].yMax
    d["cap"] = glyf[cm[0x48]].yMax
    d["asc"] = glyf[cm[0x62]].yMax
    nn = hits(contours(f, cm[0x6E]), d["xh"] * 0.5)
    d["stem"] = round(nn[1] - nn[0]) if len(nn) >= 2 else 0
    og = glyf[cm[0x6F]]
    oo = hits(contours(f, cm[0x6F]), (og.xMin + og.xMax) / 2, horiz=False)
    d["thin"] = round(oo[-1] - oo[-2]) if len(oo) >= 2 else 0
    d["contrast"] = round(d["stem"] / max(1, d["thin"]), 2)
    a = hits(contours(f, cm[0x6C]), d["xh"] * 0.25)
    b_ = hits(contours(f, cm[0x6C]), d["xh"] * 0.95)
    sl = math.degrees(math.atan2(b_[0] - a[0], d["xh"] * 0.70)) if a and b_ else 0
    d["slant"] = 0.0 if abs(sl) < 1.5 else round(sl, 1)

    # b: the design's own lowercase bowl on an ascender -- the nearest thing
    bc = contours(f, cm[0x62])
    outer = max(bc, key=lambda c: (max(p[1] for p in c) - min(p[1] for p in c)))
    counters = [c for c in bc if c is not outer]
    # The outer contour encloses stem and bowl as one shape, so a scanline
    # across it gives the letter's full width, not the stem's. The counter's
    # left edge is the stem's right edge.
    bs = hits([outer], d["xh"] * 0.5)
    cl = min(p[0] for c in counters for p in c) if counters else 0
    d["b_stem"] = (round(bs[0]), round(cl)) if bs else (0, 0)
    d["b_adv"] = hm[cm[0x62]][0]
    d["b_outer"] = tuple(round(v) for v in bbox([outer]))
    d["b_counter"] = tuple(round(v) for v in bbox(counters)) if counters else None

    # B: how this design divides a two-storey capital
    Bc = contours(f, cm[0x42])
    Bout = max(Bc, key=lambda c: (max(p[1] for p in c) - min(p[1] for p in c)))
    Bcnt = sorted((c for c in Bc if c is not Bout),
                  key=lambda c: min(p[1] for p in c))
    d["B_adv"] = hm[cm[0x42]][0]
    d["B_counters"] = [tuple(round(v) for v in bbox([c])) for c in Bcnt]
    # The waist is where the right-hand profile pinches furthest in. Sampling
    # one fixed height misses it; scan the middle band and take the minimum.
    best = None
    for i in range(60):
        y = d["cap"] * (0.38 + 0.30 * i / 59.0)
        h = hits([Bout], y)
        if len(h) >= 2:
            if best is None or max(h) < best[0]:
                best = (max(h), y)
    d["B_waist"], d["B_waist_y"] = (round(best[0]), round(best[1])) if best else (0, 0)

    sg = glyf[cm[0x73]]
    d["s_box"] = (sg.xMin, sg.yMin, sg.xMax, sg.yMax)
    d["s_adv"] = hm[cm[0x73]][0]
    f.close()
    return d


def main(repo, built):
    rows = {}
    for st in STYLES:
        p = f"{built}/CheltenhamClassic-{st}.ttf"
        if os.path.exists(p):
            rows[st] = measure(p)
    if not rows:
        print("no built fonts"); return
    R = rows["Regular"]

    def col(k, fmt=lambda v: str(v)):
        return " | ".join(fmt(rows[s][k]) for s in STYLES if s in rows)

    hdr = " | ".join(s for s in STYLES if s in rows)
    out = f"""# Drawing the eszett

`ß` (U+00DF) and `ẞ` (U+1E9E) are the last two characters missing from the
Google Fonts Latin Core set, and the only thing failing FontBakery. They
cannot be constructed from what the font holds -- five attempts are recorded
in `DRAWING.md`, and every one of them failed in the same way. They have to
be drawn.

This file is generated by `scripts/eszett_spec.py` from the built fonts, so
the numbers cannot drift away from the design.

## What the design is doing

| | {hdr} |
| --- | {' | '.join('---' for _ in rows)} |
| x-height | {col('xh')} |
| cap height | {col('cap')} |
| ascender (`b`) | {col('asc')} |
| stem (`n`, at half x-height) | {col('stem')} |
| hairline (`o`, at its centre) | {col('thin')} |
| contrast | {col('contrast')} |
| slant, degrees | {col('slant')} |

## The shapes to agree with

Measured off the Regular. The other styles are in the table above; take the
same ratios.

**`b` — a bowl on an ascender, which is half of what `ß` is.**

| | |
| --- | --- |
| advance | {R['b_adv']} |
| outer bounds | x {R['b_outer'][0]}–{R['b_outer'][2]}, y {R['b_outer'][1]}–{R['b_outer'][3]} |
| stem at half x-height | x {R['b_stem'][0]}–{R['b_stem'][1]} ({R['b_stem'][1]-R['b_stem'][0]} wide) |
| counter | x {R['b_counter'][0]}–{R['b_counter'][2]}, y {R['b_counter'][1]}–{R['b_counter'][3]} |

So a bowl in this design springs off the stem at x {R['b_stem'][1]}, reaches
x {R['b_outer'][2]} -- a protrusion of {R['b_outer'][2]-R['b_stem'][1]} -- and
leaves a counter {R['b_counter'][2]-R['b_counter'][0]} wide by
{R['b_counter'][3]-R['b_counter'][1]} tall. The bowl's own stroke is
{R['b_outer'][2]-R['b_counter'][2]} at its heaviest, on the outside of the curve.

**`B` — how this design divides two storeys.**

| | |
| --- | --- |
| advance | {R['B_adv']} |
| upper counter | x {R['B_counters'][1][0]}–{R['B_counters'][1][2]}, y {R['B_counters'][1][1]}–{R['B_counters'][1][3]} |
| lower counter | x {R['B_counters'][0][0]}–{R['B_counters'][0][2]}, y {R['B_counters'][0][1]}–{R['B_counters'][0][3]} |
| waist — where the right profile pinches in | x {R['B_waist']}, at y {R['B_waist_y']} |

The lower bowl is the larger of the two and carries further right. Note that
`ß` is **not** this shape: `B` closes its lower bowl back onto the stem,
and `ß` does not.

**`s` — the reference for the open lower stroke.**

| | |
| --- | --- |
| advance | {R['s_adv']} |
| bounds | x {R['s_box'][0]}–{R['s_box'][2]}, y {R['s_box'][1]}–{R['s_box'][3]} |

## What the five failed attempts establish

Worth reading before starting, because each one rules something out:

1. **A long-s + s ligature from existing components** collides; the stem and
   the `s` cannot both be where they need to be.
2. **Two closed bowls on an ascender** reads as a `B` on a stick, whatever
   the proportions.
3. **A bowl plus a stroked lower curve** collides at the stem.
4. **Two bowls at corrected proportions** -- the lower counter collapses to
   a slit.
5. **A working bowl plus an open stroked curve** -- the upper storey is
   right, the lower one still collides.

The common thread: the upper storey is reachable by machine, and the lower
one is not. What defeats construction every time is the **join** -- where the
lower stroke leaves the stem, and where it resolves into its terminal. Those
two moments are the letter, and they are judgement rather than geometry.

## Suggested proportions

A starting point, not a prescription, in Regular units:

| | |
| --- | --- |
| advance | about {R['b_adv'] - 20}–{R['b_adv'] + 40}, i.e. near `b` |
| stem | {R['stem']}, left edge about x 30 |
| upper storey | roughly y {round(R['xh']*0.52)}–{round(R['asc']*0.96)} |
| lower storey | roughly y 0–{round(R['xh']*0.60)}, reaching further right than the upper |
| heaviest stroke | {R['b_outer'][2]-R['b_counter'][2]}, matching `b`'s bowl, on the outside of each curve |
| lightest | {R['thin']}, at the top and bottom of each curve |

The two ranges overlap by about {round(R['xh']*0.60) - round(R['xh']*0.52)} units on
purpose: that is the pinch, where the storeys meet at the stem. `B` makes the
same move at y {R['B_waist_y']}.

The bottom right must stay **open**: that, and the pinch between the
storeys, are what keep it from reading as a `B`.

## Checking it

```sh
./scripts/build.sh
```

The missing-glyph list is printed on every run. Read that, not a rendered
proof -- a browser silently substitutes a fallback face for a missing glyph,
and it is convincing enough that it caused two wrong conclusions while this
font was being built.

When that list comes back empty, FontBakery should clear: both current
failures are these two codepoints and nothing else.
"""
    with open(f"{repo}/src/DRAWING-ESZETT.md", "w") as fh:
        fh.write(out)
    print(f"  wrote src/DRAWING-ESZETT.md from {len(rows)} styles")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
