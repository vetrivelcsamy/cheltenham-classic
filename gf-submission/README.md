# Google Fonts submission

Working directory for onboarding Cheltenham Classic. Everything here is
produced by `../scripts/build.sh`; nothing is edited by hand except
`METADATA.pb` and the two files under `designer/`.

**The font passes and the CLA is signed.** One thing is outstanding and it
is the designer's: the provenance statement in the issue below. See
`../SUBMISSION.md`.

## Contents

| Path | Purpose |
| --- | --- |
| `CheltenhamClassic-*.ttf` | The six styles, built by `fontmake` and finished by `../scripts/gf_fixup.py` |
| `METADATA.pb` | Family metadata: six styles, weights, PostScript names, subsets, upstream repository |
| `OFL.txt` | Licence. Body is the canonical SIL text; only line 1 is ours |
| `article/ARTICLE.en_us.html` | The page shown on the Google Fonts listing |
| `article/specimen.png` | Rendered from the built fonts, so it cannot drift from what ships |
| `designer/info.pb`, `designer/bio.html` | For `catalog/designers/` in `google/fonts`. The bio is a **draft** and needs reading. No portrait: it is optional, and an `avatar` naming a missing file is worse than none |

There is deliberately no `DESCRIPTION.en_us.html`: a family may have a
description **or** an article, not both, and the article is what Google
Fonts prefers.

## Status

Copy this directory into a `google/fonts` fork at `ofl/cheltenhamclassic/`
and run `fontbakery check-googlefonts ofl/cheltenhamclassic/*.ttf`:

```
FAIL 0   WARN 36   PASS 902
```

323 glyphs across six styles, and the GF Latin Core set is complete.

The thirty warnings are itemised in `../SUBMISSION.md` with a reason each.
One of them, `outline_jaggy_segments` on `B`, is a false positive and should
be left standing: the node it flags is a deliberate corner at the waist, and
smoothing it would flatten the letter.

## Draft issue text

New families are submitted as an **issue**, not a pull request. Open
<https://github.com/google/fonts/issues/new?template=1_add-font.md>, title it
`Add Cheltenham Classic`, and adapt this:

> **Font Project Link:** https://github.com/vetrivelcsamy/cheltenham-classic
>
> **Is the font already published anywhere?** Specimen and downloads at
> https://vetrivelcsamy.github.io/cheltenham-classic/ — built from the same
> sources by CI, so the site and this submission are the same binaries.
>
> **Name.** No `Cheltenham` exists in the Google Fonts catalogue, and the OFL
> declares no Reserved Font Name. The qualifier follows the pattern the
> catalogue already uses for historical names — `Libre Franklin`,
> `Libre Baskerville`, `Libre Caslon`, `EB Garamond`. <!-- If you decided to
> rename to Libre Cheltenham, say so here instead. See ../SUBMISSION.md. -->
>
> **Description.** Cheltenham Classic is a serif family in three weights with
> matching italics, drawn in the spirit of Cheltenham, the 1896 face by
> Bertram Goodhue and Ingalls Kimball for the Cheltenham Press. 323 glyphs
> covering the whole of the GF Latin Core set.
>
> **Provenance.** <!-- YOU MUST WRITE THIS YOURSELF. Google Fonts requires
> the design to be original, or a legitimate revival of a public-domain
> design. Cheltenham (1896) is public domain. Say in your own words whether
> these outlines were drawn by you from specimens or from scratch, and state
> explicitly whether any geometry came from an existing digital Cheltenham.
> If any did, name it and its licence. Do not submit without answering this;
> see ../SUBMISSION.md. -->
>
> **Sources.** Six `.glyphspackage` files under `src/`. The build is
> `scripts/build.sh`: `fontmake` from source, then `scripts/gf_fixup.py` for
> the metadata the sources do not carry. FontBakery runs in CI on every push,
> and a release cannot be tagged while any combining mark is an empty outline.
>
> **Licence.** SIL OFL 1.1. The Google Individual CLA is signed.
>
> **Constructed glyphs.** Some outlines are built to the design's own
> measurements rather than drawn by hand: nine of the fourteen combining
> marks (grave, acute, circumflex, caron, tilde, breve, ring, hungarumlaut,
> ogonek), the AE and OE ligatures, eth, section, thorn, the pilcrow, and
> the eszett. Each takes its weights from the style's own stem and hairline,
> and the italics are sheared to their own measured angle, so they are
> consistent with the family. They read correctly at text size. They are
> listed in src/DRAWING.md section 2a. <!-- Say so plainly here rather than
> letting a reviewer find it; and if you have redrawn any of them by hand
> before filing, say that instead. -->

## Reproducing

```sh
pip install -r ../requirements.txt
../scripts/build.sh
```

Two build passes: one to measure the design, then the marks, the Latin Core
expansion and the kerning are regenerated from those measurements and it
builds again. The missing-glyph list is printed on every run — read that
rather than a rendered proof, because a browser silently substitutes a
fallback face for anything absent.
