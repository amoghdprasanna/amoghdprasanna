"""Text to SVG paths.

GitHub serves README images through its own proxy, so an SVG cannot load a
webfont. Drawing every glyph as a path is the only way to get the same type on
every machine. This module shapes text with HarfBuzz (so kerning is right) and
emits outlines with fontTools. It is a build-time tool; the Action that runs on
each qubit move uses the precomputed atlas in scripts/glyphs.json instead.

Fonts are not committed. Put the files named in FONTS into tools/fonts, or
point FONT_DIR at a folder holding them. Inter and IBM Plex Mono are OFL;
DejaVu Sans Mono and FreeSerif fill in the math glyphs Plex lacks.
"""
import os
from functools import lru_cache
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

FONT_DIR = Path(os.environ.get("FONT_DIR", Path(__file__).parent / "fonts"))
FONTS = {
    "inter-light": "Inter-Light.otf",
    "inter-display-light": "InterDisplay-Light.otf",
    "inter": "Inter-Regular.otf",
    "inter-medium": "Inter-Medium.otf",
    "mono": "IBMPlexMono-Regular.woff",
    "mono-medium": "IBMPlexMono-Medium.woff",
    "dejavu-mono": "DejaVuSansMono.ttf",
    "serif": "FreeSerif.ttf",
    "serif-italic": "FreeSerifItalic.ttf",
}
# where to look when the primary face has no glyph for a character
FALLBACK = {"mono": ["dejavu-mono", "serif"], "mono-medium": ["dejavu-mono", "serif"]}


@lru_cache(None)
def face(name):
    path = FONT_DIR / FONTS[name]
    tt = TTFont(path)
    if path.suffix == ".woff":
        # HarfBuzz wants raw sfnt bytes
        from io import BytesIO
        buf = BytesIO()
        tt.flavor = None
        tt.save(buf)
        data = buf.getvalue()
        tt = TTFont(BytesIO(data))
    else:
        data = path.read_bytes()
    hbface = hb.Face(data)
    hbfont = hb.Font(hbface)
    return tt, hbfont, tt["head"].unitsPerEm, tt.getBestCmap(), tt.getGlyphSet()


def _runs(text, font):
    """Split text into runs by which font covers each character."""
    chain = [font] + FALLBACK.get(font, [])
    runs = []
    for ch in text:
        pick = next((f for f in chain if ord(ch) in face(f)[3]), font)
        if runs and runs[-1][0] == pick:
            runs[-1][1] += ch
        else:
            runs.append([pick, ch])
    return runs


def _shape(text, font, features):
    tt, hbfont, upem, _, _ = face(font)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, features or {})
    order = tt.getGlyphOrder()
    return [(order[i.codepoint], p.x_advance, p.x_offset, p.y_offset) for i, p in zip(buf.glyph_infos, buf.glyph_positions)], upem


class PathPen(BasePen):
    """SVG path data using only absolute M, L, Q, C and Z, so scripts/svgtext.py can transform it by pairs."""

    def __init__(self, glyphset):
        super().__init__(glyphset)
        self.d = []

    def _pt(self, *pts):
        return " ".join(f"{x:.2f} {y:.2f}" for x, y in pts)

    def _moveTo(self, pt):
        self.d.append("M" + self._pt(pt))

    def _lineTo(self, pt):
        self.d.append("L" + self._pt(pt))

    def _qCurveToOne(self, p1, p2):
        self.d.append("Q" + self._pt(p1, p2))

    def _curveToOne(self, p1, p2, p3):
        self.d.append("C" + self._pt(p1, p2, p3))

    def _closePath(self):
        self.d.append("Z")


def measure(text, font, size, tracking=0.0, features=None, cell=None):
    return layout(text, font, size, 0, 0, tracking=tracking, features=features, cell=cell)[1]


def layout(text, font, size, x, y, anchor="start", tracking=0.0, features=None, cell=None):
    """Return (path d, width). tracking is in em. cell forces a fixed advance in em (monospace fallback)."""
    pieces, cursor = [], 0.0
    for run_font, run in _runs(text, font):
        glyphs, upem = _shape(run, run_font, features)
        gs = face(run_font)[4]
        s = size / upem
        for name, adv, dx, dy in glyphs:
            advance = cell * size if cell else adv * s
            # centre a fallback glyph inside a fixed mono cell
            shift = (advance - adv * s) / 2 if cell and run_font != font else 0
            pieces.append((gs, name, cursor + shift + dx * s, dy * s, s))
            cursor += advance + tracking * size
    width = cursor - (tracking * size if text else 0)
    x0 = x - (width if anchor == "end" else width / 2 if anchor == "middle" else 0)
    d = []
    for gs, name, gx, gy, s in pieces:
        pen = PathPen(gs)  # needs the glyph set to resolve composite glyphs
        gs[name].draw(TransformPen(pen, (s, 0, 0, -s, x0 + gx, y - gy)))
        d.append("".join(pen.d))
    return _round("".join(d)), width


def _round(d):
    import re
    return re.sub(r"-?\d+\.\d+", lambda m: f"{float(m.group()):.2f}".rstrip("0").rstrip("."), d)


def text(t, font, size, x, y, fill, anchor="start", tracking=0.0, features=None, cell=None, extra="", child=""):
    d, _ = layout(t, font, size, x, y, anchor, tracking, features, cell)
    if not d:
        return ""
    return f'<path d="{d}" fill="{fill}"{extra}>{child}</path>' if child else f'<path d="{d}" fill="{fill}"{extra}/>'
