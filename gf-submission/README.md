# Google Fonts submission

Working directory for onboarding Cheltenham Classic to Google Fonts.
**Not ready to submit yet** — see "Remaining" below.

## Contents

| File | Purpose |
|---|---|
| `METADATA.pb` | Family metadata, six styles with weights and PostScript names |
| `DESCRIPTION.en_us.html` | The blurb shown on the Google Fonts listing |
| `OFL.txt` | Licence. First line reformatted to GF's required pattern |
| `CheltenhamClassic-*.ttf` | Fonts renamed to GF convention and run through `../scripts/gf_fixup.py` |

## FontBakery status

`fontbakery check-googlefonts *.ttf`

| | FAIL | PASS |
|---|---|---|
| Original FontLab exports | 88 | 786 |
| Same, after `gf_fixup.py` | 26 | 850 |
| **`fontmake` build + `gf_fixup.py`** | **14** | **844** |

Run `./scripts/build.sh` to reproduce.

Everything that was metadata is fixed. What remains needs drawing or a
different build.

## Remaining

- **`glyph_coverage`** — 188 of GF Latin Core's 303 codepoints are missing.
  145 of those are accented forms of letters already drawn, so they can be
  built as composites once the ~15 accent marks exist. The genuinely new
  drawing is ~21 letters (Æ Ø ß Þ Ð Œ Ł Đ Ħ ª º and lowercase), 15 symbols,
  4 punctuation. Full list: `../../chelt/missing-glyphs.txt`.
- **`mandatory_glyphs`** — `.notdef` is blank; it needs a box drawn.
- **`equal_codepoint_coverage`** — `CheltenhamClassic-Italic` is missing the
  semicolon, U+003B. The other five styles have it. One glyph to draw, and a
  real bug in the shipped font rather than only a submission blocker.
- **`family_directory_name`** — only passes inside a `google/fonts` checkout
  at `ofl/cheltenhamclassic/`.

## Source metadata

Building straight from the `.glyphspackage` files gave every style
`usWeightClass 400` with bold and italic unmarked — 45 failures, worse than
the old FontLab exports. `gf_fixup.py` now derives weight, `fsSelection` and
`macStyle` from the filename instead of trusting the source, so the build is
correct either way. The tidier fix is in Glyphs: Font Info -> Masters ->
weight, plus style linking.

## Needs a decision before release

The drawn vertical metrics are ascender 792 / descender -208, summing to
exactly 1000 = **100% of UPM**. Google Fonts requires `hhea` to equal the typo
metrics *and* that sum to fall between 120% and 200% of UPM, so the metrics as
drawn cannot pass. `gf_fixup.py` pads them to **1000 / -250 = 125%**.

This changes default line spacing in every application. It is a typographic
decision, not a configuration fix. Check a specimen before release.

## Fixed in this branch

- Source packages and built fonts renamed `...ltalic` -> `...Italic`
  (lowercase L where a capital I was meant), and the four `url()` references
  in `docs/cheltenhamclassic.css` updated to match so the site keeps resolving.
- Root `LICENSE.txt` line 1 reformatted to GF's pattern.
- `README.md` glyph count corrected from "Over 150+" to 119. The misspelling
  inside the two `fontinfo.plist` files is left alone: it appears only in a
  comment recording the original FontLab path, which is history, not config.
