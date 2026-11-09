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
| Before | 88 | 786 |
| After `gf_fixup.py` | 26 | 850 |

Everything that was metadata is fixed. What remains needs drawing or a
different build.

## Remaining

- **`glyph_coverage`** — 188 of GF Latin Core's 303 codepoints are missing.
  145 of those are accented forms of letters already drawn, so they can be
  built as composites once the ~15 accent marks exist. The genuinely new
  drawing is ~21 letters (Æ Ø ß Þ Ð Œ Ł Đ Ħ ª º and lowercase), 15 symbols,
  4 punctuation. Full list: `../../chelt/missing-glyphs.txt`.
- **`mandatory_glyphs`** — `.notdef` is blank; it needs a box drawn.
- **`smart_dropout`** — comes from the `fontmake` / ttfautohint build, cannot
  be patched post-export.
- **`family_directory_name`** — only passes inside a `google/fonts` checkout
  at `ofl/cheltenhamclassic/`.

## Needs a decision before release

The drawn vertical metrics are ascender 792 / descender -208, summing to
exactly 1000 = **100% of UPM**. Google Fonts requires `hhea` to equal the typo
metrics *and* that sum to fall between 120% and 200% of UPM, so the metrics as
drawn cannot pass. `gf_fixup.py` pads them to **1000 / -250 = 125%**.

This changes default line spacing in every application. It is a typographic
decision, not a configuration fix. Check a specimen before release.

## Also worth fixing in the repo

- `src/CheltenhamClassicBoldltalic.glyphspackage` and
  `...MediumItalic...` use a lowercase **L** where **I**talic is meant.
- Root `LICENSE.txt` line 1 reads `Copyright (c) 2024 The Cheltenham Classic
  Typeface Project Authors`. GF's pattern rejects `(c)` and expects the family
  name exactly, without "Typeface". Corrected copy is in `OFL.txt` here.
- `README.md` says "150+ glyphs"; the sources hold 116 and the built TTFs 119.
