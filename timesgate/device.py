"""Times Gate local HTTP API: one sender for all slots."""
import base64
import io
import ipaddress
import logging
import threading
import time

import requests

log = logging.getLogger("timesgate.device")


class DeviceError(RuntimeError):
    """The device rejected a command or answered garbage."""


class DeviceDown(DeviceError):
    """The device is unreachable; sends are skipped until `Device.down_until`."""


class Device:
    RETRY = 30  # seconds to wait after the device stops answering

    def __init__(self, ip, port=9000, path="/divoom_api", timeout=10, jpeg_quality=90):
        ipaddress.IPv4Address(ip)  # ValueError on a typo
        # Current Times Gate firmware: API on :9000/divoom_api (the reference repo used :80/post).
        self.url = f"http://{ip}:{port}{path}"
        self.timeout, self.quality = timeout, jpeg_quality
        self._lock = threading.Lock()  # one upload at a time; frames of an animation must not interleave
        self._last_id = 0
        self.down_until = 0  # 0 = reachable

    def command(self, payload):
        # Plain requests.post on purpose: the reference keeps one request per connection with this device.
        r = requests.post(self.url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        try:
            body = r.json()
        except ValueError as e:
            raise DeviceError(f"{payload['Command']}: not JSON: {r.text[:100]!r}") from e
        if not isinstance(body, dict) or body.get("ReturnCode", body.get("error_code")) not in (0, "0"):
            raise DeviceError(f"{payload['Command']} rejected: {body}")
        return body

    def send(self, slot, frames, speed=100):
        """Show one image, or several as an animation the device loops (`speed` ms per frame), on slot 1-5.

        The device may briefly show a "loading" hourglass while receiving, so callers send only on change.
        """
        with self._lock:
            if time.time() < self.down_until:
                raise DeviceDown("device unreachable")
            # Must increase between uploads, also across slots sending within the same second.
            self._last_id = pic_id = max(int(time.time()), self._last_id + 1)
            try:
                for offset, img in enumerate(frames):
                    buf = io.BytesIO()
                    img.save(buf, "JPEG", quality=self.quality)
                    self.command({
                        "Command": "Draw/SendHttpGif",
                        "LcdArray": [int(i == slot - 1) for i in range(5)],
                        "PicNum": len(frames), "PicOffset": offset, "PicID": pic_id,
                        "PicSpeed": speed, "PicWidth": img.width,
                        "PicData": base64.b64encode(buf.getvalue()).decode("ascii"),
                    })
                    if offset < len(frames) - 1:
                        time.sleep(0.1)  # reference app paces multi-frame uploads
            except requests.RequestException as e:
                if not self.down_until:
                    log.warning("device unreachable, retrying every %d s: %s", self.RETRY, e)
                self.down_until = time.time() + self.RETRY
                raise DeviceDown(str(e)) from e
            if self.down_until:
                log.warning("device reachable again")
                self.down_until = 0
