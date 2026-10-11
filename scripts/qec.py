"""A shared distance-5 surface code for the profile header.

Visitors open an issue titled "qec: X", "qec: Z", "qec: decode" or "qec: reset".
X and Z put that error on a random data qubit; the stabilizers that see it
light up. Decode finds the lowest-weight correction that explains the lit
stabilizers, applies it, and checks whether what is left flipped the logical
qubit. Then the header is redrawn and the README block between the QEC markers
rewritten. Standard library only, so the Action needs nothing installed.

Layout: rotated surface code [[25, 1, 5]]. Data qubit (i, j) is column i, row j.
Bulk plaquette (a, b) is Z-type when a + b is even. Weight-2 X stabilizers sit
on the top and bottom edges, Z stabilizers on the left and right. So X errors
(seen by Z stabilizers) can end silently on the top and bottom edges, logical X
is any column, and logical Z is any row.
"""
import json
import os
import random
import re
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svgtext as S  # noqa: E402
from theme import THEMES, svg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "qec.json"
README = ROOT / "README.md"
OUT = ROOT / "assets" / "qec"
TEXT = Path(__file__).with_name("banner_text.json")  # name block, drawn by tools/build.py
REPO = os.environ.get("GITHUB_REPOSITORY", "amoghdprasanna/amoghdprasanna")
rng = random.SystemRandom()

D = 5
N = D * D
W, H = 1280, 360
P = 40
CX, CY = 1030, 178
TILES = {
    "dark": {"x": "#16161b", "z": "#0b0b0d", "edge": "#26262b"},
    "light": {"x": "#ebebf0", "z": "#f6f6f8", "edge": "#dcdce2"},
}
ACTIONS = ["X", "Z", "decode", "reset"]


# ---------------------------------------------------------------- the code

def idx(i, j):
    return j * D + i


def stabilizers():
    """(kind, data qubit indices, shape) for all 24 stabilizers."""
    out = []
    for a in range(D - 1):
        for b in range(D - 1):
            kind = "z" if (a + b) % 2 == 0 else "x"
            out.append((kind, [idx(a, b), idx(a + 1, b), idx(a, b + 1), idx(a + 1, b + 1)], ("sq", a, b)))
    for a in range(D - 1):
        if (a - 1) % 2 == 1:
            out.append(("x", [idx(a, 0), idx(a + 1, 0)], ("top", a, 0)))
        if (a + D - 1) % 2 == 1:
            out.append(("x", [idx(a, D - 1), idx(a + 1, D - 1)], ("bottom", a, D - 1)))
    for b in range(D - 1):
        if (b - 1) % 2 == 0:
            out.append(("z", [idx(0, b), idx(0, b + 1)], ("left", 0, b)))
        if (D - 1 + b) % 2 == 0:
            out.append(("z", [idx(D - 1, b), idx(D - 1, b + 1)], ("right", D - 1, b)))
    assert len(out) == N - 1
    return out


STABS = stabilizers()
# Z-type stabilizers detect X errors and X-type detect Z errors
CHECKS = {"x": [s for s in STABS if s[0] == "z"], "z": [s for s in STABS if s[0] == "x"]}
LOGICAL = {"x": {idx(i, 0) for i in range(D)},   # an X residue is logical if it overlaps row 0 oddly
           "z": {idx(0, j) for j in range(D)}}   # a Z residue, if it overlaps column 0 oddly


def masks(kind):
    """Bit k of masks[q] is set if check k sees an error of this kind on qubit q."""
    m = [0] * N
    for k, (_, qs, _) in enumerate(CHECKS[kind]):
        for q in qs:
            m[q] |= 1 << k
    return m


def syndrome(kind, errs):
    m, s = masks(kind), 0
    for q in errs:
        s ^= m[q]
    return s


def decode(kind, errs, max_weight=7):
    """Lowest-weight set of qubits whose syndrome matches; exhaustive up to max_weight."""
    target, m = syndrome(kind, errs), masks(kind)
    if not target:
        return []
    for w in range(1, max_weight + 1):
        for c in combinations(range(N), w):
            s = 0
            for q in c:
                s ^= m[q]
            if s == target:
                return list(c)
    return solve(target, m)


