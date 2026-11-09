# What still needs drawing

`scripts/scaffold_latin_core.py` has laid out the Latin Core expansion. The
slots, anchors and composites exist; the outlines do not.

> **This branch is not releasable.** The 14 combining marks are empty, so all
> 145 accented glyphs currently render as the bare base letter. A reader sees
> `A` where `Á` belongs — which is worse than a missing-glyph box, because it
> looks like a correct character and is not. Draw the marks before any tag.

## 1. The 14 combining marks — do these first

`gravecomb` `acutecomb` `circumflexcomb` `tildecomb` `macroncomb` `brevecomb`
`dotaccentcomb` `dieresiscomb` `ringcomb` `hungarumlautcomb` `caroncomb`
`cedillacomb` `ogonekcomb` `commaaccentcomb`

Each has an `_top` anchor (or `_bottom` for the three that hang below) sitting
at the origin. **Draw the mark around that anchor** and all 145 composites
position themselves — the base letters carry matching `top` and `bottom`
anchors, placed from each glyph's own outline.

These 14 unlock 145 glyphs. Nothing else in the project has that ratio.

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
one, so it will report success before the font is actually finished.
