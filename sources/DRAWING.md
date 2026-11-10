# What still needs drawing

325 glyphs build across all six styles. All 14 combining marks have outlines,
`scripts/check_marks_drawn.py` passes, and nothing renders as a bare base
letter any more.

> **FontBakery passes.** Placed at `ofl/librecheltenham/` the family
> reports **zero failures**. What is left is in section 2a: glyphs that are
> built and correct but want a designer's hand before submission.

The three generation scripts are run by `scripts/build.sh`, which builds
twice: once to measure the design, then again with everything regenerated
from those measurements. Nothing in them is a hardcoded coordinate.

## 1. The combining marks

**Five are derived.** `scripts/derive_marks.py` builds them from shapes already
in the font, as components, so they carry the typeface's own modulation and
follow if the donor glyph is redrawn:

| Mark | Built from |
| --- | --- |
| `dotaccentcomb` | `period` |
| `dieresiscomb` | `period`, twice, parted by 1.35 × its width |
| `cedillacomb` | `comma` at 0.82, hung below the baseline |
| `commaaccentcomb` | `comma` |
| `macroncomb` | a bar, 0.72 × the `o` wide, weighted off the `period` |

**Nine are constructed**, by `scripts/draw_marks.py`: grave, acute,
circumflex, caron, tilde, breve, ring, hungarumlaut and ogonek. Every
dimension is a ratio applied to values measured off each style's own built
TTF — stem, hairline, x-height, ascender and slant — so the Bold's accents
carry the Bold's weight and the italics' are sheared to the italics' own
angle (13.4°–14.1°, measured; `post.italicAngle` in the raw build is 0).

It also draws `caroncomb.alt`, the upright Czech/Slovak caron.

> These nine are **construction, not revival**. They are consistent with the
> typeface's measurements, but they were not drawn by its designer. Treat them
> as a working default to refine in Glyphs. The script is the record of how
> each was derived, so adjusting a ratio and rebuilding is cheap.

Each mark has a `_top` anchor (or `_bottom` for those that hang below) at the
origin; the composites position themselves from the base letters' matching
`top` and `bottom` anchors.

### Four composites are not plain stacks

| Letter | Why |
| --- | --- |
| `ģ` | Unicode decomposes it to `g` + U+0327 *below*, but the descender owns that space, so Latvian turns the mark and sets it above. `ķ ļ ņ ŗ` and cap `Ģ` keep it below. |
| `ď ť ľ Ľ` | No room overhead, so Czech and Slovak use an upright mark at the shoulder. It must not look like an apostrophe — FontBakery's `alt_caron` fails `quoteright`, `quotesingle`, `comma` and the chevron on purpose — so `caroncomb.alt` is drawn as a straight tapered wedge. |

### The spacing accents

The legacy spacing accents (`´` U+00B4, `ˇ` U+02C7, `˛` U+02DB and ten more)
are their own codepoints, not the combining marks. Both scripts emit them as
composites of the matching mark, re-centred inside a real advance width. An
empty one trips `contour_count`; a zero-width one trips `base_has_width`.

## 2. Nothing is missing

The Google Fonts Latin Core set is complete: 325 glyphs in each of the six
styles, nothing left out.

`ß` and `ẞ` were the last two and are now drawn, by
`scripts/draw_eszett.py`. Seven attempts to assemble them from pieces failed
first, and the reason they failed is the reason the eighth worked: each one
built the stem, the upper bowl and the lower bowl separately and then had to
join them, and every failure was at a join -- welded shut, cut through,
collapsed to a slit, or reading as a `B` with a tail.

The eighth draws the whole letter as **one continuous skeleton** -- up the
stem, round the upper bowl, back to the waist, round the lower bowl, out to
the terminal -- and strokes it with a width that varies along the way. There
are no joins to get wrong, because the joins are the path. The counters form
where the stroke encloses white.

The capital is wider, with its waist nearer the middle, because cap height
and ascender are both 730 here and without that the two glyphs come out
identical -- a lowercase-shaped eszett among capitals reads as a mistake.

## 2a. Built, but wanting a designer's hand first

These ship and clear the coverage check, but they are the weakest things in
the font and a curation review will notice:

