#!/usr/bin/env python3
"""
Render the specimen that the Google Fonts submission and the article embed.

This used to be a one-off that lived nowhere, which is how its footer came to
claim 320 glyphs after the eszett took the font to 323, and how it would have
gone on saying "Cheltenham Classic" after the family was renamed. It is a
build artefact, so it belongs in the build.

Everything on the page is set in the font itself, including the style labels
and the footer. A specimen that needed a second typeface would not render the
same way on another machine, and a type specimen has no business borrowing
someone else's letters for its own captions.

The glyph count in the footer is counted from the binary, not typed.

    python3 scripts/specimen.py gf-submission documentation/article/specimen.png
"""
import glob
import os
import sys

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 900
MARGIN = 73
COL = 376                      # four columns across the content width

GROUND = (250, 250, 249)       # --stone-100
INK = (28, 25, 23)             # --stone-1000
BRAND = (230, 95, 46)          # the brand orange, unmodified
BODY = (68, 64, 60)            # --stone-800
MUTED = (168, 162, 158)        # --stone-500
FAINT = (120, 113, 108)        # --stone-600

# Two lines of the languages the Latin Core set reaches, which is the claim
# the specimen is making. Czech, Polish, Hungarian, Latvian, Icelandic; then
# Danish, French, Turkish, Maltese, Croatian, Romanian, Polish.
LINES = [
    "Příliš žluťoučký kůň úpěl ďábelské ódy · Zażółć gęślą jaźń · "
    "Árvíztűrő tükörfúrógép · Ģenerālis ķēniņš · Þingvellir, Guðrún ·",
    "Ærø, Søren Ørsted · cœur · Çalışma · Ħaġar Qim · Đakovo · "
    "Ştefan Ţara · Łódź",
]
STYLES = [("Regular", "REGULAR"), ("Medium", "MEDIUM"),
          ("Bold", "BOLD"), ("Italic", "ITALIC")]


def tracked(draw, xy, text, font, fill, track):
    """Draw letterspaced text; PIL has no tracking of its own."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + track
    return x


def main(built, out):
    def path(style):
        hits = glob.glob(f"{built}/*-{style}.ttf")
        if not hits:
            sys.exit(f"no {style} in {built}")
        return hits[0]

    reg = path("Regular")
    f = TTFont(reg, lazy=True)
    family = next(r.toUnicode() for r in f["name"].names
                  if r.nameID == 16 or r.nameID == 1)
    glyphs = f["maxp"].numGlyphs
    f.close()

    im = Image.new("RGB", (W, H), GROUND)
    d = ImageDraw.Draw(im)

    # the mark: the same square as the favicon
    d.rectangle([MARGIN, 64, MARGIN + 25, 89], fill=BRAND)

    # the family name, its last word picked out in the italic
    head, tail = family.rsplit(" ", 1) if " " in family else (family, "")
    size = 148
    fh = ImageFont.truetype(reg, size)
    fi = ImageFont.truetype(path("Italic"), size)
    while (d.textlength(head + " ", font=fh)
           + d.textlength(tail, font=fi)) > W - 2 * MARGIN and size > 60:
        size -= 2
        fh = ImageFont.truetype(reg, size)
        fi = ImageFont.truetype(path("Italic"), size)
    x = MARGIN
    d.text((x, 108), head, font=fh, fill=INK)
    x += d.textlength(head + " ", font=fh)
    d.text((x, 108), tail, font=fi, fill=BRAND)

    # four styles, labelled in the font's own capitals
    lab = ImageFont.truetype(reg, 13)
    for i, (style, label) in enumerate(STYLES):
        cx = MARGIN + i * COL
        tracked(d, (cx, 292), label, lab, MUTED, 2.6)
        d.text((cx, 322), "Handgloves",
               font=ImageFont.truetype(path(style), 44), fill=INK)

    # what the glyph set reaches
    body = ImageFont.truetype(reg, 27)
    d.text((MARGIN, 548), LINES[0], font=body, fill=BODY)
    d.text((MARGIN, 595), LINES[1], font=body, fill=BODY)

    foot = f"{glyphs} GLYPHS · THREE WEIGHTS WITH ITALICS · SIL OPEN FONT LICENSE 1.1"
    tracked(d, (MARGIN, 812), foot, ImageFont.truetype(reg, 13), FAINT, 1.9)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    im.save(out, optimize=True)
    print(f"  specimen: {out}  {family}, {glyphs} glyphs")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
