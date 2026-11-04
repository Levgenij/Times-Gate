import unittest
from unittest.mock import MagicMock

from PIL import Image

from helpers import ctx
from timesgate.device import DeviceDown
from timesgate.runner import Slot, next_time
from timesgate.widgets import Widget


class Fake(Widget):
    type = "fake"
    defaults = {"value": None}

    def frames(self):
        if isinstance(self.value, Exception):
            raise self.value
        return None if self.value is None else [Image.new("RGB", (128, 128), self.value)]


def device():
    d = MagicMock()
    d.RETRY, d.down_until = 30, 0
    return d


class SlotTest(unittest.TestCase):
    def test_first_widget_with_frames_wins(self):
        top, fallback = Fake(ctx()), Fake(ctx(), value="red")
        slot = Slot(2, [top, fallback])
        self.assertIs(slot.tick(0)[0], fallback)
        top.value = "blue"
        self.assertIs(slot.tick(100)[0], top)  # both due again after every=60

    def test_unchanged_picture_is_not_resent(self):
        dev = device()
        slot = Slot(1, [Fake(ctx(), value="red")])
        slot.step(dev, now=0)
        slot.step(dev, now=60)
        self.assertEqual(dev.send.call_count, 1)
        slot.widgets[0].value = "blue"
        slot.step(dev, now=120)
        self.assertEqual(dev.send.call_count, 2)

    def test_failure_keeps_last_frames_and_uses_retry(self):
        w = Fake(ctx(), value="red", every=300, retry=10)
        slot = Slot(1, [w])
        slot.tick(0)
        w.value = RuntimeError("api down")
        with self.assertLogs("timesgate.runner", "WARNING"):
            _, frames = slot.tick(300)
        self.assertIsNotNone(frames)
        self.assertEqual(slot.due[0], 310)

    def test_device_down_retries_send_soon(self):
        dev = device()
        dev.send.side_effect = DeviceDown("x")
        dev.down_until = 30
        slot = Slot(1, [Fake(ctx(), value="red", every=3600)])
        self.assertEqual(slot.step(dev, now=0), 30)  # not an hour
        dev.send.side_effect = None
        slot.step(dev, now=30)
        self.assertEqual(dev.send.call_count, 2)

    def test_align(self):
        self.assertEqual(next_time(125.5, 60, True), 180)
        self.assertEqual(next_time(125.5, 60, False), 185.5)


if __name__ == "__main__":
    unittest.main()
