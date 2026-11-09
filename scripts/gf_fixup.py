#!/usr/bin/env python3
"""
Post-process Cheltenham Classic TTFs into Google Fonts shape.

Run this after `fontmake` on every export. Everything here is metadata the
Glyphs sources do not currently carry, so patching the binaries by hand would
be undone by the next export — hence a script, in the repo, in the build.

Fixes, each tied to the FontBakery check it clears:
  googlefonts/fstype                 fsType 4 -> 0 (GF requires installable)
  googlefonts/font_copyright         name ID 0
  googlefonts/name/license           name ID 13, 14
  googlefonts/family_name_compliance "CheltenhamClassic" -> "Cheltenham Classic"
  googlefonts/metadata/nameid/*      ID 1/2/4/6/16/17 per GF's RIBBI rules
  name/trailing_spaces               strip every name record
  opentype/italic_angle              measured from the outlines, not guessed
  linegaps + googlefonts/vertical_metrics  lineGap 0, win metrics from yMax/yMin
"""
import sys, os, glob
from fontTools.ttLib import TTFont

REPO = "https://github.com/vetrivelcsamy/cheltenham-classic"
COPYRIGHT = f"Copyright 2024 The Cheltenham Classic Project Authors ({REPO})"
LICENSE = ("This Font Software is licensed under the SIL Open Font License, "
           "Version 1.1. This license is available with a FAQ at: "
           "https://openfontlicense.org")
LICENSE_URL = "https://openfontlicense.org"
VERSION = "Version 1.000"
FAMILY = "Cheltenham Classic"

# filename stem -> (subfamily, typographic subfamily, is RIBBI, italic)
STYLES = {
    "Regular":      ("Regular",     None,            True,  False),
    "Italic":       ("Italic",      None,            True,  True),
    "Bold":         ("Bold",        None,            True,  False),
    "BoldItalic":   ("Bold Italic", None,            True,  True),
    "Medium":       ("Regular",     "Medium",        False, False),
    "MediumItalic": ("Italic",      "Medium Italic", False, True),
}
WIN, MAC = (3, 1, 0x409), (1, 0, 0)


def measure_italic_angle(font):
    """Angle from the actual outlines: how far the stem leans between the
    baseline and the cap line. Guessing -12 would be a design decision; this
    reads what was drawn."""
    import math
    gs = font.getGlyphSet()
    for name in ("I", "l", "H"):
        if name not in gs:
            continue
        from fontTools.pens.recordingPen import RecordingPen
        pen = RecordingPen()
        gs[name].draw(pen)
        pts = [p for op, args in pen.value for p in args]
        if len(pts) < 4:
            continue
        ys = [p[1] for p in pts]
        lo, hi = min(ys), max(ys)
        if hi - lo < 100:
            continue
        band = (hi - lo) * 0.15
        low = [p for p in pts if p[1] <= lo + band]
        high = [p for p in pts if p[1] >= hi - band]
        if not low or not high:
            continue
        dx = min(p[0] for p in high) - min(p[0] for p in low)
        dy = hi - lo
        return round(-math.degrees(math.atan2(dx, dy)), 1)
    return None


def set_name(font, nid, value):
    for plat in (WIN, MAC):
        font["name"].setName(value, nid, *plat)


def fixup(path, family):
    f = TTFont(path)
    stem = os.path.basename(path).rsplit("-", 1)[-1][:-4]
    subfam, typosub, ribbi, italic = STYLES[stem]
    ps = f"CheltenhamClassic-{stem}"
    notes = []

    # --- embedding -------------------------------------------------------
    if f["OS/2"].fsType != 0:
        notes.append(f"fsType {f['OS/2'].fsType} -> 0")
        f["OS/2"].fsType = 0

    # --- names -----------------------------------------------------------
    full = FAMILY if stem == "Regular" else f"{FAMILY} {subfam if ribbi else typosub}"
    set_name(f, 0, COPYRIGHT)
    set_name(f, 1, FAMILY if ribbi else f"{FAMILY} {typosub.replace(' Italic','')}")
    set_name(f, 2, subfam)
    set_name(f, 3, f"1.000;UKWN;{ps}")
    set_name(f, 4, full)
    set_name(f, 5, VERSION)
    set_name(f, 6, ps)
    set_name(f, 13, LICENSE)
    set_name(f, 14, LICENSE_URL)
    if not ribbi:
        set_name(f, 16, FAMILY)
        set_name(f, 17, typosub)
    for rec in f["name"].names:          # name/trailing_spaces
        s = rec.toUnicode()
        if s != s.strip():
            rec.string = s.strip()
    notes.append(f"names -> '{FAMILY}' / {subfam}")

    # --- italic angle, measured -----------------------------------------
    if italic:
        ang = measure_italic_angle(f)
        if ang and ang < -0.5:
            f["post"].italicAngle = ang
            notes.append(f"italicAngle 0.0 -> {ang} (measured)")
        else:
            notes.append("italicAngle UNRESOLVED - outlines look upright")

    # --- vertical metrics -----------------------------------------------
    # Two rules that interact:
    #   os2_metrics_match_hhea  -> hhea MUST equal the typo metrics (not win)
    #   googlefonts/vertical_metrics -> hhea asc + |desc| + gap must be
    #                                   120-200% of UPM
    # The drawn metrics are 792 / -208 = 1000 = 100% of UPM, so they cannot
    # pass as-is. Padded to 1000 / -250 = 125%, a common Google Fonts choice.
    # NOTE: this changes default line spacing in every app. It is a design
    # decision, not a mechanical fix - confirm before release.
    os2, hhea = f["OS/2"], f["hhea"]
    ASC, DESC = 1000, 250
    os2.sTypoAscender = hhea.ascender = ASC
    os2.sTypoDescender = hhea.descender = -DESC
    os2.sTypoLineGap = hhea.lineGap = 0
    os2.usWinAscent, os2.usWinDescent = ASC, DESC
    os2.fsSelection |= 1 << 7            # USE_TYPO_METRICS
    notes.append(f"metrics -> typo=hhea=win {ASC}/-{DESC} ({(ASC+DESC)/10:.0f}% UPM)")

    out = path
    f.save(out)
    f.close()
    return notes


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    paths = sorted(glob.glob(os.path.join(d, "CheltenhamClassic-*.ttf")))

    # Pass 1: one set of vertical metrics for the whole family.
    ymax, ymin, tasc, tdesc = [], [], [], []
    for p in paths:
        g = TTFont(p, lazy=True)
        ymax += [g["glyf"][n].yMax for n in g.getGlyphOrder() if g["glyf"][n].numberOfContours]
        ymin += [g["glyf"][n].yMin for n in g.getGlyphOrder() if g["glyf"][n].numberOfContours]
        tasc.append(g["OS/2"].sTypoAscender); tdesc.append(g["OS/2"].sTypoDescender)
        g.close()
    family = (max(max(ymax), max(tasc)), abs(min(min(ymin), min(tdesc))))
    print(f"family vertical metrics: ascent {family[0]}, descent {family[1]}")

    # Pass 2: apply.
    for p in paths:
        print(f"\n{os.path.basename(p)}")
        for n in fixup(p, family):
            print(f"   - {n}")
