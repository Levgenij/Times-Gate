"""BTC / ALCH / SPY / BSB prices (Binance USDT-M perpetuals) on Times Gate screen 1, every 5 minutes.

Usage: python prices.py <device-ip>   (Ctrl+C to stop)
"""
import sys
import time

import requests
from PIL import Image, ImageDraw, ImageFont

from hello import SIZE, send

SCREEN = 1
EVERY = 5 * 60
ORDER = ("BTC", "ALCH", "SPY", "BSB")  # only ALCH/SPY/BSB all exist as futures, not spot


def fetch():
    """{'BTC': 80055.5, ...}; a ticker missing on Binance is left out (shown as --)."""
    r = requests.get("https://fapi.binance.com/fapi/v1/ticker/price", timeout=15)
    r.raise_for_status()
    all_prices = {p["symbol"]: float(p["price"]) for p in r.json()}
    return {t: all_prices[t + "USDT"] for t in ORDER if t + "USDT" in all_prices}


def fmt(price):
    if price is None:
        return "--"  # default font has no em dash glyph
    if price >= 1000:
        return f"{price:,.0f}"
    if price >= 1:
        return f"{price:.2f}"
    return f"{price:.4g}"


def render(prices):
    img = Image.new("RGB", (SIZE, SIZE), "black")
    d = ImageDraw.Draw(img)
    small, big = ImageFont.load_default(size=12), ImageFont.load_default(size=17)
    for y, ticker in zip((14, 41, 68, 95), ORDER):
        d.text((6, y), ticker, fill="#8a8a8a", font=small, anchor="lm")
        d.text((SIZE - 6, y), fmt(prices.get(ticker)), fill="white", font=big, anchor="rm")
    d.text((SIZE // 2, 118), time.strftime("%H:%M"), fill="#505050", font=small, anchor="mm")
    return img


def main(ip):
    while True:
        try:  # on failure keep the last good screen; the HH:MM footer shows its age
            send(ip, SCREEN, render(fetch()))
        except (requests.RequestException, ValueError, KeyError, TypeError, RuntimeError) as e:
            print(f"{time.strftime('%H:%M:%S')} update failed: {e}")
        time.sleep(EVERY)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        main(sys.argv[1])
    except KeyboardInterrupt:
        pass
