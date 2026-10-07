"""Build every static image on the profile, plus the glyph atlas the qubit bot uses.

    pip install fonttools uharfbuzz
    python3 tools/build.py

Needs the fonts listed in tools/typeset.py inside tools/fonts. Writes:
    assets/banner-{dark,light}.svg      animated tweezer array and title
    assets/hdr-*-{dark,light}.svg       section headers
    assets/btn-*-{dark,light}.svg       link buttons
    assets/gate-*-{dark,light}.svg      the qubit's gate buttons
    scripts/glyphs.json                 mono glyph outlines for scripts/svgtext.py
and then redraws the qubit card from state/qubit.json.
"""
import json
import math
import random
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

W, H = 1280, 400
COLS, ROWS, PITCH = 8, 6, 50
GX, GY = 846, 62            # centre of the top-left trap
TARGET = [(c, r) for r in range(1, 5) for c in range(2, 6)]  # 4 x 4 block in the middle
DUR = 10.0
LOAD, SORT, HOLD, FADE = 0.3, 2.2, 5.6, 9.0


def site(c, r):
    return GX + c * PITCH, GY + r * PITCH


def loaded_sites():
    # a fixed stochastic loading pattern, about half full, enough to fill the block
    rng = random.Random(7)
    while True:
        occ = [(c, r) for r in range(ROWS) for c in range(COLS) if rng.random() < 0.55]
        if len(occ) >= len(TARGET) + 4:
            return occ


def assign(occ):
    """Greedy nearest assignment of loaded atoms to target traps."""
    pairs = sorted(((abs(a[0] - t[0]) + abs(a[1] - t[1]), a, t) for a in occ for t in TARGET))
    used_a, used_t, plan = set(), set(), {}
    for _, a, t in pairs:
        if a not in used_a and t not in used_t:
            used_a.add(a), used_t.add(t)
            plan[a] = t
    return plan


def kt(*ts):
    return ";".join(f"{t / DUR:.4f}" for t in ts)


def banner(mode):
    th = THEMES[mode]
    rng = random.Random(3)
    s = [f'<defs><filter id="glow" x="-150%" y="-150%" width="400%" height="400%"><feGaussianBlur stdDeviation="3.2"/></filter>'
         f'<clipPath id="panel"><rect width="{W}" height="{H}" rx="16"/></clipPath></defs>',
         f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="{th["panel"]}" stroke="{th["edge"]}"/>']

    # left column: who and what
    s.append(f'<circle cx="68" cy="76" r="3.5" fill="{th["accent"]}"/>')
    s.append(T.text("AMOGH D. PRASANNA", "mono", 13, 84, 80.5, th["mute"], tracking=0.14))
    lines = ["Teaching noisy quantum", "hardware to compute", "correctly."]
    size = min(fit(l, "inter-display-light", 640, 56, -0.01) for l in lines)
    for i, l in enumerate(lines):
        s.append(T.text(l, "inter-display-light", size, 62, 172 + i * size * 1.12, th["fg"], tracking=-0.01))
    s.append(T.text("QUDIT COMPILATION / ERROR CORRECTION / QUANTUM GENERATIVE MODELS", "mono", 11.5, 64, 352, th["mute"], tracking=0.1))

    # right column: an optical tweezer array that loads, sorts and entangles, on a loop
    for r in range(ROWS):
        for c in range(COLS):
            x, y = site(c, r)
            s.append(f'<circle cx="{x}" cy="{y}" r="1.6" fill="{th["faint"]}"/>')
    # region of interest brackets around the target block
    x0, y0 = site(2, 1)
    x1, y1 = site(5, 4)
    m, L = 22, 10
    for (cx, cy, dx, dy) in ((x0 - m, y0 - m, 1, 1), (x1 + m, y0 - m, -1, 1), (x0 - m, y1 + m, 1, -1), (x1 + m, y1 + m, -1, -1)):
        s.append(f'<path d="M{cx} {cy + dy * L}V{cy}H{cx + dx * L}" fill="none" stroke="{th["mute"]}" stroke-width="1"/>')

    occ = loaded_sites()
    plan = assign(occ)
    order = sorted(plan, key=lambda a: (plan[a][1], plan[a][0]))
    for a in occ:
        ax, ay = site(*a)
        t_in = LOAD + rng.random() * 0.6
        if a in plan:
            tx, ty = site(*plan[a])
            i = order.index(a)
            t0 = SORT + i * 0.17
            t1, t2 = t0 + 0.32, t0 + 0.64
            move = (f'<animateTransform attributeName="transform" type="translate" dur="{DUR}s" repeatCount="indefinite" '
                    f'values="0 0;0 0;{tx - ax} 0;{tx - ax} {ty - ay};{tx - ax} {ty - ay}" keyTimes="{kt(0, t0, t1, t2, DUR)}"/>')
            fade = f'values="0;0;1;1;0;0" keyTimes="{kt(0, t_in, t_in + 0.25, FADE, FADE + 0.6, DUR)}"'
        else:
            move = ""
            t_out = SORT + len(order) * 0.17 + 0.2 + rng.random() * 0.3
            fade = f'values="0;0;1;1;0;0" keyTimes="{kt(0, t_in, t_in + 0.25, t_out, t_out + 0.35, DUR)}"'
        s.append(f'<g opacity="0"><animate attributeName="opacity" dur="{DUR}s" repeatCount="indefinite" {fade}/>{move}'
                 f'<circle cx="{ax}" cy="{ay}" r="6.5" fill="{th["fg"]}" opacity="{0.35 if mode == "dark" else 0.18}" filter="url(#glow)"/>'
                 f'<circle cx="{ax}" cy="{ay}" r="3.3" fill="{th["fg"]}"/></g>')
    # Rydberg pulse: the sorted block lights up violet twice
    pulse = f'values="0;0;0.9;0;0.9;0;0" keyTimes="{kt(0, HOLD + 0.6, HOLD + 0.9, HOLD + 1.3, HOLD + 1.6, HOLD + 2.0, DUR)}"'
    rings = "".join(f'<circle cx="{site(*t)[0]}" cy="{site(*t)[1]}" r="9" fill="{th["accent"]}" filter="url(#glow)"/>' for t in TARGET)
    s.append(f'<g opacity="0"><animate attributeName="opacity" dur="{DUR}s" repeatCount="indefinite" {pulse}/>{rings}</g>')

    # caption under the array, each word lit during its step
    steps = [("LOAD", LOAD, SORT), ("SORT", SORT, HOLD), ("ENTANGLE", HOLD, FADE)]
    cap_x = site(0, 0)[0] - 3
    for word, a, b in steps:
        s.append(T.text(word, "mono", 11, cap_x, 352, th["faint"], tracking=0.12))
        lit = f'values="0;0;1;1;0;0" keyTimes="{kt(0, a, a + 0.2, b - 0.1, b + 0.1, DUR)}"'
        s.append(T.text(word, "mono", 11, cap_x, 352, th["fg"], tracking=0.12, extra=' opacity="0"',
                        child=f'<animate attributeName="opacity" dur="{DUR}s" repeatCount="indefinite" {lit}/>'))
        cap_x += T.measure(word, "mono", 11, 0.12) + 22
    return svg(W, H, "".join(s), "Amogh D. Prasanna. Teaching noisy quantum hardware to compute correctly. "
               "An animated array of trapped atoms loads, sorts itself into a block, and is entangled.")


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
