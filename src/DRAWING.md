# What still needs drawing

310 glyphs build across all six styles. All 14 combining marks have outlines,
`scripts/check_marks_drawn.py` passes, and nothing renders as a bare base
letter any more.

> **Twelve characters are left**, listed in section 2. They are the entire
> remaining blocker: placed at `ofl/cheltenhamclassic/`, FontBakery reports 12
> failures and every one of them is a consequence of those twelve glyphs.

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

## 2. The twelve remaining characters

These are the whole of what stands between the family and a clean FontBakery
run. Everything else in Latin Core is now built.

| | Why it is not generated |
| --- | --- |
| `Æ æ` `Œ œ` | Ligatures. The two letters have to share a stem and resolve their join; that is a design decision, not an overlap. |
| `ß` `ẞ` | The eszett is its own letterform. |
| `Þ þ` | Thorn. A stem with a bowl set at mid-height — close to `b` and `P` but not reachable from either without redrawing the join. |
| `ð` `Ð` | Capital eth is a `D` with a crossbar and would be free, but lowercase eth is a wholly different curved form. **Shipping one half of a case pair breaks `case_mapping`, which currently passes**, so the capital waits for the lowercase. |
| `§` `¶` | The section and pilcrow signs. Both are compound forms with their own construction. |

`scripts/latin_core.py` deliberately stops here. Everything it does make is
either an existing glyph reused or a stroke measured off the design; none of
it invents a letterform.

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
