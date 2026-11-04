import unittest
from unittest.mock import MagicMock, patch

import requests
from PIL import Image

from timesgate.device import Device, DeviceDown, DeviceError


def ok(body=None):
    r = MagicMock()
    r.json.return_value = body if body is not None else {"ReturnCode": 0}
    return r


class DeviceTest(unittest.TestCase):
    def setUp(self):
        patches = [patch("timesgate.device.requests.post", return_value=ok()),
                   patch("timesgate.device.time.sleep"),
                   patch("timesgate.device.time.time", return_value=1_000_000)]
        self.post = patches[0].start()
        for p in patches[1:]:
            p.start()
        for p in patches:
            self.addCleanup(p.stop)
        self.dev = Device("192.168.1.60")
        self.img = Image.new("RGB", (128, 128))

    def payloads(self):
        return [c.kwargs["json"] for c in self.post.call_args_list]

    def test_animation_payload(self):
        self.dev.send(3, [self.img, self.img], speed=500)
        a, b = self.payloads()
        self.assertEqual(self.post.call_args.args[0], "http://192.168.1.60:9000/divoom_api")
        self.assertEqual(a["LcdArray"], [0, 0, 1, 0, 0])
        self.assertEqual((a["PicNum"], a["PicOffset"], b["PicOffset"]), (2, 0, 1))
        self.assertEqual(a["PicID"], b["PicID"])
        self.assertEqual(a["PicSpeed"], 500)

    def test_pic_id_increases_within_the_same_second(self):
        self.dev.send(1, [self.img])
        self.dev.send(2, [self.img])
        first, second = self.payloads()
        self.assertGreater(second["PicID"], first["PicID"])

    def test_rejected(self):
        self.post.return_value = ok({"ReturnCode": 1, "ReturnMessage": "bad"})
        with self.assertRaises(DeviceError):
            self.dev.send(1, [self.img])

    def test_unreachable_backs_off(self):
        self.post.side_effect = requests.ConnectionError("refused")
        with self.assertLogs("timesgate.device", "WARNING"), self.assertRaises(DeviceDown):
            self.dev.send(1, [self.img])
        self.post.reset_mock()
        with self.assertRaises(DeviceDown):
            self.dev.send(1, [self.img])
        self.post.assert_not_called()  # skipped until down_until


if __name__ == "__main__":
    unittest.main()
