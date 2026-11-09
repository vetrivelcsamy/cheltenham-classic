# What still needs drawing

`scripts/scaffold_latin_core.py` has laid out the Latin Core expansion. The
slots, anchors and composites exist; the outlines do not.

> **This branch is not releasable.** Nine of the 14 combining marks are still
> empty, so the glyphs built on them render as the bare base letter. A reader
> sees `A` where `Á` belongs — which is worse than a missing-glyph box,
> because it looks like a correct character and is not. `scripts/check_marks_
> drawn.py` fails while any mark is empty, and both workflows gate on it.

## 1. The combining marks

**Five are done.** `scripts/derive_marks.py` builds them from shapes already
in the font, as components, so they carry the typeface's own modulation and
follow if the donor glyph is redrawn. Re-run it after editing a donor:

| Mark | Built from |
| --- | --- |
| `dotaccentcomb` | `period` |
| `dieresiscomb` | `period`, twice, parted by 1.35 × its width |
| `cedillacomb` | `comma`, hung below the baseline |
| `commaaccentcomb` | `comma` |
| `macroncomb` | a bar, 0.72 × the `o` wide, weighted off the `period` |

**Nine still need drawing:**

`gravecomb` `acutecomb` `circumflexcomb` `tildecomb` `brevecomb` `ringcomb`
`hungarumlautcomb` `caroncomb` `ogonekcomb`

Eight of those are modulated strokes whose terminals carry the design's voice
— there is no honest way to derive them. The ninth, `ringcomb`, was tried as a
scaled-down `o` and rejected on sight: it read as a miniature letter, serif
modulation and all, where a ring wants an even-weight circle.

Each has a `_top` anchor (or `_bottom` for those that hang below) sitting at
the origin. **Draw the mark around that anchor** and the composites position
themselves — the base letters carry matching `top` and `bottom` anchors,
placed from each glyph's own outline.

### One composite is not a plain stack

`gcommaaccent` (`ģ`). Unicode decomposes it to `g` + U+0327 below, but the
descender already owns that space, so Latvian sets the mark turned and above.
`derive_marks.py` writes that exception. `ķ ļ ņ ŗ` and cap `Ģ` keep it below.

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
python3 scripts/check_marks_drawn.py build
```
