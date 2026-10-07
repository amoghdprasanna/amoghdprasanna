"""A shared qubit for the profile README.

Visitors open an issue titled "qubit: <gate>". This script applies the gate to
the stored state, samples a measurement when asked, redraws the Bloch sphere,
and rewrites the README block between the QUBIT markers.
"""
import cmath, json, math, os, random, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "qubit.json"
README = ROOT / "README.md"
REPO = os.environ.get("GITHUB_REPOSITORY", "amoghdprasanna/amoghdprasanna")
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


def load():
    if STATE.exists():
        d = json.loads(STATE.read_text())
        d["psi"] = [complex(*a) for a in d["psi"]]
        return d
    return {"psi": [1 + 0j, 0j], "ops": [], "gates": 0, "zeros": 0, "ones": 0, "last": None}


def save(d):
    out = dict(d)
    out["psi"] = [[a.real, a.imag] for a in d["psi"]]
    STATE.write_text(json.dumps(out, indent=2) + "\n")


def normalize(psi):
    # drop global phase so amplitude of |0> is real and non-negative
    a, b = psi
    if abs(a) > 1e-12:
        ph = cmath.exp(-1j * cmath.phase(a))
        a, b = a * ph, b * ph
    elif abs(b) > 1e-12:
        b = abs(b)
    n = math.sqrt(abs(a) ** 2 + abs(b) ** 2)
    return [a / n, b / n]


def bloch(psi):
    a, b = psi
    x = 2 * (a.conjugate() * b).real
    y = 2 * (a.conjugate() * b).imag
    z = abs(a) ** 2 - abs(b) ** 2
    return x, y, z


def ket(psi):
    a, b = psi
    if abs(b) < 1e-9:
        return "|0⟩"
    if abs(a) < 1e-9:
        return "|1⟩"
    phi = cmath.phase(b) / math.pi
    mag = f"{abs(b):.3f}"
    if abs(phi) < 1e-6:
        second = f"{mag}|1⟩"
    elif abs(abs(phi) - 1) < 1e-6:
        return f"{abs(a):.3f}|0⟩ − {mag}|1⟩"
    else:
        second = f"{mag}·e^(i{phi:.2f}π)|1⟩"
    return f"{abs(a):.3f}|0⟩ + {second}"


