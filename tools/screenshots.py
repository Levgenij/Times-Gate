"""Render docs/screens.png: the five default screens in English, from made-up sample data (no network, no accounts).

    python tools/screenshots.py
"""
import logging
import math
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

from timesgate.i18n import WORDS  # noqa: E402
from timesgate.render import SIZE, Theme  # noqa: E402
from timesgate.widgets import REGISTRY  # noqa: E402
from timesgate.widgets.gcalendar import Item, order, pick  # noqa: E402

logging.disable(logging.WARNING)  # "no token" warnings of the Google widgets: the sample data needs none
SCALE, GAP, PAD = 2, 18, 28
NOW = datetime(2026, 11, 5, 12, 10).astimezone()  # Thursday


def widget(kind, **opts):
    ctx = SimpleNamespace(theme=Theme(), root=Path(tempfile.gettempdir()), words=WORDS["en"])
    return REGISTRY[kind](ctx, **opts)


def calendar():
    day, at = NOW.date(), lambda h, m=0, d=0: NOW.replace(hour=h, minute=m) + timedelta(days=d)
    items = [Item(at(9), at(9, 30), "Daily stand-up", False),
             Item(at(11, 45), at(12, 40), "Design review", False),
             Item(day + timedelta(days=1), day + timedelta(days=2), "Pay the internet bill", True, True),
             Item(at(19, 0), at(20, 0), "Dinner with Anna", False),
             Item(None, None, "Fix the kitchen tap", True, True)]
    w = widget("calendar")
    return w.render(*pick(sorted(items, key=order), NOW, 4, 1), NOW)


def rates():
    w = widget("rates")
    data = {"exchangeRate": [{"currency": "USD", "purchaseRate": 41.35, "saleRate": 41.9},
                             {"currency": "EUR", "purchaseRate": 47.8, "saleRate": 48.55}]}
    with patch.object(w, "get_json", return_value=data), patch("time.strftime", return_value="05.11.2026"):
        return w.frames()[0]


def clock():
    return widget("clock").render(time.strptime("2026-11-05 12:10", "%Y-%m-%d %H:%M"))


def chart():
    w = widget("chart")
    closes = [96800 + 900 * math.sin(i / 9) + i * 22 for i in range(96)]
    candles = [[0, str(closes[0] - 300), 0, 0, str(c)] for c in closes]
    with patch.object(w, "get_json", return_value=candles):
        return w.frames()[0]


def weather():
    return widget("weather").render(12.6, 2, True, 14, 8, [(4, 61, 13, 7), (5, 0, 15, 6)])


def main():
    shots = [calendar(), rates(), clock(), chart(), weather()]
    side = SIZE * SCALE
    w, h = PAD * 2 + len(shots) * side + (len(shots) - 1) * GAP, PAD * 2 + side
    img = Image.new("RGB", (w, h), "#0c0e11")
    ImageDraw.Draw(img).rounded_rectangle([4, 4, w - 5, h - 5], radius=22, fill="#16191e", outline="#262b33")
    for i, shot in enumerate(shots):
        img.paste(shot.resize((side, side), Image.Resampling.NEAREST), (PAD + i * (side + GAP), PAD))
    out = ROOT / "docs" / "screens.png"
    out.parent.mkdir(exist_ok=True)
    img.save(out, optimize=True)
    print(out)


if __name__ == "__main__":
    main()
