"""Weather in London from Open-Meteo on Times Gate screen 5, every 15 minutes.

Usage: python weather.py <device-ip>   (Ctrl+C to stop)
"""
import sys
import time

import requests
from PIL import Image, ImageDraw, ImageFont

from hello import SIZE, send

SCREEN = 5
EVERY = 15 * 60  # Open-Meteo updates "current" every 15 min
PLACE, LAT, LON = "LONDON", 51.5074, -0.1278
# WMO weather codes -> short label (default font has no Cyrillic)
WMO = [((0,), "Clear"), ((1,), "Mostly clear"), ((2,), "Partly cloudy"), ((3,), "Overcast"),
       ((45, 48), "Fog"), (range(51, 58), "Drizzle"), (range(61, 68), "Rain"), (range(71, 78), "Snow"),
       (range(80, 83), "Showers"), ((85, 86), "Snow showers"), (range(95, 100), "Thunderstorm")]


def describe(code):
    return next((label for codes, label in WMO if code in codes), "")


def fetch():
    r = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": LAT, "longitude": LON, "timezone": "Europe/London", "forecast_days": 1,
        "current": "temperature_2m,weather_code", "daily": "temperature_2m_max,temperature_2m_min"}, timeout=15)
    r.raise_for_status()
    data = r.json()
    cur, day = data["current"], data["daily"]
    return cur["temperature_2m"], cur["weather_code"], day["temperature_2m_max"][0], day["temperature_2m_min"][0]


def render(temp, code, hi, lo):
    img = Image.new("RGB", (SIZE, SIZE), "black")
    d = ImageDraw.Draw(img)
    small, mid, big = (ImageFont.load_default(size=s) for s in (12, 15, 44))
    d.text((SIZE // 2, 12), PLACE, fill="#8a8a8a", font=small, anchor="mm")
    d.text((SIZE // 2, 52), f"{temp:.0f}°", fill="white", font=big, anchor="mm")
    d.text((SIZE // 2, 90), describe(code), fill="white", font=mid, anchor="mm")
    d.text((SIZE // 2, 114), f"{hi:.0f}° / {lo:.0f}°", fill="#8a8a8a", font=small, anchor="mm")
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
