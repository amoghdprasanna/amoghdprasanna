"""Build every static image on the profile, plus the glyph atlas the surface-code bot uses.

    pip install fonttools uharfbuzz
    python3 tools/build.py

Needs the fonts listed in tools/typeset.py inside tools/fonts. Writes:
    assets/hdr-*-{dark,light}.svg       section headers
    assets/btn-*-{dark,light}.svg       link buttons and the surface code's controls
    scripts/glyphs.json                 mono glyph outlines for scripts/svgtext.py
    scripts/banner_text.json            the header's name block, for scripts/qec.py
and then redraws the surface-code header from state/qec.json.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "scripts")]
import typeset as T  # noqa: E402
from theme import THEMES, svg  # noqa: E402

ASSETS = ROOT / "assets"
MONO_CELL = 0.6  # IBM Plex Mono advance, in em


def fit(text, font, max_w, size, tracking=0.0):
    while T.measure(text, font, size, tracking) > max_w:
        size -= 0.5
    return size


def write(name, mode, body):
    (ASSETS / f"{name}-{mode}.svg").write_text(body)


# ---------------------------------------------------------------- banner text

# The header itself is redrawn by scripts/qec.py on every move, since it shows the
# live surface code. That script has only the mono glyph atlas, so the name block
# on the left is drawn here once and stored as SVG fragments it pastes in.

def banner_text(mode, phone=False):
    th = THEMES[mode]
    handle = "amoghdprasanna"
    if not phone:
        return "".join([
            T.text(handle, "mono", 15, 64, 104, th["mute"], tracking=0.06),
            f'<circle cx="{64 + T.measure(handle, "mono", 15, 0.06) + 13:.1f}" cy="98.5" r="3.5" fill="{th["accent"]}"/>',
            T.text("Amogh D. Prasanna", "inter-display-light", 58, 61, 184, th["fg"], tracking=-0.015),
            T.text("quantum compilation · error correction · quantum simulation", "mono", 19, 64, 234, th["fg"], tracking=0.01),
            T.text("UMD, College Park", "mono", 15, 64, 276, th["mute"], tracking=0.14),
        ])
    # a tall layout for phones: everything bigger, one topic per line
    size = fit("Amogh D. Prasanna", "inter-display-light", 612, 80, -0.015)
    s = [T.text(handle, "mono", 24, 54, 92, th["mute"], tracking=0.06),
         f'<circle cx="{54 + T.measure(handle, "mono", 24, 0.06) + 18:.1f}" cy="83.5" r="5" fill="{th["accent"]}"/>',
         T.text("Amogh D. Prasanna", "inter-display-light", size, 51, 186, th["fg"], tracking=-0.015)]
    for i, topic in enumerate(["quantum compilation", "error correction", "quantum simulation"]):
        s.append(T.text(topic, "mono", 28, 54, 252 + i * 42, th["fg"], tracking=0.01))
    s.append(T.text("UMD, College Park", "mono", 22, 54, 398, th["mute"], tracking=0.14))
    return "".join(s)


# ---------------------------------------------------------------- section headers

# Drawn wide and cropped from the right: the README shows them at width 100% and
# a fixed height, so the type stays the same size on a phone and the rule simply
# runs to whatever edge the column has.
HW, HH = 1600, 44


def header(mode, num, title):
    th = THEMES[mode]
    s = [T.text(num, "mono", 12, 0, 27, th["accent"], tracking=0.1)]
    x = 34
    s.append(T.text(title, "mono-medium", 12, x, 27, th["fg"], tracking=0.16))
    x += T.measure(title, "mono-medium", 12, 0.16) + 18
    s.append(f'<line x1="{x:.1f}" y1="22.5" x2="{HW}" y2="22.5" stroke="{th["line"]}"/>')
    return svg(HW, HH, "".join(s), title.title(), aspect="xMinYMid slice")


# ---------------------------------------------------------------- link buttons

def button(mode, label, arrow=True):
    th = THEMES[mode]
    size, tr = 11.5, 0.14
    tw = T.measure(label, "mono-medium", size, tr)
    w = math.ceil(tw + 36 + (16 if arrow else 0))
    h = 34
    s = [f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="17" fill="none" stroke="{th["faint"]}"/>',
         T.text(label, "mono-medium", size, 18, 21.2, th["fg"], tracking=tr)]
    if arrow:
        ax = 18 + tw + 9
        s.append(f'<path d="M{ax} {21.5}L{ax + 7} {14.5}M{ax + 1.5} {14.5}H{ax + 7}V{20}" fill="none" stroke="{th["mute"]}" stroke-width="1.3"/>')
    return svg(w, h, "".join(s), label.title())


# ---------------------------------------------------------------- glyph atlas

ATLAS_CHARS = "".join(chr(c) for c in range(32, 127)) + "⟨⟩ψ·×−─│θφπ→↗…°±√"


def atlas():
    out = {"cell": MONO_CELL}
    for weight, font in (("regular", "mono"), ("medium", "mono-medium")):
        glyphs = {}
        for ch in ATLAS_CHARS:
            d, _ = T.layout(ch, font, 1000, 0, 0, cell=MONO_CELL)
            glyphs[ch] = T._round(d) if d else ""
        out[weight] = glyphs
    (ROOT / "scripts" / "glyphs.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")


HEADERS = {
    "why": ("01", "WHY THIS CODE IS HERE"),
    "now": ("02", "OPEN QUESTIONS"),
}
BUTTONS = {"website": "WEBSITE", "linkedin": "LINKEDIN", "email": "EMAIL"}
QEC_BUTTONS = {"x": "X ERROR", "z": "Z ERROR", "decode": "DECODE", "reset": "RESET"}


def main():
    ASSETS.mkdir(exist_ok=True)
    atlas()
    for mode in THEMES:
        for key, (num, title) in HEADERS.items():
            write(f"hdr-{key}", mode, header(mode, num, title))
        for key, label in BUTTONS.items():
            write(f"btn-{key}", mode, button(mode, label, arrow=key != "email"))
        for key, label in QEC_BUTTONS.items():
            write(f"btn-qec-{key}", mode, button(mode, label, arrow=False))
    texts = {m: banner_text(m) for m in THEMES} | {f"{m}-mobile": banner_text(m, phone=True) for m in THEMES}
    (ROOT / "scripts" / "banner_text.json").write_text(json.dumps(texts) + "\n")
    import qec
    qec.render(qec.load())


if __name__ == "__main__":
    main()
