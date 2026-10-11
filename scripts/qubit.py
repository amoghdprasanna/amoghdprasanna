"""A shared qubit for the profile README.

Visitors open an issue titled "qubit: <gate>". This script applies the gate to
the stored state (sampling by the Born rule for a measurement), draws a new
card, and rewrites the README block between the QUBIT markers.

Each card gets a new file name. GitHub serves README images from
raw.githubusercontent.com with a five minute cache and drops query strings on
the way, so reusing one name is what made the sphere lag behind the ket.
Standard library only, so the Action needs nothing installed.
"""
import cmath
import json
import math
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svgtext as S  # noqa: E402
from theme import THEMES, svg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "qubit.json"
README = ROOT / "README.md"
CARDS = ROOT / "assets" / "qubit"
REPO = os.environ.get("GITHUB_REPOSITORY", "amoghdprasanna/amoghdprasanna")
TRAIL = 8
rng = random.SystemRandom()

s2 = 1 / math.sqrt(2)
GATES = {
    "H": [[s2, s2], [s2, -s2]],
    "X": [[0, 1], [1, 0]],
    "Y": [[0, -1j], [1j, 0]],
    "Z": [[1, 0], [0, -1]],
    "S": [[1, 0], [0, 1j]],
    "T": [[1, 0], [0, cmath.exp(1j * math.pi / 4)]],
}
BUTTONS = ["H", "X", "Y", "Z", "S", "T", "measure", "reset"]


# ---------------------------------------------------------------- state

def load():
    if STATE.exists():
        d = json.loads(STATE.read_text())
        d["psi"] = [complex(*a) for a in d["psi"]]
    else:
        d = {"psi": [1 + 0j, 0j], "ops": [], "gates": 0, "zeros": 0, "ones": 0, "last": None}
    d.setdefault("trail", [])
    return d


def save(d):
    out = dict(d)
    out["psi"] = [[round(a.real, 12), round(a.imag, 12)] for a in d["psi"]]
    STATE.write_text(json.dumps(out, indent=2) + "\n")


def normalize(psi):
    # drop the global phase so the |0> amplitude is real and non-negative
    a, b = psi
    if abs(a) > 1e-12:
        ph = cmath.exp(-1j * cmath.phase(a))
        a, b = a * ph, b * ph
    else:
        a, b = 0j, complex(abs(b), 0)
    n = math.sqrt(abs(a) ** 2 + abs(b) ** 2)
    return [a / n, b / n]


def bloch(psi):
    a, b = psi
    return 2 * (a.conjugate() * b).real, 2 * (a.conjugate() * b).imag, abs(a) ** 2 - abs(b) ** 2


def phase_str(phi):
    """e^(i phi) with phi as a tidy multiple of pi when it is one."""
    q = phi / math.pi
    if q <= -1 + 1e-9:  # -π and π are the same phase; print it once
        q += 2
    for den in (1, 2, 4, 8):
        num = round(q * den)
        if abs(q * den - num) < 1e-6:
            if num == 0:
                return ""
            g = math.gcd(num, den)
            num, den = num // g, den // g
            sign = "-" if num < 0 else ""
            top = "π" if abs(num) == 1 else f"{abs(num)}π"
            return f"e^({sign}i{top})" if den == 1 else f"e^({sign}i{top}/{den})"
    return f"e^({'-' if q < 0 else ''}i{abs(q):.2f}π)"


def ket(psi):
    a, b = psi
    if abs(b) < 1e-9:
        return "|0⟩"
    if abs(a) < 1e-9:
        return "|1⟩"
    ph = phase_str(cmath.phase(b))
    if ph == "e^(iπ)":
        return f"{abs(a):.3f}|0⟩ − {abs(b):.3f}|1⟩"
    return f"{abs(a):.3f}|0⟩ + {abs(b):.3f}{'·' + ph if ph else ''}|1⟩"


# ---------------------------------------------------------------- drawing

CW, CH = 880, 330
AZ, EL = math.radians(32), math.radians(16)


def project(cx, cy, R, x, y, z):
    """Screen position and depth (positive is towards the viewer)."""
    u = -x * math.sin(AZ) + y * math.cos(AZ)
    w = x * math.cos(AZ) + y * math.sin(AZ)
    v = z * math.cos(EL) - w * math.sin(EL)
    return cx + R * u, cy - R * v, w * math.cos(EL) + z * math.sin(EL)


