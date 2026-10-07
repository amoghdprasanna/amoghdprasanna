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


def great_circle(cx, cy, R, f, stroke, width=1.0):
    front, back = [], []
    for k in range(121):
        t = 2 * math.pi * k / 120
        X, Y, D = project(cx, cy, R, *f(t))
        (front if D >= 0 else back).append((k, X, Y))

    def runs(pts):
        out, cur, prev = [], [], None
        for k, X, Y in pts:
            if prev is not None and k != prev + 1:
                out.append(cur)
                cur = []
            cur.append(f"{X:.1f},{Y:.1f}")
            prev = k
        if cur:
            out.append(cur)
        return out

    s = [f'<polyline points="{" ".join(r)}" fill="none" stroke="{stroke}" stroke-width="{width}"/>' for r in runs(front) if len(r) > 1]
    s += [f'<polyline points="{" ".join(r)}" fill="none" stroke="{stroke}" stroke-width="{width}" stroke-dasharray="2 4"/>' for r in runs(back) if len(r) > 1]
    return "".join(s)


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


def sphere(th, psi, trail, cx=176, cy=170, R=112):
    s = [f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{th["faint"]}" stroke-width="1.2"/>',
         great_circle(cx, cy, R, lambda t: (math.cos(t), math.sin(t), 0), th["faint"]),
         great_circle(cx, cy, R, lambda t: (math.cos(t), 0, math.sin(t)), th["line"])]
    for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        x1, y1, _ = project(cx, cy, R, *[-c for c in v])
        x2, y2, _ = project(cx, cy, R, *v)
        s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{th["line"]}"/>')
    for lab, v, dx, dy, anchor in (("|0⟩", (0, 0, 1.16), 0, -2, "middle"), ("|1⟩", (0, 0, -1.16), 0, 12, "middle"),
                                   ("|+⟩", (1.22, 0, 0), -2, 10, "end"), ("|+i⟩", (0, 1.14, 0), 4, 4, "start")):
        X, Y, _ = project(cx, cy, R, *v)
        s.append(S.text(lab, 12, X + dx, Y + dy, th["mute"], anchor=anchor))

    # where the state has been: a faint path over the surface
    pts = [tuple(p) for p in trail] + [bloch(psi)]
    for i in range(len(pts) - 1):
        seg = [project(cx, cy, R, *slerp(pts[i], pts[i + 1], k / 24))[:2] for k in range(25)]
        op = 0.25 + 0.5 * (i + 1) / len(pts)
        s.append(f'<polyline points="{" ".join(f"{X:.1f},{Y:.1f}" for X, Y in seg)}" fill="none" stroke="{th["accent"]}" '
                 f'stroke-width="1.2" stroke-dasharray="1 3" stroke-linecap="round" opacity="{op:.2f}"/>')
    for i, p in enumerate(pts[:-1]):
        X, Y, _ = project(cx, cy, R, *p)
        s.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="2.2" fill="{th["accent"]}" opacity="{0.3 + 0.5 * (i + 1) / len(pts):.2f}"/>')

    x, y, z = bloch(psi)
    ex, ey, depth = project(cx, cy, R, x, y, z)
    px, py, _ = project(cx, cy, R, x, y, 0)
    if math.hypot(x, y) > 0.05:
        s.append(f'<path d="M{cx} {cy}L{px:.1f} {py:.1f}L{ex:.1f} {ey:.1f}" fill="none" stroke="{th["mute"]}" stroke-dasharray="3 3"/>')
    s.append(f'<line x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{th["fg"]}" stroke-width="2.2" stroke-linecap="round"/>')
    s.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="11" fill="{th["accent"]}" opacity="0.35" filter="url(#g)"/>')
    s.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="5.2" fill="{th["fg"] if depth >= 0 else th["mute"]}"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="2.4" fill="{th["mute"]}"/>')
    return "".join(s)


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
