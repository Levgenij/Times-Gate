"""Screen 2: UAH rates, switched to the Gmail unread count when new mail arrives.

Checks Gmail every minute. Unread count went up -> show it. Went down or to zero -> back to rates.
Unchanged -> keep what is shown. Rates refresh every 5 hours as in rates.py.

Needs .env next to this file (see .env.example) with a Google app password.
Usage: python gmail.py <device-ip>   (Ctrl+C to stop)
"""
import imaplib
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

import rates
from hello import SIZE, send

SCREEN = 2
CHECK = 60
# Pillow's default font has no Cyrillic.
# shortcut: Windows-only system font, bundle a .ttf in the repo if this must run elsewhere
LABEL_FONT = ImageFont.truetype("segoeui.ttf", 14)


def credentials():
    env = {}
    for line in (Path(__file__).with_name(".env")).read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env["GMAIL_USER"], env["GMAIL_APP_PASSWORD"].replace(" ", "")


def unread(user, password):
    """Unread messages in INBOX (all Gmail tabs). STATUS does not mark anything as read."""
    with imaplib.IMAP4_SSL("imap.gmail.com", timeout=20) as imap:
        imap.login(user, password)
        _, data = imap.status("INBOX", "(UNSEEN)")
    return int(data[0].split(b"UNSEEN")[1].strip(b" )"))


def decide(prev, count, mode):
    """'mail' when the unread count grows, 'rates' when it drops or hits zero, else unchanged."""
    if count > prev:
        return "mail"
    if count < prev or count == 0:
        return "rates"
    return mode


def render_mail(count):
    img = Image.new("RGB", (SIZE, SIZE), "black")
    d = ImageDraw.Draw(img)
    d.text((SIZE // 2, 16), "Gmail", fill="#8a8a8a", font=ImageFont.load_default(size=13), anchor="mm")
    d.text((SIZE // 2, 62), str(count), fill="white", font=ImageFont.load_default(size=52), anchor="mm")
    d.text((SIZE // 2, 106), "непрочитаних", fill="#8a8a8a", font=LABEL_FONT, anchor="mm")
    return img


def main(ip):
    user, password = credentials()
    prev, mode = unread(user, password), "rates"  # fail fast on bad credentials
    mode = decide(0, prev, mode)
    rates_img, rates_due, shown = None, 0, None
    while True:
        if time.time() >= rates_due:
            try:
                rates_img = rates.render(*rates.fetch())
                rates_due = time.time() + rates.EVERY
            except (requests.RequestException, ValueError, RuntimeError) as e:
                print(f"{time.strftime('%H:%M:%S')} rates failed, retry in {rates.RETRY // 60} min: {e}")
                rates_due = time.time() + rates.RETRY
        img = render_mail(prev) if mode == "mail" else rates_img
        if img is not None and img.tobytes() != shown:  # send only when the picture changes
            try:
                send(ip, SCREEN, img)
                shown = img.tobytes()
            except (requests.RequestException, RuntimeError) as e:
                print(f"{time.strftime('%H:%M:%S')} send failed: {e}")
        time.sleep(CHECK)
        try:
            count = unread(user, password)
            mode, prev = decide(prev, count, mode), count
        except (OSError, imaplib.IMAP4.error) as e:  # keep the current screen
            print(f"{time.strftime('%H:%M:%S')} gmail check failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        main(sys.argv[1])
    except KeyboardInterrupt:
        pass
