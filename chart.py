"""BTC 24h chart (Binance USDT-M perpetual, 15m candles) on Times Gate screen 4, every 5 minutes.

Usage: python chart.py <device-ip>   (Ctrl+C to stop)
"""
import sys
import time

import requests
from PIL import Image, ImageDraw, ImageFont

from hello import SIZE, send
from prices import fmt

SCREEN = 4
EVERY = 5 * 60
TOP, BOTTOM, LEFT, RIGHT = 44, 122, 4, SIZE - 4  # chart area
GREEN, RED = ("#22c55e", "#0b3d1d"), ("#ef4444", "#4a1212")  # (line, fill under line)


def fetch():
    """(open of the first candle, closes) for the last 24h."""
    r = requests.get("https://fapi.binance.com/fapi/v1/klines",
                     params={"symbol": "BTCUSDT", "interval": "15m", "limit": 96}, timeout=15)
    r.raise_for_status()
    candles = r.json()
    return float(candles[0][1]), [float(c[4]) for c in candles]


def points(values):
    """Map values to (x, y) inside the chart area; max at TOP, min at BOTTOM."""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1  # flat series: draw along the bottom
    step = (RIGHT - LEFT) / max(len(values) - 1, 1)
    return [(LEFT + i * step, BOTTOM - (v - lo) / span * (BOTTOM - TOP)) for i, v in enumerate(values)]


def render(first_open, closes):
    img = Image.new("RGB", (SIZE, SIZE), "black")
    d = ImageDraw.Draw(img)
    small, big = ImageFont.load_default(size=12), ImageFont.load_default(size=19)
    change = (closes[-1] / first_open - 1) * 100
    line, fill = GREEN if change >= 0 else RED
    d.text((6, 10), "BTC 24h", fill="#8a8a8a", font=small, anchor="lm")
    d.text((SIZE - 6, 10), f"{change:+.1f}%", fill=line, font=small, anchor="rm")
    d.text((SIZE // 2, 29), fmt(closes[-1]), fill="white", font=big, anchor="mm")
    pts = points(closes)
    d.polygon(pts + [(RIGHT, BOTTOM), (LEFT, BOTTOM)], fill=fill)
    d.line(pts, fill=line, width=2)
    return img


def main(ip):
    while True:
        try:
            send(ip, SCREEN, render(*fetch()))
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError, RuntimeError) as e:
            print(f"{time.strftime('%H:%M:%S')} update failed: {e}")
        time.sleep(EVERY)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        main(sys.argv[1])
    except KeyboardInterrupt:
        pass
