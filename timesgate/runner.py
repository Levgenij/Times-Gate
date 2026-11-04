"""Slot scheduling: each slot runs its widgets on their intervals and shows the first one that has frames."""
import hashlib
import logging
import signal
import sys
import threading
import time

from .device import DeviceDown, DeviceError

log = logging.getLogger("timesgate.runner")


def digest(frames, speed):
    h = hashlib.blake2b(str(speed).encode(), digest_size=16)
    for img in frames:
        h.update(img.tobytes())
    return h.digest()


def next_time(now, delay, align):
    return now - now % delay + delay if align else now + delay


class Slot:
    def __init__(self, number, widgets):
        self.number, self.widgets = number, widgets
        self.results = [None] * len(widgets)  # last frames each widget returned
        self.due = [0.0] * len(widgets)
        self.shown = None  # digest of what the device shows on this slot

    def tick(self, now):
        """Run due widgets; return (widget, frames) of the highest-priority widget with frames, or (None, None)."""
        for i, w in enumerate(self.widgets):
            if now < self.due[i]:
                continue
            try:
                self.results[i] = w.frames()
                delay = w.every
            # Long-running display: an API change or outage in one widget must not kill the slot.
            except Exception as e:
                log.warning("slot %d %s: %s (keeping last frames)", self.number, w.type, e)
                delay = w.retry or w.every
            self.due[i] = next_time(now, delay, w.align)
        return next(((w, r) for w, r in zip(self.widgets, self.results) if r), (None, None))

    def step(self, device, now=None):
        """One scheduling round; sends only if the picture changed. Returns when to run again."""
        now = time.time() if now is None else now
        widget, frames = self.tick(now)
        wake = min(self.due)
        if frames:
            key = digest(frames, widget.speed)
            if key != self.shown:
                try:
                    device.send(self.number, frames, widget.speed)
                    self.shown = key
                    log.debug("slot %d: sent %s (%d frame(s))", self.number, widget.type, len(frames))
                except DeviceDown:  # logged once by Device
                    wake = min(wake, device.down_until)
                except DeviceError as e:
                    log.warning("slot %d %s: %s", self.number, widget.type, e)
                    wake = min(wake, now + device.RETRY)
        return wake

    def run(self, device, stop):
        while not stop.is_set():
            try:
                wake = self.step(device)
            except Exception:  # a bug here must not silently freeze one screen
                log.exception("slot %d crashed, restarting in 30 s", self.number)
                wake = time.time() + 30
            stop.wait(max(0.0, wake - time.time()))


_console_handler = None  # must stay referenced, or ctypes frees the callback


def on_console_close(callback):
    """Windows: call `callback` when the console window is closed; Windows waits ~5 s, then kills the process.

    Logoff / shutdown events never arrive: Windows skips them for processes that load user32/gdi32 (Pillow does).
    Ctrl+C is not handled here (it raises KeyboardInterrupt).
    """
    global _console_handler
    if sys.platform != "win32":
        return
    import ctypes

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
    def handler(event):
        if event == 2:  # CTRL_CLOSE_EVENT
            callback()
        return False  # continue with the default handling

    _console_handler = handler
    ctypes.windll.kernel32.SetConsoleCtrlHandler(handler, True)


def run(slots, device):
    stop = threading.Event()
    threads = [threading.Thread(target=s.run, args=(device, stop), name=f"slot{s.number}", daemon=True)
               for s in slots]
    for t in threads:
        t.start()
    on_console_close(lambda: (stop.set(), device.close()))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # e.g. systemd stop on a Pi -> finally below
    log.info("running slots %s on %s", ", ".join(str(s.number) for s in slots), device.url)
    try:
        while any(t.is_alive() for t in threads):
            stop.wait(1)  # short waits keep Ctrl+C responsive on Windows
    except KeyboardInterrupt:
        log.info("stopping")
    finally:
        stop.set()
        device.close()