def solve(target, m):
    """Any correction with this syndrome, by Gaussian elimination over GF(2)."""
    rows = [(m[q], 1 << q) for q in range(N)]
    basis = []  # (pivot bit, syndrome, qubits)
    for s, qs in rows:
        for bit, bs, bq in basis:
            if s >> bit & 1:
                s, qs = s ^ bs, qs ^ bq
        if s:
            basis.append((s.bit_length() - 1, s, qs))
    s, qs = target, 0
    for bit, bs, bq in sorted(basis, reverse=True):
        if s >> bit & 1:
            s, qs = s ^ bs, qs ^ bq
    return [q for q in range(N) if qs >> q & 1]


# ---------------------------------------------------------------- state

def load():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"x": [], "z": [], "moves": 0, "decodes": 0, "failures": 0, "last": None, "result": None}


def save(d):
    STATE.write_text(json.dumps(d, indent=2) + "\n")


def toggle(lst, q):
    return sorted(set(lst) ^ {q})


# ---------------------------------------------------------------- drawing

def pos(q):
    i, j = q % D, q // D
    return CX + (i - (D - 1) / 2) * P, CY + (j - (D - 1) / 2) * P


def shape(spec):
    kind, i, j = spec
    x, y = pos(idx(i, j))
    r = P / 2
    if kind == "sq":
        return f"M{x} {y}h{P}v{P}h{-P}Z"
    if kind == "top":
        return f"M{x} {y}A{r} {r} 0 0 1 {x + P} {y}Z"
    if kind == "bottom":
        return f"M{x} {y}A{r} {r} 0 0 0 {x + P} {y}Z"
    if kind == "left":
        return f"M{x} {y}A{r} {r} 0 0 0 {x} {y + P}Z"
    return f"M{x} {y}A{r} {r} 0 0 1 {x} {y + P}Z"


def center(spec):
    kind, i, j = spec
    x, y = pos(idx(i, j))
    r = P / 2
    return {"sq": (x + r, y + r), "top": (x + r, y - r / 2), "bottom": (x + r, y + r / 2),
            "left": (x - r / 2, y + r), "right": (x + r / 2, y + r)}[kind]


def kt(dur, *ts):
    return ";".join(f"{t / dur:.4f}" for t in ts)


def anim(dur, values, times, attr="opacity"):
    return (f'<animate attributeName="{attr}" dur="{dur}s" repeatCount="indefinite" '
            f'values="{values}" keyTimes="{kt(dur, *times)}"/>')


def lit_checks(x_errs, z_errs):
    """The stabilizers that fire for these errors."""
    out = []
    for kind, errs in (("x", x_errs), ("z", z_errs)):
        syn = syndrome(kind, errs)
        out += [st for k, st in enumerate(CHECKS[kind]) if syn >> k & 1]
    return out


# The header animates in every state: a demo when the code is clean, the live
# errors with their syndromes pulsing while they wait, and a replay of the last
# decode right after one.
DEMO = [idx(1, 2), idx(2, 2)]  # an X chain of two, whose ends light two Z stabilizers


def errors_layer(th, xs, zs, child=""):
    """X is a filled violet qubit, Z a violet ring, Y both."""
    def el(tag):
        return f"{tag}>{child}</circle>" if child else f"{tag}/>"
    s = []
    for q in xs:
        x, y = pos(q)
        s.append(el(f'<circle cx="{x}" cy="{y}" r="4.6" fill="{th["accent"]}"'))
    for q in zs:
        x, y = pos(q)
        s.append(el(f'<circle cx="{x}" cy="{y}" r="9.5" fill="none" stroke="{th["accent"]}" stroke-width="1.6"'))
    return s


