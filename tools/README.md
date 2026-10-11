# How the profile is drawn

GitHub strips CSS from READMEs and serves images through a proxy that can't
load web fonts, so everything styled on the profile is an SVG with its text
already turned into outlines. Body text stays as plain Markdown, so it stays
searchable and reflows on a phone.

| Path | What it is | Made by |
| --- | --- | --- |
| `assets/qec/banner-N-*.svg` | The header: name and the shared d = 5 surface code, wide and (`-mobile`) tall | `scripts/qec.py`, on every move |
| `assets/hdr-*.svg` | Section headers | `tools/build.py` |
| `assets/btn-*.svg` | Link buttons and the surface code's controls | `tools/build.py` |
| `scripts/glyphs.json` | Monospace glyph outlines the bots use | `tools/build.py` |
| `scripts/banner_text.json` | The header's name block, pasted in by `scripts/qec.py` | `tools/build.py` |

Each image comes in a `-dark` and a `-light` version, and the README picks one
with `<picture>` and `prefers-color-scheme`. The header also has a tall `-mobile`
layout with larger type, picked on screens up to 600 px wide. Colours live in `scripts/theme.py`.

## Rebuilding the static images

```bash
pip install fonttools uharfbuzz
python3 tools/build.py
```

The fonts aren't committed. Put these in `tools/fonts/`:
`Inter-Light.otf`, `Inter-Regular.otf`, `Inter-Medium.otf`, `InterDisplay-Light.otf`
([Inter](https://github.com/rsms/inter)), `IBMPlexMono-Regular.woff`, `IBMPlexMono-Medium.woff`
([IBM Plex](https://github.com/IBM/plex)), `DejaVuSansMono.ttf` and `FreeSerif.ttf`
(both fill in math glyphs like ⟩ that Plex lacks).

## The surface code

The header is a distance-5 rotated surface code that every visitor shares.
`qec: X` and `qec: Z` put that error on a random data qubit, `qec: decode` applies
the lowest-weight correction that matches the lit stabilizers (exhaustive search,
so every one- and two-qubit error is corrected) and reports whether the logical
qubit flipped, and `qec: reset` clears it. State lives in `state/qec.json`.

`.github/workflows/qec.yml` runs on every new issue whose title starts with
`qec:`. It runs `scripts/qec.py`, which uses only the standard library, then
commits the new state, header and README, replies on the issue and closes it.
Each move writes the header under a new file name because GitHub caches README
images for about five minutes and ignores query strings. If two people click
at once, the later push is rejected and that run starts again from the newer
state, so no move is lost.
