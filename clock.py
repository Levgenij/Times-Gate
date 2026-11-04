"""24-hour digital clock on the centre Times Gate screen (3 of 5).

Usage: python clock.py <device-ip>   (Ctrl+C to stop)
"""
import sys
import time

import requests

from hello import render, send

SCREEN = 3  # centre of 5


def main(ip):
    while True:
        try:
            send(ip, SCREEN, render(time.strftime("%H:%M"), size=42))
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
