#!/usr/bin/env python3
"""
Post-process Libre Cheltenham TTFs into Google Fonts shape.

Run this after `fontmake` on every export. Everything here is metadata the
Glyphs sources do not currently carry, so patching the binaries by hand would
be undone by the next export — hence a script, in the repo, in the build.

Fixes, each tied to the FontBakery check it clears:
  googlefonts/fstype                 fsType 4 -> 0 (GF requires installable)
  googlefonts/font_copyright         name ID 0
  googlefonts/name/license           name ID 13, 14
  googlefonts/family_name_compliance "LibreCheltenham" -> "Libre Cheltenham"
  googlefonts/metadata/nameid/*      ID 1/2/4/6/16/17 per GF's RIBBI rules
  name/trailing_spaces               strip every name record
  opentype/italic_angle              measured from the outlines, not guessed
  linegaps + googlefonts/vertical_metrics  lineGap 0, win metrics from yMax/yMin
"""
import sys, os, glob, math
from fontTools.ttLib import TTFont, newTable

REPO = "https://github.com/vetrivelcsamy/cheltenham-classic"
COPYRIGHT = f"Copyright 2024 The Libre Cheltenham Project Authors ({REPO})"
LICENSE = ("This Font Software is licensed under the SIL Open Font License, "
           "Version 1.1. This license is available with a FAQ at: "
           "https://openfontlicense.org")
LICENSE_URL = "https://openfontlicense.org"
# Set by the release workflow from the git tag. A hardcoded version means a
# v1.1 release ships fonts that still claim 1.000, and OS font caches use this
# string to decide whether an installed font is stale.
VERSION = "Version " + os.environ.get("FONT_VERSION", "1.000")
FAMILY = "Libre Cheltenham"