def demo(th):
    dur = 9.0
    err, syn, match, fix, calm = 1.0, 2.0, 3.4, 5.0, 6.2
    s = []
    for st in lit_checks(DEMO, []):
        s.append(f'<path d="{shape(st[2])}" fill="{th["accent"]}" opacity="0">'
                 f'{anim(dur, "0;0;0.55;0.55;0;0", (0, syn, syn + 0.3, fix + 0.4, fix + 0.9, dur))}</path>')
    (x1, y1), (x2, y2) = (center(st[2]) for st in lit_checks(DEMO, []))
    L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{th["accent"]}" stroke-width="1.6" '
             f'stroke-linecap="round" stroke-dasharray="{L:.1f}" stroke-dashoffset="{L:.1f}" opacity="0">'
             f'{anim(dur, f"{L:.1f};{L:.1f};0;0", (0, match, match + 0.7, dur), "stroke-dashoffset")}'
             f'{anim(dur, "0;0;1;1;0;0", (0, match, match + 0.05, fix + 0.6, fix + 1.1, dur))}</line>')
    for q in DEMO:
        x, y = pos(q)
        s.append(f'<circle cx="{x}" cy="{y}" r="9.5" fill="none" stroke="{th["accent"]}" stroke-width="1.5" opacity="0">'
                 f'{anim(dur, "0;0;1;1;0;0", (0, err, err + 0.3, fix, fix + 0.35, dur))}</circle>'
                 f'<circle cx="{x}" cy="{y}" r="4.6" fill="{th["accent"]}" opacity="0">'
                 f'{anim(dur, "0;0;1;1;0;0", (0, err, err + 0.3, fix, fix + 0.35, dur))}</circle>'
                 f'<circle cx="{x}" cy="{y}" r="12" fill="{th["fg"]}" opacity="0" filter="url(#glow)">'
                 f'{anim(dur, "0;0;0.8;0;0", (0, fix, fix + 0.15, fix + 0.6, dur))}</circle>')
    # caption: each step lit while it happens
    steps = [("ERROR", err, syn), ("SYNDROME", syn, match), ("MATCH", match, fix), ("CORRECT", fix, calm)]
    gap = 18
    total = sum(S.width(w, 11, 0.12) for w, *_ in steps) + gap * (len(steps) - 1)
    x = 1216 - total
    s.append(S.text("DEMO", 11, x - gap, 304, th["mute"], anchor="end", tracking=0.12))
    for word, a, b in steps:
        s.append(S.text(word, 11, x, 304, th["faint"], tracking=0.12))
        s.append(S.text(word, 11, x, 304, th["fg"], tracking=0.12, extra=' opacity="0"',
                        child=anim(dur, "0;0;1;1;0;0", (0, a, a + 0.15, b - 0.1, b + 0.1, dur))))
        x += S.width(word, 11, 0.12) + gap
    return s


def replay(th, res):
    """Loop the last decode: the errors and lit stabilizers, the correction landing, then clean."""
    dur = 7.0
    ex, ez = res.get("ex", []), res.get("ez", [])
    corr = sorted(set(res.get("cx", [])) | set(res.get("cz", [])))
    clear = 3.2
    s = []
    for st in lit_checks(ex, ez):
        s.append(f'<path d="{shape(st[2])}" fill="{th["accent"]}" opacity="0.5">'
                 f'{anim(dur, "0.5;0.5;0;0;0.5", (0, clear, clear + 0.5, dur - 0.3, dur))}</path>')
    s += errors_layer(th, ex, ez, child=anim(dur, "1;1;0;0;1", (0, clear, clear + 0.5, dur - 0.3, dur)))
    step = min(0.3, 1.6 / max(len(corr), 1))
    for k, q in enumerate(corr):
        x, y = pos(q)
        t0 = 1.0 + k * step
        s.append(f'<circle cx="{x}" cy="{y}" r="12.5" fill="none" stroke="{th["mute"]}" stroke-width="1.1" stroke-dasharray="2.5 2.5" opacity="0">'
                 f'{anim(dur, "0;0;1;1;0", (0, t0, t0 + 0.2, dur - 0.4, dur))}</circle>'
                 f'<circle cx="{x}" cy="{y}" r="12" fill="{th["fg"]}" opacity="0" filter="url(#glow)">'
                 f'{anim(dur, "0;0;0.8;0;0", (0, t0, t0 + 0.12, t0 + 0.5, dur))}</circle>')
    return s


