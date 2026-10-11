"""Build every static image on the profile, plus the glyph atlas the qubit bot uses.

    pip install fonttools uharfbuzz
    python3 tools/build.py

Needs the fonts listed in tools/typeset.py inside tools/fonts. Writes:
    assets/banner-{dark,light}.svg      name and an animated d = 5 surface code
    assets/hdr-*-{dark,light}.svg       section headers
    assets/btn-*-{dark,light}.svg       link buttons
    assets/gate-*-{dark,light}.svg      the qubit's gate buttons
    scripts/glyphs.json                 mono glyph outlines for scripts/svgtext.py
and then redraws the qubit card from state/qubit.json.
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


def fit(text, font, max_w, size, tracking=0.0):
    while T.measure(text, font, size, tracking) > max_w:
        size -= 0.5
    return size


# ---------------------------------------------------------------- banner

# A distance-5 rotated surface code, [[25, 1, 5]]: 25 data qubits, 24 stabilizers.
# On a loop, two X errors appear, the Z stabilizers next to the ends of the chain
# light up, a decoder matches the pair, and the correction clears them.
W, H = 1280, 320
D, P = 5, 40                 # code distance, pitch between data qubits
CX, CY = 1030, 172           # centre of the patch
DUR = 9.0
ERR, SYN, MATCH, FIX, CALM = 1.0, 2.0, 3.4, 5.0, 6.2
ERRORS = [(1, 2), (2, 2)]    # data qubits hit by X, as (column, row)

TILES = {
    "dark": {"x": "#16161b", "z": "#0b0b0d", "edge": "#26262b"},
    "light": {"x": "#ebebf0", "z": "#f6f6f8", "edge": "#dcdce2"},
}


def q(i, j):
    return CX + (i - (D - 1) / 2) * P, CY + (j - (D - 1) / 2) * P


def stabilizers():
    """(kind, data qubits, shape) for every stabilizer of the rotated code.

    Bulk plaquette (a, b) is Z-type when a + b is even. Weight-2 X stabilizers sit
    on the top and bottom edges and Z stabilizers on the left and right, placed
    where they continue the checkerboard.
    """
    out = []
    for a in range(D - 1):
        for b in range(D - 1):
            kind = "z" if (a + b) % 2 == 0 else "x"
            out.append((kind, [(a, b), (a + 1, b), (a, b + 1), (a + 1, b + 1)], ("sq", a, b)))
    for a in range(D - 1):
        if (a - 1) % 2 == 1:
            out.append(("x", [(a, 0), (a + 1, 0)], ("top", a, 0)))
        if (a + D - 1) % 2 == 1:
            out.append(("x", [(a, D - 1), (a + 1, D - 1)], ("bottom", a, D - 1)))
    for b in range(D - 1):
        if (b - 1) % 2 == 0:
            out.append(("z", [(0, b), (0, b + 1)], ("left", 0, b)))
        if (D - 1 + b) % 2 == 0:
            out.append(("z", [(D - 1, b), (D - 1, b + 1)], ("right", D - 1, b)))
    assert len(out) == D * D - 1
    return out


def shape(spec):
    kind, i, j = spec
    x, y = q(i, j)
    r = P / 2
    if kind == "sq":
        return f"M{x} {y}h{P}v{P}h{-P}Z", (x + r, y + r)
    if kind == "top":
        return f"M{x} {y}A{r} {r} 0 0 1 {x + P} {y}Z", (x + r, y - r / 2)
    if kind == "bottom":
        return f"M{x} {y}A{r} {r} 0 0 0 {x + P} {y}Z", (x + r, y + r / 2)
    if kind == "left":
        return f"M{x} {y}A{r} {r} 0 0 0 {x} {y + P}Z", (x - r / 2, y + r)
    return f"M{x} {y}A{r} {r} 0 0 1 {x} {y + P}Z", (x + r / 2, y + r)


def kt(*ts):
    return ";".join(f"{t / DUR:.4f}" for t in ts)


def anim(values, times, attr="opacity"):
    return f'<animate attributeName="{attr}" dur="{DUR}s" repeatCount="indefinite" values="{values}" keyTimes="{kt(*times)}"/>'


def banner(mode):
    th, tile = THEMES[mode], TILES[mode]
    s = [f'<defs><filter id="glow" x="-150%" y="-150%" width="400%" height="400%"><feGaussianBlur stdDeviation="3"/></filter></defs>',
         f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="{th["panel"]}" stroke="{th["edge"]}"/>']

    # left column: who and what
    s.append(T.text("amoghdprasanna", "mono", 13, 64, 100, th["mute"], tracking=0.06))
    s.append(f'<circle cx="{64 + T.measure("amoghdprasanna", "mono", 13, 0.06) + 12:.1f}" cy="95.5" r="3" fill="{th["accent"]}"/>')
    s.append(T.text("Amogh D. Prasanna", "inter-display-light", 54, 61, 176, th["fg"], tracking=-0.015))
    s.append(T.text("quantum compilation · error correction · generative QML", "mono", 14, 64, 222, th["fg"], tracking=0.02))
    s.append(T.text("UMD  /  FERMILAB SQMS", "mono", 11.5, 64, 260, th["mute"], tracking=0.14))

    # right column: the code patch
    s.append(T.text("ROTATED SURFACE CODE  ·  d = 5  ·  [[25,1,5]]", "mono", 11, 1216, 52, th["mute"], anchor="end", tracking=0.1, cell=MONO_CELL))
    stabs = stabilizers()
    flipped = [st for st in stabs if st[0] == "z" and sum(d in ERRORS for d in st[1]) % 2 == 1]
    assert len(flipped) == 2
    for kind, _, spec in stabs:
        d, _ = shape(spec)
        s.append(f'<path d="{d}" fill="{tile[kind]}" stroke="{tile["edge"]}"/>')
    # syndromes light up, then clear after the correction
    for _, _, spec in flipped:
        d, _ = shape(spec)
        s.append(f'<path d="{d}" fill="{th["accent"]}" opacity="0">{anim("0;0;0.55;0.55;0;0", (0, SYN, SYN + 0.3, FIX + 0.4, FIX + 0.9, DUR))}</path>')
    # the decoder's matching between the two lit syndromes
    (x1, y1), (x2, y2) = (shape(f[2])[1] for f in flipped)
    L = math.hypot(x2 - x1, y2 - y1)
    s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{th["accent"]}" stroke-width="1.6" '
             f'stroke-linecap="round" stroke-dasharray="{L:.1f}" stroke-dashoffset="{L:.1f}" opacity="0">'
             f'{anim(f"{L:.1f};{L:.1f};0;0", (0, MATCH, MATCH + 0.7, DUR), "stroke-dashoffset")}'
             f'{anim("0;0;1;1;0;0", (0, MATCH, MATCH + 0.05, FIX + 0.6, FIX + 1.1, DUR))}</line>')
    for (x, y) in ((x1, y1), (x2, y2)):
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{th["accent"]}" opacity="0">{anim("0;0;1;1;0;0", (0, SYN, SYN + 0.3, FIX + 0.4, FIX + 0.9, DUR))}</circle>')
    # data qubits
    for i in range(D):
        for j in range(D):
            x, y = q(i, j)
            s.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{th["fg"]}" opacity="{0.22 if mode == "dark" else 0.1}" filter="url(#glow)"/>'
                     f'<circle cx="{x}" cy="{y}" r="3.6" fill="{th["fg"]}"/>')
    for (i, j) in ERRORS:
        x, y = q(i, j)
        s.append(f'<circle cx="{x}" cy="{y}" r="9.5" fill="none" stroke="{th["accent"]}" stroke-width="1.5" opacity="0">'
                 f'{anim("0;0;1;1;0;0", (0, ERR, ERR + 0.3, FIX, FIX + 0.35, DUR))}</circle>')
        s.append(f'<circle cx="{x}" cy="{y}" r="3.6" fill="{th["accent"]}" opacity="0">{anim("0;0;1;1;0;0", (0, ERR, ERR + 0.3, FIX, FIX + 0.35, DUR))}</circle>')
        # the correction: a brief flash as X is applied again
        s.append(f'<circle cx="{x}" cy="{y}" r="12" fill="{th["fg"]}" opacity="0" filter="url(#glow)">{anim("0;0;0.8;0;0", (0, FIX, FIX + 0.15, FIX + 0.6, DUR))}</circle>')

    # each step lit while it happens
    steps = [("ERROR", ERR, SYN), ("SYNDROME", SYN, MATCH), ("MATCH", MATCH, FIX), ("CORRECT", FIX, CALM)]
    total = sum(T.measure(w, "mono", 11, 0.12) for w, *_ in steps) + 18 * (len(steps) - 1)
    cap_x = CX - total / 2
    for word, a, b in steps:
        s.append(T.text(word, "mono", 11, cap_x, 298, th["faint"], tracking=0.12))
        s.append(T.text(word, "mono", 11, cap_x, 298, th["fg"], tracking=0.12, extra=' opacity="0"',
                        child=anim("0;0;1;1;0;0", (0, a, a + 0.15, b - 0.1, b + 0.1, DUR))))
        cap_x += T.measure(word, "mono", 11, 0.12) + 18
    return svg(W, H, "".join(s), "Amogh D. Prasanna: quantum compilation, error correction, generative QML. UMD and Fermilab SQMS. "
               "An animated distance-5 rotated surface code: an error chain lights two syndromes, a decoder matches them, and the correction clears them.")


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
GATES = ["H", "X", "Y", "Z", "S", "T", "measure", "reset"]


def main():
    ASSETS.mkdir(exist_ok=True)
    atlas()
    for mode in THEMES:
        write("banner", mode, banner(mode))
        for key, (num, title) in HEADERS.items():
            write(f"hdr-{key}", mode, header(mode, num, title))
        for key, label in BUTTONS.items():
            write(f"btn-{key}", mode, button(mode, label, arrow=key != "email"))
        for g in GATES:
            write(f"gate-{g.lower()}", mode, gate(mode, g))
    import qubit
    qubit.render(qubit.load())


if __name__ == "__main__":
    main()
