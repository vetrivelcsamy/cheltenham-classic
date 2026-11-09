# Submitting Cheltenham Classic to Google Fonts

Everything that can be prepared is prepared. What is left needs you.

## Where it stands

Run `./scripts/build.sh`, then copy `gf-submission/` into a `google/fonts`
fork at `ofl/cheltenhamclassic/` and run FontBakery there:

```
FAIL 12   WARN 37   PASS 889
```

**All twelve failures are the same two glyphs.** `glyph_coverage` and
`shape_languages` both fail only because `ß` (U+00DF) and `ẞ` (U+1E9E) are
missing, and Google Fonts requires the complete GF Latin Core set. Nothing
else blocks the submission.

## Blockers — only you can clear these

### 1. Draw `ß` and `ẞ`

The hard blocker. Three constructions were tried and thrown away: the
historical long-s + s ligature (an overlapping `ls` smudge), a two-storey `B`
on an ascender (a blob with no counter), and a stem with a built bowl plus a
stroked lower curve (collided into the stem). See `src/DRAWING.md`.

Thorn worked because it decomposes into a stem plus a bowl. The eszett does
not decompose into anything the font holds.

### 2. Confirm the provenance, in writing

Google Fonts requires the design to be *"original, or a legitimate revival of
a design in the public domain."* They will ask, and the answer has to be
yours:

- Cheltenham (Bertram Goodhue and Ingalls Kimball, 1896) is public domain,
  so a revival is legitimate **in principle**.
- But: was this drawn from specimens, from scratch, or derived from an
  existing digital font? If any outline came from another digital typeface,
  its licence governs and that must be declared.
- The sources carry FontLab metadata pointing at
  `C:/Users/vetri/Documents/Cheltenham-Modern/Cheltenham-Regular.vfc`.
  Be ready to say what that file was.

### 3. Sign the Google CLA

Every copyright holder must complete it. If anyone else contributed
outlines, they sign too.

### 4. Kerning by eye

`scripts/kern.py` measures the white between outlines and corrects pairs that
are loose against their own category's norm, which gets `AV`, `To`, `Yo`,
`LT` and `P.` to a reasonable place and leaves `nn`, `oo`, `HH` and body text
untouched. It is a floor, not a substitute for kerning by eye. Numerals,
accented letters and the pairs that only a designer notices are untouched.

### 5. Review what was constructed rather than drawn

A curation reviewer will look at these. All are listed in
`src/DRAWING.md` §2a:

- the nine constructed combining marks (grave, acute, circumflex, caron,
  tilde, breve, ring, hungarumlaut, ogonek)
- `Æ ð § Þ þ ¶`, whose bowls and joins come from ellipses

They are consistent with the design's measurements and correct at text size.
They are not drawn by hand, and at display size that shows.

### 6. Write your own designer bio

`gf-submission/designer/bio.html` is a stub on purpose. Google Fonts keeps
profiles at `catalog/designers/<slug>/` with `info.pb`, `bio.html` and a
portrait. A biography is not something to generate on someone's behalf.

## Known warnings, and why they are left

| Warning | Why |
| --- | --- |
| `outline_jaggy_segments`, `contour_count` | The constructed glyphs. Both resolve when they are redrawn. |
| `vendor_id` | Blank. Google Fonts normally assigns or accepts this during onboarding. |
| `designer_profiles` | Clears once your profile is merged into `google/fonts`. |
| `soft_dotted` | The common cases are handled by the new `ccmp`. The remainder are rarer mark combinations. |

## The submission itself

New families are submitted as an **issue**, not a pull request.

1. Open <https://github.com/google/fonts/issues/new?template=1_add-font.md>
   — the "Submitting a new OFL Font" template.
2. Title: `Add Cheltenham Classic`.
3. Point it at `https://github.com/vetrivelcsamy/cheltenham-classic`, which
   already has what they ask for: sources in `.glyphspackage` form, a
   `fontmake` build, FontBakery in CI, and an OFL.
4. Tag a release first so there is a fixed version to review.

Draft issue text is in `gf-submission/README.md`.
