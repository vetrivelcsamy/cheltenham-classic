# What still needs drawing

320 glyphs build across all six styles. All 14 combining marks have outlines,
`scripts/check_marks_drawn.py` passes, and nothing renders as a bare base
letter any more.

> **Two characters are left** — `ß` and `ẞ` — plus three in section 2a that
> are built but want redrawing. The two are the entire remaining blocker:
> placed at `ofl/cheltenhamclassic/`, FontBakery reports 12 failures and
> every one is a consequence of them.

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

## 2. The two remaining characters

| | Why it is not generated |
| --- | --- |
| `ß` `ẞ` | The eszett is its own letterform. Nothing in the font decomposes into it, and it is not a stem plus a bowl the way thorn is. |

## 2a. Built, but wanting a designer's hand first

These three ship and clear the coverage check, but they are the weakest things
in the font and a curation review will notice:

| | What is wrong with it |
| --- | --- |
| `Æ` | `A` and `E` overlapped. The `A`'s right leg is a diagonal and the `E`'s stem is vertical, so they can only truly meet at one height — it reads as two letters touching rather than one letterform. `æ` does not have this problem, both sides being curved. |
| `ð` | The bowl is the `o` and the ascender is a straight stroke with a bar across it. A real eth's ascender *curves* out of the bowl. Legible at text size, visibly constructed at display size. |
| `§` | Two reduced `S`s overlapped. A section sign is a single continuous double curve, so there is a seam where they meet. Reads at text size; does not hold up large. |
| `Þ þ ¶` | The bowls are built from ellipses rather than drawn, so the counter is a plain oval where `P`'s is shaped, and the stroke does not thin into the join. Correct and in-style at text size; a designer would redraw the counter. |

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
| `ð Ð` | `o` with a stroked ascender; `D` with a crossbar. The capital only ships because the lowercase does — half a case pair breaks `case_mapping`. |
| `§` | Two reduced `S`s. See 2a. |
| `Þ þ` | The font's own `I`/`l` for the stem, so the serifs come free, plus a **built** bowl: a solid half-ellipse with its counter punched as a separate contour. Borrowing a bowl is impossible — in `P` and `b` the stem and bowl are one contour. |
| `¶` | Two stems and a solid half-disc hung to the left of the right one. |

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
