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


def render(text):
    img = Image.new("RGB", (SIZE, SIZE), "black")
    font = ImageFont.load_default(size=22)
    ImageDraw.Draw(img).multiline_text((SIZE // 2, SIZE // 2), text, fill="white",
                                       font=font, anchor="mm", align="center")
    return img


def send(ip, screen, *frames, speed=100):
    """Upload one image, or several as an animation the device loops (speed = ms per frame).

    The device may briefly show a "loading" hourglass while receiving, even for one frame,
    so send as rarely as possible.
    """
    pic_id = int(time.time())  # must increase between uploads; shared by all frames of one animation
    for offset, img in enumerate(frames):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        payload = {
            "Command": "Draw/SendHttpGif",
            "LcdArray": [int(i == screen - 1) for i in range(5)],
            "PicNum": len(frames), "PicOffset": offset, "PicID": pic_id,
            "PicSpeed": speed, "PicWidth": SIZE,
            "PicData": base64.b64encode(buf.getvalue()).decode("ascii"),
        }
        # Current Times Gate firmware: port 80 closed, API on :9000/divoom_api (reference used :80/post).
        r = requests.post(f"http://{ip}:9000/divoom_api", json=payload, timeout=10)
        r.raise_for_status()
        body = r.json()
        if body.get("ReturnCode", body.get("error_code")) not in (0, "0"):
            raise RuntimeError(f"Device rejected frame {offset + 1}: {body}")
        if offset < len(frames) - 1:
            time.sleep(0.1)  # reference app paces multi-frame uploads


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    screen = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    if screen not in range(1, 6):
        sys.exit("screen must be 1-5")
    send(sys.argv[1], screen, render("Hello\nWorld"))
    print(f"Sent to {sys.argv[1]}, screen {screen}")