def curve(cx, cy, R, f, front, back, n=120):
    """A curve on (or in) the sphere, split into the part facing the viewer and the part behind."""
    pts = [(k, *project(cx, cy, R, *f(k / n))) for k in range(n + 1)]
    out = []
    for side, style in ((1, front), (-1, back)):
        if style is None:
            continue
        run, prev = [], None
        for k, X, Y, D in pts + [(None, 0, 0, 0)]:
            ok = k is not None and (D >= 0) == (side > 0)
            if ok and (prev is None or k == prev + 1):
                run.append(f"{X:.1f},{Y:.1f}")
            else:
                if len(run) > 1:
                    out.append(f'<polyline points="{" ".join(run)}" fill="none" {style}/>')
                run = [f"{X:.1f},{Y:.1f}"] if ok else []
            prev = k if ok else None
    return "".join(out)


def slerp(p, q, t):
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(p, q))))
    om = math.acos(dot)
    if om < 1e-6:
        return p
    if abs(om - math.pi) < 1e-6:
        # antipodal: go over the +x side so the arc is visible
        mid = (1.0, 0.0, 0.0) if abs(p[0]) < 0.9 else (0.0, 1.0, 0.0)
        return slerp(p, mid, 2 * t) if t < 0.5 else slerp(mid, q, 2 * t - 1)
    a, b = math.sin((1 - t) * om) / math.sin(om), math.sin(t * om) / math.sin(om)
    return tuple(a * x + b * y for x, y in zip(p, q))


# The sphere is drawn as a dark glass orb full of out-of-focus atoms, lit from the
# upper right, after Oratomic's imagery. It stays dark in both themes, like a
# photograph of an object; the Bloch geometry is drawn crisply over it.
ORB = {"top": "#3b4547", "mid": "#141b1d", "low": "#07090a", "edge": "#020203",
       "rim": "#8a7cff", "rim_dark": "#251f4a", "line": "#ffffff", "vec": "#f4f4f4", "angle": "#bfb4ff"}


def orb_defs(R):
    o = ORB
    return (f'<defs><radialGradient id="orb" cx="0.70" cy="0.26" r="0.95">'
            f'<stop offset="0" stop-color="{o["top"]}"/><stop offset="0.38" stop-color="{o["mid"]}"/>'
            f'<stop offset="0.78" stop-color="{o["low"]}"/><stop offset="1" stop-color="{o["edge"]}"/></radialGradient>'
            f'<radialGradient id="rim" cx="0.5" cy="0.5" r="0.5"><stop offset="0.84" stop-color="{o["rim"]}" stop-opacity="0"/>'
            f'<stop offset="0.965" stop-color="{o["rim"]}" stop-opacity="0.16"/><stop offset="1" stop-color="{o["rim_dark"]}" stop-opacity="0.75"/></radialGradient>'
            f'<radialGradient id="ray" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ffffff" stop-opacity="0.55"/>'
            f'<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="shadow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#000000" stop-opacity="0.22"/>'
            f'<stop offset="1" stop-color="#000000" stop-opacity="0"/></radialGradient>'
            f'<filter id="b1" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="0.7"/></filter>'
            f'<filter id="b2" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2"/></filter>'
            f'<filter id="bloom" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="{R * 0.12:.1f}"/></filter>'
            f'<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="1" seed="3"/>'
            f'<feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.07 0"/></filter></defs>')