def draw(psi, mode):
    dark = mode == "dark"
    fg = "#f4f4f4" if dark else "#0a0a0a"
    mut = "#5c5c5c" if dark else "#c4c4c4"
    lab = "#8a8a8a"
    W = H = 360
    cx, cy, R = W / 2, H / 2, 128
    # oblique projection: x toward viewer (down-left), y right, z up
    def P(x, y, z):
        return cx + R * (0.94 * y - 0.36 * x), cy - R * (0.94 * z - 0.22 * x)
    s = [f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{mut}" stroke-width="1.2"/>']
    for name, f in (("eq", lambda t: (math.cos(t), math.sin(t), 0)),
                    ("mer", lambda t: (math.cos(t), 0, math.sin(t)))):
        pts = " ".join("%.1f,%.1f" % P(*f(2 * math.pi * k / 96)) for k in range(97))
        s.append(f'<polyline points="{pts}" fill="none" stroke="{mut}" stroke-width="1" stroke-dasharray="2 4"/>')
    for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        (x1, y1), (x2, y2) = P(*[-c for c in v]), P(*v)
        s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{mut}" stroke-width="1"/>')
    font = "font-family=\"'STIX Two Math','Cambria Math','DejaVu Serif',serif\" font-size=\"18\""
    tx, ty = P(0, 0, 1.18); s.append(f'<text x="{tx:.1f}" y="{ty+4:.1f}" text-anchor="middle" {font} fill="{lab}">|0⟩</text>')
    tx, ty = P(0, 0, -1.18); s.append(f'<text x="{tx:.1f}" y="{ty+12:.1f}" text-anchor="middle" {font} fill="{lab}">|1⟩</text>')
    x, y, z = bloch(psi)
    ex, ey = P(x, y, z)
    s.append(f'<line x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{fg}" stroke-width="2.2" stroke-linecap="round"/>')
    if dark:
        s.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="9" fill="{fg}" opacity="0.25"/>')
    s.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="5" fill="{fg}"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="{lab}"/>')
    (ROOT / "assets" / f"qubit-{mode}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Bloch sphere of the shared qubit">{"".join(s)}</svg>')


def link(op):
    t = f"qubit: {op}".replace(" ", "+").replace(":", "%3A")
    return f"https://github.com/{REPO}/issues/new?title={t}&body=Just+press+Submit.+The+gate+is+applied+within+a+minute."


def block(d):
    n = d["gates"]
    gates = " &nbsp; ".join(f"[`{g}`]({link(g)})" for g in ["H", "X", "Y", "Z", "S", "T"])
    gates += f" &nbsp; [`measure`]({link('measure')}) &nbsp; [`reset`]({link('reset')})"
    wire = "─".join(d["ops"][-12:]) or ""
    circuit = f"|0⟩ ─{wire}─ …" if wire else "|0⟩ ─ …"
    last = f"Last move: `{d['last']['op']}` by [@{d['last']['user']}](https://github.com/{d['last']['user']})." if d["last"] else "No one has touched it yet."
    meas = d["zeros"] + d["ones"]
    return f"""<!-- QUBIT:START -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/qubit-dark.svg?v={n}">
  <img src="assets/qubit-light.svg?v={n}" alt="Bloch sphere of the shared qubit" width="220" align="right">
</picture>

**A shared qubit.** Everyone who visits acts on the same one. Pick a gate:

{gates}

`|ψ⟩ = {ket(d['psi'])}`

`{circuit}`

<sub>{last} {n} operation{'' if n == 1 else 's'} so far, {meas} measurement{'' if meas == 1 else 's'} ({d['zeros']} × 0, {d['ones']} × 1).</sub>

<br clear="right">
<!-- QUBIT:END -->"""


def write_readme(d):
    text = README.read_text()
    new = re.sub(r"<!-- QUBIT:START -->.*?<!-- QUBIT:END -->", lambda m: block(d), text, flags=re.S)
    README.write_text(new)


def out(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{key}={value}\n")


def main():
    title = os.environ.get("TITLE", "")
    user = re.sub(r"[^A-Za-z0-9-]", "", os.environ.get("ACTOR", "someone"))
    m = re.match(r"\s*qubit:\s*(\w+)\s*$", title, re.I)
    op = m.group(1) if m else ""
    op = op.lower() if op.lower() in ("measure", "reset") else op.upper()
    d = load()

    if op in GATES:
        U = GATES[op]
        a, b = d["psi"]
        d["psi"] = normalize([U[0][0] * a + U[0][1] * b, U[1][0] * a + U[1][1] * b])
        d["ops"].append(op)
        msg = f"Applied {op}. The qubit is now |ψ⟩ = {ket(d['psi'])}."
    elif op == "measure":
        p0 = abs(d["psi"][0]) ** 2
        r = 0 if rng.random() < p0 else 1
        d["psi"] = [1 + 0j, 0j] if r == 0 else [0j, 1 + 0j]
        d["zeros" if r == 0 else "ones"] += 1
        d["ops"].append(f"M={r}")
        msg = f"Measured {r} (that outcome had probability {p0 if r == 0 else 1 - p0:.3f}). The state collapsed to |{r}⟩."
    elif op == "reset":
        d["psi"] = [1 + 0j, 0j]
        d["ops"] = []
        msg = "Reset the qubit to |0⟩."
    else:
        Path("msg.txt").write_text("Unknown gate. Try H, X, Y, Z, S, T, measure, or reset from the profile page.\n")
        out("changed", "false")
        return

    d["gates"] += 1
    d["last"] = {"op": d["ops"][-1] if d["ops"] else "reset", "user": user}
    save(d)
    for mode in ("dark", "light"):
        draw(d["psi"], mode)
    write_readme(d)
    Path("msg.txt").write_text(msg + f"\n\nThanks @{user}, see it on the [profile](https://github.com/{REPO.split('/')[0]}).\n")
    out("changed", "true")
    out("op", d["last"]["op"])


if __name__ == "__main__":
    main()
