"""Build every static image on the profile, plus the glyph atlas the qubit bot uses.

    pip install fonttools uharfbuzz
    python3 tools/build.py

Needs the fonts listed in tools/typeset.py inside tools/fonts. Writes:
    assets/hdr-*-{dark,light}.svg       section headers
    assets/btn-*-{dark,light}.svg       link buttons and the surface code's controls
    assets/gate-*-{dark,light}.svg      the qubit's gate buttons
    scripts/glyphs.json                 mono glyph outlines for scripts/svgtext.py
    scripts/banner_text.json            the header's name block, for scripts/qec.py
and then redraws the qubit card and the surface-code header from state/.
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


def write(name, mode, body):
    (ASSETS / f"{name}-{mode}.svg").write_text(body)


# ---------------------------------------------------------------- banner text

# The header itself is redrawn by scripts/qec.py on every move, since it shows the
# live surface code. That script has only the mono glyph atlas, so the name block
# on the left is drawn here once and stored as SVG fragments it pastes in.

def banner_text(mode):
    th = THEMES[mode]
    handle = "amoghdprasanna"
    return "".join([
        T.text(handle, "mono", 13, 64, 104, th["mute"], tracking=0.06),
        f'<circle cx="{64 + T.measure(handle, "mono", 13, 0.06) + 12:.1f}" cy="99.5" r="3" fill="{th["accent"]}"/>',
        T.text("Amogh D. Prasanna", "inter-display-light", 54, 61, 180, th["fg"], tracking=-0.015),
        T.text("quantum compilation · error correction · generative QML", "mono", 14, 64, 226, th["fg"], tracking=0.02),
        T.text("UMD  /  FERMILAB SQMS", "mono", 11.5, 64, 264, th["mute"], tracking=0.14),
    ])


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


# ---------------------------------------------------------------- gate buttons

def gate(mode, name):
    th = THEMES[mode]
    w, h = 56, 56
    s = [f'<line x1="0" y1="28" x2="{w}" y2="28" stroke="{th["faint"]}" stroke-width="1.2"/>',
         f'<rect x="8.6" y="8.6" width="38.8" height="38.8" rx="7" fill="{th["panel"]}" stroke="{th["fg"]}" stroke-width="1.3"/>']
    if name == "measure":
        # the standard meter symbol
        s.append(f'<path d="M17 36a11 11 0 0 1 22 0" fill="none" stroke="{th["fg"]}" stroke-width="1.4"/>'
                 f'<path d="M28 36L35.5 21.5" stroke="{th["accent"]}" stroke-width="1.6" stroke-linecap="round"/>'
                 f'<circle cx="28" cy="36" r="1.8" fill="{th["fg"]}"/>')
    elif name == "reset":
        s.append(T.text("|0⟩", "mono-medium", 14, 28, 33, th["fg"], anchor="middle", cell=MONO_CELL))
    else:
        s.append(T.text(name, "mono-medium", 19, 28, 35, th["fg"], anchor="middle"))
    label = {"measure": "Measure the qubit", "reset": "Reset the qubit to |0⟩"}.get(name, f"Apply the {name} gate")
    return svg(w, h, "".join(s), label)


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
    "qubit": ("03", "A SHARED QUBIT"),
}
BUTTONS = {"website": "WEBSITE", "linkedin": "LINKEDIN", "email": "EMAIL"}
QEC_BUTTONS = {"x": "X ERROR", "z": "Z ERROR", "decode": "DECODE", "reset": "RESET"}
GATES = ["H", "X", "Y", "Z", "S", "T", "measure", "reset"]


def main():
    ASSETS.mkdir(exist_ok=True)
    atlas()
    for mode in THEMES:
        for key, (num, title) in HEADERS.items():
            write(f"hdr-{key}", mode, header(mode, num, title))
        for key, label in BUTTONS.items():
            write(f"btn-{key}", mode, button(mode, label, arrow=key != "email"))
        for g in GATES:
            write(f"gate-{g.lower()}", mode, gate(mode, g))
        for key, label in QEC_BUTTONS.items():
            write(f"btn-qec-{key}", mode, button(mode, label, arrow=False))
    (ROOT / "scripts" / "banner_text.json").write_text(json.dumps({m: banner_text(m) for m in THEMES}) + "\n")
    import qec
    import qubit
    qubit.render(qubit.load())
    qec.render(qec.load())


if __name__ == "__main__":
    main()
