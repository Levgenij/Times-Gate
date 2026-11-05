"""Small, muted weather icons drawn with Pillow primitives (no image assets).

Drawn 4x larger and scaled down, which gives smooth anti-aliased edges on the 128x128 panel.
"""
import math

from PIL import Image, ImageDraw

S = 4  # supersampling factor
CLEAR = (0, 0, 0, 0)
COLORS = {
    "sun": "#e8b04b", "moon": "#d9d4c0", "cloud": "#b8bec6", "dark": "#7d848c",
    "rain": "#5b9bd5", "snow": "#e6eef5", "bolt": "#e8b04b", "fog": "#8a9099",
}
KINDS = ("clear", "mostly_clear", "partly", "overcast", "fog", "drizzle", "rain", "showers", "snow", "thunder")


def _box(cx, cy, r):
    return [(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S]


def _sun(d, cx, cy, r):
    for i in range(8):
        a = math.pi / 4 * i
        d.line([((cx + math.cos(a) * (r + 2.5)) * S, (cy + math.sin(a) * (r + 2.5)) * S),
                ((cx + math.cos(a) * (r + 6)) * S, (cy + math.sin(a) * (r + 6)) * S)],
               fill=COLORS["sun"], width=int(2 * S))
    d.ellipse(_box(cx, cy, r), fill=COLORS["sun"])


def _moon(d, cx, cy, r):
    d.ellipse(_box(cx, cy, r), fill=COLORS["moon"])
    d.ellipse(_box(cx + r * 0.55, cy - r * 0.35, r * 0.85), fill=CLEAR)  # bite out -> crescent


def _cloud(d, x, y, w, color, gap=0.0):
    """Cloud with flat bottom; top-left at (x, y), width w. gap > 0 first erases a margin around it."""
    for m, fill in ((gap, CLEAR), (0, color)) if gap else ((0, color),):
        d.rounded_rectangle([(x - m) * S, (y + 0.36 * w - m) * S, (x + w + m) * S, (y + 0.64 * w + m) * S],
                            radius=(0.14 * w + m) * S, fill=fill)
        d.ellipse(_box(x + 0.32 * w, y + 0.38 * w, 0.2 * w + m), fill=fill)
        d.ellipse(_box(x + 0.62 * w, y + 0.3 * w, 0.26 * w + m), fill=fill)


def _drops(d, xs, y, length, color, width=2.0):
    for x in xs:
        d.line([(x * S, y * S), ((x - length * 0.35) * S, (y + length) * S)], fill=color, width=int(width * S))


def _dots(d, xs, y, r, color):
    for i, x in enumerate(xs):
        d.ellipse(_box(x, y + (i % 2) * 4, r), fill=color)


def draw(kind, day=True, size=48):
    """RGBA icon `size` x `size` for one of KINDS."""
    img = Image.new("RGBA", (48 * S, 48 * S), CLEAR)
    d = ImageDraw.Draw(img)
    sky = _sun if day else _moon
    if kind == "clear":
        sky(d, 24, 24, 10 if day else 13)
    elif kind in ("mostly_clear", "partly"):
        sky(d, 17, 17, 8 if day else 10)
        w = 26 if kind == "mostly_clear" else 34
        _cloud(d, 46 - w - 2, 42 - 0.64 * w, w, COLORS["cloud"], gap=2)
    elif kind == "overcast":
        _cloud(d, 4, 6, 30, COLORS["dark"])
        _cloud(d, 10, 16, 34, COLORS["cloud"], gap=2)
    elif kind == "fog":
        for i, (x0, x1) in enumerate(((8, 40), (4, 36), (12, 44), (8, 34))):
            y = 14 + i * 7
            d.rounded_rectangle([x0 * S, y * S, x1 * S, (y + 3) * S], radius=1.5 * S, fill=COLORS["fog"])
    else:  # precipitation: cloud on top, something falling below
        if kind == "showers":
            sky(d, 15, 12, 7 if day else 8)
            _cloud(d, 8, 4, 34, COLORS["cloud"], gap=2)
        else:
            _cloud(d, 7, 2, 34, COLORS["dark"] if kind == "thunder" else COLORS["cloud"])
        if kind in ("rain", "showers"):
            _drops(d, (17, 25, 33), 29, 9, COLORS["rain"])
        elif kind == "drizzle":
            _drops(d, (17, 25, 33), 31, 4, COLORS["rain"])
        elif kind == "snow":
            _dots(d, (16, 24, 32), 32, 2.2, COLORS["snow"])
        elif kind == "thunder":
            d.polygon([(p[0] * S, p[1] * S) for p in ((26, 24), (19, 35), (24, 35), (21, 45), (31, 31), (25, 31), (28, 24))],
                      fill=COLORS["bolt"])
    return img.resize((size, size), Image.Resampling.LANCZOS)
