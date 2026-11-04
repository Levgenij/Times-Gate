"""24-hour digital clock with blinking colon on the centre Times Gate screen (3 of 5).

Usage: python clock.py <device-ip>   (Ctrl+C to stop)
"""
import sys
import time

import requests
from PIL import Image, ImageDraw, ImageFont

from hello import SIZE, send

SCREEN = 3  # centre of 5
DAYS = ("Пон", "Вів", "Сер", "Чет", "П’ят", "Суб", "Нед")  # tm_wday: Monday = 0
# Pillow's default font has no Cyrillic.
# shortcut: Windows-only system font, bundle a .ttf in the repo if this must run elsewhere
DATE_FONT = ImageFont.truetype("segoeui.ttf", 14)


TIME_FONT = ImageFont.load_default(size=42)


def render(now, colon=True):
    img = Image.new("RGB", (SIZE, SIZE), "black")
    d = ImageDraw.Draw(img)
    # digits are placed around a fixed colon slot so they don't move when the colon is hidden
    c, y, gap = SIZE // 2, 56, TIME_FONT.getlength(":") / 2
    d.text((c - gap, y), time.strftime("%H", now), fill="white", font=TIME_FONT, anchor="rm")
    d.text((c + gap, y), time.strftime("%M", now), fill="white", font=TIME_FONT, anchor="lm")
    if colon:
        d.text((c, y), ":", fill="white", font=TIME_FONT, anchor="mm")
    d.text((SIZE // 2, 92), f"{DAYS[now.tm_wday]} {time.strftime('%d.%m', now)}", fill="#8a8a8a",
           font=DATE_FONT, anchor="mm")
    return img


def main(ip):
    # Once a minute, a 2-frame loop the device plays itself: colon on 0.5 s, off 0.5 s.
    # Sending a frame every second instead still showed the device's "loading" icon at times.
    while True:
        try:
            now = time.localtime()
            send(ip, SCREEN, render(now), render(now, colon=False), speed=500)
        except (requests.RequestException, RuntimeError) as e:
            print(f"{time.strftime('%H:%M:%S')} send failed, retry next minute: {e}")
        time.sleep(60 - time.time() % 60)  # wake at the start of the next minute


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        main(sys.argv[1])
    except KeyboardInterrupt:
        pass