def orb_body(cx, cy, R):
    """Body, atoms, light. Fixed seed, so the orb looks the same on every move."""
    rng = random.Random(11)
    lx, ly = cx + 0.42 * R, cy - 0.46 * R
    s = [f'<clipPath id="ball"><circle cx="{cx}" cy="{cy}" r="{R}"/></clipPath>',
         f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="url(#orb)"/>', '<g clip-path="url(#ball)">']
    crisp, soft = [], []
    for _ in range(280):
        while True:
            p = [rng.uniform(-1, 1) for _ in range(3)]
            if sum(c * c for c in p) <= 0.96:
                break
        X, Y, D = project(cx, cy, R, *p)
        near = math.exp(-math.hypot(X - lx, Y - ly) / (0.9 * R))
        size = (0.8 + 4.6 * rng.random() ** 2.4) * (1 + 0.35 * D)
        op = min(1.0, 0.3 + 0.7 * near) * (0.5 + 0.5 * rng.random())
        tint = rng.choice(["#ffffff", "#ffffff", "#ffffff", "#dfe9ff", "#fff1e0"])
        (soft if size > 2.4 else crisp).append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{size:.1f}" fill="{tint}" opacity="{op:.2f}"/>')
    s.append(f'<g filter="url(#b2)" opacity="0.8">{"".join(soft)}</g><g filter="url(#b1)">{"".join(crisp)}</g>')
    # starburst: thin tapered rays from the light, then the bloom itself
    rays = []
    for k in range(30):
        a = 2 * math.pi * k / 30 + rng.uniform(-0.08, 0.08)
        L = R * rng.uniform(0.35, 1.05)
        w = rng.uniform(0.6, 1.8)
        ex, ey = lx + L * math.cos(a), ly + L * math.sin(a)
        nx, ny = -math.sin(a) * w, math.cos(a) * w
        rays.append(f'<path d="M{lx + nx:.1f} {ly + ny:.1f}L{ex:.1f} {ey:.1f}L{lx - nx:.1f} {ly - ny:.1f}Z" opacity="{rng.uniform(0.08, 0.22):.2f}"/>')
    s.append(f'<g fill="#ffffff">{"".join(rays)}</g>')
    s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{0.34 * R:.1f}" fill="url(#ray)"/>')
    s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{0.13 * R:.1f}" fill="#ffffff" opacity="0.9" filter="url(#bloom)"/>')
    s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{0.04 * R:.1f}" fill="#ffffff"/>')
    s.append(f'<rect x="{cx - R}" y="{cy - R}" width="{2 * R}" height="{2 * R}" filter="url(#grain)"/>')
    s.append("</g>")
    return "".join(s)


def sphere(th, psi, trail, cx=176, cy=166, R=112):
    o = ORB
    s = [orb_defs(R)]
    if th["panel"] == THEMES["light"]["panel"]:
        s.append(f'<ellipse cx="{cx}" cy="{cy + R + 9}" rx="{R * 0.8:.1f}" ry="{R * 0.11:.1f}" fill="url(#shadow)"/>')
    s.append(orb_body(cx, cy, R))

    behind = f'stroke="{o["line"]}" stroke-width="0.8" stroke-dasharray="1.5 3.5" opacity="0.16"'
    tau = 2 * math.pi
    # grid: meridians every 45 degrees, latitudes at 45 and 135
    grid = []
    for k in range(4):
        ph = k * math.pi / 4
        grid.append(lambda u, ph=ph: (math.cos(ph) * math.sin(tau * u), math.sin(ph) * math.sin(tau * u), math.cos(tau * u)))
    for th_ in (math.pi / 4, 3 * math.pi / 4):
        grid.append(lambda u, a=th_: (math.sin(a) * math.cos(tau * u), math.sin(a) * math.sin(tau * u), math.cos(a)))
    equator = lambda u: (math.cos(tau * u), math.sin(tau * u), 0)  # noqa: E731
    for f in grid + [equator]:
        s.append(curve(cx, cy, R, f, None, behind))

    # the equatorial plane, a faint disc
    disc = " ".join(f"{X:.1f},{Y:.1f}" for X, Y, _ in (project(cx, cy, R, *equator(k / 96)) for k in range(97)))
    s.append(f'<polygon points="{disc}" fill="{o["rim"]}" fill-opacity="0.07" stroke="none"/>')

    # axes with arrowheads on the positive ends
    for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        x1, y1, _ = project(cx, cy, R, *[-c for c in v])
        x2, y2, _ = project(cx, cy, R, *[1.12 * c for c in v])
        s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{o["line"]}" stroke-width="0.9" opacity="0.35"/>')
        s.append(arrowhead(x1, y1, x2, y2, 7, 3, th["mute"]))

    # where the state has been: a faint path over the surface
    pts = [tuple(p) for p in trail] + [bloch(psi)]
    for i in range(len(pts) - 1):
        seg = [project(cx, cy, R, *slerp(pts[i], pts[i + 1], k / 24))[:2] for k in range(25)]
        op = 0.3 + 0.5 * (i + 1) / len(pts)
        s.append(f'<polyline points="{" ".join(f"{X:.1f},{Y:.1f}" for X, Y in seg)}" fill="none" stroke="{o["angle"]}" '
                 f'stroke-width="1.2" stroke-dasharray="1 3" stroke-linecap="round" opacity="{op:.2f}"/>')
    for i, p in enumerate(pts[:-1]):
        X, Y, _ = project(cx, cy, R, *p)
        s.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="2.2" fill="{o["angle"]}" opacity="{0.35 + 0.5 * (i + 1) / len(pts):.2f}"/>')

    # the state vector, its shadow on the equatorial plane, and the angles theta and phi
    x, y, z = bloch(psi)
    ex, ey, depth = project(cx, cy, R, x, y, z)
    px, py, _ = project(cx, cy, R, x, y, 0)
    if math.hypot(x, y) > 0.05:
        s.append(f'<path d="M{cx} {cy}L{px:.1f} {py:.1f}L{ex:.1f} {ey:.1f}" fill="none" stroke="{o["line"]}" stroke-opacity="0.5" stroke-width="0.9" stroke-dasharray="3 3"/>')
        s.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2" fill="{o["line"]}" opacity="0.6"/>')
        phi = math.atan2(y, x)
        s.append(curve(cx, cy, R, lambda u: (0.3 * math.cos(phi * u), 0.3 * math.sin(phi * u), 0),
                       f'stroke="{o["angle"]}" stroke-width="1.1"', f'stroke="{o["angle"]}" stroke-width="1.1"', n=24))
        lx, ly, _ = project(cx, cy, R, 0.44 * math.cos(phi / 2), 0.44 * math.sin(phi / 2), 0)
        s.append(S.text("φ", 11, lx, ly + 4, o["angle"], anchor="middle"))
    theta = math.acos(max(-1.0, min(1.0, z)))
    if theta > 0.15:
        unit = (x, y, z)
        s.append(curve(cx, cy, R, lambda u: tuple(0.24 * c for c in slerp((0, 0, 1), unit, u)),
                       f'stroke="{o["angle"]}" stroke-width="1.1"', f'stroke="{o["angle"]}" stroke-width="1.1"', n=24))
        mid = slerp((0, 0, 1), unit, 0.5)
        lx, ly, _ = project(cx, cy, R, *[0.37 * c for c in mid])
        s.append(S.text("θ", 11, lx, ly + 4, o["angle"], anchor="middle"))
    alpha = 1 if depth >= 0 else 0.6
    # a dark keyline keeps the vector readable where it crosses the bright side of the orb
    s.append(f'<line x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#000000" stroke-opacity="0.45" stroke-width="5" stroke-linecap="round"/>')
    s.append(f'<line x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{o["vec"]}" stroke-width="2.3" stroke-linecap="round" opacity="{alpha}"/>')
    s.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="12" fill="{o["rim"]}" opacity="0.45" filter="url(#g)"/>')
    s.append(arrowhead(cx, cy, ex, ey, 13, 5.5, o["vec"], alpha))
    s.append(f'<circle cx="{cx}" cy="{cy}" r="2.6" fill="{o["vec"]}"/>')

    # the near side of the grid, then the rim of the glass
    front = f'stroke="{o["line"]}" stroke-width="0.8" opacity="0.26"'
    for f in grid:
        s.append(curve(cx, cy, R, f, front, None))
    s.append(curve(cx, cy, R, equator, f'stroke="{o["line"]}" stroke-width="1" opacity="0.45"', None))
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="url(#rim)"/>')

    # |+> points at the viewer, so its label sits on the orb and is drawn light
    for lab, v, dx, dy, anchor, fill in (("|0⟩", (0, 0, 1.2), 0, -2, "middle", th["mute"]),
                                         ("|1⟩", (0, 0, -1.16), 0, 16, "middle", th["mute"]),
                                         ("|+⟩", (1.12, 0, 0), -8, 5, "end", "#d6d6d6"),
                                         ("|+i⟩", (0, 1.2, 0), 6, 4, "start", th["mute"])):
        X, Y, _ = project(cx, cy, R, *v)
        s.append(S.text(lab, 12, X + dx, Y + dy, fill, anchor=anchor))
    return "".join(s)


def arrowhead(x1, y1, x2, y2, length, half, fill, opacity=1):
    dx, dy = x2 - x1, y2 - y1
    n = math.hypot(dx, dy)
    if n < 1e-6:
        return ""
    ux, uy = dx / n, dy / n
    bx, by = x2 - ux * length, y2 - uy * length
    return (f'<path d="M{x2:.1f} {y2:.1f}L{bx - uy * half:.1f} {by + ux * half:.1f}L{bx + uy * half:.1f} {by - ux * half:.1f}Z" '
            f'fill="{fill}" opacity="{opacity}"/>')


def wire(th, ops, x0, y, x1):
    s = [S.text("|0⟩", 14, x0, y + 5, th["mute"])]
    start = x0 + S.width("|0⟩", 14) + 10
    step, box = 42, 30
    fit = int((x1 - start - 20) // step)
    shown = ops[-fit:] if ops else []
    if len(ops) > fit:
        s.append(S.text("…", 14, start + 2, y + 5, th["mute"]))
        start += 22
    s.append(f'<line x1="{start}" y1="{y}" x2="{x1}" y2="{y}" stroke="{th["faint"]}" stroke-width="1.2"/>')
    for i, op in enumerate(shown):
        gx = start + 12 + i * step
        s.append(f'<rect x="{gx}" y="{y - box / 2}" width="{box}" height="{box}" rx="5" fill="{th["panel"]}" stroke="{th["fg"]}" stroke-width="1.2"/>')
        if op.startswith("M="):
            mx, my = gx + box / 2, y + 7
            s.append(f'<path d="M{mx - 9} {my}a9 9 0 0 1 18 0" fill="none" stroke="{th["fg"]}" stroke-width="1.2"/>'
                     f'<path d="M{mx} {my}L{mx + 6} {my - 11}" stroke="{th["accent"]}" stroke-width="1.4" stroke-linecap="round"/>')
            s.append(S.text(op[2:], 11, mx, y - box / 2 - 6, th["accent"], weight="medium", anchor="middle"))
        else:
            s.append(S.text(op, 15, gx + box / 2, y + 5.5, th["fg"], weight="medium", anchor="middle"))
    return "".join(s)


def card(d, mode):
    th = THEMES[mode]
    psi = d["psi"]
    p0 = abs(psi[0]) ** 2
    s = [f'<defs><filter id="g" x="-150%" y="-150%" width="400%" height="400%"><feGaussianBlur stdDeviation="4"/></filter></defs>',
         f'<rect x="0.5" y="0.5" width="{CW - 1}" height="{CH - 1}" rx="16" fill="{th["panel"]}" stroke="{th["edge"]}"/>',
         sphere(th, psi, d["trail"])]
    X = 356
    s.append(f'<circle cx="{X + 3.5}" cy="50" r="3.5" fill="{th["accent"]}"/>')
    s.append(S.text("LIVE  ·  ONE QUBIT, SHARED BY EVERY VISITOR", 11, X + 16, 54, th["mute"], tracking=0.12))

    k = "|ψ⟩ = " + ket(psi)
    size = 22 if S.width(k, 22) <= CW - X - 40 else 18
    s.append(S.text(k, size, X, 104, th["fg"]))

    # Born-rule probabilities
    bx, by, bw = X, 136, CW - X - 40
    s.append(S.text(f"P(0) {p0:.3f}", 11, bx, by, th["mute"], tracking=0.04))
    s.append(S.text(f"{1 - p0:.3f} P(1)", 11, bx + bw, by, th["mute"], anchor="end", tracking=0.04))
    s.append(f'<rect x="{bx}" y="{by + 10}" width="{bw}" height="6" rx="3" fill="{th["line"]}"/>')
    if p0 > 1e-6:
        s.append(f'<rect x="{bx}" y="{by + 10}" width="{max(bw * p0, 6):.1f}" height="6" rx="3" fill="{th["fg"]}"/>')

    s.append(wire(th, d["ops"], X, 214, CW - 40))

    n, meas = d["gates"], d["zeros"] + d["ones"]
    stats = f"{n} MOVE{'' if n == 1 else 'S'}  ·  {meas} MEASURED ({d['zeros']}×0, {d['ones']}×1)"
    s.append(S.text(stats, 11, X, 274, th["mute"], tracking=0.08))
    if d["last"]:
        who = d["last"]["user"]
        room = int((CW - X - 40) / (11 * (S.CELL + 0.08))) - len("LAST MOVE  ") - 6
        who = who if len(who) <= room else who[:max(room - 1, 1)] + "…"
        s.append(S.text("LAST MOVE", 11, X, 298, th["mute"], tracking=0.08))
        s.append(S.text(f'{d["last"]["op"]}  by @{who}', 11, X + S.width("LAST MOVE  ", 11, 0.08), 298, th["fg"], tracking=0.08))
    else:
        s.append(S.text("NO MOVES YET. YOURS COULD BE THE FIRST.", 11, X, 298, th["mute"], tracking=0.08))
    return svg(CW, CH, "".join(s), alt(d))


def alt(d):
    p0 = abs(d["psi"][0]) ** 2
    last = f' Last move {d["last"]["op"]} by @{d["last"]["user"]}.' if d["last"] else ""
    return f"Bloch sphere of the shared qubit. State {ket(d['psi'])}, P(0) = {p0:.3f}.{last}"


# ---------------------------------------------------------------- README

def issue_link(op):
    t = f"qubit: {op}".replace(" ", "+").replace(":", "%3A")
    return f"https://github.com/{REPO}/issues/new?title={t}&body=Press+Submit.+A+bot+applies+the+gate+within+a+minute."


def picture(name, alt_text, width):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{name}-dark.svg">'
            f'<img src="{name}-light.svg" alt="{alt_text}" width="{width}"></picture>')


def block(d):
    v = d["gates"]
    from html import escape
    gates = "".join(f'<a href="{issue_link(g)}">{picture(f"assets/gate-{g.lower()}", escape(g if len(g) == 1 else g.title()), 52)}</a>'
                    for g in BUTTONS)
    history = f"https://github.com/{REPO}/issues?q=is%3Aissue+in%3Atitle+%22qubit%3A%22"
    return f"""<!-- QUBIT:START -->
{picture(f"assets/qubit/card-{v}", escape(alt(d), quote=True), "100%")}

<p align="center">{gates}</p>

<p align="center"><sub>Pick a gate. GitHub opens an issue already titled with it; press <b>Submit</b> and a bot applies it within a minute.<br>
<code>measure</code> samples the Born rule, so the outcome is genuinely random. <a href="{history}">Every move so far</a>.</sub></p>
<!-- QUBIT:END -->"""


def render(d):
    CARDS.mkdir(parents=True, exist_ok=True)
    keep = {f"card-{d['gates']}-{m}.svg" for m in THEMES}
    for old in CARDS.glob("card-*.svg"):
        if old.name not in keep:
            old.unlink()
    for mode in THEMES:
        (CARDS / f"card-{d['gates']}-{mode}.svg").write_text(card(d, mode))
    text = README.read_text()
    new = re.sub(r"<!-- QUBIT:START -->.*?<!-- QUBIT:END -->", lambda m: block(d), text, flags=re.S)
    README.write_text(new)


# ---------------------------------------------------------------- the Action

def out(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{key}={value}\n")


def main():
    title = os.environ.get("TITLE", "")
    user = re.sub(r"[^A-Za-z0-9-]", "", os.environ.get("ACTOR", "someone"))[:39] or "someone"
    m = re.match(r"\s*qubit:\s*(\w+)\s*$", title, re.I)
    op = m.group(1) if m else ""
    op = op.lower() if op.lower() in ("measure", "reset") else op.upper()
    d = load()
    before = bloch(d["psi"])

    if op in GATES:
        U = GATES[op]
        a, b = d["psi"]
        d["psi"] = normalize([U[0][0] * a + U[0][1] * b, U[1][0] * a + U[1][1] * b])
        d["ops"].append(op)
        msg = f"Applied **{op}**. The qubit is now `|ψ⟩ = {ket(d['psi'])}`, with P(0) = {abs(d['psi'][0]) ** 2:.3f}."
    elif op == "measure":
        p0 = abs(d["psi"][0]) ** 2
        r = 0 if rng.random() < p0 else 1
        d["psi"] = [1 + 0j, 0j] if r == 0 else [0j, 1 + 0j]
        d["zeros" if r == 0 else "ones"] += 1
        d["ops"].append(f"M={r}")
        msg = f"Measured **{r}**. That outcome had probability {p0 if r == 0 else 1 - p0:.3f}. The state collapsed to `|{r}⟩`."
    elif op == "reset":
        d["psi"] = [1 + 0j, 0j]
        d["ops"] = []
        d["trail"] = []
        msg = "Reset the qubit to `|0⟩` and cleared the circuit."
    else:
        Path("msg.txt").write_text("That isn't a gate this qubit knows. Try H, X, Y, Z, S, T, measure or reset from the profile page.\n")
        out("changed", "false")
        return

    if op != "reset":
        d["trail"] = (d["trail"] + [[round(c, 6) for c in before]])[-TRAIL:]
    d["gates"] += 1
    d["last"] = {"op": d["ops"][-1] if d["ops"] else "reset", "user": user,
                 "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    save(d)
    render(d)
    Path("msg.txt").write_text(msg + f"\n\nThanks @{user}. See it on the [profile](https://github.com/{REPO.split('/')[0]}).\n")
    out("changed", "true")
    out("op", d["last"]["op"])


if __name__ == "__main__":
    main()
