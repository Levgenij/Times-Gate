"""Show "Hello World" on one Divoom Times Gate screen.

Usage: python hello.py <device-ip> [screen 1-5]
"""
import base64
import io
import sys
import time

import requests
from PIL import Image, ImageDraw, ImageFont

SIZE = 128  # each of the 5 Times Gate panels is 128x128


def render(text, size=22):
    img = Image.new("RGB", (SIZE, SIZE), "black")
    font = ImageFont.load_default(size=size)
    ImageDraw.Draw(img).multiline_text((SIZE // 2, SIZE // 2), text, fill="white",
                                       font=font, anchor="mm", align="center")
    return img


def send(ip, screen, img):
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    payload = {
        "Command": "Draw/SendHttpGif",
        "LcdArray": [int(i == screen - 1) for i in range(5)],
        "PicNum": 1, "PicOffset": 0,
        "PicID": int(time.time()),  # must increase between uploads
        "PicSpeed": 100, "PicWidth": SIZE,
        "PicData": base64.b64encode(buf.getvalue()).decode("ascii"),
    }
    # Current Times Gate firmware: port 80 closed, API on :9000/divoom_api (reference used :80/post).
    r = requests.post(f"http://{ip}:9000/divoom_api", json=payload, timeout=10)
    r.raise_for_status()
    body = r.json()
    if body.get("ReturnCode", body.get("error_code")) not in (0, "0"):
        raise RuntimeError(f"Device rejected frame: {body}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    screen = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    if screen not in range(1, 6):
        sys.exit("screen must be 1-5")
    send(sys.argv[1], screen, render("Hello\nWorld"))
    print(f"Sent to {sys.argv[1]}, screen {screen}")
