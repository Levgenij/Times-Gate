"""PrivatBank USD/EUR to UAH rates on Times Gate screen 2, refreshed every 5 hours.

Usage: python rates.py <device-ip>   (Ctrl+C to stop)
"""
import sys
import time

import requests
from PIL import Image, ImageDraw, ImageFont

from hello import SIZE, send

SCREEN = 2
URL = "https://api.privatbank.ua/p24api/exchange_rates"
EVERY = 5 * 3600
RETRY = 5 * 60  # after a failure, don't leave the screen stale for 5 hours
CURRENCIES = ("USD", "EUR")


def parse(data):
    """{'USD': (buy, sell), ...} or None if the day has no bank rates yet."""
    rows = {r["currency"]: r for r in data.get("exchangeRate", [])}
    if not all("saleRate" in rows.get(c, {}) for c in CURRENCIES):
        return None
    return {c: (rows[c]["purchaseRate"], rows[c]["saleRate"]) for c in CURRENCIES}


def fetch():
    """Today's rates; yesterday's if today's aren't published yet."""
    for days_back in (0, 1):
        day = time.strftime("%d.%m.%Y", time.localtime(time.time() - days_back * 86400))
        r = requests.get(f"{URL}?json&date={day}", timeout=15)
        r.raise_for_status()
        rates = parse(r.json())
        if rates:
            return rates, day
    raise RuntimeError("no USD/EUR rates for today or yesterday")


def render(rates, day):
    img = Image.new("RGB", (SIZE, SIZE), "black")
    d = ImageDraw.Draw(img)
    small, big = ImageFont.load_default(size=12), ImageFont.load_default(size=19)
    for y, (cur, (buy, sell)) in zip((24, 70), rates.items()):
        d.text((SIZE // 2, y), f"{cur} / UAH", fill="#8a8a8a", font=small, anchor="mm")
        d.text((SIZE // 2, y + 20), f"{buy:.2f}  {sell:.2f}", fill="white", font=big, anchor="mm")
    d.text((SIZE // 2, 118), day, fill="#505050", font=small, anchor="mm")
    return img


def main(ip):
    while True:
        try:
            send(ip, SCREEN, render(*fetch()))
            delay = EVERY
        except (requests.RequestException, ValueError, RuntimeError) as e:
            print(f"{time.strftime('%H:%M:%S')} update failed, retry in {RETRY // 60} min: {e}")
            delay = RETRY
        time.sleep(delay)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        main(sys.argv[1])
    except KeyboardInterrupt:
        pass
