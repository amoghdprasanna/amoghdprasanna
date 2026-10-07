"""Monospace text as SVG paths, from the glyph atlas in glyphs.json.

The qubit Action runs this on every move. It has no dependencies: tools/build.py
precomputes every glyph outline (IBM Plex Mono, with math symbols borrowed from
DejaVu Sans Mono and FreeSerif) at 1000 units per em, already flipped to SVG's
y-down axis, so laying out a string is just scaling and translating numbers.
"""
import json
import re
from pathlib import Path

ATLAS = json.loads((Path(__file__).with_name("glyphs.json")).read_text())
CELL = ATLAS["cell"]  # advance of every glyph, in em
_num = re.compile(r"-?\d+(?:\.\d+)?")


def width(s, size, tracking=0.0):
    n = len(s)
    return n * CELL * size + max(n - 1, 0) * tracking * size


def path(s, size, x, y, weight="regular", anchor="start", tracking=0.0):
    glyphs = ATLAS[weight]
    x0 = x - {"start": 0, "middle": width(s, size, tracking) / 2, "end": width(s, size, tracking)}[anchor]
    k = size / 1000
    out = []
    for i, ch in enumerate(s):
        d = glyphs.get(ch, glyphs.get("?", ""))
        if not d:
            continue
        gx = x0 + i * (CELL + tracking) * size
        # coordinates come in x,y pairs; every command in the atlas is absolute
        vals = iter(float(v) for v in _num.findall(d))
        coords = [f"{gx + a * k:.2f} {y + b * k:.2f}" for a, b in zip(vals, vals)]
        out.append(_rebuild(d, iter(coords)))
    return "".join(out)


def _rebuild(d, coords):
    parts = []
    for cmd, body in re.findall(r"([MLQCZ])([^MLQCZ]*)", d):
        if cmd == "Z":
            parts.append("Z")
            continue
        n = len(_num.findall(body)) // 2
        parts.append(cmd + " ".join(next(coords) for _ in range(n)))
    return "".join(parts)


def text(s, size, x, y, fill, weight="regular", anchor="start", tracking=0.0, extra=""):
    d = path(s, size, x, y, weight, anchor, tracking)
    return f'<path d="{d}" fill="{fill}"{extra}/>' if d else ""
