"""Colours shared by every image on the profile.

One accent, the violet of the 420 nm Rydberg laser that neutral-atom machines
use to entangle atoms. Everything else is greyscale.
"""
THEMES = {
    "dark": {
        "panel": "#000000",
        "edge": "#1f1f1f",
        "fg": "#ededed",
        "mute": "#8f8f8f",
        "faint": "#3d3d3d",
        "line": "#2a2a2a",
        "accent": "#a898ff",
    },
    "light": {
        "panel": "#fbfbfb",
        "edge": "#e4e4e4",
        "fg": "#0d0d0d",
        "mute": "#6a6a6a",
        "faint": "#c9c9c9",
        "line": "#e2e2e2",
        "accent": "#5a3fe0",
    },
}


def svg(w, h, body, label, aspect=None):
    from html import escape
    par = f' preserveAspectRatio="{aspect}"' if aspect else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"{par} '
            f'role="img" aria-label="{escape(label, quote=True)}"><title>{escape(label)}</title>{body}</svg>\n')