def banner(d, mode):
    th, tile = THEMES[mode], TILES[mode]
    s = [f'<defs><filter id="glow" x="-150%" y="-150%" width="400%" height="400%"><feGaussianBlur stdDeviation="3"/></filter></defs>',
         f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="{th["panel"]}" stroke="{th["edge"]}"/>',
         json.loads(TEXT.read_text())[mode]]
    s.append(S.text("ROTATED SURFACE CODE  ·  d = 5  ·  [[25,1,5]]", 11, 1216, 54, th["mute"], anchor="end", tracking=0.1))
    for st in STABS:
        s.append(f'<path d="{shape(st[2])}" fill="{tile[st[0]]}" stroke="{tile["edge"]}"/>')

    res = d.get("result") or {}
    nx, nz = len(d["x"]), len(d["z"])
    lit = lit_checks(d["x"], d["z"])
    if nx or nz:
        pulse = '<animate attributeName="opacity" values="0.35;0.65;0.35" dur="2.4s" repeatCount="indefinite"/>'
        s += [f'<path d="{shape(st[2])}" fill="{th["accent"]}" opacity="0.5">{pulse}</path>' for st in lit]
    elif res:
        s += replay(th, res)
    above = []  # drawn over the qubits
    if not (nx or nz) and not res:
        above = demo(th)

    for q in range(N):
        x, y = pos(q)
        s.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{th["fg"]}" opacity="{0.22 if mode == "dark" else 0.1}" filter="url(#glow)"/>'
                 f'<circle cx="{x}" cy="{y}" r="3.6" fill="{th["fg"]}"/>')
    if nx or nz:
        s += errors_layer(th, d["x"], d["z"])
        recent = (d.get("recent") or {}).get("q")
        if recent is not None:
            x, y = pos(recent)
            s.append(f'<circle cx="{x}" cy="{y}" r="8" fill="none" stroke="{th["accent"]}" stroke-width="1.4">'
                     f'<animate attributeName="r" values="8;22" dur="1.8s" repeatCount="indefinite"/>'
                     f'<animate attributeName="opacity" values="0.9;0" dur="1.8s" repeatCount="indefinite"/></circle>')
    s += above

    stats = f"{d['decodes']} DECODE{'' if d['decodes'] == 1 else 'S'}  ·  {d['failures']} LOGICAL FAILURE{'' if d['failures'] == 1 else 'S'}"
    if nx or nz:
        line = f"{nx} X, {nz} Z ERROR{'' if nx + nz == 1 else 'S'}  ·  {len(lit)} STABILIZER{'' if len(lit) == 1 else 'S'} LIT  ·  DECODE?"
    elif res:
        line = (f"DECODED  ·  CORRECTION WEIGHT {len(res['cx']) + len(res['cz'])}  ·  "
                + ("LOGICAL QUBIT INTACT" if not res["logical"] else f"LOGICAL {res['logical']} FLIPPED"))
    else:
        line = None  # the demo caption takes this row
        stats = "NO ERRORS  ·  ADD ONE BELOW  ·  " + stats
    if line:
        s.append(S.text(line, 11, 1216, 304, th["fg"], anchor="end", tracking=0.1))
    if d["last"] and line:
        stats += f"  ·  LAST: {d['last']['op'].upper()} BY @{d['last']['user'][:24]}"
    s.append(S.text(stats, 11, 1216, 326, th["mute"], anchor="end", tracking=0.1))
    return svg(W, H, "".join(s), alt(d))


def alt(d):
    res = d.get("result") or {}
    if d["x"] or d["z"]:
        state = f"{len(d['x'])} X and {len(d['z'])} Z errors waiting to be decoded"
    elif res:
        state = "just decoded, " + ("logical qubit intact" if not res["logical"] else f"logical {res['logical']} flipped")
    else:
        state = "no errors"
    return (f"Amogh D. Prasanna: quantum compilation, error correction, quantum simulation. UMD and Fermilab SQMS. "
            f"A shared distance-5 rotated surface code, {state}. {d['decodes']} decodes, {d['failures']} logical failures.")


# ---------------------------------------------------------------- README