| | What is wrong with it |
| --- | --- |
| `Æ` | `A` and `E` overlapped. The `A`'s right leg is a diagonal and the `E`'s stem is vertical, so they can only truly meet at one height — it reads as two letters touching rather than one letterform. `æ` does not have this problem, both sides being curved. |
| `§` | Two reduced `S`s overlapped. A section sign is a single continuous double curve, so there is a seam where they meet. Reads at text size; does not hold up large. |
| `ß ẞ` | Drawn as a stroked skeleton rather than by eye: the weights come from the style's own stem and hairline, but the curves are mine, not the designer's. Reads correctly at text and display size; worth a pass in Glyphs. |

## 2b. ð, Þ, þ and ¶ — no longer built

These four used to be in 2a. They are now cut out of, or grown from, the
designer's own letters by `scripts/borrow_bowls.py`.

The earlier note said a bowl "cannot be lifted out" of `P` or `b`, because in
both the stem and the bowl are a single contour. That is true of a component
reference, which can only move a whole glyph. It is not true of the geometry:
intersecting `P` with the half-plane to the right of its stem and above its
foot serif leaves the bowl behind, and re-hanging it on the font's own `I`
gives a `Þ` whose counter is the shape `P`'s counter is, and whose stroke
thins into the join the way `P`'s does.

| | Where it comes from now |
| --- | --- |
| `Þ` | `P`'s bowl, cut at the stem and hung at mid-cap on `I`'s stem, serifs and all. |
| `þ` | `b`'s own bowl on `l`'s stem, with `l`'s foot serif cut away — the stem runs on to the descender, so there is no foot for a serif to stand on. |
| `¶` | `P`'s bowl again, taken from the outer contour alone so it is solid, mirrored so it hangs to the left, on two stems. |
| `ð` | The `o`, with an ascender that curves out of it. The old one began at the `o`'s top-right *corner*, where the `o` has no ink — at that x its stroke is down at mid-height — so the ascender floated clear of the bowl with white in between. It is now anchored on the middle of the ring's right wall and drawn as a tapered curve, which is what 2a asked for. |

Stem and bowl are unioned into one contour rather than left overlapping, and
every cut is sheared by the master's own slant, read off `l`, so the italics
are cut along their stems rather than across them.

## 3. What was built, and from what

`scripts/latin_core.py`, run by `build.sh` after the two mark scripts:

| | |
| --- | --- |
| `dotlessi` `dotlessj` | `i` and `j` with the dot contour dropped — **and every accented `i`/`j` recomposed onto them.** The scaffold had stacked accents on the dotted forms, so `ï` carried three dots. The mark's height is re-seated on the dotless letter's own top. `į` keeps its dot, because the ogonek is below. |
| `Ț ț` | `T` and `t` over the existing `commaaccentcomb`. |
| `Đ đ` `Ħ ħ` | A crossbar at the measured hairline weight. |
| `Ł ł` `Ø ø` | A diagonal at the same weight. |
| `¢ ¥` | `c` and `Y` with the same strokes through them. |
| `« » ‹ ›` | Chevrons built to the design's own stroke weight. |
| `ª º ™ © ®` | `a o T M C R` reduced. These characters *are* smaller letters, so reduction is the construction rather than a shortcut around one. |
| `Æ æ Œ œ` | Two letters overlapped so the second's left edge lands on the first's right stem. fontmake unions them, which is the real construction of these characters. See 2a for `Æ`. |
| `ð Ð` | The lowercase is no longer a straight stroke — see 2b. `Ð` is `D` with a crossbar, and only ships because the lowercase does: half a case pair breaks `case_mapping`. |
| `§` | Two reduced `S`s. See 2a. |
| `Þ þ ¶` | No longer built from ellipses — the bowls are cut out of `P` and `b`. See 2b. |

It also repairs any glyph carrying a layer id that is not its master's.
glyphsLib drops those silently — which is why the Italic shipped with no
semicolon for so long. The outlines were drawn all along, filed under another
master's id.

## Checking progress

```sh
./scripts/build.sh
```

FontBakery's `glyph_coverage` will pass once the slots are filled. Note that
it counts codepoints, not outlines — it cannot tell an empty mark from a drawn
one, so it will report success before the font is actually finished. That gap
is why `scripts/check_marks_drawn.py` exists; run it directly to see what is
left:

```sh
python3 scripts/check_marks_drawn.py gf-submission
```

`scripts/build.sh` runs it between `gf_fixup.py` and FontBakery, and both
workflows gate on it.