# filename stem -> (subfamily, typographic subfamily, RIBBI, italic, weight)
# Weight and the fsSelection/macStyle bits are derived here rather than read
# from the sources: a fontmake build straight from the .glyphspackage files
# got all three wrong (every style claimed weight 400, bold and italic were
# unmarked), which is more failures than the old FontLab export had.
STYLES = {
    "Regular":      ("Regular",     None,            True,  False, 400),
    "Italic":       ("Italic",      None,            True,  True,  400),
    "Bold":         ("Bold",        None,            True,  False, 700),
    "BoldItalic":   ("Bold Italic", None,            True,  True,  700),
    "Medium":       ("Regular",     "Medium",        False, False, 500),
    "MediumItalic": ("Italic",      "Medium Italic", False, True,  500),
}
WEIGHT_NAMES = {400: "Regular", 500: "Medium", 700: "Bold"}
ELIDABLE = 0x2
FS_ITALIC, FS_BOLD, FS_REGULAR, FS_TYPO = 1 << 0, 1 << 5, 1 << 6, 1 << 7
MAC_BOLD, MAC_ITALIC = 1 << 0, 1 << 1
# Standard smart-dropout program: PUSHW 511, SCANCTRL, PUSHB 4, SCANTYPE.
SMART_DROPOUT = b"\xb8\x01\xff\x85\xb0\x04\x8d"
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
    subfam, typosub, ribbi, italic, weight = STYLES[stem]
    ps = f"LibreCheltenham-{stem}"
    notes = []

    # --- embedding -------------------------------------------------------
    if f["OS/2"].fsType != 0:
        notes.append(f"fsType {f['OS/2'].fsType} -> 0")
        f["OS/2"].fsType = 0

    # --- names -----------------------------------------------------------
    # Name ID 4 always carries the style, Regular included. Dropping it there
    # satisfies metadata/nameid/family_and_full_names but then breaks
    # metadata/match_fullname_postscript, which wants it to track the
    # PostScript name "LibreCheltenham-Regular". Both pass only if the full
    # name and METADATA.pb agree on "Libre Cheltenham Regular".
    full = f"{FAMILY} {subfam if ribbi else typosub}"
    set_name(f, 0, COPYRIGHT)
    set_name(f, 1, FAMILY if ribbi else f"{FAMILY} {typosub.replace(' Italic','')}")
    set_name(f, 2, subfam)
    set_name(f, 3, f"{VERSION.split()[1]};UKWN;{ps}")
    set_name(f, 4, full)
    set_name(f, 5, VERSION)
    set_name(f, 6, ps)
    set_name(f, 13, LICENSE)
    set_name(f, 14, LICENSE_URL)
    if ribbi:
        # RIBBI styles must NOT carry typographic family/subfamily records.
        # fontmake wrote 16='LibreCheltenham' / 17='BoldItalic' on Bold
        # Italic from the source, and leaving them there cascaded into eight
        # failures: camelcase family, a weightclass read off 'BoldItalic',
        # and every name/metadata consistency check.
        f["name"].removeNames(16)
        f["name"].removeNames(17)
    else:
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

    # --- weight and style bits ------------------------------------------
    os2_, head_ = f["OS/2"], f["head"]
    bold = weight >= 700
    os2_.usWeightClass = weight
    sel = FS_TYPO | (FS_ITALIC if italic else 0) | (FS_BOLD if bold else 0)
    if not italic and not bold:
        sel |= FS_REGULAR
    os2_.fsSelection = sel
    head_.macStyle = (MAC_BOLD if bold else 0) | (MAC_ITALIC if italic else 0)
    notes.append(f"weight={weight} fsSelection={sel:#010b} macStyle={head_.macStyle}")

    # --- gasp + smart dropout -------------------------------------------
    # Both are required by GF and neither survives a plain fontmake export.
    if "gasp" not in f:
        from fontTools.ttLib.tables._g_a_s_p import table__g_a_s_p
        g = table__g_a_s_p(); g.version = 1
        g.gaspRange = {0xFFFF: 0x000F}
        f["gasp"] = g
        notes.append("added gasp")
    prep_prog = f["prep"].program.getBytecode() if "prep" in f else b""
    if b"\x85" not in prep_prog:
        from fontTools.ttLib.tables._p_r_e_p import table__p_r_e_p
        from fontTools.ttLib.tables import ttProgram
        pr = table__p_r_e_p(); pr.program = ttProgram.Program()
        pr.program.fromBytecode(SMART_DROPOUT + prep_prog)
        f["prep"] = pr
        notes.append("added smart dropout to prep")

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
    # win is a clipping box, not a spacing value: it has to cover the family's
    # real extremes or Windows crops the tallest accents and deepest cedillas.
    # Line spacing stays on the typo values because USE_TYPO_METRICS is set,
    # so widening these costs nothing.
    os2.usWinAscent = max(ASC, family[0])
    os2.usWinDescent = max(DESC, family[1])
    os2.fsSelection |= 1 << 7            # USE_TYPO_METRICS
    notes.append(f"metrics -> typo=hhea {ASC}/-{DESC} ({(ASC+DESC)/10:.0f}% UPM), "
                 f"win {os2.usWinAscent}/{os2.usWinDescent}")

    # --- vendor id --------------------------------------------------------
    # Was four spaces. A real code is correct practice; registering it with
    # Microsoft is a separate step and until then the check still warns that
    # it does not recognise it, which its own text says is expected.
    f["OS/2"].achVendID = "VETR"

    # --- meta: declared and supported languages ----------------------------
    # googlefonts/meta/script_lang_tags wants the font to say what it is for.
    # Latin only, and the languages the Latin Core set actually covers.
    from fontTools.ttLib.tables import otTables
    meta = newTable("meta")
    meta.data = {"dlng": "Latn", "slng": "Latn"}
    f["meta"] = meta
    notes.append("meta: dlng/slng = Latn")

    # --- caret slope -------------------------------------------------------
    # The text cursor in an italic should lean with the text. Upright fonts
    # take rise 1 / run 0; italics take rise = UPM and run derived from the
    # angle, which is what opentype/caret_slope wants to see.
    ia = f["post"].italicAngle
    if abs(ia) < 0.01:
        hhea.caretSlopeRise, hhea.caretSlopeRun = 1, 0
    else:
        hhea.caretSlopeRise = f["head"].unitsPerEm
        hhea.caretSlopeRun = round(math.tan(math.radians(-ia)) * f["head"].unitsPerEm)
    notes.append(f"caret slope {hhea.caretSlopeRise}/{hhea.caretSlopeRun}")

    # --- STAT ------------------------------------------------------------
    # A static family still needs one: it is how a system knows these six
    # files are one family and which axis position each occupies. Each font
    # describes only its own location. The default values (weight 400, roman)
    # are elided so they do not appear in style names, and they carry the
    # links that let an app resolve bold and italic.
    from fontTools.otlLib.builder import buildStatTable
    wv = {"value": weight, "name": WEIGHT_NAMES[weight],
          "flags": ELIDABLE if weight == 400 else 0}
    if weight == 400:
        wv["linkedValue"] = 700
    iv = {"value": 1 if italic else 0, "name": "Italic" if italic else "Roman",
          "flags": 0 if italic else ELIDABLE}
    if not italic:
        iv["linkedValue"] = 1
    buildStatTable(f, [{"tag": "wght", "name": "Weight", "ordering": 0, "values": [wv]},
                       {"tag": "ital", "name": "Italic", "ordering": 1, "values": [iv]}],
                   elidedFallbackName="Regular")
    notes.append(f"STAT: wght={weight} ital={1 if italic else 0}")

    out = path
    f.save(out)
    f.close()
    return notes


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    paths = sorted(glob.glob(os.path.join(d, "LibreCheltenham-*.ttf")))

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
