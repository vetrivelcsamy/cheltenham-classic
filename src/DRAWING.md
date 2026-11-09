# What still needs drawing

`scripts/scaffold_latin_core.py` laid out the Latin Core expansion and the
two mark scripts have since filled the marks. 289 glyphs build. What is left
is the 28 characters that do not decompose, and one missing semicolon.

> **All 14 combining marks now have outlines** and `scripts/check_marks_drawn.py`
> passes, so the accented glyphs no longer render as bare base letters. What
> remains for a Google Fonts submission is the 28 characters in section 2 and
> the Italic semicolon in section 3.

Both mark scripts are run automatically by `scripts/build.sh`, which builds
twice: once to measure the design, then again with the marks regenerated from
those measurements. Nothing here is a hardcoded coordinate.

## 1. The combining marks — done

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

## 2. The 28 remaining characters — original drawings

Letters: `Æ æ` `Ø ø` `ß` `Þ þ` `Ð ð` `Đ đ` `Ħ ħ` `Ł ł` `Œ œ` `ª º`
Symbols: `¢ ¥ © ® ™ § ¶ ‹ ›`

None decompose into base + mark, so each is its own drawing.

## 3. The semicolon

`CheltenhamClassic-Italic` has no semicolon, U+003B. The other five styles do.
A live bug in the shipped font, not only a submission blocker.

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
