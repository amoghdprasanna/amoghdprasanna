# How the profile is drawn

GitHub strips CSS from READMEs and serves images through a proxy that can't
load web fonts, so everything styled on the profile is an SVG with its text
already turned into outlines. Body text stays as plain Markdown, so it stays
searchable and reflows on a phone.

| Path | What it is | Made by |
| --- | --- | --- |
| `assets/banner-*.svg` | The animated tweezer array and title | `tools/build.py` |
| `assets/hdr-*.svg` | Section headers | `tools/build.py` |
| `assets/btn-*.svg` | Link buttons | `tools/build.py` |
| `assets/gate-*.svg` | The qubit's gate buttons | `tools/build.py` |
| `assets/qubit/card-N-*.svg` | The qubit's current state | `scripts/qubit.py`, on every move |
| `scripts/glyphs.json` | Monospace glyph outlines the bot uses | `tools/build.py` |

Each image comes in a `-dark` and a `-light` version, and the README picks one
with `<picture>` and `prefers-color-scheme`. Colours live in `scripts/theme.py`.

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

## The qubit

`.github/workflows/qubit.yml` runs on every new issue whose title starts with
`qubit:`. It applies the gate with `scripts/qubit.py`, which uses only the
standard library, then commits the new state, card and README, replies on the
issue and closes it. Each move writes a card under a new file name because
GitHub caches README images for about five minutes and ignores query strings.
If two people click at once, the later push is rejected and that run starts
again from the newer state, so no move is lost.

To clear the history, delete `state/qubit.json` and run
`python3 -c "import sys; sys.path.insert(0, 'scripts'); import qubit; qubit.render(qubit.load())"`.
