"""Shared drawing helpers: theme colours, per-thread font cache, 128x128 canvas."""
import threading
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

SIZE = 128  # each of the 5 Times Gate panels is 128x128
WEEKDAYS = ["Пон", "Вів", "Сер", "Чет", "П’ят", "Суб", "Нед"]  # Monday first; needs theme.cyrillic_font


@dataclass(frozen=True)
class Theme:
    background: str = "#000000"
    text: str = "#ffffff"
    muted: str = "#8a8a8a"
    dim: str = "#505050"
    up: str = "#22c55e"
    down: str = "#ef4444"
    up_fill: str = "#0b3d1d"
    down_fill: str = "#4a1212"
    # Pillow's default font has no Cyrillic. Segoe UI ships with Windows; elsewhere point this at any Cyrillic .ttf.
    cyrillic_font: str = "segoeui.ttf"


_local = threading.local()  # FreeType font objects are not shared between slot threads


def font(size, path=None):
    """Pillow's default font, or the .ttf at `path`, loaded once per thread and size."""
    cache = _local.__dict__.setdefault("fonts", {})
    if (size, path) not in cache:
        cache[size, path] = ImageFont.truetype(path, size) if path else ImageFont.load_default(size=size)
    return cache[size, path]


def canvas(theme):
    img = Image.new("RGB", (SIZE, SIZE), theme.background)
    return img, ImageDraw.Draw(img)


def fit(text, f, width):
    """`text` cut to at most `width` pixels in font `f`, ending with "…" when cut."""
    if f.getlength(text) <= width:
        return text
    while text and f.getlength(text + "…") > width:
        text = text[:-1]
    return text.rstrip() + "…"


def fmt(price):
    """Price with precision that fits the screen: 79,920 / 767.50 / 0.0382."""
    if price is None:
        return "--"  # default font has no em dash glyph
    if price >= 1000:
        return f"{price:,.0f}"
    if price >= 1:
        return f"{price:.2f}"
    return f"{price:.4g}"