def issue_link(op):
    return (f"https://github.com/{REPO}/issues/new?title=qec%3A+{op}"
            f"&body=Press+Submit.+A+bot+updates+the+surface+code+within+a+minute.")


def picture(name, alt_text, size):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{name}-dark.svg">'
            f'<img src="{name}-light.svg" alt="{alt_text}" {size}></picture>')


def block(d):
    from html import escape
    labels = {"X": "Add an X error", "Z": "Add a Z error", "decode": "Decode", "reset": "Reset the code"}
    buttons = "&nbsp;".join(f'<a href="{issue_link(a)}">{picture(f"assets/btn-qec-{a.lower()}", labels[a], "height=\"34\"")}</a>'
                            for a in ACTIONS)
    return f"""<!-- QEC:START -->
{picture(f"assets/qec/banner-{d['moves']}", escape(alt(d), quote=True), 'width="100%"')}

<p align="center">{buttons}</p>
<!-- QEC:END -->"""


def render(d):
    OUT.mkdir(parents=True, exist_ok=True)
    keep = {f"banner-{d['moves']}-{m}.svg" for m in THEMES}
    for old in OUT.glob("banner-*.svg"):
        if old.name not in keep:
            old.unlink()
    for mode in THEMES:
        (OUT / f"banner-{d['moves']}-{mode}.svg").write_text(banner(d, mode))
    text = README.read_text()
    README.write_text(re.sub(r"<!-- QEC:START -->.*?<!-- QEC:END -->", lambda m: block(d), text, flags=re.S))


# ---------------------------------------------------------------- the Action

def out(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{key}={value}\n")


def main():
    title = os.environ.get("TITLE", "")
    user = re.sub(r"[^A-Za-z0-9-]", "", os.environ.get("ACTOR", "someone"))[:39] or "someone"
    m = re.match(r"\s*qec:\s*(\w+)\s*$", title, re.I)
    op = (m.group(1) if m else "").lower()
    d = load()

    if op in ("x", "z"):
        q = rng.randrange(N)
        d[op] = toggle(d[op], q)
        d["result"] = None
        d["recent"] = {"q": q, "kind": op}
        i, j = q % D, q // D
        lit = bin(syndrome(op, d[op])).count("1")
        msg = (f"Put {'an' if op == 'x' else 'a'} **{op.upper()}** error on data qubit ({i}, {j}). "
               f"{lit} stabilizer{'' if lit == 1 else 's'} now light{'s' if lit == 1 else ''} up. "
               f"Add more, or decode.")
    elif op == "decode":
        cx, cz = decode("x", d["x"]), decode("z", d["z"])
        rx, rz = set(d["x"]) ^ set(cx), set(d["z"]) ^ set(cz)
        flips = [name for name, r, kind in (("X", rx, "x"), ("Z", rz, "z")) if len(r & LOGICAL[kind]) % 2]
        logical = "+".join(flips)
        d["result"] = {"ex": d["x"], "ez": d["z"], "cx": cx, "cz": cz, "logical": logical}
        d["x"], d["z"], d["recent"] = [], [], None
        d["decodes"] += 1
        d["failures"] += bool(logical)
        w = len(cx) + len(cz)
        msg = (f"Decoded with a correction of weight {w}. "
               + ("The logical qubit survived." if not logical else
                  f"The errors were too many for distance 5: the logical qubit took a **{logical}** flip."))
    elif op == "reset":
        d.update({"x": [], "z": [], "result": None, "recent": None})
        msg = "Reset the code to an error-free state."
    else:
        Path("msg.txt").write_text("That isn't an action this code knows. Try X, Z, decode or reset from the profile page.\n")
        out("changed", "false")
        return

    d["moves"] += 1
    d["last"] = {"op": op if op in ("decode", "reset") else op.upper(), "user": user,
                 "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    save(d)
    render(d)
    Path("msg.txt").write_text(msg + f"\n\nThanks @{user}. See it on the [profile](https://github.com/{REPO.split('/')[0]}).\n")
    out("changed", "true")
    out("op", d["last"]["op"])


if __name__ == "__main__":
    main()
