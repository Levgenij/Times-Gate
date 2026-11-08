import socket
import struct
import threading
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from helpers import ctx
from timesgate.device import Device, DeviceDown
from timesgate.runner import WAIT_STEP, Runner, Slot, next_time
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


class SleepTest(unittest.TestCase):
    """After the PC sleeps: screens catch up with the wall clock and dead connections don't cost a refresh."""

    def test_screen_refreshes_soon_after_wake(self):
        clock = [1000.0]
        widget = Fake(ctx(), value="red", every=900)
        widget.frames = MagicMock(wraps=widget.frames)
        stop = MagicMock()
        stop.is_set.side_effect = lambda: widget.frames.call_count >= 2

        def wait(seconds):  # the PC sleeps 8 h during the first wait; Windows' timer would not count it
            self.assertLessEqual(seconds, WAIT_STEP)
            clock[0] += 8 * 3600 if clock[0] == 1000.0 else seconds
        stop.wait.side_effect = wait
        with patch("timesgate.runner.time.time", side_effect=lambda: clock[0]):
            Slot(1, [widget]).run(device(), stop)
        self.assertEqual(widget.frames.call_count, 2)
        self.assertEqual(stop.wait.call_count, 1)  # refreshed right after the first short wait, not 900 s later

    def test_sleep_hands_back_and_wake_redraws(self):
        dev = Device("192.168.1.60", on_exit={"Command": "Clock"})
        dev.command = MagicMock(return_value={"ReturnCode": 0})
        slot = Slot(1, [Fake(ctx(), value="red", every=900)])  # next refresh in 15 min: the wait must not hide resume
        runner = Runner()
        runner.cfg = MagicMock(device=dev, slots=[slot])
        stop = threading.Event()
        self.addCleanup(stop.set)

        def calls(n, tries=200):  # wait (at most tries x 0.01 s) until the device got `n` commands
            for _ in range(tries):
                if dev.command.call_count >= n:
                    break
                stop.wait(0.01)
            return dev.command.call_count
        with patch("timesgate.runner.WAIT_STEP", 0.01):
            threading.Thread(target=slot.run, args=(dev, stop), daemon=True).start()
            self.assertEqual(calls(1), 1)  # the frame
            runner.suspend()
            self.assertEqual(dev.command.call_args.args[0], {"Command": "Clock"})
            slot.due = [0.0]  # a widget due while asleep must not draw over on_exit
            self.assertEqual(calls(3, tries=20), 2)  # 0.2 s: the slot checks every 0.01 s
            runner.resume()  # the same picture as before sleep, but the device shows on_exit: send it again
            self.assertEqual(calls(3), 3)
        self.assertEqual(dev.command.call_args.args[0]["Command"], "Draw/SendHttpGif")

    def test_dropped_connection_is_retried(self):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen()
        self.addCleanup(server.close)

        def serve():
            conn, _ = server.accept()  # 1st: reset, like a kept-alive connection after the PC slept
            conn.recv(4096)
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            conn.close()
            conn, _ = server.accept()  # 2nd: a normal answer
            conn.recv(4096)
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 12\r\n"
                         b"Connection: close\r\n\r\n{\"ok\": true}")
            conn.close()
        threading.Thread(target=serve, daemon=True).start()
        self.assertEqual(Fake(ctx()).get_json(f"http://127.0.0.1:{server.getsockname()[1]}/"), {"ok": True})


if __name__ == "__main__":
    unittest.main()
